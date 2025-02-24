import re
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import uuid
import queue
import threading
import time
from django.utils import timezone

from .llm_processor import get_relevance_score, classify_link_type
from .models import Link, Crawler
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# Global dictionary to track active crawlers
active_crawlers = {}

class WebScraper:
    def __init__(self, keyword, user):
        self.keyword = keyword
        self.user = user
        self.crawler = None  # Initialize to None, we'll create it in crawl()
    
    def crawl(self, url, max_depth=3, max_workers=50):
        # Create the crawler model with proper UUID
        self.crawler_model = Crawler.objects.create(
            url=url,
            keyword=self.keyword,
            user=self.user,
            max_depth=max_depth,
            is_running=True
        )
        
        self.crawler_id = self.crawler_model.id  # Store the UUID
        self.ua = UserAgent()
        self.all_links = set()
        self.stop_requested = False
        self.is_running = True

        # Register this crawler in the global dictionary
        active_crawlers[str(self.crawler_id)] = self

    def _get_headers(self):
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'DNT': '1',
        }

    def fetch_page(self, url: str) -> str:
        try:
            scraper = cloudscraper.create_scraper(browser='chrome')
            headers = self._get_headers()
            logger.debug(f"Sending request to {url}")
            response = scraper.get(url, headers=headers)
            if response.status_code == 200:
                logger.debug(f"Page loaded successfully: {url}")
                return response.text
            else:
                raise Exception(f"Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return ""

    def parse_links(self, html: str, base_url: str) -> list:
        """
        Extracts links from the page, handling relative URLs and cases where href is "javascript:void(0)".
        Attempts to get URL from alternative attributes if needed.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            logger.error(f"Error parsing HTML with html.parser: {e}. Trying lxml...", exc_info=True)
            try:
                soup = BeautifulSoup(html, "lxml")
            except Exception as e2:
                logger.error(f"Error parsing HTML with lxml: {e2}", exc_info=True)
                return []  # If both fail, return empty list
        
        links = []
    
        for a in soup.find_all("a", href=True):
            href = a.get("href").strip()
            link_text = a.get_text(strip=True)

            # If href is "javascript:void(0)" or similar, try alternative attributes
            if href.lower().startswith("javascript:"):
                href_alternatives = [a.get("data-href"), a.get("data-url"), a.get("onclick")]
                for alt in href_alternatives:
                    if alt:
                        if "onclick" in a.attrs and alt == a.get("onclick"):
                            match = re.search(r"(https?://[^\s'\"]+)", alt)
                            if match:
                                href = match.group(1)
                                break
                        else:
                            href = alt.strip()
                            if not href.lower().startswith("javascript:"):
                                break

            if not href or href.lower().startswith("javascript:"):
                logger.debug(f"Ignored link (invalid href): {href} | Text: {link_text}")
                continue

            full_url = urljoin(base_url, href)
            links.append({"url": full_url, "text": link_text})
        logger.info(f"{len(links)} links extracted from page {base_url}.")
        return links

    def process_link(self, link: dict):
        try:
            text = link.get("text", "")
            url = link.get("url", "")
            score = float(get_relevance_score(text, self.keyword))
            link_type = classify_link_type(text)
            metadata = {"text": text}
            
            if not isinstance(url, str) or not isinstance(link_type, str):
                logger.error(f"Invalid data types for URL or link_type: {url}, {link_type}")
                return
                
            # Use Django ORM to save the link with crawler reference
            Link.objects.update_or_create(
                url=url,
                crawler=self.crawler_model,
                defaults={
                    'type': link_type,
                    'relevance_score': score,
                    'keywords': self.keyword,
                    'metadata': metadata
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing link: {str(e)}")
            return

    def is_internal(self, url: str, base_domain: str) -> bool:
        parsed_url = urlparse(url)
        return parsed_url.netloc == base_domain

    def canonicalize_url(self, url: str) -> str:
        """
        Normalizes the URL by removing query string, fragments, and trailing slashes.
        Only HTTPS scheme URLs are considered.
        """
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return ""
        path = parsed.path if parsed.path == "/" else parsed.path.rstrip("/")
        canonical = parsed._replace(path=path, query="", fragment="").geturl()
        # Optional: remove default ports if present
        if parsed.port:
            if (parsed.scheme == "http" and parsed.port == 80) or (parsed.scheme == "https" and parsed.port == 443):
                canonical = canonical.replace(f":{parsed.port}", "")
        return canonical

    def stop(self):
        """Request the crawler to stop gracefully"""
        logger.info(f"Stop requested for crawler {self.crawler_id}")
        self.stop_requested = True
        
        # Update the crawler model
        if self.crawler_model:
            self.crawler_model.is_running = False
            self.crawler_model.end_time = timezone.now()
            self.crawler_model.save()
            
        return True

    def crawl(self, start_url: str, max_depth: int = 3, max_workers: int = 50):
        """
        Performs crawling using a thread-safe queue and multiple worker threads.
        """
        # Generate a unique ID for this crawler instance
        self.crawler_id = f"{start_url}_{int(time.time())}"
        self.is_running = True
        self.stop_requested = False
        
        # Create and save the crawler model
        self.crawler_model = Crawler.objects.create(
            id=self.crawler_id,
            url=start_url,
            keyword=self.keyword,
            is_running=True,
            max_depth=max_depth,
            user=self.user  # Associate with the user
        )
        
        # Register this crawler in the global dictionary
        active_crawlers[self.crawler_id] = self
        
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc
        start_url_canonical = self.canonicalize_url(start_url)
        if not start_url_canonical:
            logger.error("Invalid initial URL after canonicalization.")
            self.is_running = False
            del active_crawlers[self.crawler_id]
            return

        url_queue = queue.Queue()
        url_queue.put((start_url_canonical, 0))
        visited = set()
        visited.add(start_url_canonical)
        lock = threading.Lock()

        def worker():
            while not self.stop_requested:
                try:
                    current_url, depth = url_queue.get(timeout=5)
                except queue.Empty:
                    break
                
                if self.stop_requested:
                    url_queue.task_done()
                    break
                    
                if depth > max_depth:
                    url_queue.task_done()
                    continue
                    
                logger.info(f"Crawling: {current_url} (depth: {depth}, queue size: {url_queue.qsize()}, visited: {len(visited)})")
                html = self.fetch_page(current_url)
                
                if not html or self.stop_requested:
                    url_queue.task_done()
                    continue
                    
                links = self.parse_links(html, current_url)
                new_links = []
                
                for link in links:
                    if self.stop_requested:
                        break
                        
                    canonical = self.canonicalize_url(link["url"])
                    if canonical and self.is_internal(canonical, base_domain):
                        with lock:
                            if canonical not in visited:
                                visited.add(canonical)
                                new_links.append(link)
                                url_queue.put((canonical, depth + 1))
                                self.all_links.add(canonical)
                
                # Process new links
                for link in new_links:
                    if self.stop_requested:
                        break
                    self.process_link(link)
                    
                url_queue.task_done()

        threads = []
        for _ in range(max_workers):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
            threads.append(t)
            
        try:
            url_queue.join()
        except KeyboardInterrupt:
            self.stop_requested = True
            
        for t in threads:
            t.join(timeout=2)  # Give threads a chance to exit gracefully

        logger.info(f"Crawling finished. Total visited URLs: {len(visited)}")
        self.is_running = False
        
        # Remove from active crawlers
        if self.crawler_id in active_crawlers:
            del active_crawlers[self.crawler_id]


# Helper functions to manage crawlers
def get_active_crawlers():
    """Return information about all active crawlers"""
    # First, sync with database
    db_crawlers = Crawler.objects.filter(is_running=True)
    
    # Return both active in-memory crawlers and from database
    result = {}
    
    # Add crawlers from memory
    for crawler_id, crawler in active_crawlers.items():
        result[crawler_id] = {
            "id": crawler_id,
            "keyword": crawler.keyword,
            "running": crawler.is_running,
            "url": crawler_id.split('_')[0],
            "start_time": crawler_id.split('_')[-1]
        }
    
    # Add crawlers from database that might not be in memory
    for db_crawler in db_crawlers:
        if db_crawler.id not in result:
            result[db_crawler.id] = {
                "id": db_crawler.id,
                "keyword": db_crawler.keyword,
                "running": db_crawler.is_running,
                "url": db_crawler.url,
                "start_time": db_crawler.start_time.timestamp()
            }
    
    return result

def stop_crawler(crawler_id):
    """Stop a specific crawler by its ID"""
    try:
        # Convert string to UUID if needed
        if isinstance(crawler_id, str):
            crawler_id = uuid.UUID(crawler_id)
            
        # Try to stop in-memory crawler first
        str_id = str(crawler_id)
        if str_id in active_crawlers:
            active_crawlers[str_id].stop()
        
        # Update database
        crawler = Crawler.objects.filter(id=crawler_id).first()
        if crawler:
            crawler.is_running = False
            crawler.end_time = timezone.now()
            crawler.save()
            return True
            
        return False
    except (ValueError, AttributeError) as e:
        logger.error(f"Error stopping crawler: {e}")
        return False

def stop_all_crawlers():
    """Stop all active crawlers"""
    # Stop in-memory crawlers
    for crawler in active_crawlers.values():
        crawler.stop()
    
    # Stop any crawlers in database
    Crawler.objects.filter(is_running=True).update(
        is_running=False,
        end_time=timezone.now()
    )
    
    return True