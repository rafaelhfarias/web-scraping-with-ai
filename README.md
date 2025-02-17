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
````

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt # or pip3 install -r requirements.txt
 ```

## Configuration
1. Install [Ollama](https://ollama.com/)
2. Pull the Llama3 model using Ollama:
```bash
ollama pull llama3
 ```

## Usage
### Starting the API Server
```bash
uvicorn api:app --reload
 ```

The API will be available at http://localhost:8000

### Running the Scraper

Use the command line interface to start the scraper:

```bash
python main.py --url https://example.com --keyword budget --depth 3
```
Available options:

- --url : Target website URL to crawl (required)
- --keyword : Keyword to analyze content relevance (required)
- --depth : Maximum crawling depth (default: 3)
- --workers : Number of concurrent workers (default: 50)
  
Example:
```bash
# Crawl a city website looking for budget-related content
python main.py --url https://www.bozeman.net --keyword budget --depth 2 --workers 30
 ```

Note: Make sure Ollama is running before starting the scraper.

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

