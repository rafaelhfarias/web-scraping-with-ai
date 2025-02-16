# api.py

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from database import Database
from scraper import WebScraper

app = FastAPI()

# Inicializa o banco de dados (pode ser configurado para cada request ou globalmente)
db = Database("links.db")

class ScrapeRequest(BaseModel):
    url: str
    keyword: str

@app.post("/scrape")
def scrape_endpoint(request: ScrapeRequest):
    scraper = WebScraper(db, request.keyword)
    scraper.scrape(request.url)
    return {"message": "Scraping concluído."}

@app.get("/links")
def get_links(
    keyword: str = None,
    link_type: str = Query(None, alias="type"),
    min_relevance: float = None
):
    """
    Consulta os links armazenados e permite filtrar por:
    - keyword: o valor exato do campo 'keywords'
    - type: o tipo do link (ex.: 'contact', 'document', etc.)
    - min_relevance: pontuação mínima para o relevance_score
    """
    results = db.query_links(keyword=keyword, type_=link_type, min_relevance=min_relevance)
    return {"links": results}
