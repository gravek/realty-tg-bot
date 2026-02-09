# api/log_event.py
from http.server import BaseHTTPRequestHandler
import json
import os
import redis
from datetime import datetime

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

            profile_key = f"user_profile:{user_id}"


            redis_client.rpush(f"user_events:{user_id}", json.dumps(data))
            event_type = data.get('event_type', 'unknown')

            if event_type == 'create_profile' and user_id != 'UNRECOGNISED_USER':
                if not redis_client.exists(profile_key):
                    user_info = data.get('details', {}).get('user_info', {})
                    if user_info:
                        redis_client.hset(profile_key, mapping={
                            "username": user_info.get('username', ''),
                            "first_name": user_info.get('first_name', ''),
                            "last_name": user_info.get('last_name', ''),
                            "language_code": user_info.get('language_code', 'ru'),
                            "fetched": datetime.now().isoformat()
                        })
                        redis_client.expire(profile_key, 60 * 24 * 3600)  # 60 дней
                    else:
                        # Если user_info пустой — логируем, но не создаём
                        print(f"Warning: Empty user_info for {user_id}")

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