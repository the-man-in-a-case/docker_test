from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.utils import timezone
# from shared.models import TenantUser
from shared.utils import jwt_decode, sign_headers
from authsvc.cache_utils import cache_result  # 导入缓存装饰器



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from shared.utils import sign_headers
from django.utils import timezone

User = get_user_model()

@cache_result(timeout=300, key_prefix="auth_validate")  # 添加缓存装饰器，缓存300秒
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        """
        body: { "username": "...", "password": "..." }
        return: { "access": "...", "refresh": "...", "role": "admin/tenant" }
        """
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=401)
        if not user.is_active:
            return Response({"detail": "User inactive"}, status=403)

        rf = RefreshToken.for_user(user)
        # 可在 claim 中加入角色、命名空间，供后端直读（也会被验证）
        rf["uid"] = user.id
        rf["role"] = user.role
        rf["ns"] = user.namespace
        access = str(rf.access_token)
        refresh = str(rf)

        user.last_login = timezone.now()
        user.last_access_at = timezone.now()
        user.save(update_fields=["last_login", "last_access_at"])
        return Response({"access": access, "refresh": refresh, "role": user.role})

class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        """
        body: { "refresh": "<token>" }
        """
        try:
            refresh = RefreshToken(request.data.get("refresh"))
            # rotate + blacklist 由 SIMPLE_JWT 控制
            access = str(refresh.access_token)
            return Response({"access": access})
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=401)

class LogoutView(APIView):
    """
    将 refresh token 拉黑，实现登出（Access 自然过期；也可改短 Access 时长实现“超时登出”）
    """
    permission_classes = [permissions.IsAuthenticated]  # 要求持有 Access
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "refresh required"}, status=400)
        try:
            rt = RefreshToken(refresh)
            rt.blacklist()
            return Response({"detail": "ok"})
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=400)

@cache_result(timeout=300, key_prefix="auth_validate")  # 添加缓存装饰器，缓存300秒
class ValidateView(APIView):
    """
    供 Ingress external auth 使用：
    - 从 Cookie: session=<jwt> 或 Authorization: Bearer <jwt> 读取 token
    - 验签并检查过期
    - 回写 X-User-ID / X-User-NS / X-Route-*
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]  # 允许直接用 Bearer 校验

    def _extract_token(self, request):
        c = request.COOKIES.get("session")
        if c: return c
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return None

    def post(self, request):
        token = self._extract_token(request)
        if not token:
            return Response(status=401)

        # 用 SimpleJWT 解码验证
        try:
            validated = JWTAuthentication().get_validated_token(token)
            uid = int(validated.get("uid"))
            ns = validated.get("ns")
            role = validated.get("role")
        except Exception:
            # 兼容：若你仍允许 legacy_token，则在这里 fallback（可选）
            return Response(status=401)

        # 若需要可检查数据库用户状态
        try:
            user = User.objects.get(id=uid, is_active=True)
        except User.DoesNotExist:
            return Response(status=401)

        user.last_access_at = timezone.now()
        user.save(update_fields=["last_access_at"])

        ts, sig = sign_headers(uid, ns)
        resp = Response(status=200)
        resp['X-User-ID'] = str(uid)
        resp['X-User-NS'] = ns
        resp['X-User-Role'] = role
        resp['X-Route-Timestamp'] = str(ts)
        resp['X-Route-Signature'] = sig
        return resp

# def _extract_token(request):
#     c = request.COOKIES.get('session')
#     if c: return c
#     auth = request.META.get('HTTP_AUTHORIZATION', '')
#     if auth.lower().startswith('bearer '):
#         return auth[7:].strip()
#     return None

# @api_view(['GET','POST'])
# @cache_result(timeout=300, key_prefix="auth_validate")  # 添加缓存装饰器，缓存300秒
# def validate(request):
#     token = _extract_token(request)
#     if not token:
#         return Response(status=status.HTTP_401_UNAUTHORIZED)

#     # 支持两种：纯 token 或 JWT
#     user = None
#     try:
#         payload = jwt_decode(token)
#         uid = int(payload.get('uid'))
#         user = TenantUser.objects.get(id=uid)
#     except Exception:
#         try:
#             user = TenantUser.objects.get(token=token)
#         except TenantUser.DoesNotExist:
#             return Response(status=status.HTTP_401_UNAUTHORIZED)

#     # 更新最后访问时间（供资源回收）
#     user.last_access_at = timezone.now()
#     user.save(update_fields=['last_access_at'])

#     ts, sig = sign_headers(user.id, user.namespace)
#     resp = Response(status=status.HTTP_200_OK)
#     resp['X-User-ID'] = str(user.id)
#     resp['X-User-NS'] = user.namespace
#     resp['X-Route-Timestamp'] = str(ts)
#     resp['X-Route-Signature'] = sig
#     return resp

@api_view(['GET'])
def health(request):
    """健康检查端点，返回服务状态"""
    try:
        # 检查数据库连接
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return Response({
            "status": "healthy",
            "service": "authsvc",
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "status": "unhealthy",
            "service": "authsvc",
            "error": str(e),
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
