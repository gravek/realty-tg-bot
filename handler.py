import asyncio
import logging
import json
import os
import sys

# Добавляем текущую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем логирование до импорта других модулей
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    from main import process_event
    logger.info("Successfully imported process_event from main.py")
except ImportError as e:
    logger.error(f"Failed to import process_event from main.py: {e}")
    logger.error(f"Python path: {sys.path}")
    logger.error(f"Current directory contents: {os.listdir('.')}")
    raise

def handler(event, context):
    """
    Entry point for Yandex Cloud Function
    """
    try:
        logger.info(f"Handler called with event: {event}")
        logger.info(f"Context: {context}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Directory contents: {os.listdir('.')}")
        
        # Проверяем наличие необходимых файлов
        required_files = ['main.py', 'handler.py', 'requirements.txt']
        for file in required_files:
            if os.path.exists(file):
                logger.info(f"File {file} exists")
            else:
                logger.error(f"File {file} does not exist")
        
        # Create new event loop for each request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run async function
        result = loop.run_until_complete(process_event(event, context))
        loop.close()
        
        logger.info(f"Function result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': str(e)
        }