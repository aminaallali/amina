import functools
from urllib.parse import urlparse

import redis
from flask import jsonify, request

from app.config import Config

parsed = urlparse(Config.REDIS_URL)
host = parsed.hostname or "localhost"
port = parsed.port or 6379
db_num = int(parsed.path.strip("/") or 0) + 1
r = redis.Redis(host=host, port=port, db=db_num)


def rate_limit(requests: int = 10, window: int = 60):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            key = f"ratelimit:{request.remote_addr}:{f.__name__}"
            current = r.get(key)

            if current is None:
                r.setex(key, window, 1)
            elif int(current) >= requests:
                return jsonify({"error": "تم تجاوز الحد المسموح. حاول لاحقاً", "retry_after": r.ttl(key)}), 429
            else:
                r.incr(key)

            return f(*args, **kwargs)

        return wrapper

    return decorator
