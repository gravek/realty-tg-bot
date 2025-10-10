import asyncio
import logging
import json
from main import process_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Entry point for Yandex Cloud Function
    """
    try:
        logger.info(f"Received event: {event}")
        
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