// frontend/js/app.js
class PostcardMap {
    constructor() {
        this.map = null;
        this.cities = [];
        this.filteredCities = [];
        this.markers = [];
        this.connections = [];
        this.cityConnections = {};
        this.allLetters = [];
        this.filters = {
            minLetters: 3,        // Минимум писем для показа города
            minConnections: 2,    // Минимум упоминаний для показа связи
            topCities: 80,        // Показывать топ-N городов по количеству писем
            showConnections: true // Показывать связи
        };
        this.init();
    }

    async init() {
        await this.loadData();
        this.applyFilters();
        this.initMap();
        await this.calculateConnections();
        this.createMarkers();
        if (this.filters.showConnections) {
            this.drawConnections();
        }
        this.initEventListeners();
        this.updateStatistics();
        this.createFilterControls();
        
        // Инициализируем лейблы
        this.updateFilterLabels();
        this.updateDebugInfo();
    }

    async loadData() {
        try {
            console.log("🔄 Загрузка данных с сервера...");
            const response = await fetch('/api/cities');
            this.cities = await response.json();
            console.log(`✅ Загружено ${this.cities.length} городов`);
            
            // Сортируем города по количеству писем (по убыванию)
            this.cities.sort((a, b) => (b.letter_count || 0) - (a.letter_count || 0));
            
        } catch (error) {
            console.error('❌ Ошибка загрузки данных:', error);
        }
    }

    // app.js - обновите метод applyNewFilters
    async applyNewFilters() {
        console.log("🔄 Применение новых фильтров...");
        
        const applyBtn = document.querySelector('.apply-btn');
        const originalText = applyBtn.textContent;
        applyBtn.textContent = '⏳ Загрузка...';
        applyBtn.disabled = true;
        
        try {
            // Обновляем фильтры из UI
            this.updateFiltersFromUI();
            
            this.applyFilters();
            
            // Удаляем старые маркеры и связи
            this.markers.forEach(marker => this.map.removeLayer(marker));
            this.connections.forEach(connection => this.map.removeLayer(connection));
            this.markers = [];
            this.connections = [];
            
            // Пересчитываем связи если нужно
            if (this.filters.showConnections) {
                await this.calculateConnections();
            } else {
                this.cityConnections = [];
            }
            
            // Создаем новые маркеры
            this.createMarkers();
            
            // Рисуем новые связи если нужно
            if (this.filters.showConnections && this.cityConnections.length > 0) {
                this.drawConnections();
            }
            
            console.log("✅ Фильтры применены успешно");
            
        } catch (error) {
            console.error('❌ Ошибка применения фильтров:', error);
        } finally {
            applyBtn.textContent = '🔄 Применить';
            applyBtn.disabled = false;
        }
    }

// Добавьте новый метод для обновления фильтров из UI
    updateFiltersFromUI() {
        const cityLimitSlider = document.getElementById('cityLimit');
        const minLettersSlider = document.getElementById('minLetters');
        const showConnectionsCheckbox = document.getElementById('showConnections');
        
        if (cityLimitSlider) {
            this.filters.topCities = parseInt(cityLimitSlider.value);
        }
        if (minLettersSlider) {
            this.filters.minLetters = parseInt(minLettersSlider.value);
        }
        if (showConnectionsCheckbox) {
            this.filters.showConnections = showConnectionsCheckbox.checked;
        }
        
        console.log("🎛️ Обновленные фильтры:", this.filters);
    }

    // Обновите метод updateFilter
    updateFilter(filterName, value) {
        console.log(`🔄 Обновление фильтра ${filterName}: ${value} (тип: ${typeof value})`);
        
        if (filterName === 'showConnections') {
            this.filters[filterName] = Boolean(value);
        } else {
            this.filters[filterName] = parseInt(value);
        }
        
        // Немедленно обновляем UI
        this.updateFilterLabels();
        
        // Обновляем отладочную информацию
        this.updateDebugInfo();
    }

    updateFilterLabels() {
        console.log("🔄 Обновление лейблов фильтров...");
        
        // Используем конкретные ID элементов
        const cityLimitLabel = document.getElementById('cityLimitLabel');
        const minLettersLabel = document.getElementById('minLettersLabel');
        
        if (cityLimitLabel) {
            cityLimitLabel.textContent = `Лимит городов: ${this.filters.topCities}`;
            console.log(`✅ Обновлен cityLimitLabel: ${this.filters.topCities}`);
        } else {
            console.log("❌ Не найден cityLimitLabel");
        }
        
        if (minLettersLabel) {
            minLettersLabel.textContent = `Мин. писем: ${this.filters.minLetters}`;
            console.log(`✅ Обновлен minLettersLabel: ${this.filters.minLetters}`);
        } else {
            console.log("❌ Не найден minLettersLabel");
        }
    }

