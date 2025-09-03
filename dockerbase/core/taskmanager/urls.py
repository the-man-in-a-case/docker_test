from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_task, name='create_task'),
    path('status/<uuid:task_id>/', views.get_task_status, name='get_task_status'),
]