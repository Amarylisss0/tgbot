#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчики команд и сообщений Telegram бота
"""

import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from config import MESSAGES, BOOKS_PER_PAGE
from database.db import (
    add_or_update_user, get_user_books, add_book_to_global, 
    add_book_to_user_library, remove_book_from_user_library,
    update_user_book_rating, search_books_in_db, get_book_by_id,
    set_user_state, get_user_state, clear_user_state,
    check_book_in_user_library
)
from services.openlibrary import openlibrary_api
from services.recommendations import recommendation_system
from services.book_sources import book_source_manager
from bot.keyboards import (
    get_main_menu_keyboard, get_add_book_keyboard, get_library_menu_keyboard,
    get_sort_keyboard, get_book_actions_keyboard, get_search_results_keyboard,
    get_pagination_keyboard, get_confirmation_keyboard, get_rating_keyboard,
    get_cancel_keyboard, get_recommendations_keyboard, get_book_detail_keyboard,
    get_book_sources_keyboard
)
from utils.validators import validate_rating, validate_text_length

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        add_or_update_user(user.id, user.username, user.first_name, user.last_name)
        
        await update.message.reply_text(
            MESSAGES['start'],
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    try:
        await update.message.reply_text(
            MESSAGES['help'],
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в help_command: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def add_book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /add"""
    try:
        await update.message.reply_text(
            "📖 Выберите способ добавления книги:",
            reply_markup=get_add_book_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в add_book_command: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def my_library_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /library"""
    try:
        user_id = update.effective_user.id
        books = get_user_books(user_id)
        
        if not books:
            await update.message.reply_text(
                MESSAGES['empty_library'],
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        await update.message.reply_text(
            f"📚 Ваша библиотека ({len(books)} книг):",
            reply_markup=get_library_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в my_library_command: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def recommendations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /recommendations"""
    try:
        user_id = update.effective_user.id
        recommendations = recommendation_system.get_recommendations(user_id)
        
        if not recommendations:
            await update.message.reply_text(
                MESSAGES['no_recommendations'],
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Показываем первые 3 рекомендации
        message = "✨ Рекомендации для вас:\n\n"
        
        for i, book in enumerate(recommendations[:3], 1):
            message += f"{i}. 📖 *{book['title']}*\n"
            message += f"👤 Автор: {book['author']}\n"
            
            if book.get('genre'):
                message += f"📂 Жанр: {book['genre']}\n"
            
            rec_type = book.get('recommendation_type', 'unknown')
            if rec_type == 'genre_based':
                message += "🎯 На основе ваших предпочтений по жанрам\n"
            elif rec_type == 'content_based':
                message += "🎯 Похожа на ваши любимые книги\n"
            elif rec_type == 'popular':
                message += "🎯 Популярная книга\n"
            
            message += "\n"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_recommendations_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в recommendations_command: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def search_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /search"""
    try:
        user_id = update.effective_user.id
        set_user_state(user_id, 'waiting_search_query')
        
        await update.message.reply_text(
            MESSAGES['enter_search_query'],
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в search_books_command: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cancel"""
    try:
        user_id = update.effective_user.id
        clear_user_state(user_id)
        
        await update.message.reply_text(
            MESSAGES['cancel'],
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_command: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        state, data = get_user_state(user_id)
        
        if state == 'waiting_search_query':
            await handle_search_query(update, context, text)
        elif state == 'adding_manual_book':
            await handle_manual_book_data(update, context, text, data)
        elif state == 'waiting_rating':
            await handle_rating_input(update, context, text, data)
        else:
            # Если нет активного состояния, показываем главное меню
            await update.message.reply_text(
                "Используйте кнопки меню или команды для навигации:",
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка в handle_text_message: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """Обработка поискового запроса"""
    try:
        user_id = update.effective_user.id
        clear_user_state(user_id)
        
        # Получаем выбранный источник
        selected_source = context.user_data.get('selected_source', 'openlibrary')
        
        # Ищем сначала в локальной базе
        local_books = search_books_in_db(query, limit=3)
        
        # Ищем в выбранных источниках
        external_books = []
        
        if selected_source == 'all':
            # Поиск во всех источниках
            all_results = book_source_manager.search_in_all_sources(query, limit_per_source=3)
            for source_id, books in all_results.items():
                external_books.extend(books)
        else:
            # Поиск в конкретном источнике
            external_books = book_source_manager.search_in_source(selected_source, query, limit=5)
        
        if not local_books and not external_books:
            await update.message.reply_text(
                MESSAGES['search_no_results'],
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Сохраняем результаты поиска в контексте
        context.user_data['search_results'] = external_books
        context.user_data['local_results'] = local_books
        context.user_data['search_query'] = query
        
        message = f"🔍 Результаты поиска по запросу '{query}':\n\n"
        
        if local_books:
            message += "📚 Из вашей базы данных:\n"
            for i, book in enumerate(local_books, 1):
                message += f"{i}. {book['title']} - {book['author']}\n"
            message += "\n"
        
        if external_books:
            source_names = {
                'openlibrary': 'Open Library',
                'googlebooks': 'Google Books',
                'loc': 'Library of Congress',
                'isbndb': 'ISBNDB'
            }
            
            if selected_source == 'all':
                message += "🌐 Из внешних источников:\n"
            else:
                source_name = source_names.get(selected_source, 'выбранного источника')
                message += f"🌐 Из {source_name}:\n"
            
            await update.message.reply_text(
                message,
                reply_markup=get_search_results_keyboard(external_books, 0, selected_source)
            )
        else:
            await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_search_query: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def handle_manual_book_data(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, data: str):
    """Обработка ручного ввода данных книги"""
    try:
        user_id = update.effective_user.id
        
        if not data:
            # Начинаем сбор данных - запрашиваем название
            set_user_state(user_id, 'adding_manual_book', json.dumps({'step': 'title', 'data': {}}))
            await update.message.reply_text(
                "📖 Введите название книги:",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        try:
            state_data = json.loads(data)
        except json.JSONDecodeError:
            state_data = {'step': 'title', 'data': {}}
        
        step = state_data.get('step')
        book_data = state_data.get('data', {})
        
        if step == 'title':
            if not validate_text_length(text, max_length=200):
                await update.message.reply_text("❌ Название слишком длинное. Максимум 200 символов.")
                return
            
            book_data['title'] = text
            set_user_state(user_id, 'adding_manual_book', 
                         json.dumps({'step': 'author', 'data': book_data}))
            await update.message.reply_text("👤 Введите автора книги:")
            
        elif step == 'author':
            if not validate_text_length(text, max_length=100):
                await update.message.reply_text("❌ Имя автора слишком длинное. Максимум 100 символов.")
                return
            
            book_data['author'] = text
            set_user_state(user_id, 'adding_manual_book', 
                         json.dumps({'step': 'genre', 'data': book_data}))
            await update.message.reply_text("📂 Введите жанр книги:")
            
        elif step == 'genre':
            if not validate_text_length(text, max_length=50):
                await update.message.reply_text("❌ Название жанра слишком длинное. Максимум 50 символов.")
                return
            
            book_data['genre'] = text
            set_user_state(user_id, 'adding_manual_book', 
                         json.dumps({'step': 'description', 'data': book_data}))
            await update.message.reply_text("📝 Введите краткое описание книги:")
            
        elif step == 'description':
            if not validate_text_length(text, max_length=1000):
                await update.message.reply_text("❌ Описание слишком длинное. Максимум 1000 символов.")
                return
            
            book_data['description'] = text
            set_user_state(user_id, 'adding_manual_book', 
                         json.dumps({'step': 'rating', 'data': book_data}))
            await update.message.reply_text("⭐ Введите вашу оценку книги (от 1 до 10):")
            
        elif step == 'rating':
            rating = validate_rating(text)
            if rating is None:
                await update.message.reply_text(MESSAGES['invalid_rating'])
                return
            
            book_data['rating'] = rating
            
            # Добавляем книгу в базу
            book_id = add_book_to_global(
                title=book_data['title'],
                author=book_data['author'],
                genre=book_data['genre'],
                description=book_data['description']
            )
            
            add_book_to_user_library(user_id, book_id, rating)
            
            clear_user_state(user_id)
            
            await update.message.reply_text(
                MESSAGES['book_added'],
                reply_markup=get_main_menu_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_manual_book_data: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def handle_rating_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, data: str):
    """Обработка ввода оценки"""
    try:
        user_id = update.effective_user.id
        
        rating = validate_rating(text)
        if rating is None:
            await update.message.reply_text(MESSAGES['invalid_rating'])
            return
        
        book_id = int(data)
        update_user_book_rating(user_id, book_id, rating)
        
        clear_user_state(user_id)
        
        await update.message.reply_text(
            MESSAGES['book_updated'],
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_rating_input: {e}")
        await update.message.reply_text(MESSAGES['error'])

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback запросов от inline клавиатур"""
    logger.info(f"Callback получен: {update.callback_query.data} от {update.callback_query.from_user.id}")
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        # ПРИОРИТЕТ: Обработка выбора книги из результатов поиска
        if data.startswith("ol_book_"):
            try:
                # Парсим данные из callback
                parts = data.split("_")
                page = int(parts[2]) if len(parts) > 2 else 0
                book_index = int(parts[3]) if len(parts) > 3 else 0
                
                # Получаем результаты поиска из контекста
                search_results = context.user_data.get('search_results', [])
                
                if book_index >= len(search_results):
                    await query.edit_message_text("❌ Книга не найдена", reply_markup=get_main_menu_keyboard())
                    return
                
                selected_book = search_results[book_index]
                
                # Добавляем книгу в глобальную базу
                book_id = add_book_to_global(
                    title=selected_book.get('title', ''),
                    author=selected_book.get('author', ''),
                    genre=selected_book.get('genre', ''),
                    description=selected_book.get('description', ''),
                    openlibrary_id=selected_book.get('external_id', ''),
                    cover_url=selected_book.get('cover_url', ''),
                    publication_year=selected_book.get('first_publish_year')
                )
                
                # Проверяем, нет ли уже книги в библиотеке пользователя
                if check_book_in_user_library(user_id, book_id):
                    await query.edit_message_text(
                        "📚 Эта книга уже есть в вашей библиотеке!",
                        reply_markup=get_main_menu_keyboard()
                    )
                    return
                
                # Показываем информацию о книге и предлагаем добавить
                title = selected_book.get('title', 'Без названия')
                author = selected_book.get('author', 'Неизвестен')
                
                message = f"📖 {title}\n"
                message += f"👤 Автор: {author}\n"
                
                if selected_book.get('genre'):
                    message += f"📂 Жанр: {selected_book['genre']}\n"
                
                if selected_book.get('first_publish_year'):
                    message += f"📅 Год: {selected_book['first_publish_year']}\n"
                
                if selected_book.get('description'):
                    desc = selected_book['description']
                    if len(desc) > 200:
                        desc = desc[:197] + "..."
                    message += f"📝 Описание: {desc}\n"
                
                message += "\n⭐ Добавить в библиотеку с оценкой:"
                
                await query.edit_message_text(
                    message,
                    reply_markup=get_rating_keyboard(book_id)
                )
                return
            except Exception as e:
                logger.error(f"Ошибка при выборе книги: {e}")
                await query.edit_message_text("❌ Ошибка при добавлении книги", reply_markup=get_main_menu_keyboard())
                return
        elif data.startswith("search_page_"):
        # Парсим номер страницы
            try:
                parts = data.split("_")
                page = int(parts[2])
            except (IndexError, ValueError):
                page = 0

         # Восстанавливаем из контекста все результаты и параметры поиска
            selected_source = context.user_data.get('selected_source', 'openlibrary')
            query_text      = context.user_data.get('search_query', '')
            all_books       = context.user_data.get('search_results', [])

         # Настройки пагинации
            page_size = 5
            total_pages = (len(all_books) + page_size - 1) // page_size
            
        # Корректируем номер страницы в пределах [0, total_pages-1]
            page = max(0, min(page, total_pages - 1))

         # Если страница пустая — сброс на границу
            start = page * page_size
            end   = start + page_size
            page_books = all_books[start:end]

    # Перерисовываем список и навигацию
            await query.edit_message_text(
                 f"🔍 Результаты поиска «{context.user_data.get('search_query')}»\nстраница {page+1}/{total_pages}:",
                 reply_markup=get_search_results_keyboard(
                    books=page_books,
                    page=page,
                    source=context.user_data.get("selected_source","openlibrary")
                )
            )
            return


        elif data.startswith("db_book_"):

            # Раскладываем callback_data: "db_book_<external_id>"
            external_id = data.split("_", 1)[1]
            search_results = context.user_data.get('search_results', [])
            selected_book = next((b for b in search_results if b.get('external_id') == external_id), None)
            if not selected_book:
                await query.edit_message_text("❌ Книга не найдена", reply_markup=get_main_menu_keyboard())
                return

            book_id = add_book_to_global(
                title=selected_book.get('title', ''),
                author=selected_book.get('author', ''),
                genre=selected_book.get('genre', ''),
                description=selected_book.get('description', ''),
                openlibrary_id=selected_book.get('external_id', ''),
                cover_url=selected_book.get('cover_url', ''),
                publication_year=selected_book.get('first_publish_year')
            )

            if check_book_in_user_library(user_id, book_id):
                await query.edit_message_text(
                    "📚 Эта книга уже есть в вашей библиотеке!",
                    reply_markup=get_main_menu_keyboard()
                )
                return

            title = selected_book.get('title', 'Без названия')
            author = selected_book.get('author', 'Неизвестен')
            message = f"📖 {title}\n👤 Автор: {author}\n"
            if selected_book.get('genre'):
                message += f"📂 Жанр: {selected_book['genre']}\n"
            if selected_book.get('first_publish_year'):
                message += f"📅 Год: {selected_book['first_publish_year']}\n"
            if selected_book.get('description'):
                desc = selected_book['description']
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                message += f"📝 Описание: {desc}\n"
            message += "\n⭐ Добавить в библиотеку с оценкой:"

            await query.edit_message_text(
                message,
                reply_markup=get_rating_keyboard(book_id)
            )
            return
        
        # Главное меню
        if data == "main_menu":
            await query.edit_message_text(
                MESSAGES['choose_action'],
                reply_markup=get_main_menu_keyboard()
            )
        
        # Добавление книги
        elif data == "add_book":
            await query.edit_message_text(
                "📖 Выберите способ добавления книги:",
                reply_markup=get_add_book_keyboard()
            )
        
        elif data == "add_manual":
            clear_user_state(user_id)
            set_user_state(user_id, 'adding_manual_book', json.dumps({'step': 'title', 'data': {}}))
            await query.edit_message_text(
                "📖 Введите название книги:",
                reply_markup=get_cancel_keyboard()
            )
        
        elif data == "search_multiple_sources":
            await query.edit_message_text(
                "🌐 Выберите источник для поиска книг:",
                reply_markup=get_book_sources_keyboard()
            )
        
        # Обработка выбора источника
        elif data.startswith("source_"):
            source_type = data[7:]  # Убираем префикс "source_"
            context.user_data['selected_source'] = source_type
            set_user_state(user_id, 'waiting_search_query')
            
            source_names = {
                'openlibrary': '📚 Open Library',
                'googlebooks': '📖 Google Books',
                'loc': '🏛️ Library of Congress',
                'isbndb': '📘 ISBNDB',
                'all': '🔍 Все источники'
            }
            
            source_name = source_names.get(source_type, 'выбранном источнике')
            message = f"🔍 Поиск в {source_name}\n\n" + MESSAGES['enter_search_query']
            
            await query.edit_message_text(
                message,
                reply_markup=get_cancel_keyboard()
            )
        
        # Библиотека
        elif data == "my_library":
            books = get_user_books(user_id)
            if not books:
                await query.edit_message_text(
                    MESSAGES['empty_library'],
                    reply_markup=get_main_menu_keyboard()
                )
            else:
                await query.edit_message_text(
                    f"📚 Ваша библиотека ({len(books)} книг):",
                    reply_markup=get_library_menu_keyboard()
                )
        
        elif data == "library_all":
            await show_user_books(query, user_id)
        
        elif data == "library_sort":
            await query.edit_message_text(
                "🔤 Выберите критерий сортировки:",
                reply_markup=get_sort_keyboard()
            )
        
        elif data.startswith("sort_"):
            sort_by = data[5:]  # Убираем префикс "sort_"
            await show_user_books(query, user_id, sort_by=sort_by)
        
        # Поиск
        elif data == "search_books":
            set_user_state(user_id, 'waiting_search_query')
            await query.edit_message_text(
                MESSAGES['enter_search_query'],
                reply_markup=get_cancel_keyboard()
            )
        
        # Рекомендации
        elif data == "recommendations":
            recommendations = recommendation_system.get_recommendations(user_id)
            
            if not recommendations:
                await query.edit_message_text(
                    MESSAGES['no_recommendations'],
                    reply_markup=get_main_menu_keyboard()
                )
                return
            
            # Показываем рекомендации
            message = "✨ Рекомендации для вас:\n\n"
            
            for i, book in enumerate(recommendations[:5], 1):
                message += f"{i}. 📖 *{book['title']}*\n"
                message += f"👤 {book['author']}\n"
                if book.get('genre'):
                    message += f"📂 {book['genre']}\n"
                message += "\n"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_recommendations_keyboard()
            )
        
        elif data == "refresh_recommendations":
            # Пересчитываем рекомендации
            recommendations = recommendation_system.get_recommendations(user_id)
            
            message = "✨ Обновленные рекомендации:\n\n"
            
            for i, book in enumerate(recommendations[:5], 1):
                message += f"{i}. 📖 *{book['title']}*\n"
                message += f"👤 {book['author']}\n"
                if book.get('genre'):
                    message += f"📂 {book['genre']}\n"
                message += "\n"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=get_recommendations_keyboard()
            )
        
        # Действия с книгами
        elif data.startswith("add_to_library_"):
            book_id = int(data.split("_")[-1])
            
            # Проверяем, нет ли уже книги в библиотеке
            if check_book_in_user_library(user_id, book_id):
                await query.edit_message_text("📚 Эта книга уже есть в вашей библиотеке!")
                return
            
            set_user_state(user_id, 'waiting_rating', str(book_id))
            await query.edit_message_text(
                "⭐ Введите вашу оценку книги (от 1 до 10):",
                reply_markup=get_cancel_keyboard()
            )
        
        elif data.startswith("rate_"):
            # разбираем данные
            _, str_book_id, str_rating = data.split("_")
            book_id = int(str_book_id)
            rating = int(str_rating)

            # если ещё не в библиотеке — вставляем, иначе обновляем
            if not check_book_in_user_library(user_id, book_id):
                add_book_to_user_library(user_id, book_id, rating)
                text = MESSAGES['book_added']      # «Книга добавлена и оценка 
            else:   
                update_user_book_rating(user_id, book_id, rating)
                text = MESSAGES['book_updated']    # «Оценка обновлена»
            await query.edit_message_text(
                text,
                reply_markup=get_main_menu_keyboard()
            )
        
        elif data.startswith("remove_book_"):
            book_id = int(data.split("_")[-1])
            await query.edit_message_text(
                "🗑️ Вы уверены, что хотите удалить эту книгу из библиотеки?",
                reply_markup=get_confirmation_keyboard("remove", book_id)
            )
        

        
        elif data.startswith("confirm_remove_"):
            book_id = int(data.split("_")[-1])
            remove_book_from_user_library(user_id, book_id)
            
            await query.edit_message_text(
                MESSAGES['book_deleted'],
                reply_markup=get_main_menu_keyboard()
            )
        
        elif data.startswith("edit_rating_"):
            book_id = int(data.split("_")[-1])
            await query.edit_message_text(
                "⭐ Выберите новую оценку:",
                reply_markup=get_rating_keyboard(book_id)
            )
        
        # Отмена
        elif data == "cancel":
            clear_user_state(user_id)
            await query.edit_message_text(
                MESSAGES['cancel'],
                reply_markup=get_main_menu_keyboard()
            )
        
        # Помощь
        elif data == "help":
            await query.edit_message_text(
                MESSAGES['help'],
                reply_markup=get_main_menu_keyboard()
            )
        
        # Обработка выбора книги из результатов поиска  
        elif data.startswith("ol_book_"):
            try:
                # Парсим данные из callback
                parts = data.split("_")
                page = int(parts[2]) if len(parts) > 2 else 0
                book_index = int(parts[3]) if len(parts) > 3 else 0
                
                # Получаем результаты поиска из контекста
                search_results = context.user_data.get('search_results', [])
                
                if book_index >= len(search_results):
                    await query.edit_message_text("❌ Книга не найдена", reply_markup=get_main_menu_keyboard())
                    return
                
                selected_book = search_results[book_index]
                
                # Добавляем книгу в глобальную базу
                book_id = add_book_to_global(
                    title=selected_book.get('title', ''),
                    author=selected_book.get('author', ''),
                    genre=selected_book.get('genre', ''),
                    description=selected_book.get('description', ''),
                    openlibrary_id=selected_book.get('external_id', ''),
                    cover_url=selected_book.get('cover_url', ''),
                    publication_year=selected_book.get('first_publish_year')
                )
                
                # Проверяем, нет ли уже книги в библиотеке пользователя
                if check_book_in_user_library(user_id, book_id):
                    await query.edit_message_text(
                        "📚 Эта книга уже есть в вашей библиотеке!",
                        reply_markup=get_main_menu_keyboard()
                    )
                    return
                
                # Показываем информацию о книге и предлагаем добавить
                title = selected_book.get('title', 'Без названия')
                author = selected_book.get('author', 'Неизвестен')
                
                message = f"📖 {title}\n"
                message += f"👤 Автор: {author}\n"
                
                if selected_book.get('genre'):
                    message += f"📂 Жанр: {selected_book['genre']}\n"
                
                if selected_book.get('first_publish_year'):
                    message += f"📅 Год: {selected_book['first_publish_year']}\n"
                
                if selected_book.get('description'):
                    desc = selected_book['description']
                    if len(desc) > 200:
                        desc = desc[:197] + "..."
                    message += f"📝 Описание: {desc}\n"
                
                message += "\n⭐ Добавить в библиотеку с оценкой:"
                
                await query.edit_message_text(
                    message,
                    reply_markup=get_rating_keyboard(book_id)
                )
            except Exception as e:
                logger.error(f"Ошибка при выборе книги: {e}")
                await query.edit_message_text("❌ Ошибка при добавлении книги", reply_markup=get_main_menu_keyboard())
        
        else:
            logger.warning(f"Неизвестный callback_data: {data}")
        
    except BadRequest as e:
        logger.error(f"BadRequest в handle_callback_query: {e}")
    except Exception as e:
        logger.error(f"Ошибка в handle_callback_query: {e}")
        try:
            await update.callback_query.edit_message_text(MESSAGES['error'])
        except:
            pass

async def show_user_books(query, user_id: int, sort_by: str = 'date_added', page: int = 0):
    """Показ книг пользователя с пагинацией"""
    try:
        books = get_user_books(user_id, sort_by=sort_by)
        
        if not books:
            await query.edit_message_text(
                MESSAGES['empty_library'],
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Пагинация
        start_idx = page * BOOKS_PER_PAGE
        end_idx = start_idx + BOOKS_PER_PAGE
        page_books = books[start_idx:end_idx]
        
        total_pages = (len(books) + BOOKS_PER_PAGE - 1) // BOOKS_PER_PAGE
        
        # Формируем сообщение
        sort_names = {
            'date_added': 'дате добавления',
            'title': 'названию',
            'author': 'автору',
            'genre': 'жанру',
            'rating': 'оценке'
        }
        
        message = f"📚 Ваша библиотека (сортировка по {sort_names.get(sort_by, sort_by)}):\n\n"
        
        for i, book in enumerate(page_books, start_idx + 1):
            message += f"{i}. 📖 *{book['title']}*\n"
            message += f"👤 {book['author']}\n"
            
            if book.get('genre'):
                message += f"📂 {book['genre']}\n"
            
            if book.get('user_rating'):
                stars = "⭐" * book['user_rating']
                message += f"⭐ {stars} ({book['user_rating']}/10)\n"
            
            message += "\n"
        
        # Создаем клавиатуру с пагинацией
        keyboard = []
        
        # Кнопки навигации по страницам
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"library_page_{page-1}_{sort_by}"))
            
            nav_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
            
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"library_page_{page+1}_{sort_by}"))
            
            keyboard.append(nav_buttons)
        
        # Кнопки управления
        keyboard.extend([
            [InlineKeyboardButton("🔤 Сортировка", callback_data="library_sort")],
            [InlineKeyboardButton("🔙 Назад", callback_data="my_library")]
        ])
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_user_books: {e}")
        await query.edit_message_text(MESSAGES['error'])
