import sqlite3
import os
import json
from datetime import datetime
import pandas as pd
import random

class SimpleDB:
    def __init__(self, db_path="postcards.db"):
        self.db_path = db_path
        self.init_db()
        self.load_or_create_data()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                latitude REAL,
                longitude REAL,
                letter_count INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                year INTEGER,
                content TEXT,
                theme TEXT,
                sentiment TEXT,
                excerpt TEXT,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
    def load_or_create_data(self):
        """Загружаем данные из Excel или создаем демо-данные"""
        excel_path = "../data/Пишу тебе. Корпус для хакатона (2024).xlsx"
        
        if os.path.exists(excel_path):
            print("🔄 Загружаем данные из Excel...")
            try:
                if self.process_excel_data(excel_path):
                    print("✅ Данные из Excel загружены!")
                    return
            except Exception as e:
                print(f"❌ Ошибка загрузки из Excel: {e}")
        
        # Если Excel не загрузился, создаем демо-данные
        print("📝 Создаем демо-данные...")
        self.create_demo_data()

    def process_excel_data(self, excel_path):
        """Обработка реальных данных из Excel"""
        try:
            # Читаем Excel файл
            df = pd.read_excel(excel_path)
            print(f"📊 Загружено {len(df)} записей из Excel")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Очищаем таблицы
            cursor.execute('DELETE FROM letters')
            cursor.execute('DELETE FROM cities')
            
            # Словарь для хранения городов и их координат
            cities_dict = {}
            city_letters = {}
            
            # Функция для нормализации названий городов
            def normalize_city_name(city_str):
                if pd.isna(city_str) or city_str in ['[нрзб]', '[отсутствует]', 'нрзб', 'отсутствует']:
                    return None
                
                city_str = str(city_str).strip()
                
                # Убираем указания на губернии
                if 'губерния' in city_str.lower():
                    parts = city_str.split(',')
                    city_str = parts[-1].strip()
                
                # Убираем префиксы
                for prefix in ['г.', 'город', 'гор.', 'с.', 'село', 'дер.', 'деревня']:
                    if city_str.lower().startswith(prefix.lower()):
                        city_str = city_str[len(prefix):].strip()
                
                return city_str if city_str else None
            
            # Собираем уникальные города
            for _, row in df.iterrows():
                from_city_raw = row.get('Населенный пункт (откуда)', '')
                to_city_raw = row.get('Населенный пункт (куда)', '')
                
                from_city = normalize_city_name(from_city_raw)
                to_city = normalize_city_name(to_city_raw)
                
                for city_name in [from_city, to_city]:
                    if city_name and city_name not in cities_dict:
                        cities_dict[city_name] = {
                            'latitude': None,
                            'longitude': None,
                            'letter_count': 0
                        }
                        city_letters[city_name] = []
            
            # Получаем координаты для городов
            cities_dict = self.get_cities_coordinates(cities_dict)
            
            # Вставляем города в БД
            for city_name, city_data in cities_dict.items():
                if city_data['latitude'] and city_data['longitude']:
                    cursor.execute(
                        'INSERT INTO cities (name, latitude, longitude, letter_count) VALUES (?, ?, ?, ?)',
                        (city_name, city_data['latitude'], city_data['longitude'], 0)
                    )
            
            # Получаем ID городов
            cursor.execute('SELECT id, name FROM cities')
            city_ids = {name: id for id, name in cursor.fetchall()}
            
            # Обрабатываем письма
            letter_id = 1
            for _, row in df.iterrows():
                from_city = normalize_city_name(row.get('Населенный пункт (откуда)', ''))
                to_city = normalize_city_name(row.get('Населенный пункт (куда)', ''))
                
                content = row.get('Текст открытки', '')
                if pd.isna(content):
                    content = ''
                
                # Год из даты
                year = None
                date_str = row.get('Дата открытки (нормализованная)', '')
                if not pd.isna(date_str):
                    try:
                        date_str = str(date_str)
                        if '.' in date_str:
                            year_str = date_str.split('.')[-1]
                            year = int(year_str)
                            if year < 1800 or year > 2100:
                                year = None
                    except:
                        year = None
                
                # Если год не определился, пробуем из других полей
                if not year:
                    try:
                        other_date = row.get('Дата печати открытки', '')
                        if not pd.isna(other_date):
                            year_str = str(other_date).split('.')[-1]
                            year = int(year_str)
                    except:
                        year = 1900  # год по умолчанию
                
                theme = self.detect_theme(content)
                sentiment = self.analyze_sentiment(content)
                excerpt = content[:100] + '...' if len(content) > 100 else content
                
                # Добавляем письма для городов отправителей
                if from_city and from_city in city_ids:
                    city_id = city_ids[from_city]
                    cursor.execute(
                        'INSERT INTO letters (city_id, year, content, theme, sentiment, excerpt) VALUES (?, ?, ?, ?, ?, ?)',
                        (city_id, year, content, theme, sentiment, excerpt)
                    )
                    city_letters[from_city].append(letter_id)
                    letter_id += 1
                
                # Добавляем письма для городов получателей
                if to_city and to_city in city_ids and to_city != from_city:
                    city_id = city_ids[to_city]
                    cursor.execute(
                        'INSERT INTO letters (city_id, year, content, theme, sentiment, excerpt) VALUES (?, ?, ?, ?, ?, ?)',
                        (city_id, year, content, theme, sentiment, excerpt)
                    )
                    city_letters[to_city].append(letter_id)
                    letter_id += 1
            
            # Обновляем счетчики писем
            for city_name, letters in city_letters.items():
                if city_name in city_ids:
                    cursor.execute(
                        'UPDATE cities SET letter_count = ? WHERE id = ?',
                        (len(letters), city_ids[city_name])
                    )
            
            conn.commit()
            conn.close()
            
            print(f"✅ Обработано {len(cities_dict)} городов и {letter_id-1} писем")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обработки Excel: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_cities_coordinates(self, cities_dict):
        """Получаем координаты для городов"""
        known_coordinates = {
            'Москва': (55.7558, 37.6173),
            'Санкт-Петербург': (59.9343, 30.3351),
            'Петроград': (59.9343, 30.3351),
            'Одесса': (46.4825, 30.7233),
            'Тифлис': (41.7225, 44.7925),
            'Ростов-на-Дону': (47.2225, 39.7188),
            'Ростов на Дону': (47.2225, 39.7188),
            'Рига': (56.9496, 24.1052),
            'Владивосток': (43.1155, 131.8855),
            'Вологда': (59.2187, 39.8936),
            'Великий Устюг': (60.7604, 46.2993),
            'Ялта': (44.4952, 34.1663),
            'Киев': (50.4501, 30.5234),
            'Хабаровск': (48.4802, 135.0719),
            'Иркутск': (52.2864, 104.2807),
            'Чита': (52.0339, 113.4994),
            'Тула': (54.1930, 37.6173),
            'Нижний Новгород': (56.3269, 44.0065),
            'Казань': (55.7963, 49.1088),
            'Екатеринбург': (56.8389, 60.6057),
            'Пермь': (58.0105, 56.2502),
            'Самара': (53.1959, 50.1002),
            'Уфа': (54.7355, 55.9587),
            'Краснодар': (45.0355, 38.9750),
            'Воронеж': (51.6615, 39.2003),
            'Саратов': (51.5336, 46.0343),
            'Тверь': (56.8587, 35.9176),
            'Ярославль': (57.6261, 39.8845),
            'Кострома': (57.7678, 40.9269),
            'Вятка': (58.6036, 49.6680),
            'Орлов': (58.5389, 48.8986),
            'Псков': (57.8194, 28.3318),
            'Смоленск': (54.7826, 32.0453),
            'Курск': (51.7304, 36.1926),
            'Белгород': (50.5955, 36.5873),
            'Орел': (52.9703, 36.0635),
            'Тамбов': (52.7213, 41.4527),
            'Липецк': (52.6088, 39.5992),
            'Томск': (56.4846, 84.9482),
            'Омск': (54.9885, 73.3242),
            'Новосибирск': (55.0084, 82.9357),
            'Красноярск': (56.0153, 92.8932),
            'Барнаул': (53.3563, 83.7616),
            'Кемерово': (55.3547, 86.0873),
            'Новокузнецк': (53.7576, 87.1360),
            'Тюмень': (57.1522, 65.5272),
            'Челябинск': (55.1644, 61.4368),
            'Магнитогорск': (53.4072, 58.9794),
            'Ульяновск': (54.3142, 48.4031),
            'Пенза': (53.1950, 45.0183),
            'Астрахань': (46.3497, 48.0408),
            'Волгоград': (48.7080, 44.5133),
            'Рязань': (54.6294, 39.7410),
            'Калуга': (54.5138, 36.2612),
            'Брянск': (53.2436, 34.3634),
            'Курган': (55.4410, 65.3411),
            'Сургут': (61.2541, 73.3962),
            'Нижневартовск': (60.9397, 76.5694),
            'Сочи': (43.5855, 39.7231),
            'Севастополь': (44.6167, 33.5254),
            'Симферополь': (44.9521, 34.1024),
            'Ревель': (59.4370, 24.7536),
            'Лида': (53.8930, 25.3027),
            'Варшава': (52.2297, 21.0122),
            'Дрезден': (51.0504, 13.7373),
            'Кологрив': (58.8275, 44.3189),
            'Котлас': (61.2529, 46.6513),
            'Царское Село': (59.7167, 30.4167),
            'Екатеринослав': (48.4647, 35.0462),
            'Сумы': (50.9077, 34.7981),
            'Могилев': (53.9007, 30.3310),
            'Ставрополь': (45.0445, 41.9691),
            'Верхопенье': (51.1175, 37.1819),
            'Славянск': (48.8534, 37.6255),
            'Челябинск': (55.1644, 61.4368),
            'Никитовка': (48.3389, 38.2489),
            'Митрофановское': (51.1628, 58.2833),
            'Выру': (57.8489, 27.0194),
            'Майоренгоф': (56.9833, 24.1333),
            'Передольск': (58.5167, 29.9667),
            'Стрельна': (59.8572, 30.0594),
            'Алупка': (44.4197, 34.0431),
            'Симеиз': (44.4061, 34.0083),
            'Бахчисарай': (44.7528, 33.8608),
            'Массандра': (44.5181, 34.1883),
            'Артек': (44.5497, 34.2928),
        }
        
        for city_name in cities_dict:
            if city_name in known_coordinates:
                cities_dict[city_name]['latitude'], cities_dict[city_name]['longitude'] = known_coordinates[city_name]
            else:
                # Для неизвестных городов используем случайные координаты в пределах России
                cities_dict[city_name]['latitude'] = 55.0 + random.uniform(-10, 15)
                cities_dict[city_name]['longitude'] = 30.0 + random.uniform(-10, 150)
        
        return cities_dict

    def detect_theme(self, content):
        """Определяем тему письма по содержанию"""
        if not content:
            return 'личное'
            
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['любов', 'мил', 'дорог', 'целую', 'обнимаю', 'любим']):
            return 'любовь'
        elif any(word in content_lower for word in ['семь', 'мама', 'папа', 'брат', 'сестра', 'родител', 'дети']):
            return 'семья'
        elif any(word in content_lower for word in ['друг', 'товарищ', 'приятель', 'знаком']):
            return 'дружба'
        elif any(word in content_lower for word in ['поздрав', 'с праздником', 'христос воскресе', 'с пасхой']):
            return 'поздравление'
        elif any(word in content_lower for word in ['работа', 'служб', 'дело', 'бизнес', 'заработ']):
            return 'работа'
        elif any(word in content_lower for word in ['учен', 'школ', 'урок', 'экзамен', 'учиться']):
            return 'учеба'
        else:
            return 'личное'

    def analyze_sentiment(self, content):
        """Анализ тональности текста"""
        if not content:
            return 'neutral'
            
        content_lower = content.lower()
        
        positive_words = ['рад', 'хорош', 'прекрасн', 'счастлив', 'любов', 'спасибо', 'здоров', 'успех', 'весел', 'приятн']
        negative_words = ['скуч', 'груст', 'тяжел', 'больн', 'плох', 'несчаст', 'жаль', 'умер', 'трудн', 'проблем']
        
        pos_count = sum(1 for word in positive_words if word in content_lower)
        neg_count = sum(1 for word in negative_words if word in content_lower)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'

    def create_demo_data(self):
        """Создание демо-данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Очищаем таблицы
        cursor.execute('DELETE FROM letters')
        cursor.execute('DELETE FROM cities')
        
        # Демо-города
        demo_cities = [
            ('Москва', 55.7558, 37.6173, 47),
            ('Санкт-Петербург', 59.9343, 30.3351, 38),
            ('Нижний Новгород', 56.3269, 44.0065, 23),
        ]
        
        cursor.executemany(
            'INSERT INTO cities (name, latitude, longitude, letter_count) VALUES (?, ?, ?, ?)',
            demo_cities
        )
        
        cursor.execute('SELECT id, name FROM cities')
        cities = {name: id for id, name in cursor.fetchall()}
        
        # Демо-письма
        demo_letters = [
            (cities['Москва'], 1910, 'Дорогой друг, получил твое письмо из Петербурга...', 'дружба', 'positive', 'Дорогой друг, получил твое письмо из Петербурга...'),
            (cities['Санкт-Петербург'], 1905, 'Любимая, как же я скучаю по тебе!...', 'любовь', 'positive', 'Любимая, как же я скучаю по тебе!...'),
        ]
        
        cursor.executemany(
            'INSERT INTO letters (city_id, year, content, theme, sentiment, excerpt) VALUES (?, ?, ?, ?, ?, ?)',
            demo_letters
        )
        
        conn.commit()
        conn.close()
        print("✅ Демо-данные созданы!")

    def get_cities(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM cities')
        cities = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return cities
    
    def get_city_detail(self, city_id):
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
    
    def get_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM letters')
        total_letters = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cities')
        total_cities = cursor.fetchone()[0]
        
        cursor.execute('SELECT theme, COUNT(*) FROM letters GROUP BY theme')
        themes = [{"theme": row[0] or "другое", "count": row[1]} for row in cursor.fetchall()]
        
        cursor.execute('SELECT sentiment, COUNT(*) FROM letters GROUP BY sentiment')
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

# Создаем глобальный экземпляр БД - данные загрузятся автоматически
db = SimpleDB()