# AI Web Scraper Backend

Django-based backend for the AI Web Scraper project.

## Setup

1. Start the PostgreSQL database:
```bash
docker-compose up -d
```

2. Create and activate a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
 ```

3. Install dependencies:
```bash
pip install -r requirements.txt
 ```

4. Run migrations:
```bash
python manage.py migrate
 ```

5. Create a superuser (optional):
```bash
python manage.py createsuperuser
 ```

6. Start the development server:
```bash
python manage.py runserver
 ```

7. Run migrations and start the server:
```bash
cd ./backend
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
 ```

## API Endpoints
- GET /api/links/ : List all links
  
  - Query parameters:
    - keyword : Filter by keyword
    - type : Filter by link type (document, contact, service, news, unknown)
    - min_relevance : Filter by minimum relevance score (0.0 to 1.0)
- POST /api/links/start_crawl/ : Start a new crawl
  
  - Request body:
    ```json
    {
      "url": "https://example.com",
      "keyword": "budget",
      "depth": 3,
      "workers": 50
    }
     ```
