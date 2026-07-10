from django.urls import path
from . import views

urlpatterns = [
    path('satellite_view/', views.satellite_view, name='satellite_view'),
    path('', views.rainfall_raster, name='rainfall_raster'),
    path("sentinel/",views.sentinel_truecolour,name="sentinel_truecolour"),
    path("sentinel/<int:year>/<int:month>/",views.sentinel_truecolour,name="sentinel_truecolour_date"),
       
]
