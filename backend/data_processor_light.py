# app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from data_processor_light import db  # Импортируем из data_processor_light
from typing import List, Optional
import os

app = FastAPI(title="Postcard Analytics", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статические файлы фронтенда
app.mount("/static", StaticFiles(directory="../frontend"), name="static")
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")

@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

@app.get("/{path:path}")
async def serve_frontend(path: str):
    frontend_path = f"../frontend/{path}"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return FileResponse("../frontend/index.html")

# API endpoints
@app.get("/api/")
async def read_root():
    return {"message": "Postcard Analytics API"}

@app.get("/api/cities")
def get_cities():
    return db.get_cities()

@app.get("/api/cities/{city_id}")
def get_city_detail(city_id: int):
    city = db.get_city_detail(city_id)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    return city

@app.get("/api/statistics")
def get_statistics():
    return db.get_statistics()

@app.get("/api/letters")
def get_letters(
    city_id: Optional[int] = Query(None),
    theme: Optional[str] = Query(None)
):
    all_letters = []
    cities = db.get_cities()
    
    for city in cities:
        city_detail = db.get_city_detail(city['id'])
        if city_detail and 'letters' in city_detail:
            for letter in city_detail['letters']:
                if city_id and letter['city_id'] != city_id:
                    continue
                if theme and letter['theme'] != theme:
                    continue
                all_letters.append(letter)
    
    return all_letters[:50]

@app.get("/api/search")
def search_letters(
    q: str = Query(..., description="Поисковый запрос")
):
    results = []
    cities = db.get_cities()
    
    for city in cities:
        city_detail = db.get_city_detail(city['id'])
        if city_detail and 'letters' in city_detail:
            for letter in city_detail['letters']:
                if q.lower() in letter['content'].lower() or q.lower() in letter['excerpt'].lower():
                    results.append(letter)
    
    return results[:20]

@app.get("/api/debug")
def debug_info():
    """Endpoint для отладки - показывает что в базе"""
    cities = db.get_cities()
    stats = db.get_statistics()
    
    return {
        "cities_count": len(cities),
        "cities": cities[:5],  # первые 5 городов
        "statistics": stats,
        "total_letters_in_db": stats["total_letters"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)