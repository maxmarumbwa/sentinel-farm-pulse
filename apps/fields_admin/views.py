from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos import Polygon
from .models import Admin1, Admin2, Field
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def digitize_field(request):
    """View for field digitization page"""
    admins = Admin1.objects.all().order_by('name')
    context = {
        'admins': admins
    }
    return render(request, 'fields_admin/digitize.html', context)

@login_required
def digitize_field2(request):
    """View for field digitization page"""
    admins = Admin1.objects.all().order_by('name')
    context = {
        'admins': admins
    }
    return render(request, 'fields_admin/digitize2.html', context)



@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_create_field(request):
    """API endpoint to create a field"""
    try:
        # Parse JSON data
        data = json.loads(request.body)
        logger.info(f"Creating field for user {request.user.username}")
        logger.info(f"Data received: {data}")
        
        # Validate required fields
        if not data.get('field_name'):
            return JsonResponse({'error': 'Field name is required'}, status=400)
        
        if not data.get('geometry'):
            return JsonResponse({'error': 'Geometry is required'}, status=400)
        
        # Create field instance
        field = Field(
            user=request.user,
            field_name=data.get('field_name'),
            crop=data.get('crop', 'Maize'),
            production_system=data.get('production_system', 'Rainfed'),
        )
        
        # Add admin references
        if data.get('adm1'):
            try:
                field.adm1_id = int(data.get('adm1'))
            except (ValueError, TypeError):
                logger.warning(f"Invalid adm1 ID: {data.get('adm1')}")
        
        if data.get('adm2'):
            try:
                field.adm2_id = int(data.get('adm2'))
            except (ValueError, TypeError):
                logger.warning(f"Invalid adm2 ID: {data.get('adm2')}")
        
        # Set geometry - ensure it's a valid polygon
        geom_json = data.get('geometry')
        if geom_json:
            try:
                # Create polygon from coordinates
                coords = geom_json.get('coordinates', [])
                if coords and len(coords) > 0:
                    # Convert to proper GeoJSON format
                    geojson = {
                        'type': 'Polygon',
                        'coordinates': coords
                    }
                    geom = GEOSGeometry(json.dumps(geojson), srid=4326)
                    
                    # Validate it's a polygon
                    if geom.geom_type != 'Polygon':
                        return JsonResponse({'error': 'Geometry must be a Polygon'}, status=400)
                    
                    field.geometry = geom
                else:
                    return JsonResponse({'error': 'Invalid polygon coordinates'}, status=400)
            except Exception as e:
                logger.error(f"Error processing geometry: {str(e)}")
                return JsonResponse({'error': f'Invalid geometry: {str(e)}'}, status=400)
        
        # Save the field
        field.save()
        
        return JsonResponse({
            'id': field.id,
            'field_name': field.field_name,
            'area_ha': field.area_ha,
            'message': 'Field created successfully'
        }, status=201)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating field: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def api_admin2(request):
    """API endpoint to get Admin2 by Admin1"""
    try:
        admin1_id = request.GET.get('admin1')
        
        if not admin1_id:
            return JsonResponse([], safe=False)
        
        # Get admin2s for this admin1
        admin2s = Admin2.objects.filter(admin1_id=admin1_id).order_by('name')
        
        data = [{'id': a.id, 'name': a.name} for a in admin2s]
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        logger.error(f"Error in api_admin2: {str(e)}")
        return JsonResponse([], safe=False)
    
    ##################### Load Sentinel Monthly Composite #####################
    from django.shortcuts import render
import ee
from datetime import datetime

def satellite_view(request):
    """Display a satellite image from Earth Engine"""
    image = (
        ee.ImageCollection("COPERNICUS/S2")
        .filterDate("2025-01-01", "2025-12-31")
        .filterBounds(ee.Geometry.Point([30.0, -1.0]))
        .first()
    )

    try:
        info = image.getInfo()

        # Extract bands
        bands_list = []
        if "bands" in info:
            for band in info["bands"]:
                bands_list.append(band.get("id", "unknown"))

        # Convert timestamp to readable date
        timestamp = info.get("properties", {}).get("GENERATION_TIME")
        if timestamp:
            # Convert milliseconds to datetime
            readable_date = datetime.fromtimestamp(timestamp / 1000).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            readable_date = "Unknown"

        context = {
            "image_id": info.get("id", "Unknown"),
            "bands": bands_list,
            "date": readable_date,
            "cloud_cover": info.get("properties", {}).get(
                "CLOUDY_PIXEL_PERCENTAGE", "N/A"
            ),
        }
    except Exception as e:
        context = {"error": str(e)}

    return render(request, "satellite.html", context)


# View to display rainfall raster
def rainfall_raster(request):
    """Display CHIRPS daily rainfall raster for Malawi"""
    try:
        # Use daily CHIRPS with a single date
        rainfall = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterDate("2023-03-20", "2023-03-21")
            .select("precipitation")
            .mean()
        )

        # Clip to Malawi
        malawi = ee.Geometry.Polygon(
            [[[32.7, -17.1], [35.9, -17.1], [35.9, -9.4], [32.7, -9.4], [32.7, -17.1]]]
        )
        rainfall_clipped = rainfall.clip(malawi)

        # Visualization
        vis_params = {
            "min": 0,
            "max": 60,
            "palette": ["ffffcc", "a1dab4", "41b6c4", "2c7fb8", "253494"],
        }

        map_id = rainfall_clipped.getMapId(vis_params)
        tile_url = map_id["tile_fetcher"].url_format

        context = {"tile_url": tile_url, "date": "March 20, 2023"}

    except Exception as e:
        context = {"error": str(e)}

    return render(request, "rainfall_raster.html", context)


################# Sentinel-2 True Colour Composite View ############################
# Sentinel view

import ee
import datetime
import calendar
import os
import json
from django.shortcuts import render
def sentinel_truecolour(request):
    """Sentinel-2 True Colour Composite"""

    try:

        # -------------------------------
        # User inputs
        # -------------------------------

        start_year = int(request.GET.get("start_year", 2025))
        start_month = int(request.GET.get("start_month", 1))

        end_year = int(request.GET.get("end_year", 2025))
        end_month = int(request.GET.get("end_month", 1))

        cloud_cover = int(request.GET.get("cloud", 20))

        cloud_cover = max(0, min(100, cloud_cover))


        # Province selection
        province = request.GET.get("province", "Zimbabwe")


        # -------------------------------
        # Dates
        # -------------------------------

        start = datetime.date(start_year, start_month, 1)

        if end_month == 12:
            end = datetime.date(end_year + 1, 1, 1)
        else:
            end = datetime.date(end_year, end_month + 1, 1)



        # -------------------------------
        # Load Zimbabwe Admin1 GeoJSON
        # -------------------------------

        geojson_path = os.path.join(
            "static",
            "geojson",
            "zwe_admin1.geojson"
        )


        with open(
            geojson_path,
            "r",
            encoding="utf-8"
        ) as f:

            geojson = json.load(f)



        # -------------------------------
        # Province list
        # -------------------------------

        provinces = ["Zimbabwe"]

        for feature in geojson["features"]:

            name = feature["properties"]["adm1_name"]

            if name not in provinces:
                provinces.append(name)



        provinces = sorted(provinces)



        # -------------------------------
        # Area of interest
        # -------------------------------

        if province == "Zimbabwe":


            region = ee.Geometry.Polygon(
                [[
                    [25.24, -22.42],
                    [33.07, -22.42],
                    [33.07, -15.61],
                    [25.24, -15.61],
                    [25.24, -22.42],
                ]]
            )


        else:

            region = None


            for feature in geojson["features"]:

                name = feature["properties"]["adm1_name"]


                if name == province:

                    geom = feature["geometry"]

                    region = ee.Geometry(
                        geom
                    )

                    break



            if region is None:

                raise Exception(
                    f"Province {province} not found"
                )



        # -------------------------------
        # Sentinel Composite
        # -------------------------------

        image = (
            ee.ImageCollection(
                "COPERNICUS/S2_SR_HARMONIZED"
            )
            .filterBounds(region)
            .filterDate(
                str(start),
                str(end)
            )
            .filter(
                ee.Filter.lt(
                    "CLOUDY_PIXEL_PERCENTAGE",
                    cloud_cover
                )
            )
            .median()
            .clip(region)
        )



        vis_params = {

            "bands": [
                "B4",
                "B3",
                "B2"
            ],

            "min": 0,

            "max": 3000,

            "gamma": 1.2,
        }



        tile_url = (
            image
            .getMapId(vis_params)
            ["tile_fetcher"]
            .url_format
        )



        # -------------------------------
        # Map extent
        # -------------------------------

        bounds = (
            region
            .bounds()
            .coordinates()
            .getInfo()
        )[0]


        west = bounds[0][0]
        south = bounds[0][1]

        east = bounds[2][0]
        north = bounds[2][1]



        # -------------------------------
        # Context
        # -------------------------------

        context = {


            "tile_url": tile_url,


            "start_year": start_year,
            "start_month": start_month,

            "end_year": end_year,
            "end_month": end_month,


            "cloud_cover": cloud_cover,


            "province": province,

            "provinces": provinces,


            "bounds": [
                [south, west],
                [north, east]
            ],



            "date": (

                f"{calendar.month_name[start_month]}"
                f" {start_year}"

                f" - "

                f"{calendar.month_name[end_month]}"
                f" {end_year}"

            ),



            "years": list(
                range(
                    2017,
                    datetime.date.today().year + 1
                )
            ),



            "months": [

                (1, "January"),
                (2, "February"),
                (3, "March"),
                (4, "April"),
                (5, "May"),
                (6, "June"),
                (7, "July"),
                (8, "August"),
                (9, "September"),
                (10, "October"),
                (11, "November"),
                (12, "December"),

            ],

        }



    except Exception as e:


        context = {

            "error": str(e),


            "years": list(
                range(
                    2017,
                    datetime.date.today().year + 1
                )
            ),


            "months": [

                (1, "January"),
                (2, "February"),
                (3, "March"),
                (4, "April"),
                (5, "May"),
                (6, "June"),
                (7, "July"),
                (8, "August"),
                (9, "September"),
                (10, "October"),
                (11, "November"),
                (12, "December"),

            ],

            "provinces": ["Zimbabwe"],

        }



    return render(
        request,
        "fields_admin/digitize_sentinel_truecolour.html",
        
        context
    )


