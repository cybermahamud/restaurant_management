# apps/common/urls.py
from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]