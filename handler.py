import asyncio
import logging
import nest_asyncio  # Для nested loops в serverless

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорт process_event из main
from main import process_event

def handler(event, context):
    """
    Entry point for Yandex Cloud Function
    """
    nest_asyncio.apply()  # Разрешаем nested loops
    
    try:
        # Yandex CF уже имеет loop, используем run_until_complete без new_event_loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(process_event(event, context))
        
        # Не закрываем loop вручную — пусть Yandex управляет
        return result
    except Exception as e:
        logger.error(f"Error in handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': str(e)
        }