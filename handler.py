import asyncio
import logging
from main import process_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_event(event, context))
        return result
    except Exception as e:
        logger.error(f"Error in handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': str(e)
        }