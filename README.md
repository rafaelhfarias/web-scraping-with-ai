# AI Web Scraper

An intelligent web scraper that uses LLM (Large Language Model) to analyze and score webpage content relevance. The scraper crawls websites, extracts links, and stores them in a SQLite database with relevance scores.

## Features

- Multi-threaded web crawling
- LLM-powered content relevance scoring
- Automatic link type classification (document, contact, unknown)
- Cloud-flare bypass capabilities
- REST API for accessing scraped data
- SQLite database storage

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai_web_scrapper

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
 ```

## Configuration
1. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY=your_api_key_here
 ```

## Usage
### Starting the API Server
```bash
uvicorn api:app --reload
 ```

The API will be available at http://localhost:8000

### Running the Scraper
```python
from scraper import WebScraper
from database import Database

# Initialize database
db = Database()

# Create scraper instance with keyword
scraper = WebScraper(db, keyword="budget")

# Start crawling
scraper.crawl("https://example.com", max_depth=3)
 ```

## API Endpoints
### Get Links
- GET /links : Retrieve all scraped links
- Query Parameters:
  - keyword : Filter by keyword
  - type : Filter by link type (document, contact, unknown)
  - min_relevance : Filter by minimum relevance score (0.0 to 1.0)
Example:

```bash
curl "http://localhost:8000/links?keyword=budget&type=document&min_relevance=0.7"
 ```
```

## Database Schema
The SQLite database ( links.db ) contains a single table with the following structure:

```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    type TEXT,
    relevance_score REAL,
    keywords TEXT,
    metadata TEXT
);
 ```

