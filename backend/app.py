from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import db
from typing import List, Optional
import os
import sqlite3

# Импортируем инициализатор базы данных ПЕРВЫМ
import db_init

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

# Главная страница
@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

# API endpoints
@app.get("/api/")
async def read_root():
    return {"message": "Postcard Analytics API"}

@app.get("/api/cities")
def get_cities():
    cities = db.get_cities()
    return cities

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
        "cities": cities[:5],
        "statistics": stats,
        "total_letters_in_db": stats["total_letters"]
    }

@app.get("/api/test-data")
def test_data():
    """Тестовый endpoint для проверки данных"""
    conn = sqlite3.connect("postcards.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Проверяем первые 5 городов
    cursor.execute("SELECT * FROM cities LIMIT 5")
    cities = [dict(row) for row in cursor.fetchall()]
    
    # Проверяем первые 5 писем
    cursor.execute("SELECT * FROM letters LIMIT 5")
    letters = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "cities_sample": cities,
        "letters_sample": letters,
        "message": "Данные из базы"
    }

# Catch-all роут для фронтенда
@app.get("/{path:path}")
async def serve_frontend(path: str):
    frontend_path = f"../frontend/{path}"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return FileResponse("../frontend/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)