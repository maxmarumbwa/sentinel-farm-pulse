from django.urls import path
from . import views

app_name = 'fields_admin'

urlpatterns = [
    path('fields/digitize/', views.digitize_field, name='digitize_field'),
    path("fields/digitize-sentinel/",views.sentinel_truecolour,name="sentinel_truecolour"),
    path('fields/digitize2/', views.digitize_field2, name='digitize_field2'),
    path('api/fields/', views.api_create_field, name='api_create_field'),
    path('api/admin2/', views.api_admin2, name='api_admin2'),
    path("sentinel-test/",views.sentinel_truecolour,name="sentinel_truecolour-test"),
    #path('fields/digitize-sentinel/', views.sentinel_monthly_composite, name='digitize_sentinel'),
    #################### view digitised farms ###################################
    path('fields/dashboard/', views.field_dashboard, name='field_dashboard'),
    path('api/fields/list/', views.api_field_list, name='api_field_list'), 
    path('api/fields/stats/', views.api_field_stats, name='api_field_stats'),
    path('api/fields/<int:field_id>/delete/', views.api_delete_field, name='api_delete_field'), 
    path('api/fields/check-duplicates/', views.api_check_duplicates, name='api_check_duplicates'),
    #################### NDVI calc ###################################
    path('api/ndvi/point/', views.api_ndvi_point, name='api_ndvi_point'), 
    path('api/ndvi/default/', views.api_ndvi_default, name='api_ndvi_default'),  
    path('api/ndvi/area/', views.api_ndvi_area, name='api_ndvi_area'),  # POST - For polygons
    path('test/ndvi/', views.test_ndvi_view, name='test_ndvi'),  # Test view for NDVI API
    
]

