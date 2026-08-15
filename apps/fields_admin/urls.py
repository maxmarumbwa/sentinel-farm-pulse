from django.urls import path
from . import views

app_name = 'fields_admin'

urlpatterns = [
    path('test/', views.test, name='test'),
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
    path('api/fields/latest-health/', views.api_fields_latest_health, name='api_fields_latest_health'),
    # View multiple param latlon 
    path('api/geo-intel/', views.api_geo_intel, name='api_geo_intel'),

    
    ################################### NDVI API URLs ##########################
    # NDVI MAP - MAIN VIEW
    path('ndvi-map/', views.ndvi_map_view, name='ndvi_map'),
     # NDVI API - GET SINGLE TILE FOR ALL FIELDS
    path('api/fields/ndvi-all/', views.api_ndvi_all_fields, name='api_ndvi_all_fields'),
    path('api/fields/ndvi-single/', views.api_ndvi_single_field, name='api_ndvi_single_field'),
    path('view/ndvi-graph/', views.field_analytics_view, name='ndvi-graph'),
    
    # NDVI Province (lat/lon) endpoints  
    path('api/ndvi/all/', views.api_ndvi_all_provinces, name='api_ndvi_all_provinces'),
    path('api/ndvi/save/', views.api_save_ndvi_data, name='api_save_ndvi_data'),
    path('api/ndvi/db/', views.api_ndvi_from_db, name='api_ndvi_from_db'),
    path('api/ndvi/export/', views.api_ndvi_export_csv, name='api_ndvi_export_csv'),
    path('ndvi-to-db/', views.ndvi_to_db, name='ndvi_to_db'),


    # path('fields-map/', views.fields_map_view, name='fields_map'),
    # path('api/fields/<int:field_id>/ndvi-simple/', views.api_field_ndvi_simple, name='api_field_ndvi_simple'),
    # path('view/ndvi_lookback/', views.ndvi_lookback, name='ndvi_lookback'),
    # path('ndvi-map/', views.ndvi_map_view, name='ndvi_map'),
    # path('api/fields/ndvi-all/', views.api_ndvi_all_fields, name='api_ndvi_all_fields'),
    
    
    ############################################## Rainfall API URLs ##############################################
    path('api/rainfall/provinces/', views.api_rainfall_all_provinces, name='api_rainfall_all_provinces'),
    path('api/rainfall/point/', views.api_rainfall_single_point, name='api_rainfall_single_point'),
        # Rainfall Database URLs
    path(' ', views.api_save_rainfall_data, name='api_save_rainfall_data'),
    path('api/rainfall/db/', views.api_rainfall_from_db, name='api_rainfall_from_db'),
    path('test/rainfall/', views.test_rainfall_view, name='test_rainfall'),  
    path('save/rainfall/', views.rainfall_to_db, name='rainfall_to_db'),
    path('view/rainfall_db_pages/', views.rainfall_db, name='rainfall_db'), # old
    # export large db
    path('view/rainfall_db_all/', views.rainfall_db_all, name='rainfall_db_all'),
    path('view/rainfall_db_all_paged/', views.rainfall_db_all_paged, name='rainfall_db_all_paged'),
    path('api/rainfall/export/', views.api_rainfall_export_csv, name='api_rainfall_export_csv'),
    path('api/rainfall_db_al_page/', views.api_rainfall_export_csv_paginated, name='api_rainfall_export'),
    path('api/rainfall/dashboard/', views.rainfall_dashboad, name='rainfall_dashboad'),
    ##### Db aggregation
        # Main aggregation endpoint
    path('api/climate/aggregate/', views.climate_aggregate, name='climate_aggregate'),
    
    # rainfall aggregation 
    path('api/rainfall/monthly/', views.api_rainfall_monthly, name='api_rainfall_monthly'),
    path('api/rainfall/dekadal/', views.api_rainfall_dekadal, name='api_rainfall_dekadal'),
    path('api/rainfall/annual/', views.api_rainfall_annual, name='api_rainfall_annual'),
    

    # path('api/rainfall/provinces/', views.api_rainfall_all_provinces, name='api_rainfall_all_provinces'),
    # path('api/rainfall/point/', views.api_rainfall_single_point, name='api_rainfall_single_point'),
    # path('test/rainfall/', views.test_rainfall_view, name='test_rainfall'), 
    
    
    #################### NDVI calc ###################################
    path('api/ndvi/point-range/', views.api_ndvi_point_date_range, name='api_ndvi_point_date_range'),
    path('api/ndvi/point/', views.api_ndvi_point, name='api_ndvi_point'), 
    path('api/ndvi/default/', views.api_ndvi_default, name='api_ndvi_default'),  
    path('api/ndvi/area/', views.api_ndvi_area, name='api_ndvi_area'),  # POST - For polygons
    path('test/ndvi/', views.test_ndvi_view, name='test_ndvi'),  # Test view for NDVI API
    
    #save lat/lon points
    path('api/points/save/', views.api_save_points, name='api_save_points'),
    path('api/points/load/', views.api_load_points, name='api_load_points'),
    
]

