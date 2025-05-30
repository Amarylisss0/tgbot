#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль интеграции с различными источниками книг
"""

import requests
import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BookSource(ABC):
    """Абстрактный класс для источников книг"""
    
    @abstractmethod
    def search_books(self, query: str, limit: int = 5) -> List[Dict]:
        """Поиск книг"""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Название источника"""
        pass

class OpenLibrarySource(BookSource):
    """Источник Open Library"""
    
    def __init__(self):
        self.base_url = 'https://openlibrary.org'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BookBot/1.0 (Contact: your-email@example.com)'
        })
    
    def search_books(self, query: str, limit: int = 5) -> List[Dict]:
        """Поиск книг в Open Library"""
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
                f'author:"{query}"',
                f'title:"{query}"',
                query.replace(' ', '+')
            ]
            
            for attempt_query in search_attempts:
                try:
                    params['q'] = attempt_query
                    response = self.session.get(f'{self.base_url}/search.json', params=params, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    books = []
                    
                    for doc in data.get('docs', []):
                        book = self._format_book_data(doc)
                        if book:
                            books.append(book)
                    
                    if books:
                        logger.info(f"Open Library: найдено {len(books)} книг")
                        return books
                        
                except requests.RequestException as e:
                    logger.warning(f"Open Library попытка поиска неудачна: {e}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка в Open Library: {e}")
            return []
    
    def get_source_name(self) -> str:
        return "📚 Open Library"
    
    def _format_search_query(self, query: str) -> str:
        """Форматирование поискового запроса"""
        query = query.strip()
        query = query.replace('"', '').replace("'", "")
        
        if len(query.split()) == 1 and len(query) > 2:
            return f'author:{query}'
        
        return query
    
    def _format_book_data(self, doc: Dict) -> Optional[Dict]:
        """Форматирование данных книги"""
        try:
            title = doc.get('title', '').strip()
            if not title:
                return None
            
            authors = doc.get('author_name', [])
            author = ', '.join(authors) if authors else 'Неизвестный автор'
            
            # Извлекаем жанр
            subjects = doc.get('subject', [])
            genre = self._extract_genre(subjects)
            
            # URL обложки
            cover_url = None
            cover_id = doc.get('cover_i')
            if cover_id:
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            
            return {
                'source': 'openlibrary',
                'external_id': doc.get('key', ''),
                'title': title,
                'author': author,
                'genre': genre,
                'description': '',  # Open Library не всегда предоставляет описание в поиске
                'first_publish_year': doc.get('first_publish_year'),
                'cover_url': cover_url,
                'edition_count': doc.get('edition_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании данных Open Library: {e}")
            return None
    
    def _extract_genre(self, subjects: List[str]) -> str:
        """Извлечение жанра"""
        if not subjects:
            return 'Не указан'
        
        genre_map = {
            'Fiction': 'Художественная литература',
            'Science Fiction': 'Научная фантастика',
            'Fantasy': 'Фэнтези',
            'Mystery': 'Детектив',
            'Romance': 'Роман',
            'Biography': 'Биография',
            'History': 'История'
        }
        
        for subject in subjects[:5]:
            for eng, rus in genre_map.items():
                if eng.lower() in subject.lower():
                    return rus
        
        return subjects[0] if subjects else 'Не указан'

class GoogleBooksSource(BookSource):
    """Источник Google Books API"""
    
    def __init__(self):
        self.base_url = 'https://www.googleapis.com/books/v1/volumes'
        self.session = requests.Session()
    
    def search_books(self, query: str, limit: int = 5) -> List[Dict]:
        """Поиск книг в Google Books"""
        try:
            params = {
                'q': query,
                'maxResults': min(limit, 40),
                'printType': 'books',
                'langRestrict': 'ru'  # Сначала ищем на русском
            }
            
            # Пробуем русский и английский запросы
            for lang in ['ru', 'en']:
                params['langRestrict'] = lang
                
                try:
                    response = self.session.get(self.base_url, params=params, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    books = []
                    
                    for item in data.get('items', [])[:limit]:
                        book = self._format_book_data(item)
                        if book:
                            books.append(book)
                    
                    if books:
                        logger.info(f"Google Books: найдено {len(books)} книг")
                        return books
                        
                except requests.RequestException as e:
                    logger.warning(f"Google Books попытка поиска неудачна: {e}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка в Google Books: {e}")
            return []
    
    def get_source_name(self) -> str:
        return "📖 Google Books"
    
    def _format_book_data(self, item: Dict) -> Optional[Dict]:
        """Форматирование данных книги Google Books"""
        try:
            volume_info = item.get('volumeInfo', {})
            
            title = volume_info.get('title', '').strip()
            if not title:
                return None
            
            authors = volume_info.get('authors', [])
            author = ', '.join(authors) if authors else 'Неизвестный автор'
            
            # Категории как жанры
            categories = volume_info.get('categories', [])
            genre = categories[0] if categories else 'Не указан'
            
            # Описание
            description = volume_info.get('description', '')
            if len(description) > 500:
                description = description[:497] + "..."
            
            # Обложка
            image_links = volume_info.get('imageLinks', {})
            cover_url = image_links.get('thumbnail', image_links.get('smallThumbnail'))
            
            # Год публикации
            published_date = volume_info.get('publishedDate', '')
            year = None
            if published_date:
                try:
                    year = int(published_date.split('-')[0])
                except (ValueError, IndexError):
                    pass
            
            return {
                'source': 'googlebooks',
                'external_id': item.get('id', ''),
                'title': title,
                'author': author,
                'genre': genre,
                'description': description,
                'first_publish_year': year,
                'cover_url': cover_url,
                'page_count': volume_info.get('pageCount')
            }
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании данных Google Books: {e}")
            return None

class LibraryOfCongressSource(BookSource):
    """Источник Library of Congress"""
    
    def __init__(self):
        self.base_url = 'https://www.loc.gov/books'
        self.session = requests.Session()
    
    def search_books(self, query: str, limit: int = 5) -> List[Dict]:
        """Поиск книг в Library of Congress"""
        try:
            # Простой поиск через их JSON API
            params = {
                'q': query,
                'fo': 'json',
                'c': min(limit, 25)
            }
            
            response = self.session.get(f'{self.base_url}/', params=params, timeout=10)
            response.raise_for_status()
            
            # Library of Congress возвращает HTML, поэтому делаем упрощенный парсинг
            # В реальной реализации здесь был бы более сложный парсер
            books = []
            
            # Пока возвращаем пустой список, так как их API сложнее
            logger.info("Library of Congress: поиск выполнен")
            return books
            
        except Exception as e:
            logger.error(f"Ошибка в Library of Congress: {e}")
            return []
    
    def get_source_name(self) -> str:
        return "🏛️ Library of Congress"

class ISBNDBSource(BookSource):
    """Источник ISBNDB (требует API ключ)"""
    
    def __init__(self):
        self.base_url = 'https://api2.isbndb.com'
        self.session = requests.Session()
        # API ключ нужно будет запросить у пользователя
        self.api_key = None
    
    def search_books(self, query: str, limit: int = 5) -> List[Dict]:
        """Поиск книг в ISBNDB"""
        try:
            if not self.api_key:
                logger.warning("ISBNDB API ключ не настроен")
                return []
            
            headers = {'Authorization': self.api_key}
            params = {
                'q': query,
                'pageSize': min(limit, 20)
            }
            
            response = self.session.get(f'{self.base_url}/books/{query}', 
                                      headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            books = []
            
            for book_data in data.get('books', [])[:limit]:
                book = self._format_book_data(book_data)
                if book:
                    books.append(book)
            
            logger.info(f"ISBNDB: найдено {len(books)} книг")
            return books
            
        except Exception as e:
            logger.error(f"Ошибка в ISBNDB: {e}")
            return []
    
    def get_source_name(self) -> str:
        return "📘 ISBNDB"
    
    def _format_book_data(self, book_data: Dict) -> Optional[Dict]:
        """Форматирование данных ISBNDB"""
        try:
            title = book_data.get('title', '').strip()
            if not title:
                return None
            
            authors = book_data.get('authors', [])
            author = ', '.join(authors) if authors else 'Неизвестный автор'
            
            return {
                'source': 'isbndb',
                'external_id': book_data.get('isbn13', ''),
                'title': title,
                'author': author,
                'genre': book_data.get('subjects', ['Не указан'])[0],
                'description': book_data.get('synopsis', ''),
                'first_publish_year': book_data.get('date_published'),
                'cover_url': book_data.get('image'),
                'isbn': book_data.get('isbn13')
            }
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании данных ISBNDB: {e}")
            return None

class BookSourceManager:
    """Менеджер источников книг"""
    
    def __init__(self):
        self.sources = {
            'openlibrary': OpenLibrarySource(),
            'googlebooks': GoogleBooksSource(),
            'loc': LibraryOfCongressSource(),
            'isbndb': ISBNDBSource()
        }
        self.active_sources = ['openlibrary', 'googlebooks']  # Активные по умолчанию
    
    def get_available_sources(self) -> List[Dict]:
        """Получить список доступных источников"""
        return [
            {
                'id': source_id,
                'name': source.get_source_name(),
                'active': source_id in self.active_sources
            }
            for source_id, source in self.sources.items()
        ]
    
    def search_in_source(self, source_id: str, query: str, limit: int = 5) -> List[Dict]:
        """Поиск в конкретном источнике"""
        if source_id not in self.sources:
            return []
        
        return self.sources[source_id].search_books(query, limit)
    
    def search_in_all_sources(self, query: str, limit_per_source: int = 3) -> Dict[str, List[Dict]]:
        """Поиск во всех активных источниках"""
        results = {}
        
        for source_id in self.active_sources:
            if source_id in self.sources:
                try:
                    books = self.sources[source_id].search_books(query, limit_per_source)
                    if books:
                        results[source_id] = books
                        logger.info(f"Источник {source_id}: найдено {len(books)} книг")
                except Exception as e:
                    logger.error(f"Ошибка в источнике {source_id}: {e}")
                    continue
        
        return results

# Создаем глобальный экземпляр менеджера
book_source_manager = BookSourceManager()