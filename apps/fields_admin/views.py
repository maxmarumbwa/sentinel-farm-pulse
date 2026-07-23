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
    
def test_ndvi_view(request):
    """Test view for NDVI API"""
    return render(request, 'fields_admin/test_ndvi.html', {})