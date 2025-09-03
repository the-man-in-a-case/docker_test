from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import User
from .serializers import UserAuthSerializer, TokenSerializer
import jwt
import requests
from django.conf import settings
from datetime import datetime, timedelta

class AuthViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def login(self, request):
        """用户登录并获取token"""
        email = request.data.get('email')
        password = request.data.get('password')
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                # 生成JWT token
                payload = {
                    'user_id': str(user.id),
                    'email': user.email,
                    'exp': datetime.utcnow() + timedelta(days=1)
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                
                return Response({
                    'token': token,
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'username': user.username
                    }
                })
            else:
                return Response(
                    {'error': 'Invalid credentials'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """验证用户token并返回用户信息"""
        token = request.META.get('HTTP_AUTHORIZATION', '').split(' ')[-1]
        
        if not token:
            return Response(
                {'error': 'No token provided'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            
            # 验证通过后，返回用户信息用于Ingress路由
            return Response({
                'user_id': str(user.id),
                'username': user.username,
                'email': user.email,
                'authenticated': True
            })
        except jwt.ExpiredSignatureError:
            return Response(
                {'error': 'Token expired'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid token'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=False, methods=['post'])
    def register(self, request):
        """用户注册"""
        serializer = UserAuthSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User created successfully',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'healthy'})