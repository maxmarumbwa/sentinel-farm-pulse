from django.urls import path
from . import views

app_name = 'fields_admin'

urlpatterns = [
    path('fields/digitize/', views.digitize_field, name='digitize_field'),
    path('api/fields/', views.api_create_field, name='api_create_field'),
    path('api/admin2/', views.api_admin2, name='api_admin2'),
    #path('fields/digitize-sentinel/', views.sentinel_monthly_composite, name='digitize_sentinel'),
]