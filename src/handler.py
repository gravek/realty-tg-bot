import asyncio
import logging
from src.main import process_event

# Configure logging
logging.basicConfig(level=logging.INFO)

def handler(event, context):
    """
    Entry point for Yandex Cloud Function
    """
    try:
        # Run async function in event loop
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(process_event(event, context))
        return result
    except Exception as e:
        logging.error(f"Error in handler: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }