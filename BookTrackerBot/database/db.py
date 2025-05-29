#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль работы с базой данных SQLite
"""

import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

def get_connection():
    """Получение соединения с базой данных"""
    return sqlite3.connect(DATABASE_PATH)

def init_database():
    """Инициализация базы данных и создание таблиц"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица книг в глобальной базе
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT,
                    description TEXT,
                    openlibrary_id TEXT UNIQUE,
                    cover_url TEXT,
                    publication_year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица личных библиотек пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    user_rating INTEGER CHECK(user_rating >= 1 AND user_rating <= 10),
                    user_notes TEXT,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (book_id) REFERENCES books (id),
                    UNIQUE(user_id, book_id)
                )
            ''')
            
            # Таблица состояний пользователей для мультишагового диалога
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    state TEXT,
                    data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
            logger.info("База данных успешно инициализирована")
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

def add_or_update_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавление или обновление пользователя"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при добавлении/обновлении пользователя {user_id}: {e}")
        raise

def add_book_to_global(title: str, author: str, genre: str = None, description: str = None, 
                      openlibrary_id: str = None, cover_url: str = None, 
                      publication_year: int = None) -> int:
    """Добавление книги в глобальную базу"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO books (title, author, genre, description, openlibrary_id, cover_url, publication_year)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, author, genre, description, openlibrary_id, cover_url, publication_year))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Книга уже существует, возвращаем её ID
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM books WHERE openlibrary_id = ?', (openlibrary_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при добавлении книги в глобальную базу: {e}")
        raise

def add_book_to_user_library(user_id: int, book_id: int, rating: int = None, notes: str = None):
    """Добавление книги в личную библиотеку пользователя"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_books (user_id, book_id, user_rating, user_notes)
                VALUES (?, ?, ?, ?)
            ''', (user_id, book_id, rating, notes))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при добавлении книги в библиотеку пользователя {user_id}: {e}")
        raise

def get_user_books(user_id: int, sort_by: str = 'date_added', search_query: str = None) -> List[Dict]:
    """Получение книг пользователя с сортировкой и поиском"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            base_query = '''
                SELECT b.id, b.title, b.author, b.genre, b.description, b.cover_url, 
                       b.publication_year, ub.user_rating, ub.user_notes, ub.date_added
                FROM user_books ub
                JOIN books b ON ub.book_id = b.id
                WHERE ub.user_id = ?
            '''
            
            params = [user_id]
            
            # Добавление поиска
            if search_query:
                base_query += ' AND (b.title LIKE ? OR b.author LIKE ? OR b.genre LIKE ?)'
                search_pattern = f'%{search_query}%'
                params.extend([search_pattern, search_pattern, search_pattern])
            
            # Добавление сортировки
            if sort_by == 'title':
                base_query += ' ORDER BY b.title'
            elif sort_by == 'author':
                base_query += ' ORDER BY b.author'
            elif sort_by == 'genre':
                base_query += ' ORDER BY b.genre'
            elif sort_by == 'rating':
                base_query += ' ORDER BY ub.user_rating DESC'
            else:  # date_added
                base_query += ' ORDER BY ub.date_added DESC'
            
            cursor.execute(base_query, params)
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
                    'user_rating': row[7],
                    'user_notes': row[8],
                    'date_added': row[9]
                })
            
            return books
            
    except Exception as e:
        logger.error(f"Ошибка при получении книг пользователя {user_id}: {e}")
        raise

def get_book_by_id(book_id: int) -> Optional[Dict]:
    """Получение книги по ID"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, author, genre, description, cover_url, publication_year
                FROM books WHERE id = ?
            ''', (book_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'author': row[2],
                    'genre': row[3],
                    'description': row[4],
                    'cover_url': row[5],
                    'publication_year': row[6]
                }
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении книги по ID {book_id}: {e}")
        raise

def remove_book_from_user_library(user_id: int, book_id: int):
    """Удаление книги из личной библиотеки пользователя"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_books WHERE user_id = ? AND book_id = ?', 
                         (user_id, book_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при удалении книги из библиотеки пользователя {user_id}: {e}")
        raise

def update_user_book_rating(user_id: int, book_id: int, rating: int):
    """Обновление оценки книги пользователем"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_books SET user_rating = ? 
                WHERE user_id = ? AND book_id = ?
            ''', (rating, user_id, book_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при обновлении оценки книги: {e}")
        raise

def get_user_genres_and_ratings(user_id: int) -> List[Tuple[str, float]]:
    """Получение жанров и средних оценок пользователя для рекомендаций"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.genre, AVG(ub.user_rating) as avg_rating, COUNT(*) as count
                FROM user_books ub
                JOIN books b ON ub.book_id = b.id
                WHERE ub.user_id = ? AND b.genre IS NOT NULL AND ub.user_rating IS NOT NULL
                GROUP BY b.genre
                ORDER BY avg_rating DESC, count DESC
            ''', (user_id,))
            
            return cursor.fetchall()
            
    except Exception as e:
        logger.error(f"Ошибка при получении жанров пользователя {user_id}: {e}")
        raise

def search_books_in_db(query: str, limit: int = 10) -> List[Dict]:
    """Поиск книг в локальной базе данных"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f'%{query}%'
            cursor.execute('''
                SELECT id, title, author, genre, description, cover_url, publication_year
                FROM books 
                WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?
                LIMIT ?
            ''', (search_pattern, search_pattern, search_pattern, limit))
            
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
                    'publication_year': row[6]
                })
            
            return books
            
    except Exception as e:
        logger.error(f"Ошибка при поиске книг в БД: {e}")
        raise

def set_user_state(user_id: int, state: str, data: str = None):
    """Установка состояния пользователя для мультишагового диалога"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_states (user_id, state, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, state, data))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при установке состояния пользователя {user_id}: {e}")
        raise

def get_user_state(user_id: int) -> Optional[Tuple[str, str]]:
    """Получение состояния пользователя"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT state, data FROM user_states WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result if result else (None, None)
    except Exception as e:
        logger.error(f"Ошибка при получении состояния пользователя {user_id}: {e}")
        raise

def clear_user_state(user_id: int):
    """Очистка состояния пользователя"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при очистке состояния пользователя {user_id}: {e}")
        raise

def check_book_in_user_library(user_id: int, book_id: int) -> bool:
    """Проверка наличия книги в библиотеке пользователя"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM user_books WHERE user_id = ? AND book_id = ?', 
                         (user_id, book_id))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке книги в библиотеке: {e}")
        raise
