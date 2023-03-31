import os
import time
from typing import Dict

import jwt

JWT_SECRET = os.environ.get("SESSION_SECRET")
JWT_ALGORITHM = "HS256"


def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], audience='flowxo')
        return decoded_token if decoded_token["exp"] >= time.time() else None
    except Exception as e:
        return {}