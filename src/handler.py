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
        # Create new event loop for each request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run async function
        result = loop.run_until_complete(process_event(event, context))
        loop.close()
        
        return result
    except Exception as e:
        logging.error(f"Error in handler: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }