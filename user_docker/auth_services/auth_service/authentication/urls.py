# auth_service/auth_service/urls.py (需要创建)
from django.contrib import admin
from django.urls import path, include
from .views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('health/', health_check, name='health_check'),
]