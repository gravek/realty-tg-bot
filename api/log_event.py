# api/log_event.py
from http.server import BaseHTTPRequestHandler
import json
import os
import redis

redis_client = redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Обработка preflight-запроса для CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')  # кэш на сутки
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            user_id = data.get('user_id')
            
            if not user_id:
                self._send_response(400, {"error": "No user_id"})
                return

            redis_client.rpush(f"user_events:{user_id}", json.dumps(data))
            event_type = data.get('event_type', 'unknown')
            redis_client.hincrby(f"user_stats:{user_id}", event_type, 1)
            redis_client.expire(f"user_events:{user_id}", 60 * 24 * 3600)
            redis_client.expire(f"user_stats:{user_id}", 60 * 24 * 3600)

            self._send_response(200, {"status": "ok"})
        
        except Exception as e:
            self._send_response(500, {"error": str(e)})

    def do_GET(self):
        self._send_response(405, {"error": "Method not allowed"})

    def _send_response(self, status, response_dict):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # на всякий случай
        self.end_headers()
        self.wfile.write(json.dumps(response_dict).encode())