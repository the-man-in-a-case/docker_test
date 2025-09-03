from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class UpdateLastAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            # 轻量更新（避免每次写库的开销，可以加节流，例如每 60s 才写）
            user.last_access_at = timezone.now()
            user.save(update_fields=["last_access_at"])
