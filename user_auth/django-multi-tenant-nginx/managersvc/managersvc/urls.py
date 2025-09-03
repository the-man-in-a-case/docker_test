"""
URL configuration for managersvc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.http import JsonResponse
# from shared.models import TenantUser
from django.contrib.auth import get_user_model
User = get_user_model()
from shared.utils import jwt_encode
from django.contrib import admin
from users.views import health
from users.views import EnsureUserDeployment 

def issue_jwt(request, uid:int):
    try:
        # u = TenantUser.objects.get(id=uid)
        u = User.objects.get(id=uid)
        return JsonResponse({"token": jwt_encode({"uid": u.id})})
    except User.DoesNotExist:
        return JsonResponse({"error":"not found"}, status=404)

urlpatterns = [ path('issue-jwt/<int:uid>/', issue_jwt),
                path('health', health),
                path('wakeup/', EnsureUserDeployment.as_view()),
                # path('scale-down', ScaleDownUserDeployment.as_view()),
                # path('scale-up', ScaleUpUserDeployment.as_view()),
                path('admin/', admin.site.urls)]

