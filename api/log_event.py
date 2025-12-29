# api/log_event.py
from http.server import BaseHTTPRequestHandler
import json
import os
import redis

# Подключаемся к Upstash Redis
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
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No user_id"}).encode())
                return

            # Сохраняем полное событие в список
            redis_client.rpush(f"user_events:{user_id}", json.dumps(data))
            
            # Счётчик событий по типу
            event_type = data.get('event_type', 'unknown')
            redis_client.hincrby(f"user_stats:{user_id}", event_type, 1)
            
            # Устанавливаем TTL 60 дней
            redis_client.expire(f"user_events:{user_id}", 60 * 24 * 3600)
            redis_client.expire(f"user_stats:{user_id}", 60 * 24 * 3600)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        self.send_response(405)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())

    def _send_response(self, status, response_dict):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # на всякий случай
        self.end_headers()
        self.wfile.write(json.dumps(response_dict).encode())