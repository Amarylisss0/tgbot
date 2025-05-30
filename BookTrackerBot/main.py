#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот для учета прочитанных книг с рекомендательной системой
"""

import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
from database.db import init_database
from bot.handlers import (
    start, help_command, add_book_command, my_library_command, 
    recommendations_command, search_books_command, handle_text_message,
    handle_callback_query, cancel_command
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация базы данных
        init_database()
        logger.info("База данных инициализирована")
        
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавление обработчиков команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("add", add_book_command))
        application.add_handler(CommandHandler("library", my_library_command))
        application.add_handler(CommandHandler("recommendations", recommendations_command))
        application.add_handler(CommandHandler("search", search_books_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        
        # Обработчик callback запросов (для inline клавиатур)
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        logger.info("Бот запускается...")
        
        # Запуск бота
        application.run_polling(allowed_updates=['message', 'callback_query'])
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()
