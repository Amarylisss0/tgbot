#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль клавиатур для Telegram бота
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from typing import List, Dict

def get_main_menu_keyboard():
    """Главное меню бота"""
    keyboard = [
        [InlineKeyboardButton("📖 Добавить книгу", callback_data="add_book")],
        [InlineKeyboardButton("📚 Моя библиотека", callback_data="my_library")],
        [InlineKeyboardButton("🔍 Поиск книг", callback_data="search_books")],
        [InlineKeyboardButton("✨ Рекомендации", callback_data="recommendations")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_add_book_keyboard():
    """Клавиатура для добавления книги"""
    keyboard = [
        [InlineKeyboardButton("🌐 Найти в общей библиотеке", callback_data="search_multiple_sources")],
        [InlineKeyboardButton("📝 Добавить вручную", callback_data="add_manual")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_book_sources_keyboard():
    """Клавиатура для выбора источника книг"""
    keyboard = [
        [InlineKeyboardButton("📚 Open Library", callback_data="source_openlibrary")],
        [InlineKeyboardButton("📖 Google Books", callback_data="source_googlebooks")],
        [InlineKeyboardButton("🏛️ Library of Congress", callback_data="source_loc")],
        [InlineKeyboardButton("📘 ISBNDB", callback_data="source_isbndb")],
        [InlineKeyboardButton("🔍 Все источники", callback_data="source_all")],
        [InlineKeyboardButton("🔙 Назад", callback_data="add_book")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_library_menu_keyboard():
    """Клавиатура для библиотеки"""
    keyboard = [
        [InlineKeyboardButton("📋 Все книги", callback_data="library_all")],
        [InlineKeyboardButton("🔤 Сортировка", callback_data="library_sort")],
        [InlineKeyboardButton("🔍 Поиск", callback_data="library_search")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_sort_keyboard():
    """Клавиатура для сортировки"""
    keyboard = [
        [InlineKeyboardButton("📅 По дате добавления", callback_data="sort_date")],
        [InlineKeyboardButton("🔤 По названию", callback_data="sort_title")],
        [InlineKeyboardButton("👤 По автору", callback_data="sort_author")],
        [InlineKeyboardButton("📂 По жанру", callback_data="sort_genre")],
        [InlineKeyboardButton("⭐ По оценке", callback_data="sort_rating")],
        [InlineKeyboardButton("🔙 Назад", callback_data="my_library")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_book_actions_keyboard(book_id: int, in_library: bool = False):
    """Клавиатура действий с книгой"""
    keyboard = []
    
    if not in_library:
        keyboard.append([InlineKeyboardButton("➕ Добавить в библиотеку", 
                                            callback_data=f"add_to_library_{book_id}")])
    else:
        keyboard.extend([
            [InlineKeyboardButton("✏️ Изменить оценку", callback_data=f"edit_rating_{book_id}")],
            [InlineKeyboardButton("🗑️ Удалить из библиотеки", callback_data=f"remove_book_{book_id}")]
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="my_library")])
    return InlineKeyboardMarkup(keyboard)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict

def get_search_results_keyboard(
    books: List[Dict],
    page: int,
    total_pages: int,
    source: str = "openlibrary"
) -> InlineKeyboardMarkup:
    """
    books        — список книг на текущей странице,
    page         — индекс текущей страницы (0-based),
    total_pages  — общее число страниц,
    source       — 'openlibrary' или 'database'.
    """
    keyboard = []
    # 1) Кнопки для каждой книги
    for idx, book in enumerate(books):
        if source == "openlibrary":
            cb = f"ol_book_{page}_{idx}"
        else:
            cb = f"db_book_{book.get('external_id','')}"
        title = book.get("title", "Без названия")[:30]
        author = book.get("author", "Неизвестный")[:20]
        keyboard.append([
            InlineKeyboardButton(f"📖 {title} — {author}", callback_data=cb)
        ])

    # 2) Навигационная строка
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"search_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️ Далее", callback_data=f"search_page_{page+1}"))
    keyboard.append(nav)

    # 3) В главное меню
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(keyboard)

def get_pagination_keyboard(page: int, total_pages: int, action_prefix: str):
    """Универсальная клавиатура пагинации"""
    keyboard = []
    
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{action_prefix}_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"{action_prefix}_{page+1}"))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="my_library")])
    
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action: str, item_id: int):
    """Клавиатура подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ Нет", callback_data="my_library")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_rating_keyboard(book_id: int):
    """Клавиатура для выбора оценки"""
    keyboard = []
    
    # Первый ряд: 1-5
    row1 = [InlineKeyboardButton(str(i), callback_data=f"rate_{book_id}_{i}") for i in range(1, 6)]
    keyboard.append(row1)
    
    # Второй ряд: 6-10
    row2 = [InlineKeyboardButton(str(i), callback_data=f"rate_{book_id}_{i}") for i in range(6, 11)]
    keyboard.append(row2)
    
    keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="my_library")])
    
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)

def get_recommendations_keyboard():
    """Клавиатура для рекомендаций"""
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить рекомендации", callback_data="refresh_recommendations")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_book_detail_keyboard(book_id: int, in_library: bool = False, source: str = "db"):
    """Детальная клавиатура для отдельной книги"""
    keyboard = []
    
    if not in_library:
        if source == "openlibrary":
            keyboard.append([InlineKeyboardButton("➕ Добавить в библиотеку", 
                                                callback_data=f"add_ol_book_{book_id}")])
        else:
            keyboard.append([InlineKeyboardButton("➕ Добавить в библиотеку", 
                                                callback_data=f"add_to_library_{book_id}")])
    else:
        keyboard.extend([
            [InlineKeyboardButton("✏️ Изменить оценку", callback_data=f"edit_rating_{book_id}")],
            [InlineKeyboardButton("🗑️ Удалить", callback_data=f"confirm_remove_{book_id}")]
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="my_library")])
    
    return InlineKeyboardMarkup(keyboard)
