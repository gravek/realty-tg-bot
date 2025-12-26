# realty-tg-bot/api/log_event.py
import json
from flask import request, jsonify
import redis
import os

redis_client = redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)

def handler(event, context=None):
    if request.method != 'POST':
        return jsonify({"error": "Method not allowed"}), 405

    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "No user_id"}), 400

    # Сохраняем событие в список (хронология)
    redis_client.rpush(f"user_events:{user_id}", json.dumps(data))
    # Опционально: счётчики
    redis_client.hincrby(f"user_stats:{user_id}", data.get('event_type', 'unknown'), 1)
    # TTL 60 дней
    redis_client.expire(f"user_events:{user_id}", 60 * 24 * 3600)
    redis_client.expire(f"user_stats:{user_id}", 60 * 24 * 3600)

    return jsonify({"status": "ok"})