#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль рекомендательной системы
"""

import logging
from typing import List, Dict, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from database.db import (
    get_user_books, get_user_genres_and_ratings, 
    search_books_in_db, get_connection
)
from services.openlibrary import openlibrary_api
from config import MAX_RECOMMENDATIONS

logger = logging.getLogger(__name__)

class RecommendationSystem:
    """Система рекомендаций книг"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
    
    def get_recommendations(self, user_id: int) -> List[Dict]:
        """Получение персональных рекомендаций для пользователя"""
        try:
            user_books = get_user_books(user_id)
            if len(user_books) <= 2:
                return self._get_popular_books()
            
            # Комбинируем разные подходы к рекомендациям
            genre_recs = self._get_genre_based_recommendations(user_id)
            content_recs = self._get_content_based_recommendations(user_id)
            
            import random
            all_recommendations = genre_recs + content_recs
            unique_recs = self._remove_duplicates(all_recommendations)
            
            user_book_ids = {b['id'] for b in user_books}
            # Фильтруем персональные рекомендации

            personal_recs = [b for b in unique_recs if b['id'] not in user_book_ids]
            # Рандомизируем порядок
            random.shuffle(personal_recs)

            if personal_recs:
                return personal_recs[:MAX_RECOMMENDATIONS]
            # Иначе — переходим к фоллбэку популярных
            popular = self._get_popular_books()
            # Фильтруем популярных от того же
            popular = [b for b in popular if b['id'] not in user_book_ids]
            random.shuffle(popular)
            return popular[:MAX_RECOMMENDATIONS]
            
        except Exception as e:
            logger.error(f"Ошибка при генерации рекомендаций для пользователя {user_id}: {e}")
            return self._get_popular_books()
    
    def _get_genre_based_recommendations(self, user_id: int) -> List[Dict]:
        """Рекомендации на основе предпочитаемых жанров"""
        try:
            user_genres = get_user_genres_and_ratings(user_id)
            if not user_genres:
                return []
            
            # Берем жанры с высокой оценкой (>= 7)
            preferred_genres = [
                genre for genre, avg_rating, count in user_genres
                if avg_rating >= 5.0
            ]
            
            if not preferred_genres:
                # Если нет высоких оценок, берем топ-3 жанра
                preferred_genres = [genre for genre, _, _ in user_genres[:3]]
            
            recommendations = []
            for genre in preferred_genres[:3]:  # Ограничиваем количество жанров
                genre_books = self._find_books_by_genre(genre, limit=5)
                recommendations.extend(genre_books)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Ошибка при поиске рекомендаций по жанрам: {e}")
            return []
    
    def _get_content_based_recommendations(self, user_id: int) -> List[Dict]:
        """Рекомендации на основе содержания книг (TF-IDF)"""
        try:
            user_books = get_user_books(user_id)
            high_rated_books = [
                book for book in user_books 
                if book.get('user_rating', 0) >= 5
            ]
            
            if not high_rated_books:
                return []
            
            # Подготавливаем тексты для анализа
            user_texts = []
            for book in high_rated_books:
                text_parts = []
                if book.get('title'):
                    text_parts.append(book['title'])
                if book.get('author'):
                    text_parts.append(book['author'])
                if book.get('genre'):
                    text_parts.append(book['genre'])
                if book.get('description'):
                    text_parts.append(book['description'][:500])  # Ограничиваем длину
                
                user_texts.append(' '.join(text_parts))
            
            if not user_texts:
                return []
            
            # Получаем кандидатов для рекомендаций
            candidate_books = self._get_candidate_books()
            if not candidate_books:
                return []
            
            candidate_texts = []
            for book in candidate_books:
                text_parts = []
                if book.get('title'):
                    text_parts.append(book['title'])
                if book.get('author'):
                    text_parts.append(book['author'])
                if book.get('genre'):
                    text_parts.append(book['genre'])
                if book.get('description'):
                    text_parts.append(book['description'][:500])
                
                candidate_texts.append(' '.join(text_parts))
            
            # Вычисляем TF-IDF и схожесть
            all_texts = user_texts + candidate_texts
            
            if len(all_texts) < 2:
                return []
            
            try:
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(all_texts)
            except ValueError:
                # Если не удается построить TF-IDF (например, все тексты пустые)
                return []
            
            user_matrix = tfidf_matrix[:len(user_texts)]
            candidate_matrix = tfidf_matrix[len(user_texts):]
            
            # Вычисляем среднюю схожесть с пользовательскими книгами
            similarities = cosine_similarity(candidate_matrix, user_matrix)
            avg_similarities = np.mean(similarities, axis=1)
            
            # Сортируем кандидатов по схожести
            sorted_indices = np.argsort(avg_similarities)[::-1]
            
            recommendations = []
            for idx in sorted_indices[:10]:  # Топ-10 похожих книг
                if avg_similarities[idx] > 0.05:  # Минимальный порог схожести
                    book = candidate_books[idx].copy()
                    book['similarity_score'] = float(avg_similarities[idx])
                    recommendations.append(book)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Ошибка при контент-анализе: {e}")
            return []
    
    def _find_books_by_genre(self, genre: str, limit: int = 5) -> List[Dict]:
        """Поиск книг по жанру в локальной базе"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, title, author, genre, description, cover_url, publication_year
                    FROM books 
                    WHERE genre LIKE ?
                    ORDER BY RANDOM()
                    LIMIT ?
                ''', (f'%{genre}%', limit))
                
                rows = cursor.fetchall()
                books = []
                for row in rows:
                    books.append({
                        'id': row[0],
                        'title': row[1],
                        'author': row[2],
                        'genre': row[3],
                        'description': row[4],
                        'cover_url': row[5],
                        'publication_year': row[6],
                        'recommendation_type': 'genre_based'
                    })
                
                return books
                
        except Exception as e:
            logger.error(f"Ошибка при поиске книг по жанру {genre}: {e}")
            return []
    
    def _get_candidate_books(self, limit: int = 100) -> List[Dict]:
        """Получение кандидатов для контент-анализа"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, title, author, genre, description, cover_url, publication_year
                    FROM books 
                    WHERE description IS NOT NULL AND description != ''
                    ORDER BY RANDOM()
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                books = []
                for row in rows:
                    books.append({
                        'id': row[0],
                        'title': row[1],
                        'author': row[2],
                        'genre': row[3],
                        'description': row[4],
                        'cover_url': row[5],
                        'publication_year': row[6],
                        'recommendation_type': 'content_based'
                    })
                
                return books
                
        except Exception as e:
            logger.error(f"Ошибка при получении кандидатов: {e}")
            return []
    
    def _get_popular_books(self, limit: int = 10) -> List[Dict]:
        """Получение популярных книг для новых пользователей"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT b.id, b.title, b.author, b.genre, b.description, 
                           b.cover_url, b.publication_year, COUNT(ub.book_id) as popularity
                    FROM books b
                    LEFT JOIN user_books ub ON b.id = ub.book_id
                    GROUP BY b.id
                    ORDER BY popularity DESC, b.id DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                books = []
                for row in rows:
                    books.append({
                        'id': row[0],
                        'title': row[1],
                        'author': row[2],
                        'genre': row[3],
                        'description': row[4],
                        'cover_url': row[5],
                        'publication_year': row[6],
                        'recommendation_type': 'popular'
                    })
                
                return books
                
        except Exception as e:
            logger.error(f"Ошибка при получении популярных книг: {e}")
            return []
    
    def _remove_duplicates(self, books: List[Dict]) -> List[Dict]:
        """Удаление дубликатов из списка книг"""
        seen_ids = set()
        unique_books = []
        
        for book in books:
            book_id = book.get('id')
            if book_id and book_id not in seen_ids:
                seen_ids.add(book_id)
                unique_books.append(book)
        
        return unique_books

# Создаем глобальный экземпляр системы рекомендаций
recommendation_system = RecommendationSystem()
