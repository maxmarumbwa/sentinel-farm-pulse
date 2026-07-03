from django.urls import path
from . import views

urlpatterns = [
    path('satellite_view/', views.satellite_view, name='satellite_view'),
    path('rainfall_raster/', views.rainfall_raster, name='rainfall_raster'),
]
