"""
URL configuration for authsvc project.

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
from django.urls import path
from authsvc.views import validate, health
from authsvc.views import LoginView, RefreshView, LogoutView, ValidateView

urlpatterns = [ 
                path('auth/login', LoginView.as_view()),      # 签发 access + refresh
                path('auth/refresh', RefreshView.as_view()),  # 刷新 access
                path('auth/logout', LogoutView.as_view()),    # 黑名单登出
                path('auth/validate', ValidateView.as_view()), # 给 Ingress 用的“外部认证”
                path('health', health) ]    
