
from django.urls import path
from . import views

urlpatterns = [
    path('satellite_view/', views.satellite_view, name='satellite_view'), 
]

