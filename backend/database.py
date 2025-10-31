import sqlite3
import os

class Database:
    def __init__(self, db_path="postcards.db"):
        self.db_path = db_path
    
    def get_cities(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM cities')
            cities = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return cities
        except Exception as e:
            print(f"❌ Ошибка загрузки городов: {e}")
            return []
    
    def get_city_detail(self, city_id):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM cities WHERE id = ?', (city_id,))
            city_row = cursor.fetchone()
            city = dict(city_row) if city_row else None
            
            if city:
                cursor.execute('SELECT * FROM letters WHERE city_id = ?', (city_id,))
                letters = [dict(row) for row in cursor.fetchall()]
                city['letters'] = letters
            
            conn.close()
            return city
        except Exception as e:
            print(f"❌ Ошибка загрузки деталей города: {e}")
            return None
    
    # database.py
    def get_statistics(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Вместо COUNT(*) из letters, считаем уникальные письма
            cursor.execute('SELECT COUNT(DISTINCT content) FROM letters WHERE content != ""')
            total_letters = cursor.fetchone()[0]
            
            # Альтернативный метод: если хотите точнее считать
            # cursor.execute('SELECT COUNT(*) FROM (SELECT DISTINCT content, year FROM letters WHERE content != "")')
            # total_letters = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM cities')
            total_cities = cursor.fetchone()[0]
            
            # Для тем и тональности используем DISTINCT
            cursor.execute('SELECT theme, COUNT(DISTINCT content) FROM letters WHERE content != "" GROUP BY theme')
            themes = [{"theme": row[0] or "другое", "count": row[1]} for row in cursor.fetchall()]
            
            cursor.execute('SELECT sentiment, COUNT(DISTINCT content) FROM letters WHERE content != "" GROUP BY sentiment')
            sentiments = [{"sentiment": row[0] or "neutral", "count": row[1]} for row in cursor.fetchall()]
            
            cursor.execute('SELECT MIN(year), MAX(year) FROM letters WHERE year IS NOT NULL')
            year_range = cursor.fetchone()
            years_range = [year_range[0] or 1900, year_range[1] or 1950]
            
            conn.close()
            
            return {
                "total_letters": total_letters,
                "total_cities": total_cities,
                "years_range": years_range,
                "popular_themes": sorted(themes, key=lambda x: x["count"], reverse=True)[:5],
                "sentiment_distribution": sentiments
            }
        except Exception as e:
            print(f"❌ Ошибка загрузки статистики: {e}")
            return {
                "total_letters": 0,
                "total_cities": 0,
                "years_range": [1900, 1950],
                "popular_themes": [],
                "sentiment_distribution": []
            }

# Создаем глобальный экземпляр БД
db = Database()