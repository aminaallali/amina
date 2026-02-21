import hashlib
import json
import secrets
from datetime import datetime

import jwt
import redis


class CryptoService:
    def __init__(self, config):
        self.config = config
        self.redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)

    def generate_jwt(self, user_id: str, username: str) -> str:
        payload = {
            "sub": user_id,
            "username": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.config.JWT_EXPIRATION,
            "jti": secrets.token_hex(16),
        }
        return jwt.encode(payload, self.config.JWT_SECRET, algorithm="HS256")

    def verify_jwt(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.config.JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise ValueError("انتهت صلاحية الجلسة") from exc
        except jwt.InvalidTokenError as exc:
            raise ValueError("رمز جلسة غير صالح") from exc

    def generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def store_temp_data(self, key: str, data: dict, ttl: int = 300):
        self.redis_client.setex(f"jibas:temp:{key}", ttl, json.dumps(data))

    def retrieve_temp_data(self, key: str):
        data = self.redis_client.get(f"jibas:temp:{key}")
        return json.loads(data) if data else None

    def delete_temp_data(self, key: str):
        self.redis_client.delete(f"jibas:temp:{key}")

    def create_composite_hash(self, seed: str, outer_offset: int, inner_offset: int) -> str:
        payload = f"{seed}:{outer_offset}:{inner_offset}"
        return hashlib.pbkdf2_hmac("sha256", payload.encode(), seed.encode(), iterations=100000).hex()
