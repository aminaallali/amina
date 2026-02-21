import os
from datetime import timedelta


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///jibas.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(64).hex())
    JWT_SECRET = os.getenv("JWT_SECRET", os.urandom(64).hex())
    JWT_EXPIRATION = timedelta(minutes=30)

    WHEEL_SIZE = 20
    NUM_WHEELS = 2
    MAX_CATEGORIES = 2
    CHALLENGE_EXPIRY = 120
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 900
    SHUFFLE_ENTROPY_BITS = 256

    IMAGE_POOL_SIZE = 100
    IMAGE_SERVE_FORMAT = "webp"
    IMAGE_TILE_SIZE = (80, 80)
    CANVAS_WIDTH = 800
    CANVAS_HEIGHT = 400

    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_WINDOW = 60

    MIN_INTERACTION_TIME = 2.0
    MIN_MOVEMENT_EVENTS = 3
    REQUIRE_DIRECTION_CHANGE = True

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
