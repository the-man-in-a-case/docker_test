import hmac, hashlib
from django.conf import settings

def verify_internal_signature(request):
    """
    使用 Ingress 注入的 X-Route-* 头来校验 Dispatcher→Manager 的内部调用。
    也可换成 mTLS/NetworkPolicy。
    """
    uid = request.headers.get("X-User-ID", "")
    ns  = request.headers.get("X-User-NS", "")
    ts  = request.headers.get("X-Route-Timestamp", "")
    sig = request.headers.get("X-Route-Signature", "")
    if not (uid and ns and ts and sig):
        return False
    msg = f"{uid}:{ns}:{ts}".encode()
    calc = hmac.new(settings.ROUTE_SIGNING_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, sig)
