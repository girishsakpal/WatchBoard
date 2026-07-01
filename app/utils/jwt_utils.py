"""
JWT helpers. Fails loudly at import time if JWT_SECRET is missing,
rather than silently signing tokens with an empty/default secret.
"""
import os
import datetime
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set. Refusing to start without it.")

TOKEN_TTL = datetime.timedelta(days=7)
ALGORITHM = "HS256"


def sign_token(payload: dict) -> str:
    to_encode = {
        **payload,
        "exp": datetime.datetime.now(datetime.timezone.utc) + TOKEN_TTL,
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
