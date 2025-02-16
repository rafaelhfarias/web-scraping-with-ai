# scraper.py
import re
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import queue
import threading

from llm_processor import get_relevance_score
from database import Database
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WebScraper:
    def __init__(self, db: Database, keyword: str):
        self.db = db
        self.keyword = keyword
        self.ua = UserAgent()
        self.all_links = set() 

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
            score = float(get_relevance_score(text, self.keyword))  # Ensure score is float
            link_type = self.determine_link_type(text)
            metadata = {"text": text}
            
            # Ensure all parameters are of correct type
            if not isinstance(url, str) or not isinstance(link_type, str):
                logger.error(f"Invalid data types for URL or link_type: {url}, {link_type}")
                return
                
            self.db.insert_link(url, link_type, score, self.keyword, metadata)
            
        except Exception as e:
            logger.error(f"Error processing link: {str(e)}")
            return

    def determine_link_type(self, text: str) -> str:
        lower_text = text.lower()
        if "contact" in lower_text or "director" in lower_text or "email" in lower_text:
            return "contact"
        if any(term in lower_text for term in ["acfr", "budget", "report", "file"]):
            return "document"
        return "unknown"

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

    def crawl(self, start_url: str, max_depth: int = 3, max_workers: int = 50):
        """
        Performs crawling using a thread-safe queue and multiple worker threads.
        Only internal HTTPS URLs will be considered; duplicates and invalid links are ignored.
        """
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc
        start_url_canonical = self.canonicalize_url(start_url)
        if not start_url_canonical:
            logger.error("Invalid initial URL after canonicalization.")
            return

        url_queue = queue.Queue()
        url_queue.put((start_url_canonical, 0))
        visited = set()
        visited.add(start_url_canonical)
        lock = threading.Lock()

        def worker():
            while True:
                try:
                    current_url, depth = url_queue.get(timeout=5)
                except queue.Empty:
                    break
                if depth > max_depth:
                    url_queue.task_done()
                    continue
                logger.info(f"Crawling: {current_url} (depth: {depth}, queue size: {url_queue.qsize()}, visited: {len(visited)})")
                html = self.fetch_page(current_url)
                if not html:
                    url_queue.task_done()
                    continue
                links = self.parse_links(html, current_url)
                new_links = []
                for link in links:
                    canonical = self.canonicalize_url(link["url"])
                    if canonical and self.is_internal(canonical, base_domain):
                        with lock:
                            if canonical not in visited:
                                visited.add(canonical)
                                new_links.append(link)
                                url_queue.put((canonical, depth + 1))
                                self.all_links.add(canonical)
                # Process new links (can be parallelized if needed)
                for link in new_links:
                    self.process_link(link)
                url_queue.task_done()

        threads = []
        for _ in range(max_workers):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
            threads.append(t)
        url_queue.join()
        for t in threads:
            t.join()

        logger.info(f"Crawling finished. Total visited URLs: {len(visited)}")