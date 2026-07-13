from django.urls import path
from . import views

app_name = 'fields_admin'

urlpatterns = [
    path('fields/digitize/', views.digitize_field, name='digitize_field'),
    path('fields/digitize2/', views.digitize_field2, name='digitize_field2'),
    path('api/fields/', views.api_create_field, name='api_create_field'),
    path('api/admin2/', views.api_admin2, name='api_admin2'),
    path("sentinel-test/",views.sentinel_truecolour,name="sentinel_truecolour"),
    #path('fields/digitize-sentinel/', views.sentinel_monthly_composite, name='digitize_sentinel'),
    path('api/test/', views.test_api, name='test_api'),
]