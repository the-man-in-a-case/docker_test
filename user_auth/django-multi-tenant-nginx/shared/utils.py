import hmac, time, hashlib, jwt
from django.conf import settings

def jwt_encode(payload: dict, ttl_sec: int = 3600):
    return jwt.encode(
        {**payload, "exp": int(time.time()) + ttl_sec},
        settings.JWT_SECRET, algorithm="HS256"
    )

def jwt_decode(token: str):
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])

def sign_headers(user_id: int, namespace: str, ts: int | None = None):
    """生成 HMAC-SHA256 签名，供 Ingress→Dispatcher→后端校验防伪造"""
    ts = ts or int(time.time())
    msg = f"{user_id}:{namespace}:{ts}".encode()
    sig = hmac.new(settings.ROUTE_SIGNING_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return ts, sig
