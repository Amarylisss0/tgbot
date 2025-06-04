#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль валидации пользовательского ввода
"""

import re
from typing import Optional

def validate_rating(text: str) -> Optional[int]:
    """Валидация оценки книги (1-10)"""
    try:
        rating = int(text.strip())
        if 1 <= rating <= 10:
            return rating
        return None
    except (ValueError, TypeError):
        return None

def validate_text_length(text: str, min_length: int = 1, max_length: int = 1000) -> bool:
    """Валидация длины текста"""
    if not text or not isinstance(text, str):
        return False
    
    text = text.strip()
    return min_length <= len(text) <= max_length

def validate_book_title(title: str) -> bool:
    """Валидация названия книги"""
    return validate_text_length(title, min_length=1, max_length=200)

def validate_author_name(author: str) -> bool:
    """Валидация имени автора"""
    return validate_text_length(author, min_length=1, max_length=100)

def validate_genre(genre: str) -> bool:
    """Валидация жанра"""
    return validate_text_length(genre, min_length=1, max_length=50)

def validate_description(description: str) -> bool:
    """Валидация описания книги"""
    return validate_text_length(description, min_length=0, max_length=1000)

def sanitize_text(text: str) -> str:
    """Очистка текста от потенциально опасных символов"""
    if not text:
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def validate_search_query(query: str) -> bool:
    """Валидация поискового запроса"""
    if not query or not isinstance(query, str):
        return False
    
    query = query.strip()
    
    # Минимум 2 символа, максимум 100
    if len(query) < 2 or len(query) > 100:
        return False
    
    # Проверяем, что есть хотя бы одна буква или цифра
    if not re.search(r'[a-zA-Zа-яА-Я0-9]', query):
        return False
    
    return True

def validate_year(year_str: str) -> Optional[int]:
    """Валидация года публикации"""
    try:
        year = int(year_str.strip())
        # Разумные границы для года публикации
        if 1000 <= year <= 2030:
            return year
        return None
    except (ValueError, TypeError):
        return None

def normalize_author_name(author: str) -> str:
    """Нормализация имени автора"""
    if not author:
        return "Неизвестный автор"
    
    # Удаляем лишние пробелы и приводим к правильному регистру
    author = sanitize_text(author)
    
    # Разбиваем на слова и делаем первую букву заглавной
    words = author.split()
    normalized_words = []
    
    for word in words:
        if word:
            # Делаем первую букву заглавной, остальные строчными
            normalized_word = word[0].upper() + word[1:].lower()
            normalized_words.append(normalized_word)
    
    return ' '.join(normalized_words) if normalized_words else "Неизвестный автор"

def normalize_title(title: str) -> str:
    """Нормализация названия книги"""
    if not title:
        return "Без названия"
    
    title = sanitize_text(title)
    
    # Удаляем лишние кавычки в начале и конце
    title = title.strip('"\'«»""''')
    
    return title if title else "Без названия"

def validate_openlibrary_key(key: str) -> bool:
    """Валидация ключа Open Library"""
    if not key or not isinstance(key, str):
        return False
    
    # Паттерн для ключей Open Library (например: /works/OL123456W)
    pattern = r'^(/works/)?OL\d+[MW]?$'
    return bool(re.match(pattern, key))

def extract_numbers_from_text(text: str) -> Optional[int]:
    """Извлечение числа из текста"""
    if not text:
        return None
    
    # Ищем первое число в тексте
    match = re.search(r'\d+', text)
    if match:
        try:
            return int(match.group())
        except ValueError:
            pass
    
    return None

def is_valid_url(url: str) -> bool:
    """Проверка валидности URL"""
    if not url or not isinstance(url, str):
        return False
    
    # Простая проверка URL
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(url_pattern, url))

def clean_description(description: str) -> str:
    """Очистка описания книги"""
    if not description:
        return ""
    
    # Удаляем HTML теги
    description = re.sub(r'<[^>]+>', '', description)
    
    # Удаляем лишние переносы строк и пробелы
    description = re.sub(r'\n+', '\n', description)
    description = re.sub(r'\s+', ' ', description).strip()
    
    # Ограничиваем длину
    if len(description) > 1000:
        description = description[:997] + "..."
    
    return description