###########################################################################################
################################ View digitised field in a dashboard #####################################
###########################################################################################

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.gis.geos import GEOSGeometry
from .models import Admin1, Admin2, Field
from django.db.models import Count, Sum, Avg, Q
import json
import logging

logger = logging.getLogger(__name__)

# =====================================================
# FIELD DASHBOARD VIEW
# =====================================================

@login_required
def field_dashboard(request):
    """Field dashboard with map and table view"""
    admins1 = Admin1.objects.all().order_by('name')
    
    # Get unique crops for filter
    crops = Field.objects.filter(user=request.user).values_list('crop', flat=True).distinct().order_by('crop')
    
    context = {
        'admins1': admins1,
        'crops': crops,
    }
    
    return render(request, 'fields_admin/dashboard.html', context)


# =====================================================
# API: FIELD LIST WITH FILTERS
# =====================================================

@login_required
def api_field_list(request):
    """API endpoint to get fields as GeoJSON with filters"""
    try:
        # Get filter parameters
        province = request.GET.get('province')
        crop = request.GET.get('crop')
        production_system = request.GET.get('production_system')
        search = request.GET.get('search')
        
        # Base queryset
        fields = Field.objects.filter(user=request.user).select_related('adm1', 'adm2')
        
        # Apply filters
        if province:
            fields = fields.filter(adm1_id=province)
        if crop:
            fields = fields.filter(crop=crop)
        if production_system:
            fields = fields.filter(production_system=production_system)
        if search:
            fields = fields.filter(
                Q(field_name__icontains=search) |
                Q(crop__icontains=search)
            )
        
        # Convert to GeoJSON
        geojson = {
            'type': 'FeatureCollection',
            'features': []
        }
        
        crop_colors = {
            'Maize': '#f1c40f',
            'Groundnuts': '#e67e22',
            'Soybeans': '#2ecc71',
            'Cotton': '#ecf0f1',
            'Tobacco': '#e74c3c',
            'Sunflower': '#f39c12',
            'Sorghum': '#d35400',
            'Millet': '#f1c40f',
            'Beans': '#27ae60',
            'Potatoes': '#8e44ad',
            'Tomatoes': '#e74c3c',
            'Other': '#95a5a6',
        }
        
        for field in fields:
            if field.geometry:
                geom_json = json.loads(field.geometry.geojson)
                feature = {
                    'type': 'Feature',
                    'geometry': geom_json,
                    'properties': {
                        'id': field.id,
                        'field_name': field.field_name,
                        'crop': field.crop,
                        'production_system': field.production_system,
                        'area_ha': field.area_ha,
                        'province': field.adm1.name if field.adm1 else None,
                        'district': field.adm2.name if field.adm2 else None,
                        'created_at': field.created_at.strftime('%Y-%m-%d %H:%M'),
                        'color': crop_colors.get(field.crop, '#95a5a6'),
                    }
                }
                geojson['features'].append(feature)
        
        return JsonResponse(geojson)
        
    except Exception as e:
        logger.error(f"Error in api_field_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: FIELD STATISTICS
# =====================================================

@login_required
def api_field_stats(request):
    """API endpoint to get field statistics"""
    try:
        # Get filter parameters
        province = request.GET.get('province')
        crop = request.GET.get('crop')
        production_system = request.GET.get('production_system')
        search = request.GET.get('search')
        
        # Base queryset
        fields = Field.objects.filter(user=request.user)
        
        # Apply filters
        if province:
            fields = fields.filter(adm1_id=province)
        if crop:
            fields = fields.filter(crop=crop)
        if production_system:
            fields = fields.filter(production_system=production_system)
        if search:
            fields = fields.filter(
                Q(field_name__icontains=search) |
                Q(crop__icontains=search)
            )
        
        # Calculate statistics
        total_fields = fields.count()
        total_area = fields.aggregate(Sum('area_ha'))['area_ha__sum'] or 0
        avg_area = fields.aggregate(Avg('area_ha'))['area_ha__avg'] or 0
        
        # Crop distribution
        crop_stats = fields.values('crop').annotate(
            count=Count('id'),
            area=Sum('area_ha')
        ).order_by('-count')
        
        crop_distribution = []
        for item in crop_stats:
            crop_distribution.append({
                'crop': item['crop'],
                'count': item['count'],
                'area': round(item['area'] or 0, 2),
                'percentage': round((item['count'] / total_fields * 100) if total_fields > 0 else 0, 1)
            })
        
        stats = {
            'total_fields': total_fields,
            'total_area': round(total_area, 2),
            'avg_area': round(avg_area, 2),
            'crop_distribution': crop_distribution,
        }
        
        return JsonResponse(stats)
        
    except Exception as e:
        logger.error(f"Error in api_field_stats: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: DELETE FIELD
# =====================================================

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_field(request, field_id):
    """API endpoint to delete a field"""
    try:
        field = get_object_or_404(Field, id=field_id, user=request.user)
        field_name = field.field_name
        field.delete()
        
        return JsonResponse({
            'message': f'Field "{field_name}" deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in api_delete_field: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
# =====================================================
# API: CHECK DUPLICATE FIELDS when imporing from shapefile or geojson
# =====================================================

@login_required
def api_check_duplicates(request):
    """Check if fields already exist in the database using geometry overlap (50% threshold)"""
    try:
        data = json.loads(request.body)
        features = data.get('features', [])
        
        # Get existing fields for the user
        existing_fields = Field.objects.filter(user=request.user)
        
        duplicates = []
        new_features = []
        
        for feature in features:
            geom = feature.get('geometry')
            if not geom or not geom.get('coordinates'):
                continue
            
            # Create GEOSGeometry from the feature
            try:
                geojson = {
                    'type': 'Polygon',
                    'coordinates': geom['coordinates']
                }
                new_geom = GEOSGeometry(json.dumps(geojson), srid=4326)
                
                # Check for overlap with existing fields
                is_duplicate = False
                duplicate_info = None
                
                for existing in existing_fields:
                    if not existing.geometry:
                        continue
                    
                    try:
                        # Calculate intersection area
                        intersection = new_geom.intersection(existing.geometry)
                        if intersection and intersection.area > 0:
                            # Calculate overlap percentage
                            overlap_area = intersection.area
                            new_area = new_geom.area
                            existing_area = existing.geometry.area
                            
                            # Use smaller area for percentage calculation
                            min_area = min(new_area, existing_area)
                            if min_area > 0:
                                overlap_percentage = (overlap_area / min_area) * 100
                                
                                # If overlap is >= 50%, consider it a duplicate
                                if overlap_percentage >= 50:
                                    is_duplicate = True
                                    duplicate_info = {
                                        'field_name': existing.field_name,
                                        'overlap_percentage': round(overlap_percentage, 1),
                                        'existing_id': existing.id
                                    }
                                    break
                    except Exception as e:
                        logger.warning(f"Error calculating overlap: {str(e)}")
                        continue
                
                if is_duplicate:
                    duplicates.append({
                        'field_name': feature.get('properties', {}).get('name', 'Unknown'),
                        'reason': f'Overlaps with "{duplicate_info["field_name"]}" ({duplicate_info["overlap_percentage"]}%)'
                    })
                else:
                    new_features.append(feature)
                    
            except Exception as e:
                logger.error(f"Error processing geometry: {str(e)}")
                # If geometry is invalid, skip it
                duplicates.append({
                    'field_name': feature.get('properties', {}).get('name', 'Unknown'),
                    'reason': 'Invalid geometry'
                })
                continue
        
        return JsonResponse({
            'total': len(features),
            'duplicates': duplicates,
            'duplicate_count': len(duplicates),
            'new_count': len(new_features),
            'new_features': new_features
        })
        
    except Exception as e:
        logger.error(f"Error checking duplicates: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


    
##################################################################################################

######################################### Rainfall monitoring - chirps #######################################

##################################################################################################
#NEW VIEW getting datadirect from google earth engine and saving to database

# =====================================================
# RAINFALL DATA - CHIRPS (No Login Required)
# =====================================================

import ee
import datetime
import json
import logging
from django.http import JsonResponse
from django.db import IntegrityError

logger = logging.getLogger(__name__)

# Import your model
from .models import RainfallProvince

# Zimbabwe Province Representative Points
ZIMBABWE_PROVINCES = {
    'Harare': {'lat': -17.8252, 'lng': 31.0335},
    'Bulawayo': {'lat': -20.1486, 'lng': 28.5880},
    'Manicaland': {'lat': -18.9216, 'lng': 32.1746},
    'Mashonaland Central': {'lat': -16.7633, 'lng': 31.0702},
    'Mashonaland East': {'lat': -17.5192, 'lng': 31.8667},
    'Mashonaland West': {'lat': -17.3000, 'lng': 30.4000},
    'Masvingo': {'lat': -20.0667, 'lng': 30.8333},
    'Matabeleland North': {'lat': -18.9833, 'lng': 27.0000},
    'Matabeleland South': {'lat': -21.0000, 'lng': 29.0000},
    'Midlands': {'lat': -19.0000, 'lng': 30.0000},
}


def get_rainfall_at_point(lat, lng, start_date, end_date):
    """Get rainfall (CHIRPS) at a specific point for a date range."""
    try:
        point = ee.Geometry.Point([lng, lat])
        
        collection = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterBounds(point)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .select('precipitation')
        )
        
        def extract_rainfall(img):
            date = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd')
            rainfall = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=1000,
                maxPixels=1e9
            )
            return ee.Feature(None, {
                'date': date,
                'rainfall': rainfall.get('precipitation')
            })
        
        features = collection.map(extract_rainfall)
        feature_list = features.getInfo()
        
        results = []
        for feature in feature_list.get('features', []):
            props = feature.get('properties', {})
            date = props.get('date')
            rainfall = props.get('rainfall')
            
            if date and rainfall is not None:
                results.append({
                    'date': date,
                    'rainfall': round(float(rainfall), 2)
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error in get_rainfall_at_point: {str(e)}")
        raise Exception(f"Failed to extract rainfall: {str(e)}")


# =====================================================
# API: GET RAINFALL FOR ALL PROVINCES (NO LOGIN)
# =====================================================

def api_rainfall_all_provinces(request):
    """
    Get rainfall data for all Zimbabwe provinces.
    No login required - open access.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    """
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        results = {}
        
        for province, coords in ZIMBABWE_PROVINCES.items():
            try:
                rainfall_data = get_rainfall_at_point(
                    coords['lat'], 
                    coords['lng'], 
                    start_date, 
                    end_date
                )
                
                rain_values = [r['rainfall'] for r in rainfall_data if r['rainfall'] is not None]
                total_rain = sum(rain_values) if rain_values else 0
                avg_rain = total_rain / len(rain_values) if rain_values else 0
                max_rain = max(rain_values) if rain_values else 0
                min_rain = min(rain_values) if rain_values else 0
                rainy_days = len([r for r in rain_values if r > 1])
                
                results[province] = {
                    'coords': coords,
                    'data': rainfall_data,
                    'stats': {
                        'total': round(total_rain, 2),
                        'avg': round(avg_rain, 2),
                        'max': round(max_rain, 2),
                        'min': round(min_rain, 2),
                        'rainy_days': rainy_days,
                        'total_days': len(rainfall_data)
                    }
                }
            except Exception as e:
                logger.error(f"Error processing {province}: {str(e)}")
                results[province] = {
                    'coords': coords,
                    'error': str(e),
                    'data': [],
                    'stats': {
                        'total': 0,
                        'avg': 0,
                        'max': 0,
                        'min': 0,
                        'rainy_days': 0,
                        'total_days': 0
                    }
                }
        
        return JsonResponse({
            'success': True,
            'provinces': results,
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'metadata': {
                'collection': 'UCSB-CHG/CHIRPS/DAILY',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in api_rainfall_all_provinces: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: GET RAINFALL FOR A SINGLE POINT (NO LOGIN)
# =====================================================

def api_rainfall_single_point(request):
    """
    Get rainfall for a single point.
    No login required - open access.
    
    Query parameters:
    - lat: Latitude (required)
    - lng: Longitude (required)
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    """
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        rainfall_data = get_rainfall_at_point(lat, lng, start_date, end_date)
        
        rain_values = [r['rainfall'] for r in rainfall_data if r['rainfall'] is not None]
        total_rain = sum(rain_values) if rain_values else 0
        avg_rain = total_rain / len(rain_values) if rain_values else 0
        max_rain = max(rain_values) if rain_values else 0
        min_rain = min(rain_values) if rain_values else 0
        
        return JsonResponse({
            'success': True,
            'location': {'lat': lat, 'lng': lng},
            'data': rainfall_data,
            'stats': {
                'total': round(total_rain, 2),
                'avg': round(avg_rain, 2),
                'max': round(max_rain, 2),
                'min': round(min_rain, 2),
                'total_days': len(rainfall_data),
                'data_points': len(rain_values)
            },
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'metadata': {
                'collection': 'UCSB-CHG/CHIRPS/DAILY',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in api_rainfall_single_point: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# SAVE RAINFALL DATA TO DATABASE
# =====================================================

def save_rainfall_to_db(province_name, date_str, rainfall_value, lat=None, lng=None):
    """
    Save rainfall data for a province to the database.
    Returns (success, message)
    """
    try:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        
        obj, created = RainfallProvince.objects.update_or_create(
            province=province_name,
            date=date,
            defaults={
                'rainfall_mm': round(rainfall_value, 2),
                'source': 'CHIRPS',
                'lat': lat,
                'lng': lng
            }
        )
        
        return True, f"{'Created' if created else 'Updated'} record for {province_name} on {date_str}"
        
    except Exception as e:
        return False, f"Error saving: {str(e)}"


# =====================================================
# API: SAVE RAINFALL DATA TO DATABASE
# =====================================================

def api_save_rainfall_data(request):
    """
    Save rainfall data from Earth Engine to database.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - overwrite: (optional) 'true' to overwrite existing data
    """
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        overwrite = request.GET.get('overwrite', 'false').lower() == 'true'
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        results = {}
        saved_count = 0
        errors = []
        
        for province_name, coords in ZIMBABWE_PROVINCES.items():
            try:
                rainfall_data = get_rainfall_at_point(
                    coords['lat'],
                    coords['lng'],
                    start_date,
                    end_date
                )
                
                province_results = []
                for item in rainfall_data:
                    date_str = item['date']
                    rainfall_value = item['rainfall']
                    
                    if overwrite:
                        RainfallProvince.objects.filter(
                            province=province_name,
                            date=datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        ).delete()
                    
                    success, msg = save_rainfall_to_db(
                        province_name, 
                        date_str, 
                        rainfall_value,
                        coords['lat'],
                        coords['lng']
                    )
                    
                    if success:
                        saved_count += 1
                        province_results.append({
                            'date': date_str,
                            'rainfall': rainfall_value,
                            'status': 'saved'
                        })
                    else:
                        errors.append(msg)
                        
                results[province_name] = {
                    'coords': coords,
                    'data': province_results,
                    'count': len(province_results)
                }
                
            except Exception as e:
                errors.append(f"{province_name}: {str(e)}")
                results[province_name] = {
                    'coords': coords,
                    'error': str(e)
                }
        
        return JsonResponse({
            'success': True,
            'message': f'Data saved successfully. {saved_count} records saved.',
            'saved_count': saved_count,
            'errors': errors,
            'results': results,
            'metadata': {
                'collection': 'UCSB-CHG/CHIRPS/DAILY',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error saving rainfall data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: GET RAINFALL DATA FROM DATABASE (FAST)
# =====================================================
#
#
from django.db import connection
def api_rainfall_from_db(request):
    """
    Get rainfall data - ULTRA FAST with single SQL query using JSON aggregation.
    """
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        province_filter = request.GET.get('province', '')
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 100)), 500)
        format_type = request.GET.get('format', 'summary')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        offset = (page - 1) * page_size
        table_name = RainfallProvince._meta.db_table
        
        # ============================================================
        # SINGLE SQL QUERY - Everything in one go
        # ============================================================
        sql = """
            WITH filtered_data AS (
                SELECT 
                    date,
                    province,
                    rainfall_mm,
                    lat,
                    lng
                FROM {table_name}
                WHERE date >= %s AND date <= %s
                AND (%s = '' OR province = %s)
            ),
            stats AS (
                SELECT 
                    province,
                    COUNT(*) as total_days,
                    COALESCE(SUM(rainfall_mm), 0) as total_rainfall,
                    COALESCE(AVG(rainfall_mm), 0) as avg_rainfall,
                    COALESCE(MAX(rainfall_mm), 0) as max_rainfall,
                    COALESCE(MIN(rainfall_mm), 0) as min_rainfall,
                    COUNT(CASE WHEN rainfall_mm > 1 THEN 1 END) as rainy_days
                FROM filtered_data
                GROUP BY province
            ),
            paginated AS (
                SELECT 
                    date,
                    province,
                    rainfall_mm,
                    lat,
                    lng
                FROM filtered_data
                ORDER BY date, province
                LIMIT %s OFFSET %s
            ),
            total_count AS (
                SELECT COUNT(*) as total FROM filtered_data
            )
            SELECT 
                (SELECT total FROM total_count) as total_records,
                (SELECT json_agg(json_build_object(
                    'date', date,
                    'province', province,
                    'rainfall', rainfall_mm,
                    'lat', lat,
                    'lng', lng
                )) FROM paginated) as data,
                (SELECT json_agg(json_build_object(
                    'province', province,
                    'total_days', total_days,
                    'total_rainfall', total_rainfall,
                    'avg_rainfall', avg_rainfall,
                    'max_rainfall', max_rainfall,
                    'min_rainfall', min_rainfall,
                    'rainy_days', rainy_days
                )) FROM stats) as stats
        """.format(table_name=table_name)
        
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                start_date, 
                end_date, 
                province_filter, 
                province_filter,
                page_size, 
                offset
            ])
            result = cursor.fetchone()
        
        if not result or result[0] == 0:
            return JsonResponse({
                'success': True,
                'message': 'No data found in database for this date range.',
                'provinces': {},
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_records': 0,
                    'total_pages': 0,
                    'has_next': False,
                    'has_previous': False
                },
                'date_range': {
                    'start': start_date_str,
                    'end': end_date_str
                },
                'metadata': {
                    'source': 'database',
                    'records': 0,
                    'provinces_found': 0,
                    'format': format_type,
                    'processed_at': datetime.datetime.now().isoformat()
                }
            }, status=200)
        
        total_records = result[0]
        data_list = result[1] or []
        stats_list = result[2] or []
        
        # Process data
        results = {}
        province_data = {}
        province_coords = {}
        
        for item in data_list:
            province = item['province']
            if province not in province_data:
                province_data[province] = []
                province_coords[province] = {
                    'lat': item['lat'],
                    'lng': item['lng']
                }
            province_data[province].append({
                'date': item['date'].strftime('%Y-%m-%d') if isinstance(item['date'], datetime.date) else item['date'],
                'rainfall': item['rainfall']
            })
        
        # Build stats dict
        stats_dict = {}
        for stat in stats_list:
            province = stat['province']
            stats_dict[province] = {
                'total_days': stat['total_days'],
                'total_rainfall': round(stat['total_rainfall'], 2),
                'avg_rainfall': round(stat['avg_rainfall'], 2),
                'max_rainfall': round(stat['max_rainfall'], 2),
                'min_rainfall': round(stat['min_rainfall'], 2),
                'rainy_days': stat['rainy_days']
            }
        
        # Build final results
        for province, data in province_data.items():
            stats = stats_dict.get(province, {})
            total_days = stats.get('total_days', 0)
            province_total_pages = (total_days + page_size - 1) // page_size if total_days > 0 else 0
            
            results[province] = {
                'coords': province_coords.get(province, {'lat': None, 'lng': None}),
                'data': data if format_type == 'full' else [],
                'stats': {
                    'total': stats.get('total_rainfall', 0),
                    'avg': stats.get('avg_rainfall', 0),
                    'max': stats.get('max_rainfall', 0),
                    'min': stats.get('min_rainfall', 0),
                    'rainy_days': stats.get('rainy_days', 0),
                    'total_days': total_days
                },
                'pagination': {
                    'total_records': total_days,
                    'showing': len(data),
                    'page': page,
                    'page_size': page_size,
                    'total_pages': province_total_pages
                }
            }
        
        total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
        
        return JsonResponse({
            'success': True,
            'provinces': results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total_records,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'next_page': page + 1 if page < total_pages else None,
                'previous_page': page - 1 if page > 1 else None
            },
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'metadata': {
                'source': 'database',
                'records': total_records,
                'provinces_found': len(results),
                'format': format_type,
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid parameter: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error getting rainfall from DB: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
#
################################################################################################################
###################################### Csv export of exporting all data from database ############################
################################################################################################################
import csv
from django.http import HttpResponse, JsonResponse
import datetime
import logging

logger = logging.getLogger(__name__)

def api_rainfall_export_csv(request):
    """
    Export all rainfall records as CSV (default) or JSON.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - province: (optional) Filter by specific province
    - format: 'csv' (default) or 'json'
    """
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        province_filter = request.GET.get('province', '')
        output_format = request.GET.get('format', 'csv').lower()  # Default: CSV (backward compatible)
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        queryset = RainfallProvince.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date', 'province')
        
        if province_filter:
            queryset = queryset.filter(province=province_filter)
        
        # Build data list
        data = []
        for record in queryset:
            data.append({
                'date': record.date.strftime('%Y-%m-%d'),
                'province': record.province,
                'rainfall': record.rainfall_mm
            })
        
        # ============================================================
        # Return JSON if format=json is specified
        # ============================================================
        if output_format == 'json':
            return JsonResponse({
                'success': True,
                'data': data,
                'count': len(data),
                'date_range': {
                    'start': start_date_str,
                    'end': end_date_str
                },
                'filters': {
                    'province': province_filter if province_filter else 'All'
                },
                'metadata': {
                    'source': 'database',
                    'exported_at': datetime.datetime.now().isoformat()
                }
            }, status=200)
        
        # ============================================================
        # Default: Return CSV (for backward compatibility)
        # ============================================================
        response = HttpResponse(content_type='text/csv')
        filename = f"rainfall_{start_date_str}_to_{end_date_str}"
        if province_filter:
            filename += f"_{province_filter}"
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Province', 'Rainfall (mm)'])
        
        for record in queryset:
            writer.writerow([
                record.date.strftime('%Y-%m-%d'),
                record.province,
                f"{record.rainfall_mm:.2f}"
            ])
        
        return response
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid date format: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error exporting rainfall data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
############################################################################################
####################################### paginated verion ##############################
###############################################################################################

def api_rainfall_export_csv_paginated(request):
    """
    Export rainfall data with pagination support.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - province: (optional) Filter by specific province
    - page: Page number (default: 1)
    - page_size: Records per page (default: 100, max: 1000)
    - format: 'json' or 'csv' (default: 'json')
    """
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        province_filter = request.GET.get('province', '')
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 100)), 1000)
        output_format = request.GET.get('format', 'json').lower()
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'error': 'start_date and end_date are required',
                'example': '/api/rainfall/export/?start_date=2020-01-01&end_date=2026-07-26&province=Masvingo&page=1&page_size=100'
            }, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        offset = (page - 1) * page_size
        table_name = RainfallProvince._meta.db_table
        
        # ============================================================
        # QUERY 1: Get total count
        # ============================================================
        sql_count = """
            SELECT COUNT(*) as total
            FROM {table_name}
            WHERE date >= %s AND date <= %s
            AND (%s = '' OR province = %s)
        """.format(table_name=table_name)
        
        with connection.cursor() as cursor:
            cursor.execute(sql_count, [start_date, end_date, province_filter, province_filter])
            total_records = cursor.fetchone()[0]
        
        if total_records == 0:
            return JsonResponse({
                'success': True,
                'message': 'No data found in database for this date range.',
                'data': [],
                'count': 0,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_records': 0,
                    'total_pages': 0,
                    'has_next': False,
                    'has_previous': False
                },
                'date_range': {
                    'start': start_date_str,
                    'end': end_date_str
                },
                'filters': {
                    'province': province_filter if province_filter else 'All'
                },
                'metadata': {
                    'source': 'database',
                    'exported_at': datetime.datetime.now().isoformat()
                }
            }, status=200)
        
        # ============================================================
        # QUERY 2: Get paginated data
        # ============================================================
        sql_data = """
            SELECT 
                date,
                province,
                rainfall_mm
            FROM {table_name}
            WHERE date >= %s AND date <= %s
            AND (%s = '' OR province = %s)
            ORDER BY date, province
            LIMIT %s OFFSET %s
        """.format(table_name=table_name)
        
        with connection.cursor() as cursor:
            cursor.execute(sql_data, [
                start_date, 
                end_date, 
                province_filter, 
                province_filter,
                page_size, 
                offset
            ])
            rows = cursor.fetchall()
        
        # Process data
        data = []
        for row in rows:
            data.append({
                'date': row[0].strftime('%Y-%m-%d'),
                'province': row[1],
                'rainfall': row[2]
            })
        
        # Calculate pagination
        total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
        
        pagination = {
            'page': page,
            'page_size': page_size,
            'total_records': total_records,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'previous_page': page - 1 if page > 1 else None
        }
        
        # ============================================================
        # Return JSON or CSV
        # ============================================================
        if output_format == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv')
            filename = f"rainfall_{start_date_str}_to_{end_date_str}"
            if province_filter:
                filename += f"_{province_filter}"
            filename += f"_page{page}"
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Date', 'Province', 'Rainfall (mm)'])
            for row in data:
                writer.writerow([row['date'], row['province'], f"{row['rainfall']:.2f}"])
            
            return response
        
        # Return JSON
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'total_records': total_records,
            'pagination': pagination,
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'filters': {
                'province': province_filter if province_filter else 'All'
            },
            'metadata': {
                'source': 'database',
                'exported_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid parameter: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error exporting rainfall data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
##
#
#
#  
#
#
#
#  
#
############################## ==============================###########################=======================
############################ MONTHLY RAINFALL AGGREGATION VIEW ###########################
########################### ==============================###########################=======================
# =====================================================
#  MONTHLY RAINFALL AGGREGATION VIEW
# =====================================================

import datetime
import calendar
import logging
from django.http import JsonResponse
from django.db.models import Sum
from django.db import connection
from .models import RainfallProvince

logger = logging.getLogger(__name__)


def api_rainfall_monthly(request):
    """
    Get monthly aggregated rainfall data - OPTIMIZED version.
    Uses a single SQL query with GROUP BY.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - province: (optional) Filter by specific province
    - format: json (default) or csv
    """
    try:
        # Get query parameters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        province_filter = request.GET.get('province')
        output_format = request.GET.get('format', 'json').lower()
        
        # Validate required parameters
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'error': 'start_date and end_date are required',
                'example': '/api/rainfall/monthly/?start_date=2024-01-01&end_date=2024-12-31'
            }, status=400)
        
        # Parse dates
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # ============================================================
        # OPTIMIZED: Single SQL query with GROUP BY
        # ============================================================
        
        table_name = RainfallProvince._meta.db_table
        
        # Build the WHERE clause
        where_clause = "date >= %s AND date <= %s"
        params = [start_date, end_date]
        
        if province_filter:
            where_clause += " AND province = %s"
            params.append(province_filter)
        
        # Single query with GROUP BY year, month, province
        sql = """
            SELECT 
                EXTRACT(YEAR FROM date)::int as year,
                EXTRACT(MONTH FROM date)::int as month,
                province,
                SUM(rainfall_mm) as total_rainfall
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date), province
            ORDER BY year, month, province
        """.format(table_name=table_name, where_clause=where_clause)
        
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        
        # Check if data exists
        if not rows:
            return JsonResponse({
                'success': False,
                'message': 'No data found in database for the given date range.',
                'data': []
            }, status=404)
        
        # ============================================================
        # Process results into the required format
        # ============================================================
        
        # Get all provinces from the results
        if province_filter:
            provinces = [province_filter]
        else:
            provinces = sorted(set(row[2] for row in rows))
        
        # Group data by year-month
        month_data = {}
        for row in rows:
            year = row[0]
            month = row[1]
            province = row[2]
            total = row[3]
            
            key = f"{year}-{month:02d}"
            
            if key not in month_data:
                month_data[key] = {
                    'year': year,
                    'month': month,
                    'month_name': calendar.month_name[month],
                    'month_abbr': calendar.month_abbr[month],
                    'date': f"{year}-{month:02d}-01",
                    'period': f"{calendar.month_name[month]} {year}",
                    'sort_key': f"{year}-{month:02d}",
                }
                # Initialize all provinces with 0
                for p in provinces:
                    month_data[key][p] = 0.0
            
            month_data[key][province] = round(total, 2)
        
        # Convert to list and sort by date
        data = sorted(month_data.values(), key=lambda x: x['sort_key'])
        
        # ============================================================
        # Build response
        # ============================================================
        
        response_data = {
            'success': True,
            'aggregation': 'monthly',
            'aggregation_label': 'Monthly',
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'provinces': provinces,
            'total_months': len(data),
            'data': data,
            'metadata': {
                'source': 'database',
                'exported_at': datetime.datetime.now().isoformat()
            }
        }
        
        # ============================================================
        # Return as CSV if requested
        # ============================================================
        
        if output_format == 'csv':
            return export_monthly_csv_optimized(response_data)
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error in monthly rainfall aggregation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def export_monthly_csv_optimized(response_data):
    """Export monthly aggregation data as CSV."""
    import csv
    from django.http import HttpResponse
    
    data = response_data['data']
    provinces = response_data['provinces']
    
    if not data:
        return JsonResponse({'error': 'No data to export'}, status=404)
    
    csv_response = HttpResponse(content_type='text/csv')
    filename = f"rainfall_monthly_{response_data['date_range']['start']}_to_{response_data['date_range']['end']}.csv"
    csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(csv_response)
    
    header = ['Year', 'Month', 'Month Name', 'Period'] + provinces
    writer.writerow(header)
    
    for row in data:
        row_data = [
            row['year'],
            row['month'],
            row['month_name'],
            row['period']
        ]
        for province in provinces:
            row_data.append(row.get(province, 0.0))
        writer.writerow(row_data)
    
    return csv_response
#

# =====================================================
# DEKADAL RAINFALL AGGREGATION VIEW (OPTIMIZED)
# =====================================================

import datetime
import calendar
import logging
from django.http import JsonResponse
from django.db import connection
from .models import RainfallProvince

logger = logging.getLogger(__name__)


def api_rainfall_dekadal(request):
    """
    Get dekadal aggregated rainfall data (10-day periods).
    Dekad 1 = days 01-10
    Dekad 2 = days 11-20
    Dekad 3 = days 21-end of month
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - province: (optional) Filter by specific province
    - format: json (default) or csv
    
    Example:
    /api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31
    /api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31&province=Harare
    /api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31&format=csv
    """
    try:
        # Get query parameters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        province_filter = request.GET.get('province')
        output_format = request.GET.get('format', 'json').lower()
        
        # Validate required parameters
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'error': 'start_date and end_date are required',
                'example': '/api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31'
            }, status=400)
        
        # Parse dates
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # ============================================================
        # OPTIMIZED: Single SQL query with GROUP BY for dekads
        # ============================================================
        
        table_name = RainfallProvince._meta.db_table
        
        # Build the WHERE clause
        where_clause = "date >= %s AND date <= %s"
        params = [start_date, end_date]
        
        if province_filter:
            where_clause += " AND province = %s"
            params.append(province_filter)
        
        # Single query with GROUP BY year, month, dekad, province
        sql = """
            SELECT 
                EXTRACT(YEAR FROM date)::int as year,
                EXTRACT(MONTH FROM date)::int as month,
                CASE 
                    WHEN EXTRACT(DAY FROM date) <= 10 THEN 1
                    WHEN EXTRACT(DAY FROM date) <= 20 THEN 2
                    ELSE 3
                END as dekad,
                province,
                SUM(rainfall_mm) as total_rainfall,
                COUNT(*) as record_count
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY 
                EXTRACT(YEAR FROM date),
                EXTRACT(MONTH FROM date),
                CASE 
                    WHEN EXTRACT(DAY FROM date) <= 10 THEN 1
                    WHEN EXTRACT(DAY FROM date) <= 20 THEN 2
                    ELSE 3
                END,
                province
            ORDER BY year, month, dekad, province
        """.format(table_name=table_name, where_clause=where_clause)
        
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        
        # Check if data exists
        if not rows:
            return JsonResponse({
                'success': False,
                'message': 'No data found in database for the given date range.',
                'data': []
            }, status=404)
        
        # ============================================================
        # Process results into the required format
        # ============================================================
        
        # Get all provinces from the results
        if province_filter:
            provinces = [province_filter]
        else:
            provinces = sorted(set(row[3] for row in rows))
        
        # Group data by year-month-dekad
        dekad_data = {}
        for row in rows:
            year = row[0]
            month = row[1]
            dekad = row[2]
            province = row[3]
            total = row[4]
            count = row[5]
            
            # Calculate start and end dates for the dekad
            if dekad == 1:
                start_day = 1
                end_day = 10
            elif dekad == 2:
                start_day = 11
                end_day = 20
            else:
                start_day = 21
                end_day = calendar.monthrange(year, month)[1]
            
            start_date_str_key = f"{year}-{month:02d}-{start_day:02d}"
            end_date_str_key = f"{year}-{month:02d}-{end_day:02d}"
            
            # Create key for grouping
            key = f"{year}-{month:02d}-D{dekad}"
            
            if key not in dekad_data:
                month_name = calendar.month_name[month][:3]  # Jan, Feb, etc.
                dekad_data[key] = {
                    'year': year,
                    'month': month,
                    'month_name': calendar.month_name[month],
                    'month_abbr': calendar.month_abbr[month],
                    'dekad': dekad,
                    'dekad_label': f"D{dekad}",
                    'date': f"{year}-{month:02d}-{start_day:02d}",
                    'start_date': f"{year}-{month:02d}-{start_day:02d}",
                    'end_date': f"{year}-{month:02d}-{end_day:02d}",
                    'period': f"{month_name} D{dekad}",
                    'sort_key': f"{year}-{month:02d}-{dekad:02d}",
                }
                # Initialize all provinces with 0
                for p in provinces:
                    dekad_data[key][p] = 0.0
                    dekad_data[key][f"{p}_count"] = 0
            
            dekad_data[key][province] = round(total, 2)
            dekad_data[key][f"{province}_count"] = count
        
        # Convert to list and sort by date
        data = sorted(dekad_data.values(), key=lambda x: x['sort_key'])
        
        # ============================================================
        # Build response
        # ============================================================
        
        response_data = {
            'success': True,
            'aggregation': 'dekadal',
            'aggregation_label': 'Dekadal (10-day periods)',
            'dekad_definitions': {
                'Dekad 1': 'Days 01-10',
                'Dekad 2': 'Days 11-20',
                'Dekad 3': 'Days 21-end of month'
            },
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'provinces': provinces,
            'total_dekads': len(data),
            'data': data,
            'metadata': {
                'source': 'database',
                'exported_at': datetime.datetime.now().isoformat()
            }
        }
        
        # ============================================================
        # Return as CSV if requested
        # ============================================================
        
        if output_format == 'csv':
            return export_dekadal_csv(response_data)
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error in dekadal rainfall aggregation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def export_dekadal_csv(response_data):
    """Export dekadal aggregation data as CSV."""
    import csv
    from django.http import HttpResponse
    
    data = response_data['data']
    provinces = response_data['provinces']
    
    if not data:
        return JsonResponse({'error': 'No data to export'}, status=404)
    
    csv_response = HttpResponse(content_type='text/csv')
    filename = f"rainfall_dekadal_{response_data['date_range']['start']}_to_{response_data['date_range']['end']}.csv"
    csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(csv_response)
    
    # Write header
    header = ['Year', 'Month', 'Dekad', 'Start Date', 'End Date', 'Period'] + provinces
    writer.writerow(header)
    
    # Write data rows
    for row in data:
        row_data = [
            row['year'],
            row['month'],
            row['dekad'],
            row['start_date'],
            row['end_date'],
            row['period']
        ]
        for province in provinces:
            row_data.append(row.get(province, 0.0))
        writer.writerow(row_data)
    
    return csv_response
#  
#
#
#
#
#
#
#
#
#
#
#OLD VIEW getting datadirect from google earth engine
# # =====================================================
# # RAINFALL DATA - CHIRPS
# # =====================================================

# import ee
# import datetime
# import json
# import logging
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods

# logger = logging.getLogger(__name__)

# # Zimbabwe Province Representative Points
# ZIMBABWE_PROVINCES = {
#     'Harare': {'lat': -17.8252, 'lng': 31.0335},
#     'Bulawayo': {'lat': -20.1486, 'lng': 28.5880},
#     'Manicaland': {'lat': -18.9216, 'lng': 32.1746},
#     'Mashonaland Central': {'lat': -16.7633, 'lng': 31.0702},
#     'Mashonaland East': {'lat': -17.5192, 'lng': 31.8667},
#     'Mashonaland West': {'lat': -17.3000, 'lng': 30.4000},
#     'Masvingo': {'lat': -20.0667, 'lng': 30.8333},
#     'Matabeleland North': {'lat': -18.9833, 'lng': 27.0000},
#     'Matabeleland South': {'lat': -21.0000, 'lng': 29.0000},
#     'Midlands': {'lat': -19.0000, 'lng': 30.0000},
# }


# def get_rainfall_at_point(lat, lng, start_date, end_date):
#     """
#     Get rainfall (CHIRPS) at a specific point for a date range.
#     Returns daily rainfall values.
#     """
#     try:
#         point = ee.Geometry.Point([lng, lat])
        
#         # Get CHIRPS daily rainfall
#         collection = (
#             ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
#             .filterBounds(point)
#             .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
#             .select('precipitation')
#         )
        
#         # Extract rainfall at point
#         def extract_rainfall(img):
#             date = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd')
#             rainfall = img.reduceRegion(
#                 reducer=ee.Reducer.mean(),
#                 geometry=point,
#                 scale=1000,
#                 maxPixels=1e9
#             )
#             return ee.Feature(None, {
#                 'date': date,
#                 'rainfall': rainfall.get('precipitation')
#             })
        
#         features = collection.map(extract_rainfall)
#         feature_list = features.getInfo()
        
#         results = []
#         for feature in feature_list.get('features', []):
#             props = feature.get('properties', {})
#             date = props.get('date')
#             rainfall = props.get('rainfall')
            
#             if date and rainfall is not None:
#                 results.append({
#                     'date': date,
#                     'rainfall': round(float(rainfall), 2)
#                 })
        
#         return results
        
#     except Exception as e:
#         logger.error(f"Error in get_rainfall_at_point: {str(e)}")
#         raise Exception(f"Failed to extract rainfall: {str(e)}")


# # =====================================================
# # API: GET RAINFALL FOR ALL PROVINCES 
# # =====================================================

# def api_rainfall_all_provinces(request):
#     """
#     Get rainfall data for all Zimbabwe provinces.
        
#     Query parameters:
#     - start_date: Start date (YYYY-MM-DD) (required)
#     - end_date: End date (YYYY-MM-DD) (required)
#     """
#     try:
#         start_date_str = request.GET.get('start_date')
#         end_date_str = request.GET.get('end_date')
        
#         if not start_date_str or not end_date_str:
#             return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
#         start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
#         end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
#         results = {}
        
#         for province, coords in ZIMBABWE_PROVINCES.items():
#             try:
#                 rainfall_data = get_rainfall_at_point(
#                     coords['lat'], 
#                     coords['lng'], 
#                     start_date, 
#                     end_date
#                 )
                
#                 # Calculate stats
#                 rain_values = [r['rainfall'] for r in rainfall_data if r['rainfall'] is not None]
#                 total_rain = sum(rain_values) if rain_values else 0
#                 avg_rain = total_rain / len(rain_values) if rain_values else 0
#                 max_rain = max(rain_values) if rain_values else 0
#                 min_rain = min(rain_values) if rain_values else 0
#                 rainy_days = len([r for r in rain_values if r > 1])  # >1mm considered rainy
                
#                 results[province] = {
#                     'coords': coords,
#                     'data': rainfall_data,
#                     'stats': {
#                         'total': round(total_rain, 2),
#                         'avg': round(avg_rain, 2),
#                         'max': round(max_rain, 2),
#                         'min': round(min_rain, 2),
#                         'rainy_days': rainy_days,
#                         'total_days': len(rainfall_data)
#                     }
#                 }
#             except Exception as e:
#                 logger.error(f"Error processing {province}: {str(e)}")
#                 results[province] = {
#                     'coords': coords,
#                     'error': str(e),
#                     'data': [],
#                     'stats': {
#                         'total': 0,
#                         'avg': 0,
#                         'max': 0,
#                         'min': 0,
#                         'rainy_days': 0,
#                         'total_days': 0
#                     }
#                 }
        
#         return JsonResponse({
#             'success': True,
#             'provinces': results,
#             'date_range': {
#                 'start': start_date_str,
#                 'end': end_date_str
#             },
#             'metadata': {
#                 'collection': 'UCSB-CHG/CHIRPS/DAILY',
#                 'processed_at': datetime.datetime.now().isoformat()
#             }
#         }, status=200)
        
#     except Exception as e:
#         logger.error(f"Error in api_rainfall_all_provinces: {str(e)}")
#         return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: GET RAINFALL FOR A SINGLE POINT (NO LOGIN)
# =====================================================

# def api_rainfall_single_point(request):
#     """
#     Get rainfall for a single point.
  
    
#     Query parameters:
#     - lat: Latitude (required)
#     - lng: Longitude (required)
#     - start_date: Start date (YYYY-MM-DD) (required)
#     - end_date: End date (YYYY-MM-DD) (required)
#     """
#     try:
#         lat = float(request.GET.get('lat'))
#         lng = float(request.GET.get('lng'))
#         start_date_str = request.GET.get('start_date')
#         end_date_str = request.GET.get('end_date')
        
#         if not start_date_str or not end_date_str:
#             return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
#         start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
#         end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
#         rainfall_data = get_rainfall_at_point(lat, lng, start_date, end_date)
        
#         # Calculate stats
#         rain_values = [r['rainfall'] for r in rainfall_data if r['rainfall'] is not None]
#         total_rain = sum(rain_values) if rain_values else 0
#         avg_rain = total_rain / len(rain_values) if rain_values else 0
#         max_rain = max(rain_values) if rain_values else 0
#         min_rain = min(rain_values) if rain_values else 0
        
#         return JsonResponse({
#             'success': True,
#             'location': {'lat': lat, 'lng': lng},
#             'data': rainfall_data,
#             'stats': {
#                 'total': round(total_rain, 2),
#                 'avg': round(avg_rain, 2),
#                 'max': round(max_rain, 2),
#                 'min': round(min_rain, 2),
#                 'total_days': len(rainfall_data),
#                 'data_points': len(rain_values)
#             },
#             'date_range': {
#                 'start': start_date_str,
#                 'end': end_date_str
#             },
#             'metadata': {
#                 'collection': 'UCSB-CHG/CHIRPS/DAILY',
#                 'processed_at': datetime.datetime.now().isoformat()
#             }
#         }, status=200)
        
#     except Exception as e:
#         logger.error(f"Error in api_rainfall_single_point: {str(e)}")
#         return JsonResponse({'error': str(e)}, status=500)




def test(request):
    """Test view for NDVI API"""
    return render(request, 'fields_admin/test.html', {})

def test_ndvi_view(request):
    """Test view for NDVI API"""
    return render(request, 'fields_admin/test_ndvi.html', {})

def test_rainfall_view(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/test_rainfall.html', {})
def rainfall_db(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/view_rainfall_db.html', {})
def rainfall_db_all(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/view_rainfall_db_all.html', {})
def rainfall_db_all_paged(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/view_rainfall_db_all_paged.html', {})

def rainfall_dashboad(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/rainfall_dashboard.html', {})


def rainfall_to_db(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/save_rain_to_db.html', {})





#
##
#
#
#
#
#
#
##
#
#
#
#
##
##
#
#
#

#
#
#
#
#
##
#
#
#
#
##
##
#
#
#
#
#
    
    
    
##################################################################################################

######################################### Crop monitoring - SENTINEL NDVI #######################################

##################################################################################################

# =====================================================
# SIMPLE NDVI CALCULATOR - Point/Area Based
# =====================================================

import ee
import datetime
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


def get_ndvi_at_point(lat, lng, start_date=None, end_date=None, cloud_cover=20):
    """
    Get NDVI at a specific point (lat/lng) using Sentinel-2.
    Returns the NDVI value and image date.
    """
    # Set default dates (last 30 days)
    if not start_date or not end_date:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
    
    # Create point geometry
    point = ee.Geometry.Point([lng, lat])
    
    # Get Sentinel-2 collection
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(point)
        .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
        .sort('system:time_start', False)  # Most recent first
        .limit(10)  # Get last 10 images for averaging
    )
    
    # Calculate NDVI for each image
    def add_ndvi(img):
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        return img.addBands(ndvi)
    
    collection = collection.map(add_ndvi)
    
    # Extract NDVI at point for each image
    def extract_ndvi(img):
        date = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd')
        ndvi = img.select('ndvi').reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=10,
            maxPixels=1e9
        )
        return ee.Feature(None, {
            'date': date,
            'ndvi': ndvi.get('ndvi')
        })
    
    features = collection.map(extract_ndvi)
    
    try:
        # Get the data
        feature_list = features.getInfo()
        
        results = []
        for feature in feature_list.get('features', []):
            props = feature.get('properties', {})
            date = props.get('date')
            ndvi = props.get('ndvi')
            
            if date and ndvi is not None:
                results.append({
                    'date': date,
                    'ndvi': round(float(ndvi), 4)
                })
        
        return results
        
    except Exception as e:
        raise Exception(f"Failed to extract NDVI: {str(e)}")


def get_ndvi_for_geometry(geometry, start_date=None, end_date=None, cloud_cover=20):
    """
    Get NDVI statistics for a geometry (polygon).
    Returns mean, min, max, std, and tile URL.
    """
    # Set default dates (last 30 days)
    if not start_date or not end_date:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
    
    # Create EE geometry
    if isinstance(geometry, dict):
        coords = geometry.get('coordinates', [])
        ee_geometry = ee.Geometry.Polygon(coords)
    else:
        ee_geometry = geometry
    
    # Get Sentinel-2 collection
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(ee_geometry)
        .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
    )
    
    # Calculate NDVI
    def add_ndvi(img):
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        return img.addBands(ndvi)
    
    collection = collection.map(add_ndvi)
    
    # Create median composite
    composite = collection.median()
    ndvi = composite.select('ndvi')
    
    # Get statistics
    stats = ndvi.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.min(), '', True
        ).combine(
            ee.Reducer.max(), '', True
        ).combine(
            ee.Reducer.stdDev(), '', True
        ).combine(
            ee.Reducer.count(), '', True
        ),
        geometry=ee_geometry,
        scale=10,
        maxPixels=1e9
    )
    
    # Get tile URL
    vis_params = {
        'min': -0.5,
        'max': 0.8,
        'palette': ['ff0000', 'ffff00', '00ff00']
    }
    ndvi_clipped = ndvi.clip(ee_geometry)
    map_id = ndvi_clipped.getMapId(vis_params)
    tile_url = map_id['tile_fetcher'].url_format
    
    # Get stats values
    try:
        stats_dict = stats.getInfo()
        ndvi_stats = {
            'mean': round(float(stats_dict.get('ndvi_mean', 0)), 4) if stats_dict.get('ndvi_mean') is not None else None,
            'min': round(float(stats_dict.get('ndvi_min', 0)), 4) if stats_dict.get('ndvi_min') is not None else None,
            'max': round(float(stats_dict.get('ndvi_max', 0)), 4) if stats_dict.get('ndvi_max') is not None else None,
            'std': round(float(stats_dict.get('ndvi_std', 0)), 4) if stats_dict.get('ndvi_std') is not None else None,
            'count': int(stats_dict.get('ndvi_count', 0)) if stats_dict.get('ndvi_count') is not None else 0
        }
    except:
        ndvi_stats = {
            'mean': None,
            'min': None,
            'max': None,
            'std': None,
            'count': 0
        }
    
    return {
        'stats': ndvi_stats,
        'tile_url': tile_url
    }


# =====================================================
# API: GET NDVI AT A POINT (FASTEST)
# =====================================================

# date range flexible start -end
@login_required
def api_ndvi_point_date_range(request):
    """
    Get NDVI at a specific point with custom date range.
    
    Query parameters:
    - lat: Latitude (required)
    - lng: Longitude (required)
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - cloud_cover: Maximum cloud cover (default: 20)
    """
    try:
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        cloud_cover = int(request.GET.get('cloud_cover', 20))
        
        if not lat or not lng:
            return JsonResponse({'error': 'lat and lng are required'}, status=400)
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        lat = float(lat)
        lng = float(lng)
        
        # Parse dates
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Create point geometry
        point = ee.Geometry.Point([lng, lat])
        
        # Get Sentinel-2 collection with date range
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(point)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
            .sort('system:time_start', False)  # Most recent first
        )
        
        # Calculate NDVI for each image
        def add_ndvi(img):
            ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
            return img.addBands(ndvi)
        
        collection = collection.map(add_ndvi)
        
        # Extract NDVI at point for each image
        def extract_ndvi(img):
            date = ee.Date(img.get('system:time_start')).format('YYYY-MM-DD')
            ndvi = img.select('ndvi').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=10,
                maxPixels=1e9
            )
            cloud = img.get('CLOUDY_PIXEL_PERCENTAGE')
            return ee.Feature(None, {
                'date': date,
                'ndvi': ndvi.get('ndvi'),
                'cloud_cover': cloud
            })
        
        features = collection.map(extract_ndvi)
        
        try:
            feature_list = features.getInfo()
            results = []
            for feature in feature_list.get('features', []):
                props = feature.get('properties', {})
                date = props.get('date')
                ndvi = props.get('ndvi')
                cloud = props.get('cloud_cover')
                
                if date and ndvi is not None:
                    results.append({
                        'date': date,
                        'ndvi': round(float(ndvi), 4),
                        'cloud_cover': round(float(cloud), 1) if cloud is not None else None
                    })
        except Exception as e:
            raise Exception(f"Failed to extract NDVI: {str(e)}")
        
        # Calculate average NDVI
        ndvi_values = [r['ndvi'] for r in results if r['ndvi'] is not None]
        avg_ndvi = round(sum(ndvi_values) / len(ndvi_values), 4) if ndvi_values else None
        
        return JsonResponse({
            'success': True,
            'location': {
                'lat': lat,
                'lng': lng
            },
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'cloud_cover': cloud_cover,
            'data_points': len(results),
            'average_ndvi': avg_ndvi,
            'all_data': results,
            'metadata': {
                'collection': 'COPERNICUS/S2_SR_HARMONIZED',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




# fixed dates 30 days from today

#@login_required
def api_ndvi_point(request):
    """
    Get NDVI at a specific point (lat/lng).
    This is the fastest endpoint.
    
    Query parameters:
    - lat: Latitude (required)
    - lng: Longitude (required)
    - days: Number of days to look back (default: 30)
    - cloud_cover: Maximum cloud cover (default: 20)
    
    Example: /api/ndvi/point/?lat=-17.49072&lng=30.97355&days=30
    """
    try:
        # Get parameters
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')
        days = int(request.GET.get('days', 30))
        cloud_cover = int(request.GET.get('cloud_cover', 20))
        
        if not lat or not lng:
            return JsonResponse({
                'error': 'lat and lng are required'
            }, status=400)
        
        lat = float(lat)
        lng = float(lng)
        
        # Set date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get NDVI
        results = get_ndvi_at_point(lat, lng, start_date, end_date, cloud_cover)
        
        # Calculate average NDVI
        ndvi_values = [r['ndvi'] for r in results if r['ndvi'] is not None]
        avg_ndvi = round(sum(ndvi_values) / len(ndvi_values), 4) if ndvi_values else None
        
        return JsonResponse({
            'success': True,
            'location': {
                'lat': lat,
                'lng': lng
            },
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'cloud_cover': cloud_cover,
            'data_points': len(results),
            'average_ndvi': avg_ndvi,
            'recent_ndvi': results[:10],  # Last 10 values
            'metadata': {
                'collection': 'COPERNICUS/S2_SR_HARMONIZED',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: GET NDVI AT DEFAULT LOCATION
# =====================================================

#@login_required
def api_ndvi_default(request):
    """
    Get NDVI at the default location (-17.49072, 30.97355).
        
    Query parameters:
    - days: Number of days to look back (default: 30)
    - cloud_cover: Maximum cloud cover (default: 20)
    
    Example: /api/ndvi/default/?days=30
    """
    try:
        # Default coordinates
        lat = -17.49072
        lng = 30.97355
        days = int(request.GET.get('days', 30))
        cloud_cover = int(request.GET.get('cloud_cover', 20))
        
        # Set date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get NDVI
        results = get_ndvi_at_point(lat, lng, start_date, end_date, cloud_cover)
        
        # Calculate average NDVI
        ndvi_values = [r['ndvi'] for r in results if r['ndvi'] is not None]
        avg_ndvi = round(sum(ndvi_values) / len(ndvi_values), 4) if ndvi_values else None
        
        # Get current NDVI (most recent)
        current_ndvi = results[0]['ndvi'] if results else None
        
        return JsonResponse({
            'success': True,
            'location': {
                'lat': lat,
                'lng': lng,
                'name': 'Default Location'
            },
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'cloud_cover': cloud_cover,
            'data_points': len(results),
            'current_ndvi': current_ndvi,
            'average_ndvi': avg_ndvi,
            'recent_ndvi': results[:10],
            'all_data': results,
            'metadata': {
                'collection': 'COPERNICUS/S2_SR_HARMONIZED',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: GET NDVI FOR A POLYGON (AREA)
# =====================================================

#@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_ndvi_area(request):
    """
    Get NDVI for an area (polygon).
    
    Expected POST data:
    {
        "geometry": {GeoJSON Polygon},
        "days": 30,  # optional
        "cloud_cover": 20  # optional
    }
    """
    try:
        data = json.loads(request.body)
        geometry = data.get('geometry')
        days = int(data.get('days', 30))
        cloud_cover = int(data.get('cloud_cover', 20))
        
        if not geometry:
            return JsonResponse({'error': 'Geometry is required'}, status=400)
        
        if geometry.get('type') != 'Polygon':
            return JsonResponse({'error': 'Geometry must be a Polygon'}, status=400)
        
        # Set date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get NDVI for geometry
        result = get_ndvi_for_geometry(geometry, start_date, end_date, cloud_cover)
        
        # Calculate area
        coords = geometry.get('coordinates', [])
        ee_geometry = ee.Geometry.Polygon(coords)
        area = ee_geometry.area().getInfo()
        area_ha = round(area / 10000, 2)
        
        return JsonResponse({
            'success': True,
            'area_ha': area_ha,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'cloud_cover': cloud_cover,
            'ndvi_stats': result['stats'],
            'tile_url': result['tile_url'],
            'metadata': {
                'collection': 'COPERNICUS/S2_SR_HARMONIZED',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

#######################################################################################
######################### View to save lat lon coords for ndvi extraction ##############
#######################################################################################
import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

# Path to save coords.json
COORDS_FILE = os.path.join(os.path.dirname(__file__), 'coords.json')

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_save_points(request):
    """Save monitoring points to coords.json"""
    try:
        data = json.loads(request.body)
        points = data.get('points', [])
        
        # Save to file
        with open(COORDS_FILE, 'w') as f:
            json.dump(points, f, indent=2)
        
        return JsonResponse({
            'success': True,
            'message': f'Saved {len(points)} points',
            'count': len(points)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_load_points(request):
    """Load monitoring points from coords.json"""
    try:
        if os.path.exists(COORDS_FILE):
            with open(COORDS_FILE, 'r') as f:
                points = json.load(f)
            return JsonResponse({
                'success': True,
                'points': points,
                'count': len(points)
            })
        else:
            return JsonResponse({
                'success': True,
                'points': [],
                'count': 0
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)