# main.py

import argparse
from database import Database
from scraper import WebScraper

def main():
    parser = argparse.ArgumentParser(description="Web crawler with LLM")
    parser.add_argument("url", help="Initial URL for crawling")
    parser.add_argument("--keyword", default="Budget", help="keyword to search for")
    parser.add_argument("--max_depth", type=int, default=3, help="Max depth for crawling")
    parser.add_argument("--max_workers", type=int, default=50, help="Max number of workers for crawling")
    args = parser.parse_args()

    db = Database("links.db")
    scraper = WebScraper(db, args.keyword)
    scraper.crawl(args.url, max_depth=args.max_depth, max_workers=args.workers)

if __name__ == "__main__":
    main()
