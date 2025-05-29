#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль интеграции с Open Library API
"""

import requests
import logging
from typing import List, Dict, Optional
from config import (
    OPENLIBRARY_SEARCH_URL, OPENLIBRARY_WORKS_URL, 
    OPENLIBRARY_COVERS_URL, SEARCH_RESULTS_PER_PAGE
)

logger = logging.getLogger(__name__)

class OpenLibraryAPI:
    """Класс для работы с Open Library API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BookBot/1.0 (Contact: your-email@example.com)'
        })
    
    def search_books(self, query: str, limit: int = SEARCH_RESULTS_PER_PAGE) -> List[Dict]:
        """Поиск книг по названию или автору"""
        try:
            # Улучшаем поисковый запрос
            formatted_query = self._format_search_query(query)
            
            params = {
                'q': formatted_query,
                'limit': limit,
                'fields': 'key,title,author_name,first_publish_year,subject,cover_i,edition_count'
            }
            
            # Делаем несколько попыток с разными форматами запроса
            search_attempts = [
                formatted_query,
                f'author:"{query}"',  # Поиск по автору
                f'title:"{query}"',   # Поиск по названию
                query.replace(' ', '+')  # Замена пробелов на +
            ]
            
            for attempt_query in search_attempts:
                try:
                    params['q'] = attempt_query
                    response = self.session.get(OPENLIBRARY_SEARCH_URL, params=params, timeout=15)
                    response.raise_for_status()
                    
                    data = response.json()
                    books = []
                    
                    for doc in data.get('docs', []):
                        book = self._format_book_data(doc)
                        if book:
                            books.append(book)
                    
                    if books:  # Если нашли результаты, возвращаем их
                        logger.info(f"Найдено {len(books)} книг по запросу: {attempt_query}")
                        return books
                        
                except requests.RequestException as e:
                    logger.warning(f"Попытка поиска с запросом '{attempt_query}' неудачна: {e}")
                    continue
            
            logger.warning(f"Все попытки поиска для '{query}' неудачны")
            return []
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при поиске книг: {e}")
            return []
    
    def _format_search_query(self, query: str) -> str:
        """Форматирование поискового запроса для лучших результатов"""
        query = query.strip()
        
        # Убираем лишние символы
        query = query.replace('"', '').replace("'", "")
        
        # Если запрос короткий (вероятно фамилия автора), форматируем для поиска автора
        if len(query.split()) == 1 and len(query) > 2:
            return f'author:{query}'
        
        return query
    
    def get_book_details(self, work_key: str) -> Optional[Dict]:
        """Получение подробной информации о книге по work key"""
        try:
            # Убираем префикс /works/ если он есть
            if work_key.startswith('/works/'):
                work_key = work_key[7:]
            
            url = f"{OPENLIBRARY_WORKS_URL}/{work_key}.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'key': data.get('key', ''),
                'title': data.get('title', ''),
                'description': self._extract_description(data.get('description')),
                'subjects': data.get('subjects', []),
                'first_publish_date': data.get('first_publish_date'),
                'covers': data.get('covers', [])
            }
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении деталей книги {work_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении деталей книги: {e}")
            return None
    
    def get_cover_url(self, cover_id: int, size: str = 'M') -> str:
        """Получение URL обложки книги"""
        if not cover_id:
            return None
        return f"{OPENLIBRARY_COVERS_URL}/{cover_id}-{size}.jpg"
    
    def _format_book_data(self, doc: Dict) -> Optional[Dict]:
        """Форматирование данных книги из API ответа"""
        try:
            title = doc.get('title', '').strip()
            if not title:
                return None
            
            authors = doc.get('author_name', [])
            author = ', '.join(authors) if authors else 'Неизвестный автор'
            
            # Извлекаем жанр из subjects
            subjects = doc.get('subject', [])
            genre = self._extract_main_genre(subjects)
            
            # URL обложки
            cover_url = None
            cover_id = doc.get('cover_i')
            if cover_id:
                cover_url = self.get_cover_url(cover_id)
            
            return {
                'openlibrary_key': doc.get('key', ''),
                'title': title,
                'author': author,
                'genre': genre,
                'first_publish_year': doc.get('first_publish_year'),
                'cover_url': cover_url,
                'edition_count': doc.get('edition_count', 0),
                'subjects': subjects[:5]  # Первые 5 тем
            }
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании данных книги: {e}")
            return None
    
    def _extract_description(self, description_field) -> str:
        """Извлечение описания из поля description"""
        if not description_field:
            return ''
        
        if isinstance(description_field, str):
            return description_field
        elif isinstance(description_field, dict):
            return description_field.get('value', '')
        elif isinstance(description_field, list) and description_field:
            first_desc = description_field[0]
            if isinstance(first_desc, str):
                return first_desc
            elif isinstance(first_desc, dict):
                return first_desc.get('value', '')
        
        return ''
    
    def _extract_main_genre(self, subjects: List[str]) -> str:
        """Извлечение основного жанра из списка тем"""
        if not subjects:
            return 'Не указан'
        
        # Приоритетные жанры на английском
        priority_genres = [
            'Fiction', 'Science Fiction', 'Fantasy', 'Mystery', 'Romance',
            'Thriller', 'Horror', 'Biography', 'History', 'Philosophy',
            'Poetry', 'Drama', 'Adventure', 'Classic Literature', 'Young Adult',
            'Children', 'Non-fiction', 'Self-help', 'Science', 'Technology'
        ]
        
        # Ищем приоритетные жанры
        for genre in priority_genres:
            for subject in subjects:
                if genre.lower() in subject.lower():
                    return self._translate_genre(genre)
        
        # Если не найден приоритетный жанр, берем первый
        if subjects:
            return self._translate_genre(subjects[0])
        
        return 'Не указан'
    
    def _translate_genre(self, genre: str) -> str:
        """Перевод жанра на русский язык"""
        translations = {
            'Fiction': 'Художественная литература',
            'Science Fiction': 'Научная фантастика',
            'Fantasy': 'Фэнтези',
            'Mystery': 'Детектив',
            'Romance': 'Роман',
            'Thriller': 'Триллер',
            'Horror': 'Ужасы',
            'Biography': 'Биография',
            'History': 'История',
            'Philosophy': 'Философия',
            'Poetry': 'Поэзия',
            'Drama': 'Драма',
            'Adventure': 'Приключения',
            'Classic Literature': 'Классическая литература',
            'Young Adult': 'Молодежная литература',
            'Children': 'Детская литература',
            'Non-fiction': 'Документальная литература',
            'Self-help': 'Саморазвитие',
            'Science': 'Наука',
            'Technology': 'Технологии'
        }
        
        return translations.get(genre, genre)

# Создаем глобальный экземпляр API
openlibrary_api = OpenLibraryAPI()
