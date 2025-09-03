from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, health_check

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health_check, name='health_check'),
]