    updateDebugInfo() {
        const debugCityCount = document.getElementById('debugCityCount');
        const debugFilters = document.getElementById('debugFilters');
        
        if (debugCityCount) {
            debugCityCount.textContent = this.filteredCities.length;
        }
        
        if (debugFilters) {
            debugFilters.textContent = `topCities=${this.filters.topCities}, minLetters=${this.filters.minLetters}`;
        }
    }

    initMap() {
        this.map = L.map('map').setView([55.7558, 37.6173], 4);

        // Более светлая подложка для лучшей видимости маркеров
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '© OpenStreetMap, © CartoDB',
            maxZoom: 19
        }).addTo(this.map);

        this.map.setMaxBounds([
            [35.0, 19.0],
            [82.0, 190.0]
        ]);
        
        console.log("🗺️ Карта инициализирована");
    }

    async calculateConnections() {
        if (!this.filters.showConnections) return;
        
        console.log("🔗 Анализ связей между городами...");
        this.cityConnections = {};
        
        // Загружаем письма только для отфильтрованных городов
        await this.loadLettersForFilteredCities();
        
        const citiesById = {};
        this.filteredCities.forEach(city => {
            citiesById[city.id] = city;
        });
        
        // Анализируем письма для поиска связей
        this.allLetters.forEach(letter => {
            const cityId = letter.city_id;
            const city = citiesById[cityId];
            
            if (!city) return;
            
            // Ищем упоминания других отфильтрованных городов
            this.filteredCities.forEach(targetCity => {
                if (targetCity.id !== cityId && 
                    targetCity.name && 
                    city.name &&
                    letter.content && 
                    this.hasCityMention(letter.content, targetCity.name)) {
                    
                    const connectionKey = [cityId, targetCity.id].sort().join('-');
                    
                    if (!this.cityConnections[connectionKey]) {
                        this.cityConnections[connectionKey] = {
                            city1: city,
                            city2: targetCity,
                            count: 0
                        };
                    }
                    
                    this.cityConnections[connectionKey].count++;
                }
            });
        });
        
        // Фильтруем слабые связи
        const strongConnections = Object.values(this.cityConnections)
            .filter(conn => conn.count >= this.filters.minConnections)
            .sort((a, b) => b.count - a.count)
            .slice(0, 30); // Ограничиваем количество связей
        
        console.log(`✅ Найдено ${strongConnections.length} значимых связей`);
        
        this.cityConnections = strongConnections;
    }

    async loadLettersForFilteredCities() {
        try {
            // Загружаем письма только для отфильтрованных городов
            const lettersPromises = this.filteredCities.map(city => 
                fetch(`/api/cities/${city.id}`).then(r => r.json())
            );
            
            const citiesData = await Promise.all(lettersPromises);
            this.allLetters = citiesData.flatMap(cityData => cityData.letters || []);
            
            console.log(`✅ Загружено ${this.allLetters.length} писем для анализа связей`);
        } catch (error) {
            console.error('❌ Ошибка загрузки писем:', error);
            this.allLetters = [];
        }
    }

    hasCityMention(content, cityName) {
        if (!content || !cityName) return false;
        
        const contentLower = content.toLowerCase();
        const cityNameLower = cityName.toLowerCase();
        
        // Простая проверка на вхождение названия города
        return contentLower.includes(cityNameLower);
    }

    // app.js - замените метод createMarkers
    createMarkers() {
        this.markers.forEach(marker => this.map.removeLayer(marker));
        this.markers = [];

        console.log(`🔄 Создание маркеров для ${this.filteredCities.length} городов`);

        // Создаем кастомные иконки разного размера
        const createCustomIcon = (letterCount) => {
            const radius = this.calculateRadius(letterCount);
            const intensity = Math.min(1, Math.log(letterCount || 1) / Math.log(50));
            const hue = 210;
            const saturation = 80 + (intensity * 20);
            const lightness = 50 - (intensity * 15);
            
            return L.divIcon({
                className: 'city-marker',
                html: `<div style="
                    width: ${radius}px; 
                    height: ${radius}px; 
                    background: hsl(${hue}, ${saturation}%, ${lightness}%); 
                    border: 2px solid white; 
                    border-radius: 50%; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    cursor: pointer;
                "></div>`,
                iconSize: [radius, radius],
                iconAnchor: [radius/2, radius/2]
            });
        };

        this.filteredCities.forEach(city => {
            if (!city.latitude || !city.longitude) return;

            const lat = parseFloat(city.latitude);
            const lng = parseFloat(city.longitude);
            
            if (isNaN(lat) || isNaN(lng)) return;

            try {
                const marker = L.marker([lat, lng], {
                    icon: createCustomIcon(city.letter_count || 1),
                    title: city.name
                }).addTo(this.map);

                marker.bindPopup(`
                    <div class="popup-content">
                        <h3>${city.name}</h3>
                        <p><strong>📨 Писем:</strong> ${city.letter_count || 0}</p>
                        <button onclick="app.showCityDetail(${city.id})" 
                                class="popup-btn">📖 Подробнее</button>
                    </div>
                `);

                marker.cityId = city.id;
                
                // Упрощаем обработчики событий
                marker.on('click', (e) => {
                    e.originalEvent.stopPropagation();
                    this.showCityDetail(city.id);
                });

                marker.on('mouseover', () => {
                    marker.setZIndexOffset(1000);
                });

                marker.on('mouseout', () => {
                    marker.setZIndexOffset(0);
                });

                this.markers.push(marker);
                
            } catch (error) {
                console.error(`❌ Ошибка создания маркера для ${city.name}:`, error);
            }
        });

        console.log(`✅ Создано ${this.markers.length} маркеров`);
        
        if (this.markers.length > 0) {
            const group = new L.featureGroup(this.markers);
            this.map.fitBounds(group.getBounds().pad(0.1));
        }
    }

    drawConnections() {
        this.connections.forEach(connection => this.map.removeLayer(connection));
        this.connections = [];

        if (!this.filters.showConnections || this.cityConnections.length === 0) return;

        console.log(`🔄 Отрисовка ${this.cityConnections.length} связей`);

        this.cityConnections.forEach(connection => {
            const { city1, city2, count } = connection;
            
            if (!city1.latitude || !city1.longitude || !city2.latitude || !city2.longitude) {
                return;
            }

            // Толщина и прозрачность зависят от силы связи (уменьшили в 2 раза)
            const maxCount = Math.max(...this.cityConnections.map(c => c.count));
            const relativeStrength = count / maxCount;
            
            const weight = Math.max(1, Math.min(3, relativeStrength * 3)); // Уменьшили толщину
            const opacity = Math.max(0.3, Math.min(0.6, relativeStrength * 0.6)); // Уменьшили прозрачность
            
            const line = L.polyline([
                [city1.latitude, city1.longitude],
                [city2.latitude, city2.longitude]
            ], {
                color: '#1E88E5', // Яркий синий
                weight: weight,
                opacity: opacity,
                className: 'city-connection'
            }).addTo(this.map);

            line.bindPopup(`
                <div class="connection-popup">
                    <h4>🔗 Связь между городами</h4>
                    <p><strong>${city1.name}</strong> ↔ <strong>${city2.name}</strong></p>
                    <p>📊 Сила связи: ${count} упоминаний</p>
                </div>
            `);

            this.connections.push(line);
        });

        console.log(`✅ Нарисовано ${this.connections.length} линий связей`);
    }

    highlightConnections(cityId) {
        this.connections.forEach(connection => {
            const connectionData = this.cityConnections.find(conn => 
                conn.city1.id === cityId || conn.city2.id === cityId
            );
            
            if (connectionData) {
                connection.setStyle({
                    color: '#FF6B6B',
                    weight: connection.options.weight + 1, // Уменьшили подсветку
                    opacity: 0.8
                });
            }
        });
    }

    resetConnections() {
        this.connections.forEach(connection => {
            connection.setStyle({
                color: '#1E88E5',
                weight: connection.options.weight,
                opacity: connection.options.opacity
            });
        });
    }

    calculateRadius(letterCount) {
        const count = letterCount || 1;
        // Уменьшили размер маркеров в 2 раза
        return Math.max(6, Math.min(20, Math.log(count) * 5 + 5));
    }

    async showCityDetail(cityId) {
        try {
            const response = await fetch(`/api/cities/${cityId}`);
            const cityData = await response.json();
            
            if (!cityData) return;
            
            this.displayCityPanel(cityData);
        } catch (error) {
            console.error('❌ Ошибка загрузки деталей города:', error);
        }
    }

    displayCityPanel(cityData) {
        const panel = document.getElementById('cityPanel');
        const cityName = document.getElementById('cityName');
        const cityLetterCount = document.getElementById('cityLetterCount');
        const lettersList = document.getElementById('lettersList');

        cityName.textContent = cityData.name;
        cityLetterCount.textContent = cityData.letter_count || 0;

        // Находим связи для этого города
        const cityConnections = this.cityConnections.filter(conn => 
            conn.city1.id === cityData.id || conn.city2.id === cityData.id
        );

        let connectionsHTML = '';
        if (cityConnections.length > 0) {
            connectionsHTML = `
                <div class="connections-section">
                    <h4>🔗 Связи с другими городами:</h4>
                    ${cityConnections.map(conn => {
                        const otherCity = conn.city1.id === cityData.id ? conn.city2 : conn.city1;
                        return `<div class="connection-item">
                            <span class="city-link">${otherCity.name}</span>
                            <span class="connection-count">${conn.count} упоминаний</span>
                        </div>`;
                    }).join('')}
                </div>
            `;
        }

        if (cityData.letters && cityData.letters.length > 0) {
            // Показываем только первые 10 писем
            const displayLetters = cityData.letters.slice(0, 10);
            lettersList.innerHTML = connectionsHTML + displayLetters.map(letter => `
                <div class="letter-card">
                    <div class="letter-year">${letter.year || 'Неизвестно'}</div>
                    <div class="letter-theme">${letter.theme || 'личное'}</div>
                    <div class="letter-excerpt">${letter.excerpt || 'Нет текста'}</div>
                    <div class="letter-sentiment ${letter.sentiment}">
                        ${this.getSentimentEmoji(letter.sentiment)} ${letter.sentiment}
                    </div>
                </div>
            `).join('');
        } else {
            lettersList.innerHTML = connectionsHTML + '<p>Письма не найдены</p>';
        }

        panel.style.display = 'block';
    }

    getSentimentEmoji(sentiment) {
        const emojis = {
            'positive': '😊',
            'negative': '😔', 
            'neutral': '😐'
        };
        return emojis[sentiment] || '📝';
    }

    initEventListeners() {
        document.getElementById('closePanel').addEventListener('click', () => {
            document.getElementById('cityPanel').style.display = 'none';
        });
    }

    async updateStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const stats = await response.json();
            
            // Исправляем отображение количества писем - берем из статистики API
            document.getElementById('totalLetters').textContent = stats.total_letters || 0;
            document.getElementById('totalCities').textContent = stats.total_cities || 0;
            
            const themesList = document.getElementById('themesList');
            if (stats.popular_themes && stats.popular_themes.length > 0) {
                themesList.innerHTML = stats.popular_themes.map(theme => `
                    <div class="theme-item">
                        <span class="theme-name">${theme.theme}</span>
                        <span class="theme-count">${theme.count}</span>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки статистики:', error);
        }
    }

    createFilterControls() {
        // Создаем панель управления фильтрами в левом верхнем углу
        const filterControl = L.control({ position: 'topleft' });
        
        filterControl.onAdd = (map) => {
            const div = L.DomUtil.create('div', 'filter-control');
            div.innerHTML = `
                <div class="filter-panel">
                    <h4>🎛️ Фильтры</h4>
                    
                    <div class="filter-group">
                        <label>Лимит городов: ${this.filters.topCities}</label>
                        <input type="range" id="cityLimit" min="20" max="150" value="${this.filters.topCities}" 
                               onchange="app.updateFilter('topCities', this.value)">
                    </div>
                    
                    <div class="filter-group">
                        <label>Мин. писем: ${this.filters.minLetters}</label>
                        <input type="range" id="minLetters" min="1" max="10" value="${this.filters.minLetters}" 
                               onchange="app.updateFilter('minLetters', this.value)">
                    </div>
                    
                    <div class="filter-group checkbox-group">
                        <label>
                            <input type="checkbox" id="showConnections" ${this.filters.showConnections ? 'checked' : ''}
                                   onchange="app.updateFilter('showConnections', this.checked)">
                            Показывать связи
                        </label>
                    </div>
                    
                    <button onclick="app.applyNewFilters()" class="apply-btn">🔄 Применить</button>
                </div>
            `;
            return div;
        };
        
        filterControl.addTo(this.map);
    }

    updateFilter(filterName, value) {
        if (filterName === 'showConnections') {
            this.filters[filterName] = Boolean(value);
        } else {
            this.filters[filterName] = parseInt(value);
        }
        
        // Обновляем label
        const label = document.querySelector(`label[for="${filterName}"]`);
        if (label) {
            if (filterName === 'showConnections') {
                // Для чекбокса не обновляем текст
            } else {
                label.textContent = label.textContent.split(':')[0] + ': ' + this.filters[filterName];
            }
        }
    }
    applyFilters() {
        console.log("🔄 Применение фильтров...");
        
        // Фильтруем города по минимальному количеству писем
        let filtered = this.cities.filter(city => 
            (city.letter_count || 0) >= this.filters.minLetters
        );
        
        // Берем топ-N городов по количеству писем
        filtered = filtered.slice(0, this.filters.topCities);
        
        console.log(`✅ После фильтрации: ${filtered.length} городов`);
        this.filteredCities = filtered;
    }

    
}

// Инициализация приложения
const app = new PostcardMap();