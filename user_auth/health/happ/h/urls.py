from django.urls import path
from . import api

urlpatterns = [
    path('users/create/', api.create_user, name='create_user'),
]