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
# Removed @login_required
def api_field_list(request):
    """API endpoint to get fields as GeoJSON with filters"""
    try:
        # Get filter parameters
        province = request.GET.get('province')
        crop = request.GET.get('crop')
        production_system = request.GET.get('production_system')
        search = request.GET.get('search')
        
        # ✅ FIX: Only try to filter by user if they are actually logged in
        if request.user.is_authenticated:
            fields = Field.objects.filter(user=request.user).select_related('adm1', 'adm2')
        else:
            # If Postman or an AnonymousUser calls it, return empty list safely
            return JsonResponse({
                'type': 'FeatureCollection',
                'features': []
            })
        
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

######################################### Sentinel NDVI monitoring #######################################

##################################################################################################
@login_required
def ndvi_map_view(request):
    """
    Display fields with NDVI overlay on a map.
    """
    fields = Field.objects.filter(user=request.user).select_related('adm1', 'adm2')
    
    context = {
        'fields': fields,
        'total_fields': fields.count(),
    }
    
    return render(request, 'fields_admin/ndvi_map.html', context)
#
# 
# 
# 
# 
# 

# =====================================================
# SIMPLE NDVI API FOR FIELD - start and end date
# =====================================================
@login_required
def api_ndvi_all_fields(request):
    """
    Get a single NDVI raster tile covering all user's fields.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - cloud_cover: Maximum cloud cover (default: 30)
    """
    try:
        # Get parameters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        cloud_cover = int(request.GET.get('cloud_cover', 30))
        
        # Validate dates
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'start_date and end_date are required (YYYY-MM-DD)'
            }, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date > end_date:
            return JsonResponse({
                'success': False,
                'error': 'start_date must be before end_date'
            }, status=400)
        
        # Get all fields for the user
        fields = Field.objects.filter(user=request.user)
        
        if not fields:
            return JsonResponse({
                'success': False,
                'error': 'No fields found'
            }, status=404)
        
        # Combine all field geometries
        combined_geometry = None
        
        for field in fields:
            if not field.geometry:
                continue
            
            geom_json = json.loads(field.geometry.geojson)
            coords = geom_json.get('coordinates', [])
            
            if not coords or len(coords) == 0:
                continue
            
            ee_geom = ee.Geometry.Polygon(coords)
            
            if combined_geometry is None:
                combined_geometry = ee_geom
            else:
                combined_geometry = combined_geometry.union(ee_geom)
        
        if combined_geometry is None:
            return JsonResponse({
                'success': False,
                'error': 'No valid geometries found'
            }, status=404)
        
        # Buffer slightly to ensure coverage
        combined_geometry = combined_geometry.buffer(50)
        
        # Get Sentinel-2 collection
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(combined_geometry)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
        )
        
        # Calculate NDVI
        def add_ndvi(img):
            ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
            return img.addBands(ndvi)
        
        collection = collection.map(add_ndvi)
        
        # Get median composite
        composite = collection.median()
        ndvi_image = composite.select('ndvi')
        
        # Clip to geometry
        ndvi_clipped = ndvi_image.clip(combined_geometry)
        
        # Get tile URL
        vis_params = {
            'min': -0.2,
            'max': 0.8,
            'palette': [
                '#d73027', '#f46d43', '#fdae61', '#fee08b',
                '#d9ef8b', '#a6d96a', '#66bd63', '#1a9850'
            ]
        }
        
        map_id = ndvi_clipped.getMapId(vis_params)
        tile_url = map_id['tile_fetcher'].url_format
        
        return JsonResponse({
            'success': True,
            'tile_url': tile_url,
            'field_count': fields.count(),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'cloud_cover': cloud_cover
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in api_ndvi_all_fields: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

###########################################################################################################
####            ####################### View NDVI ################################
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Field

@login_required
def fields_map_view(request):
    """
    Simple view to display user's fields on a Leaflet map.
    """
    # Get all fields for the current user
    fields = Field.objects.filter(user=request.user).select_related('adm1', 'adm2')
    
    context = {
        'fields': fields,
        'total_fields': fields.count(),
    }
    
    return render(request, 'fields_admin/fields_map.html', context)

############################## API for zonal stats for single field start -end date #################################
############################################################################################################
############## Get NDVI for a single field over a selected period    ######################
from django.http import JsonResponse
from .models import Field, FieldNDVI
from datetime import datetime

def api_ndvi_single_field(request):
    """
    Get a TIME-SERIES of NDVI values from the DATABASE only.
    """
    try:
        field_id = request.GET.get('field_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if not all([field_id, start_date_str, end_date_str]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        try:
            field = Field.objects.get(id=field_id)
        except Field.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Field not found'}, status=404)
        
        # Query the database (Instant query!)
        ndvi_records = FieldNDVI.objects.filter(
            field=field,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        data = [{"date": r.date.strftime('%Y-%m-%d'), "ndvi": r.ndvi_value} for r in ndvi_records]
        
        return JsonResponse({
            'success': True,
            'field_id': int(field_id),
            'field_name': field.field_name,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'data': data
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

################# Works on the flier-################## 
# REMOVED @login_required decorator for Postman testing
# def api_ndvi_single_field(request):
    """
    Get a TIME-SERIES of NDVI values for a SINGLE field within a date range.
    """
    try:
        # Get parameters
        field_id = request.GET.get('field_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        cloud_cover = int(request.GET.get('cloud_cover', 30))
        
        if not field_id:
            return JsonResponse({'success': False, 'error': 'field_id is required'}, status=400)
        if not start_date_str or not end_date_str:
            return JsonResponse({'success': False, 'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date > end_date:
            return JsonResponse({'success': False, 'error': 'start_date must be before end_date'}, status=400)
        
        # 1. Get the field (REMOVED user ownership check for Postman testing)
        try:
            field = Field.objects.get(id=field_id)
        except Field.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Field not found'}, status=404)
        
        if not field.geometry:
            return JsonResponse({'success': False, 'error': 'Field has no geometry'}, status=400)
        
        geom_json = json.loads(field.geometry.geojson)
        coords = geom_json.get('coordinates', [])
        if not coords or len(coords) == 0:
            return JsonResponse({'success': False, 'error': 'Invalid field geometry'}, status=400)
        
        ee_geom = ee.Geometry.Polygon(coords)
        
        # 2. Get Sentinel-2 collection
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(ee_geom)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
        )
        
        # 3. Check if there are any images at all
        collection_size = collection.size().getInfo()
        if collection_size == 0:
            return JsonResponse({
                'success': False, 
                'error': f'No Sentinel-2 images found for this date range ({start_date} to {end_date}) with {cloud_cover}% cloud cover.'
            }, status=404)
        
        # 4. Calculate NDVI for the entire collection
        def add_ndvi(img):
            ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
            return img.addBands(ndvi)
        
        collection = collection.map(add_ndvi)
        
        # 5. Get ALL images with their Dates and NDVI in one go
        def extract_ndvi(img):
            ndvi_val = img.select('ndvi').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geom,
                scale=250,
                maxPixels=1e9,
                bestEffort=True
            ).get('ndvi')
            
            return ee.Feature(None, {
                'date': img.date().format('YYYY-MM-dd'),
                'ndvi': ndvi_val
            })

        features = collection.map(extract_ndvi)
        features = features.filter(ee.Filter.notNull(['ndvi']))
        feature_list = features.getInfo()
        
        # 6. Parse into dictionary to remove duplicates (AGGREGATION LOGIC)
        date_ndvi_dict = {}
        for feature in feature_list['features']:
            props = feature['properties']
            date_str = props['date']
            ndvi_val = props['ndvi']
            
            # If the date already exists in our dictionary, we average the values
            if date_str in date_ndvi_dict:
                # Sum the previous value and the new one, then divide by 2 
                # (This works perfectly because we only have 2 images per day maximum)
                existing_avg = date_ndvi_dict[date_str]
                new_avg = (existing_avg + ndvi_val) / 2
                date_ndvi_dict[date_str] = round(new_avg, 4)
            else:
                # First time seeing this date, just add it
                date_ndvi_dict[date_str] = round(ndvi_val, 4)
        
        # Convert dictionary back to a sorted list for the JSON response
        ndvi_time_series = []
        for date_str, ndvi_val in date_ndvi_dict.items():
            ndvi_time_series.append({
                "date": date_str,
                "ndvi": ndvi_val
            })
        
        # Sort by date (oldest to newest)
        ndvi_time_series.sort(key=lambda x: x['date'])
        
        return JsonResponse({
            'success': True,
            'field_id': int(field_id),
            'field_name': field.field_name,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'data': ndvi_time_series
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in api_ndvi_single_field: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

#
#
#
    """
    Get a TIME-SERIES of NDVI values for a SINGLE field within a date range.
    Skips dates with no satellite data.
    """
    try:
        # Get parameters
        field_id = request.GET.get('field_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        cloud_cover = int(request.GET.get('cloud_cover', 30))
        
        if not field_id:
            return JsonResponse({'success': False, 'error': 'field_id is required'}, status=400)
        if not start_date_str or not end_date_str:
            return JsonResponse({'success': False, 'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date > end_date:
            return JsonResponse({'success': False, 'error': 'start_date must be before end_date'}, status=400)
        
        # 1. Get the field (Ensure user owns it)
        try:
            field = Field.objects.get(id=field_id, user=request.user)
        except Field.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Field not found or access denied'}, status=404)
        
        if not field.geometry:
            return JsonResponse({'success': False, 'error': 'Field has no geometry'}, status=400)
        
        geom_json = json.loads(field.geometry.geojson)
        coords = geom_json.get('coordinates', [])
        if not coords or len(coords) == 0:
            return JsonResponse({'success': False, 'error': 'Invalid field geometry'}, status=400)
        
        ee_geom = ee.Geometry.Polygon(coords)
        
        # 2. Get Sentinel-2 collection (All images in the range)
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(ee_geom)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
        )
        
        # 3. Check if there are ANY images at all
        collection_size = collection.size().getInfo()
        if collection_size == 0:
            return JsonResponse({
                'success': False, 
                'error': f'No satellite images found for {start_date} to {end_date} with {cloud_cover}% cloud cover.'
            }, status=404)
        
        # 4. Calculate NDVI for the entire collection
        def add_ndvi(img):
            ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
            return img.addBands(ndvi)
        
        collection = collection.map(add_ndvi)
        
        # 5. Get unique dates from the satellite images
        unique_dates = collection.aggregate_array('system:time_start').getInfo()
        
        # 6. Loop through ONLY the dates that exist, and get NDVI
        ndvi_time_series = []
        for timestamp in unique_dates:
            # Convert GEE timestamp to date string
            date_obj = datetime.datetime.fromtimestamp(timestamp / 1000).date()
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # Filter collection for this specific date
            daily_collection = collection.filterDate(date_str, date_str)
            daily_size = daily_collection.size().getInfo()  # Check size manually
            
            # SAFETY CHECK: Only proceed if images exist for this day
            if daily_size > 0:
                daily_img = daily_collection.first()
                
                # Clip and reduce region
                ndvi_clipped = daily_img.select('ndvi').clip(ee_geom)
                
                mean_ndvi = ndvi_clipped.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=ee_geom,
                    scale=250,
                    maxPixels=1e9
                ).get('ndvi')
                
                ndvi_value = mean_ndvi.getInfo()
                
                if ndvi_value is not None:
                    ndvi_time_series.append({
                        "date": date_str,
                        "ndvi": round(ndvi_value, 4)
                    })
        
        if len(ndvi_time_series) == 0:
            return JsonResponse({
                'success': False,
                'error': 'Images found but all data was filtered out (possible heavy clouds).'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'field_id': int(field_id),
            'field_name': field.field_name,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'data': ndvi_time_series
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in api_ndvi_single_field: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

#######################

    """
    Get a TIME-SERIES of NDVI values for a SINGLE field within a date range.
    """
    try:
        # Get parameters
        field_id = request.GET.get('field_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        cloud_cover = int(request.GET.get('cloud_cover', 30))
        
        if not field_id:
            return JsonResponse({'success': False, 'error': 'field_id is required'}, status=400)
        if not start_date_str or not end_date_str:
            return JsonResponse({'success': False, 'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date > end_date:
            return JsonResponse({'success': False, 'error': 'start_date must be before end_date'}, status=400)
        
        # 1. Get the field (Ensure user owns it)
        try:
            field = Field.objects.get(id=field_id, user=request.user)
        except Field.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Field not found or access denied'}, status=404)
        
        if not field.geometry:
            return JsonResponse({'success': False, 'error': 'Field has no geometry'}, status=400)
        
        geom_json = json.loads(field.geometry.geojson)
        coords = geom_json.get('coordinates', [])
        if not coords or len(coords) == 0:
            return JsonResponse({'success': False, 'error': 'Invalid field geometry'}, status=400)
        
        ee_geom = ee.Geometry.Polygon(coords)
        
        # 2. Get Sentinel-2 collection
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(ee_geom)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
        )
        
        # 3. Calculate NDVI for the entire collection
        def add_ndvi(img):
            ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
            return img.addBands(ndvi)
        
        collection = collection.map(add_ndvi)
        
        # 4. Get the list of image dates to iterate over
        image_ids = collection.aggregate_array('system:time_start').getInfo()
        if len(image_ids) == 0:
            return JsonResponse({'success': False, 'error': f'No Sentinel-2 images found for the range {start_date} to {end_date}.'}, status=404)
        
        # 5. Loop through each image and get the NDVI for that specific date
        ndvi_time_series = []
        for timestamp in image_ids:
            # Convert GEE timestamp to readable date
            date_obj = datetime.datetime.fromtimestamp(timestamp / 1000).date()
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # Filter the collection to a 1-day window for this specific image
            daily_img = collection.filterDate(date_str, date_str).first()
            
            # Clip and reduce region
            ndvi_clipped = daily_img.select('ndvi').clip(ee_geom)
            
            mean_ndvi = ndvi_clipped.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geom,
                scale=250,          # Faster processing with 250m resolution
                maxPixels=1e9
            ).get('ndvi')
            
            ndvi_value = mean_ndvi.getInfo()
            
            # Only add to array if valid data exists (not null)
            if ndvi_value is not None:
                ndvi_time_series.append({
                    "date": date_str,
                    "ndvi": round(ndvi_value, 4)
                })
        
        return JsonResponse({
            'success': True,
            'field_id': int(field_id),
            'field_name': field.field_name,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'data': ndvi_time_series  # <--- This is your array of data!
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in api_ndvi_single_field: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
 
 ###
 #
 #
 #
# ####################### Single val over selected period  ##################
# # REMOVED @login_required decorator
# def api_ndvi_single_field(request):
#     """
#     Get the average NDVI value for a SINGLE specific user field.
#     """
#     try:
#         # Get parameters
#         field_id = request.GET.get('field_id')
#         start_date_str = request.GET.get('start_date')
#         end_date_str = request.GET.get('end_date')
#         cloud_cover = int(request.GET.get('cloud_cover', 30))
        
#         # Validate inputs
#         if not field_id:
#             return JsonResponse({'success': False, 'error': 'field_id is required'}, status=400)
#         if not start_date_str or not end_date_str:
#             return JsonResponse({'success': False, 'error': 'start_date and end_date are required'}, status=400)
        
#         start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
#         end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
#         if start_date > end_date:
#             return JsonResponse({'success': False, 'error': 'start_date must be before end_date'}, status=400)
        
#         # REMOVED: Authentication check for the user
        
#         # Get the specific field (REMOVED user ownership requirement)
#         try:
#             # REMOVED: user=request.user from this query
#             field = Field.objects.get(id=field_id)
#         except Field.DoesNotExist:
#             return JsonResponse({'success': False, 'error': 'Field not found'}, status=404)
        
#         if not field.geometry:
#             return JsonResponse({'success': False, 'error': 'Field has no geometry'}, status=400)
        
#         # Convert field geometry to Earth Engine format
#         geom_json = json.loads(field.geometry.geojson)
#         coords = geom_json.get('coordinates', [])
        
#         if not coords or len(coords) == 0:
#             return JsonResponse({'success': False, 'error': 'Invalid field geometry'}, status=400)
        
#         ee_geom = ee.Geometry.Polygon(coords)
        
#         # Get Sentinel-2 collection
#         collection = (
#             ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
#             .filterBounds(ee_geom)
#             .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
#             .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
#         )
        
#         # Check if we found any images
#         collection_size = collection.size().getInfo()
#         if collection_size == 0:
#             return JsonResponse({
#                 'success': False, 
#                 'error': f'No Sentinel-2 images found for this date range ({start_date} to {end_date}) with {cloud_cover}% cloud cover.'
#             }, status=404)
        
#         # Calculate NDVI
#         def add_ndvi(img):
#             ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
#             return img.addBands(ndvi)
        
#         collection = collection.map(add_ndvi)
        
#         # Get median composite and select NDVI band
#         composite = collection.median()
#         ndvi_image = composite.select('ndvi')
        
#         # Clip to the specific field geometry
#         ndvi_clipped = ndvi_image.clip(ee_geom)
        
#         # Calculate the MEAN NDVI value for this specific polygon
#         mean_ndvi = ndvi_clipped.reduceRegion(
#             reducer=ee.Reducer.mean(),
#             geometry=ee_geom,
#             scale=100,
#             maxPixels=1e9
#         ).get('ndvi')
        
#         ndvi_value = mean_ndvi.getInfo()
        
#         if ndvi_value is None:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'No valid NDVI data available for this field.'
#             }, status=404)
        
#         ndvi_value = round(ndvi_value, 4)
        
#         return JsonResponse({
#             'success': True,
#             'ndvi': ndvi_value,
#             'field_id': int(field_id),
#             'field_name': field.field_name,
#             'date_range': {
#                 'start': start_date.strftime('%Y-%m-%d'),
#                 'end': end_date.strftime('%Y-%m-%d')
#             },
#             'cloud_cover': cloud_cover
#         }, status=200)
        
#     except Exception as e:
#         logger.error(f"Error in api_ndvi_single_field: {str(e)}")
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)
# #
#
#
###########################################################################################################
######################################### Get latest NDVI ##########################################
#
## Get the latest ndviv from database
# def api_fields_latest_health(request):
#     """
#     Returns a lightweight list of every field and its latest NDVI record.
#     """
#     try:
#         # Get all fields for the user
#         fields = Field.objects.filter(user=request.user)
        
#         data = []
#         for field in fields:
#             # Get the latest NDVI record from your FieldNDVI table
#             latest_record = FieldNDVI.objects.filter(field=field).order_by('-date').first()
            
#             if latest_record:
#                 data.append({
#                     "id": field.id,
#                     "name": field.field_name,
#                     "province": field.adm1.name if field.adm1 else "Unknown",
#                     "district": field.adm2.name if field.adm2 else "Unknown",
#                     "latest_ndvi": latest_record.ndvi_value,
#                     "date": latest_record.date.strftime('%Y-%m-%d')
#                 })
        
#         return JsonResponse(data, safe=False)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
#
#
### Get latest ndvi, plus prev deks and trends
# from django.http import JsonResponse
# from django.contrib.auth.decorators import login_required
# from django.db.models import Max
# from .models import Field, FieldNDVI
# import datetime

# #removed @login_required
def api_fields_latest_health(request):
    """
    Returns a detailed list of every field including:
    - Latest NDVI (date + value)
    - Last 3 historical readings
    - Calculated trend (declining / improving / stable)
    - Health status (Stressed / Moderate / Healthy)
    """
    try:
        fields = Field.objects.filter(user=request.user)
        data = []

        for field in fields:
            # 1. Get ALL records for this field, ordered by date descending
            records = FieldNDVI.objects.filter(field=field).order_by('-date')
            
            if not records.exists():
                continue
            
            # 2. Latest Record
            latest = records.first()
            latest_data = {
                "date": latest.date.strftime('%Y-%m-%d'),
                "ndvi": latest.ndvi_value
            }

            # 3. History (Up to 3 previous readings, excluding the latest)
            history = []
            for rec in records[1:4]:  # Skip latest, take next 3
                history.append({
                    "date": rec.date.strftime('%Y-%m-%d'),
                    "ndvi": rec.ndvi_value
                })

            # 4. Calculate Trend
            # Compare latest to the average of the previous 3 records
            if len(history) >= 2:
                avg_prev = sum([h['ndvi'] for h in history]) / len(history)
                diff = latest.ndvi_value - avg_prev
                
                if diff > 0.05:
                    trend = "improving"
                elif diff < -0.05:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"  # Default if not enough data

            # 5. Calculate Status based on latest value
            if latest.ndvi_value < 0.3:
                status = "Stressed"
            elif latest.ndvi_value < 0.5:
                status = "Moderate"
            else:
                status = "Healthy"

            # 6. Build the full object
            data.append({
                "id": field.id,
                "name": field.field_name,
                "province": field.adm1.name if field.adm1 else "Unknown",
                "district": field.adm2.name if field.adm2 else "Unknown",
                "latest": latest_data,
                "history": history,
                "trend": trend,
                "status": status
            })
        
        return JsonResponse(data, safe=False)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
#

###################################################################################################

#####                   API for gettng satellite data for lat/long point                #############

###########################################################################################################
# New with cloud filter and date
from django.http import JsonResponse
import datetime
import ee
from apps.gee.ee_auth import initialize_earth_engine
from concurrent.futures import ThreadPoolExecutor
from django.core.cache import cache
import hashlib

# Initialize GEE
try:
    initialize_earth_engine()
except:
    pass

# ==========================================
# DATASET RESOLUTIONS AND CONFIG
# ==========================================
RESOLUTIONS = {
    'sentinel2': 10,
    'smap': 9000,
    'chirps': 5500,
    'era5': 27700,
    'srtm': 30,
}

# Cache TTLs (in seconds)
CACHE_TTL = {
    'srtm': 2592000,      # 30 days (static)
    'ndvi': 43200,        # 12 hours
    'soil': 86400,        # 24 hours
    'rainfall': 86400,    # 24 hours
    'temperature': 86400, # 24 hours
}

def get_cache_key(dataset, lat, lon, buffer_m):
    """Generate consistent cache key"""
    rounded_lat = round(lat, 3)
    rounded_lon = round(lon, 3)
    rounded_buffer = round(buffer_m, 0)
    key_str = f"{dataset}_{rounded_lat}_{rounded_lon}_{rounded_buffer}"
    return hashlib.md5(key_str.encode()).hexdigest()

def get_image_value_single_request(collection, ee_geom, band_name, scale, max_pixels=1e9, date_range_days=None):
    """
    Optimized: Single Earth Engine request for both date and value.
    Uses ee.Dictionary to combine date and stats in one getInfo() call.
    """
    try:
        # Apply date filter if specified (for faster search)
        if date_range_days:
            now = ee.Date(datetime.datetime.now())
            start_date = now.advance(-date_range_days, 'day')
            filtered = collection.filterDate(start_date, now)
        else:
            filtered = collection
        
        # Get latest image
        latest = (
            filtered
            .filterBounds(ee_geom)
            .sort('system:time_start', False)
            .limit(1)
            .first()
        )
        
        if not latest:
            # If no image found with date filter, try without date filter
            # This ensures we always get the latest available data
            latest = (
                collection
                .filterBounds(ee_geom)
                .sort('system:time_start', False)
                .limit(1)
                .first()
            )
            
            if not latest:
                return None, None, None
        
        # Reduce region
        stats = latest.select(band_name).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee_geom,
            scale=scale,
            maxPixels=max_pixels,
            bestEffort=True
        )
        
        # Combine date and value into single dictionary
        output = ee.Dictionary({
            'date': latest.date().format('YYYY-MM-dd'),
            'value': stats.get(band_name)
        })
        
        # Single getInfo() call
        result = output.getInfo()
        
        if result is None:
            return None, None, None
        
        date_str = result.get('date')
        value = result.get('value')
        
        # Check for NaN or None
        if value is None or (isinstance(value, float) and (value != value)):
            return None, date_str, None
            
        return None, date_str, value
        
    except Exception as e:
        print(f"Error in get_image_value_single_request: {e}")
        return None, None, None

def get_cached_or_fetch(cache_key, fetch_func, ttl):
    """Helper to get from cache or fetch and cache"""
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    result = fetch_func()
    if result is not None:
        cache.set(cache_key, result, ttl)
    return result

def api_geo_intel(request):
    """
    Optimized geospatial intelligence API.
    - Single getInfo() per dataset
    - Parallel processing
    - Aggressive caching
    - Centroid-based extraction
    """
    try:
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        buffer_m = request.GET.get('buffer', '0')
        
        if not lat or not lon:
            return JsonResponse({'error': 'lat and lon parameters are required'}, status=400)
        
        try:
            lat = float(lat)
            lon = float(lon)
            buffer_m = float(buffer_m)
        except ValueError:
            return JsonResponse({'error': 'lat, lon, and buffer must be valid numbers'}, status=400)
        
        # Use centroid for point extraction (faster than buffered mean)
        # But allow user to override with buffer parameter
        use_centroid = buffer_m <= 0
        if use_centroid:
            ee_geom = ee.Geometry.Point([lon, lat])
        else:
            ee_geom = ee.Geometry.Point([lon, lat]).buffer(buffer_m)
        
        def get_geom_for_dataset(resolution):
            """Create geometry with buffer = resolution (or user buffer if larger)"""
            if use_centroid:
                return ee.Geometry.Point([lon, lat])
            buffer_size = max(buffer_m, resolution)
            return ee.Geometry.Point([lon, lat]).buffer(buffer_size)
        
        # ==========================================
        # DEFINE ALL FETCH FUNCTIONS
        # ==========================================
        def fetch_ndvi():
            """Sentinel-2 NDVI - cached, 60-day search window"""
            cache_key = get_cache_key('ndvi', lat, lon, buffer_m)
            
            def fetch():
                try:
                    ee_geom_s2 = get_geom_for_dataset(RESOLUTIONS['sentinel2'])
                    
                    # Pre-compute NDVI on the server
                    s2_collection = (
                        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                        .filterBounds(ee_geom_s2)
                        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                    )
                    
                    # Map NDVI function
                    def add_ndvi(img):
                        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
                        return img.addBands(ndvi)
                    
                    s2_with_ndvi = s2_collection.map(add_ndvi)
                    
                    # Single request for date and value
                    _, date_str, ndvi_val = get_image_value_single_request(
                        s2_with_ndvi, ee_geom_s2, 'ndvi', 
                        RESOLUTIONS['sentinel2'], date_range_days=60  # Last 60 days only
                    )
                    
                    if ndvi_val is not None:
                        return {'value': round(ndvi_val, 4), 'date': date_str}
                    return {'value': None, 'date': None}
                except Exception as e:
                    print(f"NDVI error: {e}")
                    return {'value': None, 'date': None}
            
            return get_cached_or_fetch(cache_key, fetch, CACHE_TTL['ndvi'])
        
        def fetch_soil():
            """SMAP Soil Moisture - cached, 30-day search window"""
            cache_key = get_cache_key('soil', lat, lon, buffer_m)
            
            def fetch():
                try:
                    ee_geom_smap = get_geom_for_dataset(RESOLUTIONS['smap'])
                    smap_collection = ee.ImageCollection("NASA/SMAP/SPL4SMGP/008")
                    
                    _, date_str, soil_val = get_image_value_single_request(
                        smap_collection, ee_geom_smap, 'sm_surface',
                        RESOLUTIONS['smap'], date_range_days=30
                    )
                    
                    if soil_val is not None:
                        return {'value': round(soil_val * 100, 1), 'date': date_str}
                    return {'value': None, 'date': None}
                except Exception as e:
                    print(f"Soil moisture error: {e}")
                    return {'value': None, 'date': None}
            
            return get_cached_or_fetch(cache_key, fetch, CACHE_TTL['soil'])
        
        def fetch_elevation_slope():
            """SRTM Elevation & Slope - combined in one request, cached"""
            cache_key = get_cache_key('srtm', lat, lon, buffer_m)
            
            def fetch():
                try:
                    ee_geom_srtm = get_geom_for_dataset(RESOLUTIONS['srtm'])
                    srtm = ee.Image("USGS/SRTMGL1_003")
                    
                    # Combine elevation and slope into single image
                    slope_img = ee.Terrain.slope(srtm)
                    terrain = srtm.addBands(slope_img.rename('slope'))
                    
                    # Single reducer for both bands
                    terrain_reducer = terrain.select(['elevation', 'slope']).reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=ee_geom_srtm,
                        scale=RESOLUTIONS['srtm'],
                        maxPixels=1e9,
                        bestEffort=True
                    )
                    
                    # Single getInfo()
                    result = terrain_reducer.getInfo()
                    elevation = result.get('elevation')
                    slope = result.get('slope')
                    
                    return {
                        'elevation': round(elevation, 0) if elevation else None,
                        'slope': round(slope, 2) if slope else None
                    }
                except Exception as e:
                    print(f"Elevation/Slope error: {e}")
                    return {'elevation': None, 'slope': None}
            
            return get_cached_or_fetch(cache_key, fetch, CACHE_TTL['srtm'])
        
        def fetch_rainfall():
            """CHIRPS Rainfall - cached, NO date filter (continuous data)"""
            cache_key = get_cache_key('rainfall', lat, lon, buffer_m)
            
            def fetch():
                try:
                    # Use a larger buffer for CHIRPS (5.5km resolution)
                    chirps_buffer = max(buffer_m, RESOLUTIONS['chirps'])
                    ee_geom_chirps = ee.Geometry.Point([lon, lat]).buffer(chirps_buffer)
                    
                    chirps_collection = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                    
                    # NO date filter - get the latest available image
                    # CHIRPS is continuous, so there's always data
                    _, date_str, rain_val = get_image_value_single_request(
                        chirps_collection, ee_geom_chirps, 'precipitation',
                        RESOLUTIONS['chirps'], date_range_days=None  # No date filter
                    )
                    
                    if rain_val is not None:
                        return {'value': round(rain_val, 0), 'date': date_str}
                    return {'value': None, 'date': None}
                except Exception as e:
                    print(f"Rainfall error: {e}")
                    return {'value': None, 'date': None}
            
            return get_cached_or_fetch(cache_key, fetch, CACHE_TTL['rainfall'])
        
        def fetch_temperature():
            """ERA5 Temperature - cached, NO date filter (continuous data)"""
            cache_key = get_cache_key('temperature', lat, lon, buffer_m)
            
            def fetch():
                try:
                    # Use a larger buffer for ERA5 (31km resolution)
                    era5_buffer = max(buffer_m, RESOLUTIONS['era5'])
                    ee_geom_era5 = ee.Geometry.Point([lon, lat]).buffer(era5_buffer)
                    
                    era5_collection = ee.ImageCollection("ECMWF/ERA5/DAILY")
                    
                    # NO date filter - get the latest available image
                    # ERA5 is continuous, so there's always data
                    _, date_str, temp_k = get_image_value_single_request(
                        era5_collection, ee_geom_era5, 'mean_2m_air_temperature',
                        RESOLUTIONS['era5'], date_range_days=None  # No date filter
                    )
                    
                    if temp_k is not None:
                        return {'value': round(temp_k - 273.15, 1), 'date': date_str}
                    return {'value': None, 'date': None}
                except Exception as e:
                    print(f"Temperature error: {e}")
                    return {'value': None, 'date': None}
            
            return get_cached_or_fetch(cache_key, fetch, CACHE_TTL['temperature'])
        
        # ==========================================
        # PARALLEL EXECUTION
        # ==========================================
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_ndvi = executor.submit(fetch_ndvi)
            future_soil = executor.submit(fetch_soil)
            future_elev = executor.submit(fetch_elevation_slope)
            future_rain = executor.submit(fetch_rainfall)
            future_temp = executor.submit(fetch_temperature)
            
            # Collect results
            ndvi_result = future_ndvi.result(timeout=60)
            soil_result = future_soil.result(timeout=60)
            elev_result = future_elev.result(timeout=60)
            rain_result = future_rain.result(timeout=60)
            temp_result = future_temp.result(timeout=60)
        
        # ==========================================
        # BUILD RESPONSE
        # ==========================================
        return JsonResponse({
            'success': True,
            'lat': round(lat, 6),
            'lon': round(lon, 6),
            'buffer_m': buffer_m,
            'use_centroid': use_centroid,
            'sentinel_ndvi': ndvi_result.get('value'),
            'sentinel_ndvi_date': ndvi_result.get('date'),
            'soil_moisture': soil_result.get('value'),
            'soil_moisture_date': soil_result.get('date'),
            'elevation': elev_result.get('elevation'),
            'slope': elev_result.get('slope'),
            'rainfall_latest': rain_result.get('value'),
            'rainfall_date': rain_result.get('date'),
            'temperature_latest': temp_result.get('value'),
            'temperature_date': temp_result.get('date'),
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    
    #
#
#
# OLD no dates and cloud filter
# import datetime
# import ee
# from apps.gee.ee_auth import initialize_earth_engine

# # Initialize GEE
# try:
#     initialize_earth_engine()
# except:
#     pass

# def api_geo_intel(request):
#     """
#     Returns essential geospatial intelligence for any Lat/Lon coordinate.
#     Optimized for speed - only returns key metrics.
#     Expects GET parameters: lat, lon
#     Optional GET parameter: buffer (meters, default 0)
#     """
#     try:
#         lat = request.GET.get('lat')
#         lon = request.GET.get('lon')
#         buffer_m = request.GET.get('buffer', '0')
        
#         if not lat or not lon:
#             return JsonResponse({'error': 'lat and lon parameters are required'}, status=400)
        
#         try:
#             lat = float(lat)
#             lon = float(lon)
#             buffer_m = float(buffer_m)
#         except ValueError:
#             return JsonResponse({'error': 'lat, lon, and buffer must be valid numbers'}, status=400)
        
#         # Create geometry
#         if buffer_m > 0:
#             ee_geom = ee.Geometry.Point([lon, lat]).buffer(buffer_m)
#         else:
#             ee_geom = ee.Geometry.Point([lon, lat])

#         # ==========================================
#         # 1. SENTINEL-2 NDVI (Quick, single most recent)
#         # ==========================================
#         end_date = datetime.date.today()
#         start_date = end_date - datetime.timedelta(days=30)
        
#         sentinel_ndvi = None
#         try:
#             s2_collection = (
#                 ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
#                 .filterBounds(ee_geom)
#                 .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
#                 .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
#                 .sort('system:time_start', False)  # Get most recent
#                 .limit(1)  # Just get one image for speed
#             )
            
#             if s2_collection.size().getInfo() > 0:
#                 def add_ndvi(img):
#                     ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
#                     return img.addBands(ndvi)
                
#                 s2_img = s2_collection.map(add_ndvi).first()
#                 s2_reducer = s2_img.select('ndvi').reduceRegion(
#                     reducer=ee.Reducer.mean(),
#                     geometry=ee_geom,
#                     scale=10,
#                     maxPixels=1e9,
#                     bestEffort=True
#                 )
#                 sentinel_ndvi = s2_reducer.get('ndvi').getInfo()
#                 if sentinel_ndvi is not None:
#                     sentinel_ndvi = round(sentinel_ndvi, 4)
#         except:
#             pass

#         # ==========================================
#         # 2. SOIL MOISTURE (Latest SMAP)
#         # ==========================================
#         soil_moisture = None
#         try:
#             smap = ee.ImageCollection("NASA/SMAP/SPL4SMGP/007")
#             latest_smap = smap.filterBounds(ee_geom).sort('system:time_start', False).limit(1).first()
            
#             if latest_smap:
#                 smap_reducer = latest_smap.select('sm_surface').reduceRegion(
#                     reducer=ee.Reducer.mean(),
#                     geometry=ee_geom,
#                     scale=9000,
#                     maxPixels=1e9,
#                     bestEffort=True
#                 )
#                 soil_moisture = smap_reducer.get('sm_surface').getInfo()
#                 if soil_moisture is not None:
#                     soil_moisture = round(soil_moisture * 100, 1)
#         except:
#             pass

#         # ==========================================
#         # 3. ELEVATION & SLOPE (SRTM) - Optimized
#         # ==========================================
#         elevation = None
#         slope = None
#         try:
#             srtm = ee.Image("USGS/SRTMGL1_003")
            
#             # Use a smaller scale for faster processing
#             elevation_reducer = srtm.reduceRegion(
#                 reducer=ee.Reducer.mean(),
#                 geometry=ee_geom,
#                 scale=90,  # Increased scale for speed
#                 maxPixels=1e9,
#                 bestEffort=True
#             )
#             elevation = elevation_reducer.get('elevation').getInfo()
#             if elevation is not None:
#                 elevation = round(elevation, 0)
            
#             slope_img = ee.Terrain.slope(srtm)
#             slope_reducer = slope_img.reduceRegion(
#                 reducer=ee.Reducer.mean(),
#                 geometry=ee_geom,
#                 scale=90,  # Increased scale for speed
#                 maxPixels=1e9,
#                 bestEffort=True
#             )
#             slope = slope_reducer.get('slope').getInfo()
#             if slope is not None:
#                 slope = round(slope, 2)
#         except:
#             pass

#         # ==========================================
#         # 4. RAINFALL - Latest single day (CHIRPS)
#         # ==========================================
#         rainfall_latest = None
#         try:
#             chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
#             latest_chirps = chirps.filterBounds(ee_geom).sort('system:time_start', False).limit(1).first()
            
#             if latest_chirps:
#                 latest_reducer = latest_chirps.select('precipitation').reduceRegion(
#                     reducer=ee.Reducer.mean(),
#                     geometry=ee_geom,
#                     scale=5500,
#                     maxPixels=1e9,
#                     bestEffort=True
#                 )
#                 rainfall_latest = latest_reducer.get('precipitation').getInfo()
#                 if rainfall_latest is not None:
#                     rainfall_latest = round(rainfall_latest, 0)
#         except:
#             pass

#         # ==========================================
#         # 5. TEMPERATURE - Latest day (ERA5)
#         # ==========================================
#         temperature_latest = None
#         try:
#             era5 = ee.ImageCollection("ECMWF/ERA5/DAILY")
#             latest_era5 = era5.filterBounds(ee_geom).sort('system:time_start', False).limit(1).first()
            
#             if latest_era5:
#                 latest_temp_reducer = latest_era5.select('mean_2m_air_temperature').reduceRegion(
#                     reducer=ee.Reducer.mean(),
#                     geometry=ee_geom,
#                     scale=27700,
#                     maxPixels=1e9,
#                     bestEffort=True
#                 )
#                 temp_k = latest_temp_reducer.get('mean_2m_air_temperature').getInfo()
#                 if temp_k is not None:
#                     temperature_latest = round(temp_k - 273.15, 1)
#         except:
#             pass

#         # ==========================================
#         # 6. Build Minimal Response
#         # ==========================================
#         return JsonResponse({
#             'success': True,
#             'lat': round(lat, 6),
#             'lon': round(lon, 6),
#             'buffer_m': buffer_m,
#             'sentinel_ndvi': sentinel_ndvi,
#             'soil_moisture': soil_moisture,
#             'elevation': elevation,
#             'slope': slope,
#             'rainfall_latest': rainfall_latest,
#             'temperature_latest': temperature_latest,
#         }, status=200)

#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)





###################################################################################################


                                #  AGGRREGATION FUNCTION YEAR - MONTH, DEKAD


##########################################################################################################
#
# apps/fields_admin/views.py
"""
API views for climate data aggregation.
"""
@csrf_exempt
@require_http_methods(['GET'])
def climate_aggregate(request):
    """
    Main aggregation endpoint.
    
    Query parameters:
    - product: rainfall, ndvi, temperature, or all
    - start_date: YYYY-MM-DD (required)
    - end_date: YYYY-MM-DD (required)
    - period: daily, dekad, monthly, annual, seasonal
    - aggregation: sum, mean, median, max, min, std
    - include_lta: true/false (default: false)
    - lta_start: YYYY (optional) - if not provided, uses default from config
    - lta_end: YYYY (optional) - if not provided, uses default from config
    - metrics: comma-separated list (anomaly, pct_average, zscore, spi, vci, tci, vhi)
    - province: (optional) Filter by specific province
    - season: (optional) For seasonal aggregation
    - format: json (default) or csv
    
    Data Flow:
    1. Load raw daily data for requested period
    2. Aggregate for requested period (monthly/dekad/seasonal/etc)
    3. If LTA requested:
       a. Use default LTA from config OR user-specified lta_start/lta_end
       b. Load raw daily data for LTA period
       c. Aggregate using SAME aggregation method
       d. Calculate LTA: average per period-province (for seasonal: per season-province)
    4. Apply metrics (anomaly, pct_average, etc.)
    5. Serialize and return
    """
    try:
        # Parse query parameters
        product = request.GET.get('product')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        period = request.GET.get('period', 'monthly')
        aggregation = request.GET.get('aggregation')
        include_lta = request.GET.get('include_lta', 'false').lower() == 'true'
        lta_start = request.GET.get('lta_start')
        lta_end = request.GET.get('lta_end')
        metrics_param = request.GET.get('metrics', '')
        province_filter = request.GET.get('province')
        season = request.GET.get('season', 'FULL')
        output_format = request.GET.get('format', 'json').lower()
        
        # Validate required parameters
        if not product:
            return JsonResponse({
                'error': 'product is required',
                'available_products': list(PRODUCTS.keys())
            }, status=400)
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'error': 'start_date and end_date are required',
                'example': '/api/climate/aggregate/?product=rainfall&start_date=2000-01-01&end_date=2024-12-31&period=monthly'
            }, status=400)
        
        # Parse dates
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            return JsonResponse({
                'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
            }, status=400)
        
        # Resolve product
        product_configs = resolve_product(product)
        if not product_configs:
            return JsonResponse({
                'error': f'Invalid product: {product}',
                'available_products': list(PRODUCTS.keys())
            }, status=400)
        
        # ============================================================
        # DETERMINE LTA PERIOD
        # Always use default from config unless user specifies
        # ============================================================
        lta_start_year = None
        lta_end_year = None
        lta_start_date = None
        lta_end_date = None
        
        if include_lta:
            # Get the first product's config for default LTA
            first_product_config = product_configs[0].get('config', {})
            
            if lta_start and lta_end:
                # User explicitly specified LTA period - use it
                try:
                    lta_start_year = int(lta_start)
                    lta_end_year = int(lta_end)
                    lta_start_date = datetime.date(lta_start_year, 1, 1)
                    lta_end_date = datetime.date(lta_end_year, 12, 31)
                    logger.info(f"Using user-specified LTA period: {lta_start_year}-{lta_end_year}")
                except ValueError:
                    return JsonResponse({
                        'error': 'lta_start and lta_end must be valid years'
                    }, status=400)
            else:
                # No user LTA specified - use default from config
                default_lta = first_product_config.get('default_lta', DEFAULT_LTA)
                lta_start_year = default_lta[0]
                lta_end_year = default_lta[1]
                lta_start_date = datetime.date(lta_start_year, 1, 1)
                lta_end_date = datetime.date(lta_end_year, 12, 31)
                logger.info(f"Using default LTA period from config: {lta_start_year}-{lta_end_year}")
        
        # Get aggregation method
        if not aggregation:
            product_config = product_configs[0].get('config', {})
            aggregation = product_config.get('default_aggregation', 'mean')
        
        # Prepare filters
        filters = {}
        if province_filter:
            filters['province'] = province_filter
        
        # Process each product
        all_results = []
        all_metadata = {
            'products': [],
            'period': period,
            'aggregation': aggregation,
            'include_lta': include_lta,
            'lta_period': None
        }
        
        metrics_list = []
        
        for product_config in product_configs:
            product_name = product_config['product']
            model = product_config['model']
            product_info = product_config.get('config', {})
            value_field = product_info.get('value_field', 'value')
            
            # ============================================================
            # STEP 1: Load raw daily data for requested period
            # ============================================================
            raw_data = load_data(model, start_date, end_date, filters)
            
            if not raw_data:
                logger.warning(f"No data found for {product_name}")
                continue
            
            logger.info(f"Loaded {len(raw_data)} raw records for {product_name}")
            
            # ============================================================
            # STEP 2: Aggregate for requested period
            # ============================================================
            kwargs = {}
            season_def = None
            if period == 'seasonal':
                season_def = SEASON_DEFINITIONS.get(season)
                if not season_def:
                    return JsonResponse({
                        'error': f'Invalid season: {season}',
                        'available_seasons': list(SEASON_DEFINITIONS.keys())
                    }, status=400)
                kwargs['season_def'] = season_def
                kwargs['season'] = season
                kwargs['season_label'] = season_def['label']
                kwargs['cross_year'] = season_def['cross_year']
            
            # Aggregate the data
            aggregated = aggregate(raw_data, period, aggregation, **kwargs)
            
            logger.info(f"Aggregated to {len(aggregated)} records for {product_name}")
            
            # ============================================================
            # STEP 3: Calculate LTA from raw data for LTA period
            # Uses default from config OR user-specified
            # ============================================================
            lta_lookup = {}
            lta_count_lookup = {}
            lta_years = []
            
            if include_lta and lta_start_date is not None and lta_end_date is not None:
                # Load raw data for LTA period
                lta_raw_data = load_data(model, lta_start_date, lta_end_date, filters)
                
                if lta_raw_data:
                    logger.info(f"Loaded {len(lta_raw_data)} raw records for LTA period {lta_start_year}-{lta_end_year}")
                    
                    # Aggregate LTA data using SAME aggregation method
                    lta_aggregated = aggregate(lta_raw_data, period, aggregation, **kwargs)
                    
                    logger.info(f"LTA aggregated to {len(lta_aggregated)} records")
                    
                    # ============================================================
                    # Group LTA by PERIOD TYPE (not by year)
                    # For seasonal: group by season|province
                    # For monthly: group by month|province
                    # For dekad: group by month-dekad|province
                    # ============================================================
                    lta_groups = {}
                    
                    for item in lta_aggregated:
                        province = item['province']
                        value = item['value']
                        
                        if period == 'seasonal':
                            # For seasonal: group by season|province
                            season_name = item.get('season', season)
                            group_key = f"{season_name}|{province}"
                        elif period == 'monthly':
                            # For monthly: group by month|province
                            month = item['metadata'].get('month', 0)
                            group_key = f"M{month:02d}|{province}"
                        elif period == 'dekad':
                            # For dekad: group by month-dekad|province
                            month = item['metadata'].get('month', 0)
                            dekad = item['metadata'].get('dekad', 0)
                            group_key = f"M{month:02d}-D{dekad}|{province}"
                        elif period == 'annual':
                            # For annual: group by province only
                            group_key = f"ANNUAL|{province}"
                        else:
                            # Default: group by period_key and province
                            group_key = f"{item['period_key']}|{province}"
                        
                        if group_key not in lta_groups:
                            lta_groups[group_key] = []
                        lta_groups[group_key].append(value)
                    
                    # Calculate averages for each group
                    for group_key, values in lta_groups.items():
                        if values:
                            lta_lookup[group_key] = round(sum(values) / len(values), 2)
                            lta_count_lookup[group_key] = len(values)
                            logger.debug(f"LTA for {group_key}: {lta_lookup[group_key]} from {len(values)} values")
                    
                    # Get unique years for LTA period
                    lta_years = sorted(set(
                        item.get('year', 0) for item in lta_aggregated 
                        if item.get('year')
                    ))
                    
                    all_metadata['lta_period'] = {
                        'start_year': lta_start_year,
                        'end_year': lta_end_year,
                        'num_years': len(lta_years),
                        'years': lta_years,
                        'description': f"{len(lta_years)} years ({lta_start_year}-{lta_end_year})",
                        'note': 'LTA is calculated from the available data in the LTA period'
                    }
                    
                    logger.info(f"LTA calculated for {len(lta_lookup)} period-province combinations")
                    logger.info(f"LTA keys: {list(lta_lookup.keys())}")
                else:
                    logger.warning(f"No data found for LTA period {lta_start_year}-{lta_end_year}")
            
            # ============================================================
            # STEP 4: Add LTA to aggregated data
            # ============================================================
            product_data = []
            for item in aggregated:
                product_item = {
                    'period_key': item['period_key'],
                    'province': item.get('province', 'Unknown'),
                    'value': item['value'],
                    'count': item['count'],
                    'metadata': item['metadata'],
                    'product': product_name,
                    'value_field': value_field
                }
                
                # Add season info if seasonal
                if period == 'seasonal':
                    product_item['season'] = item.get('season', season)
                    if 'metadata' in product_item and product_item['metadata']:
                        product_item['metadata']['season'] = item.get('season', season)
                
                # Add LTA if available
                if include_lta and lta_lookup:
                    # Build the lookup key based on period type
                    if period == 'seasonal':
                        season_name = item.get('season', season)
                        lookup_key = f"{season_name}|{item['province']}"
                    elif period == 'monthly':
                        month = item['metadata'].get('month', 0)
                        lookup_key = f"M{month:02d}|{item['province']}"
                    elif period == 'dekad':
                        month = item['metadata'].get('month', 0)
                        dekad = item['metadata'].get('dekad', 0)
                        lookup_key = f"M{month:02d}-D{dekad}|{item['province']}"
                    elif period == 'annual':
                        lookup_key = f"ANNUAL|{item['province']}"
                    else:
                        lookup_key = f"{item['period_key']}|{item['province']}"
                    
                    product_item['lta'] = lta_lookup.get(lookup_key, 0)
                    product_item['lta_count'] = lta_count_lookup.get(lookup_key, 0)
                    
                    logger.debug(f"Item {item['period_key']}|{item['province']} LTA: {product_item['lta']}")
                else:
                    product_item['lta'] = 0
                    product_item['lta_count'] = 0
                
                product_data.append(product_item)
            
            # ============================================================
            # STEP 5: Apply metrics
            # ============================================================
            if metrics_param:
                requested_metrics = [m.strip().lower() for m in metrics_param.split(',') if m.strip()]
                for metric_name in requested_metrics:
                    if metric_name in METRIC_FUNCTIONS:
                        try:
                            metric_func = METRIC_FUNCTIONS[metric_name]
                            product_data = metric_func(product_data)
                            if metric_name not in metrics_list:
                                metrics_list.append(metric_name)
                        except Exception as e:
                            logger.error(f"Error applying metric {metric_name}: {str(e)}")
            
            # Add product data to results
            all_results.extend(product_data)
            all_metadata['products'].append({
                'name': product_name,
                'display_name': product_info.get('display_name', product_name),
                'unit': product_info.get('unit', ''),
                'records': len(product_data)
            })
        
        # Check if we have any results
        if not all_results:
            return JsonResponse({
                'success': False,
                'message': 'No data found for the given parameters',
                'data': []
            }, status=404)
        
        # ============================================================
        # STEP 6: Serialize data (pivot format)
        # ============================================================
        serialized_data = serialize(all_results, all_metadata, pivot=True)
        
        # ============================================================
        # STEP 7: Build response
        # ============================================================
        response = build_response(
            serialized_data['data'],
            product,
            period,
            aggregation,
            include_lta,
            metrics_list if metrics_param else []
        )
        
        # Add metadata to response
        response['metadata']['products'] = all_metadata['products']
        response['metadata']['lta_period'] = all_metadata.get('lta_period')
        response['metadata']['date_range'] = {
            'start': start_date_str,
            'end': end_date_str
        }
        
        response['provinces'] = serialized_data.get('provinces', [])
        response['total_periods'] = len(serialized_data['data'])
        
        response['fields_explanation'] = {
            'rainfall': 'Total monthly rainfall (mm)',
            'lta': 'Long-Term Average monthly rainfall (mm)',
            'lta_count': 'Number of years used to calculate LTA',
            'anomaly': 'Rainfall - LTA (mm)',
            'pct_avg': 'Percentage of LTA (%)'
        }
        
        # If CSV requested
        if output_format == 'csv':
            return export_pivot_csv(response)
        
        return JsonResponse(response, status=200)
        
    except Exception as e:
        logger.error(f"Error in climate_aggregate: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


def export_pivot_csv(response_data):
    """Export pivot table data to CSV."""
    data = response_data.get('data', [])
    provinces = response_data.get('provinces', [])
    
    if not data:
        return JsonResponse({'error': 'No data to export'}, status=404)
    
    csv_response = HttpResponse(content_type='text/csv')
    filename = f"climate_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(csv_response)
    
    # Build header
    header = ['Period', 'Year', 'Month']
    if data and 'month_name' in data[0]:
        header.append('Month Name')
    
    for province in provinces:
        header.extend([
            f'{province}',
            f'{province}_lta',
            f'{province}_lta_count',
            f'{province}_anomaly',
            f'{province}_pct_avg'
        ])
    
    writer.writerow(header)
    
    # Write data rows
    for row in data:
        row_data = [
            row.get('period', ''),
            row.get('year', ''),
            row.get('month', '')
        ]
        
        if 'month_name' in row:
            row_data.append(row.get('month_name', ''))
        
        for province in provinces:
            row_data.extend([
                row.get(province, 0.0),
                row.get(f'{province}_lta', 0.0),
                row.get(f'{province}_lta_count', 0),
                row.get(f'{province}_anomaly', 0.0),
                row.get(f'{province}_pct_avg', 0.0)
            ])
        
        writer.writerow(row_data)
    
    return csv_response


# Backward compatibility functions
def rainfall_monthly(request):
    """Backward compatibility for monthly rainfall endpoint."""
    request.GET = request.GET.copy()
    request.GET['product'] = 'rainfall'
    request.GET['period'] = 'monthly'
    if 'format' not in request.GET:
        request.GET['format'] = 'json'
    return climate_aggregate(request)


def rainfall_dekadal(request):
    """Backward compatibility for dekadal rainfall endpoint."""
    request.GET = request.GET.copy()
    request.GET['product'] = 'rainfall'
    request.GET['period'] = 'dekad'
    if 'format' not in request.GET:
        request.GET['format'] = 'json'
    return climate_aggregate(request)


def rainfall_annual(request):
    """Backward compatibility for annual rainfall endpoint."""
    request.GET = request.GET.copy()
    request.GET['product'] = 'rainfall'
    request.GET['period'] = 'seasonal'
    if 'format' not in request.GET:
        request.GET['format'] = 'json'
    return climate_aggregate(request)


def health_check(request):
    """Health check endpoint."""
    return JsonResponse({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'available_products': list(PRODUCTS.keys()),
        'available_metrics': list(METRIC_FUNCTIONS.keys())
    })

##
#
##############################################################################################

#
#                           OLD rainfall aggreation only api
#
#
###########################################################################################@@
# MONTHLY RAINFALL AGGREGATION WITH CORRECT LTA
# LTA is calculated from the data available in the date range
# # =====================================================

# import datetime
# import calendar
# import logging
# from django.http import JsonResponse
# from django.db import connection
# from .models import RainfallProvince

# logger = logging.getLogger(__name__)


# def api_rainfall_monthly(request):
#     """
#     Get monthly aggregated rainfall data with Long-Term Average (LTA),
#     Anomaly, and Percentage of Average.
    
#     LTA is calculated from the data available in the requested date range.
#     e.g., if start_date=2000-01-01 and end_date=2001-03-31,
#     LTA_Jan = (Jan2000 + Jan2001) / 2
    
#     Query parameters:
#     - start_date: Start date (YYYY-MM-DD) (required)
#     - end_date: End date (YYYY-MM-DD) (required)
#     - province: (optional) Filter by specific province
#     - lta_start: (optional) Override start year for LTA
#     - lta_end: (optional) Override end year for LTA
#     - format: json (default) or csv
#     """
#     try:
#         # Get query parameters
#         start_date_str = request.GET.get('start_date')
#         end_date_str = request.GET.get('end_date')
#         province_filter = request.GET.get('province')
#         lta_start_year = request.GET.get('lta_start')
#         lta_end_year = request.GET.get('lta_end')
#         output_format = request.GET.get('format', 'json').lower()
        
#         if not start_date_str or not end_date_str:
#             return JsonResponse({
#                 'error': 'start_date and end_date are required',
#                 'example': '/api/rainfall/monthly/lta/?start_date=2000-01-01&end_date=2020-12-31'
#             }, status=400)
        
#         start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
#         end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
#         # Determine LTA period
#         # If lta_start/lta_end are provided, use them
#         # Otherwise, use the years from the requested date range
#         if lta_start_year and lta_end_year:
#             lta_start = int(lta_start_year)
#             lta_end = int(lta_end_year)
#         else:
#             # Use the years from the requested date range
#             lta_start = start_date.year
#             lta_end = end_date.year
        
#         # ============================================================
#         # STEP 1: Get monthly totals for the requested period
#         # ============================================================
        
#         table_name = RainfallProvince._meta.db_table
        
#         where_clause = "date >= %s AND date <= %s"
#         params = [start_date, end_date]
        
#         if province_filter:
#             where_clause += " AND province = %s"
#             params.append(province_filter)
        
#         sql_monthly = f"""
#             SELECT 
#                 EXTRACT(YEAR FROM date)::int as year,
#                 EXTRACT(MONTH FROM date)::int as month,
#                 province,
#                 SUM(rainfall_mm) as total_rainfall
#             FROM {table_name}
#             WHERE {where_clause}
#             GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date), province
#             ORDER BY year, month, province
#         """
        
#         with connection.cursor() as cursor:
#             cursor.execute(sql_monthly, params)
#             monthly_rows = cursor.fetchall()
        
#         if not monthly_rows:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'No data found for the given date range.',
#                 'data': []
#             }, status=404)
        
#         # Get all provinces
#         if province_filter:
#             provinces = [province_filter]
#         else:
#             provinces = sorted(set(row[2] for row in monthly_rows))
        
#         # ============================================================
#         # STEP 2: Calculate LTA for each month using the LTA period
#         # LTA = average of monthly totals for each month within LTA period
#         # ============================================================
        
#         lta_where = f"EXTRACT(YEAR FROM date) BETWEEN {lta_start} AND {lta_end}"
#         if province_filter:
#             lta_where += f" AND province = '{province_filter}'"
        
#         # Get monthly totals for LTA period
#         sql_monthly_lta = f"""
#             SELECT 
#                 EXTRACT(YEAR FROM date)::int as year,
#                 EXTRACT(MONTH FROM date)::int as month,
#                 province,
#                 SUM(rainfall_mm) as monthly_total
#             FROM {table_name}
#             WHERE {lta_where}
#             GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date), province
#         """
        
#         with connection.cursor() as cursor:
#             cursor.execute(sql_monthly_lta)
#             monthly_lta_rows = cursor.fetchall()
        
#         # Group monthly totals by month and province
#         lta_data = {}
#         lta_years_set = set()
        
#         for row in monthly_lta_rows:
#             year = row[0]
#             month = row[1]
#             province = row[2]
#             monthly_total = row[3]
            
#             key = f"{month}-{province}"
#             if key not in lta_data:
#                 lta_data[key] = []
#             lta_data[key].append(monthly_total)
#             lta_years_set.add(year)
        
#         # Calculate LTA as average of monthly totals
#         lta_lookup = {}
#         lta_count_lookup = {}
        
#         for key, values in lta_data.items():
#             lta_lookup[key] = round(sum(values) / len(values), 2)
#             lta_count_lookup[key] = len(values)
        
#         lta_num_years = len(lta_years_set)
#         lta_years = sorted(lta_years_set)
        
#         # ============================================================
#         # STEP 3: Combine data with LTA
#         # ============================================================
        
#         month_data = {}
#         for row in monthly_rows:
#             year = row[0]
#             month = row[1]
#             province = row[2]
#             total = row[3]
            
#             key = f"{year}-{month:02d}"
            
#             if key not in month_data:
#                 month_data[key] = {
#                     'year': year,
#                     'month': month,
#                     'month_name': calendar.month_name[month],
#                     'month_abbr': calendar.month_abbr[month],
#                     'date': f"{year}-{month:02d}-01",
#                     'period': f"{calendar.month_name[month]} {year}",
#                     'sort_key': f"{year}-{month:02d}",
#                 }
#                 for p in provinces:
#                     month_data[key][p] = 0.0
#                     month_data[key][f"{p}_lta"] = 0.0
#                     month_data[key][f"{p}_lta_count"] = 0
#                     month_data[key][f"{p}_anomaly"] = 0.0
#                     month_data[key][f"{p}_pct_avg"] = 0.0
            
#             lta_key = f"{month}-{province}"
#             lta_value = lta_lookup.get(lta_key, 0.0)
#             lta_count = lta_count_lookup.get(lta_key, 0)
            
#             anomaly = total - lta_value
#             pct_avg = (total / lta_value * 100) if lta_value > 0 else 0
            
#             month_data[key][province] = round(total, 2)
#             month_data[key][f"{province}_lta"] = lta_value
#             month_data[key][f"{province}_lta_count"] = lta_count
#             month_data[key][f"{province}_anomaly"] = round(anomaly, 2)
#             month_data[key][f"{province}_pct_avg"] = round(pct_avg, 1)
        
#         data = sorted(month_data.values(), key=lambda x: x['sort_key'])
        
#         # ============================================================
#         # STEP 4: Build response
#         # ============================================================
        
#         response_data = {
#             'success': True,
#             'aggregation': 'monthly',
#             'aggregation_label': 'Monthly with LTA',
#             'lta_period': {
#                 'start_year': lta_start,
#                 'end_year': lta_end,
#                 'num_years': lta_num_years,
#                 'years': lta_years,
#                 'description': f"{lta_num_years} years ({lta_start}-{lta_end})",
#                 'note': 'LTA is calculated from the available data in the LTA period'
#             },
#             'date_range': {
#                 'start': start_date_str,
#                 'end': end_date_str
#             },
#             'provinces': provinces,
#             'total_months': len(data),
#             'fields_explanation': {
#                 'rainfall': 'Total monthly rainfall (mm)',
#                 'lta': 'Long-Term Average monthly rainfall (mm)',
#                 'lta_count': 'Number of years used to calculate LTA',
#                 'anomaly': 'Rainfall - LTA (mm)',
#                 'pct_avg': 'Percentage of LTA (%)'
#             },
#             'data': data,
#             'metadata': {
#                 'source': 'database',
#                 'exported_at': datetime.datetime.now().isoformat()
#             }
#         }
        
#         if output_format == 'csv':
#             return export_monthly_lta_csv(response_data)
        
#         return JsonResponse(response_data, status=200)
        
#     except Exception as e:
#         logger.error(f"Error in monthly LTA aggregation: {str(e)}")
#         return JsonResponse({'error': str(e)}, status=500)


# def export_monthly_csv_optimized(response_data):


# =====================================================
#OLD working ANNUAL/SEASONAL RAINFALL AGGREGATION WITH LTA
# # =====================================================

# import datetime
# import calendar
# import logging
# from django.http import JsonResponse
# from django.db import connection
# from .models import RainfallProvince

# logger = logging.getLogger(__name__)


# def api_rainfall_annual(request):
#     """
#     Get annual and seasonal aggregated rainfall data with Long-Term Average (LTA),
#     Anomaly, and Percentage of Average.
    
#     Seasons:
#     - FULL: January - December (Full Year)
#     - OND: October, November, December (Early summer / onset)
#     - NDJ: November, December, January (Mid-summer transition)
#     - DJF: December, January, February (Peak summer rainy season)
#     - JFM: January, February, March (Late summer / tropical cyclone)
#     - FMA: February, March, April (End of summer / tail-end)
#     - ONDJFM: October, November, December, January, February, March (Cross-year rainy season)
#     - ON: October, November (Early onset)
#     - ND: November, December (Mid onset)
#     - JF: January, February (Peak rains)
#     - MA: March, April (Late rains / tail-end)
    
#     LTA is calculated from the data available in the requested date range.
#     e.g., if start_year=2000 and end_year=2024,
#     LTA_DJF = average of all DJF seasons from 2000-2024
    
#     Query parameters:
#     - start_year: Start year (YYYY) (required)
#     - end_year: End year (YYYY) (required)
#     - province: (optional) Filter by specific province
#     - season: (optional) full, OND, NDJ, DJF, JFM, FMA, ONDJFM, ON, ND, JF, MA (default: full)
#     - lta_start: (optional) Override start year for LTA
#     - lta_end: (optional) Override end year for LTA
#     - format: json (default) or csv
    
#     Example:
#     /api/rainfall/annual/lta/?start_year=2000&end_year=2024&province=Harare
#     /api/rainfall/annual/lta/?start_year=2000&end_year=2024&season=DJF&province=Harare
#     """
#     try:
#         # Get query parameters
#         start_year = int(request.GET.get('start_year'))
#         end_year = int(request.GET.get('end_year'))
#         province_filter = request.GET.get('province')
#         season_filter = request.GET.get('season', 'FULL').upper()
#         lta_start_year = request.GET.get('lta_start')
#         lta_end_year = request.GET.get('lta_end')
#         output_format = request.GET.get('format', 'json').lower()
        
#         # Validate parameters
#         if start_year > end_year:
#             return JsonResponse({'error': 'start_year must be less than or equal to end_year'}, status=400)
        
#         # ============================================================
#         # SEASON DEFINITIONS
#         # ============================================================
        
#         season_definitions = {
#             'FULL': {
#                 'label': 'Full Year',
#                 'months': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
#                 'months_abbr': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
#                 'description': 'January - December',
#                 'year_offset': 0,
#                 'cross_year': False
#             },
#             'OND': {
#                 'label': 'OND (Early Summer)',
#                 'months': [10, 11, 12],
#                 'months_abbr': ['Oct', 'Nov', 'Dec'],
#                 'description': 'October, November, December - Early summer / onset of rainy season',
#                 'year_offset': 0,
#                 'cross_year': False
#             },
#             'NDJ': {
#                 'label': 'NDJ (Mid-Summer)',
#                 'months': [11, 12, 1],
#                 'months_abbr': ['Nov', 'Dec', 'Jan'],
#                 'description': 'November, December, January - Mid-summer transition',
#                 'year_offset': 1,
#                 'cross_year': True
#             },
#             'DJF': {
#                 'label': 'DJF (Peak Summer)',
#                 'months': [12, 1, 2],
#                 'months_abbr': ['Dec', 'Jan', 'Feb'],
#                 'description': 'December, January, February - Peak summer rainy season',
#                 'year_offset': 1,
#                 'cross_year': True
#             },
#             'JFM': {
#                 'label': 'JFM (Late Summer)',
#                 'months': [1, 2, 3],
#                 'months_abbr': ['Jan', 'Feb', 'Mar'],
#                 'description': 'January, February, March - Late summer / peak tropical cyclone season',
#                 'year_offset': 0,
#                 'cross_year': False
#             },
#             'FMA': {
#                 'label': 'FMA (End of Summer)',
#                 'months': [2, 3, 4],
#                 'months_abbr': ['Feb', 'Mar', 'Apr'],
#                 'description': 'February, March, April - End of summer / tail-end of rains',
#                 'year_offset': 0,
#                 'cross_year': False
#             },
#             'ONDJFM': {
#                 'label': 'ONDJFM (Rainy Season)',
#                 'months': [10, 11, 12, 1, 2, 3],
#                 'months_abbr': ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
#                 'description': 'October, November, December, January, February, March - Full rainy season (cross-year)',
#                 'year_offset': 1,
#                 'cross_year': True
#             },
#             'ON': {
#                 'label': 'ON (Early Onset)',
#                 'months': [10, 11],
#                 'months_abbr': ['Oct', 'Nov'],
#                 'description': 'October, November - Early onset of rains',
#                 'year_offset': 0,
#                 'cross_year': False
#             },
#             'ND': {
#                 'label': 'ND (Mid Onset)',
#                 'months': [11, 12],
#                 'months_abbr': ['Nov', 'Dec'],
#                 'description': 'November, December - Mid onset of rains',
#                 'year_offset': 0,
#                 'cross_year': False
#             },
#             'JF': {
#                 'label': 'JF (Peak Rains)',
#                 'months': [1, 2],
#                 'months_abbr': ['Jan', 'Feb'],
#                 'description': 'January, February - Peak rains',
#                 'year_offset': 0,
#                 'cross_year': False
#             },
#             'MA': {
#                 'label': 'MA (Late Rains)',
#                 'months': [3, 4],
#                 'months_abbr': ['Mar', 'Apr'],
#                 'description': 'March, April - Late rains / tail-end',
#                 'year_offset': 0,
#                 'cross_year': False
#             }
#         }
        
#         # Validate season
#         valid_seasons = list(season_definitions.keys())
#         if season_filter not in valid_seasons:
#             return JsonResponse({
#                 'error': f'Invalid season. Use: {", ".join(valid_seasons)}',
#                 'example': '/api/rainfall/annual/lta/?start_year=2000&end_year=2024&season=DJF'
#             }, status=400)
        
#         season_info = season_definitions[season_filter]
#         months = season_info['months']
#         cross_year = season_info['cross_year']
        
#         # Determine LTA period
#         if lta_start_year and lta_end_year:
#             lta_start = int(lta_start_year)
#             lta_end = int(lta_end_year)
#         else:
#             # Use the years from the requested date range
#             lta_start = start_year
#             lta_end = end_year
        
#         # ============================================================
#         # STEP 1: Build SQL for the requested period
#         # ============================================================
        
#         table_name = RainfallProvince._meta.db_table
        
#         # Build month condition
#         month_conditions = ' OR '.join([f"EXTRACT(MONTH FROM date) = {m}" for m in months])
        
#         # Build WHERE clause
#         where_clause = f"EXTRACT(YEAR FROM date) BETWEEN %s AND %s AND ({month_conditions})"
#         params = [start_year, end_year]
        
#         if province_filter:
#             where_clause += " AND province = %s"
#             params.append(province_filter)
        
#         # Build SQL with year adjustment for seasons that cross year boundary
#         if cross_year:
#             sql_data = f"""
#                 SELECT 
#                     CASE 
#                         WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
#                         ELSE EXTRACT(YEAR FROM date)::int
#                     END as season_year,
#                     province,
#                     SUM(rainfall_mm) as total_rainfall
#                 FROM {table_name}
#                 WHERE {where_clause}
#                 GROUP BY 
#                     CASE 
#                         WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
#                         ELSE EXTRACT(YEAR FROM date)::int
#                     END,
#                     province
#                 ORDER BY season_year, province
#             """
#         else:
#             sql_data = f"""
#                 SELECT 
#                     EXTRACT(YEAR FROM date)::int as year,
#                     province,
#                     SUM(rainfall_mm) as total_rainfall
#                 FROM {table_name}
#                 WHERE {where_clause}
#                 GROUP BY EXTRACT(YEAR FROM date), province
#                 ORDER BY year, province
#             """
        
#         with connection.cursor() as cursor:
#             cursor.execute(sql_data, params)
#             data_rows = cursor.fetchall()
        
#         if not data_rows:
#             return JsonResponse({
#                 'success': False,
#                 'message': f'No data found for the given years and season {season_filter}.',
#                 'data': []
#             }, status=404)
        
#         # Get all provinces
#         if province_filter:
#             provinces = [province_filter]
#         else:
#             provinces = sorted(set(row[1] for row in data_rows))
        
#         # ============================================================
#         # STEP 2: Calculate LTA for each season using the LTA period
#         # LTA = average of seasonal totals for each season within LTA period
#         # ============================================================
        
#         lta_where = f"EXTRACT(YEAR FROM date) BETWEEN {lta_start} AND {lta_end} AND ({month_conditions})"
#         if province_filter:
#             lta_where += f" AND province = '{province_filter}'"
        
#         # Build LTA SQL
#         if cross_year:
#             sql_lta = f"""
#                 SELECT 
#                     CASE 
#                         WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
#                         ELSE EXTRACT(YEAR FROM date)::int
#                     END as season_year,
#                     province,
#                     SUM(rainfall_mm) as seasonal_total
#                 FROM {table_name}
#                 WHERE {lta_where}
#                 GROUP BY 
#                     CASE 
#                         WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
#                         ELSE EXTRACT(YEAR FROM date)::int
#                     END,
#                     province
#             """
#         else:
#             sql_lta = f"""
#                 SELECT 
#                     EXTRACT(YEAR FROM date)::int as year,
#                     province,
#                     SUM(rainfall_mm) as seasonal_total
#                 FROM {table_name}
#                 WHERE {lta_where}
#                 GROUP BY EXTRACT(YEAR FROM date), province
#             """
        
#         with connection.cursor() as cursor:
#             cursor.execute(sql_lta)
#             lta_rows = cursor.fetchall()
        
#         # Group seasonal totals by province
#         lta_data = {}
#         lta_years_set = set()
        
#         for row in lta_rows:
#             if cross_year:
#                 year = row[0]
#                 province = row[1]
#                 seasonal_total = row[2]
#             else:
#                 year = row[0]
#                 province = row[1]
#                 seasonal_total = row[2]
            
#             key = f"{province}"
#             if key not in lta_data:
#                 lta_data[key] = []
#             lta_data[key].append(seasonal_total)
#             lta_years_set.add(year)
        
#         # Calculate LTA as average of seasonal totals
#         lta_lookup = {}
#         lta_count_lookup = {}
        
#         for key, values in lta_data.items():
#             lta_lookup[key] = round(sum(values) / len(values), 2)
#             lta_count_lookup[key] = len(values)
        
#         lta_num_years = len(lta_years_set)
#         lta_years = sorted(lta_years_set)
        
#         # ============================================================
#         # STEP 3: Combine data with LTA
#         # ============================================================
        
#         season_data = {}
#         for row in data_rows:
#             if cross_year:
#                 year = row[0]
#                 province = row[1]
#                 total = row[2]
#                 # Season year display: e.g., 2020 represents 2019/2020 season
#                 display_year = year
#                 season_label = f"{year-1}/{year}"
#                 season_display = f"{year-1} - {year}"
#             else:
#                 year = row[0]
#                 province = row[1]
#                 total = row[2]
#                 display_year = year
#                 season_label = str(year)
#                 season_display = str(year)
            
#             if display_year not in season_data:
#                 season_data[display_year] = {
#                     'year': display_year,
#                     'season_year': season_label,
#                     'season_display': season_display,
#                     'season': season_filter,
#                     'season_label': season_info['label'],
#                     'season_description': season_info['description'],
#                     'months': ', '.join(season_info['months_abbr']),
#                     'cross_year': cross_year,
#                 }
#                 for p in provinces:
#                     season_data[display_year][p] = 0.0
#                     season_data[display_year][f"{p}_lta"] = 0.0
#                     season_data[display_year][f"{p}_lta_count"] = 0
#                     season_data[display_year][f"{p}_anomaly"] = 0.0
#                     season_data[display_year][f"{p}_pct_avg"] = 0.0
            
#             lta_key = province
#             lta_value = lta_lookup.get(lta_key, 0.0)
#             lta_count = lta_count_lookup.get(lta_key, 0)
            
#             anomaly = total - lta_value
#             pct_avg = (total / lta_value * 100) if lta_value > 0 else 0
            
#             season_data[display_year][province] = round(total, 2)
#             season_data[display_year][f"{province}_lta"] = lta_value
#             season_data[display_year][f"{province}_lta_count"] = lta_count
#             season_data[display_year][f"{province}_anomaly"] = round(anomaly, 2)
#             season_data[display_year][f"{province}_pct_avg"] = round(pct_avg, 1)
        
#         data = sorted(season_data.values(), key=lambda x: x['year'])
        
#         # ============================================================
#         # STEP 4: Build response
#         # ============================================================
        
#         response_data = {
#             'success': True,
#             'aggregation': 'annual',
#             'aggregation_label': 'Annual/Seasonal with LTA',
#             'season': season_filter,
#             'season_label': season_info['label'],
#             'season_description': season_info['description'],
#             'season_months': season_info['months_abbr'],
#             'cross_year': cross_year,
#             'lta_period': {
#                 'start_year': lta_start,
#                 'end_year': lta_end,
#                 'num_years': lta_num_years,
#                 'years': lta_years,
#                 'description': f"{lta_num_years} years ({lta_start}-{lta_end})",
#                 'note': 'LTA is calculated from the available data in the LTA period'
#             },
#             'year_range': {
#                 'start': start_year,
#                 'end': end_year
#             },
#             'provinces': provinces,
#             'total_seasons': len(data),
#             'fields_explanation': {
#                 'rainfall': 'Total seasonal rainfall (mm)',
#                 'lta': 'Long-Term Average seasonal rainfall (mm)',
#                 'lta_count': 'Number of years used to calculate LTA',
#                 'anomaly': 'Rainfall - LTA (mm)',
#                 'pct_avg': 'Percentage of LTA (%)'
#             },
#             'data': data,
#             'metadata': {
#                 'source': 'database',
#                 'exported_at': datetime.datetime.now().isoformat()
#             }
#         }
        
#         if output_format == 'csv':
#             return export_annual_lta_csv(response_data)
        
#         return JsonResponse(response_data, status=200)
        
#     except ValueError as e:
#         return JsonResponse({'error': f'Invalid parameter: {str(e)}'}, status=400)
#     except Exception as e:
#         logger.error(f"Error in annual LTA aggregation: {str(e)}")
#         return JsonResponse({'error': str(e)}, status=500)


# def export_annual_lta_csv(response_data):
#     """Export annual LTA data as CSV."""
#     import csv
#     from django.http import HttpResponse
    
#     data = response_data['data']
#     provinces = response_data['provinces']
#     cross_year = response_data.get('cross_year', False)
    
#     if not data:
#         return JsonResponse({'error': 'No data to export'}, status=404)
    
#     csv_response = HttpResponse(content_type='text/csv')
#     filename = f"rainfall_annual_lta_{response_data['year_range']['start']}_to_{response_data['year_range']['end']}_{response_data['season']}.csv"
#     csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
#     writer = csv.writer(csv_response)
    
#     # Write header
#     if cross_year:
#         header = ['Year', 'Season Year', 'Season', 'Season Description', 'Months']
#     else:
#         header = ['Year', 'Season', 'Season Description', 'Months']
    
#     for province in provinces:
#         header.extend([
#             f'{province}_rainfall',
#             f'{province}_lta',
#             f'{province}_lta_count',
#             f'{province}_anomaly',
#             f'{province}_pct_avg'
#         ])
#     writer.writerow(header)
    
#     # Write data rows
#     for row in data:
#         if cross_year:
#             row_data = [
#                 row['year'],
#                 row['season_display'],
#                 row['season_label'],
#                 row['season_description'],
#                 row['months']
#             ]
#         else:
#             row_data = [
#                 row['year'],
#                 row['season_label'],
#                 row['season_description'],
#                 row['months']
#             ]
        
#         for province in provinces:
#             row_data.extend([
#                 row.get(province, 0.0),
#                 row.get(f'{province}_lta', 0.0),
#                 row.get(f'{province}_lta_count', 0),
#                 row.get(f'{province}_anomaly', 0.0),
#                 row.get(f'{province}_pct_avg', 0.0)
#             ])
#         writer.writerow(row_data)
    
#     return csv_response

# #
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#

#
#
#
#########################################################################################################
#################################  Get Rainfall for zim prov Lat/ lon  #########################################################
############################################################################################@@@@@@@@@@@@@

#from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Field


#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
##
#
#
#


    
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
# =======================================================================================================================
#                        NDVI DATA - Sentinel-2 (No Login Required)
# =======================================================================================================================

import ee
import datetime
import json
import logging
from django.http import JsonResponse
from django.db import IntegrityError
from django.db import connection

logger = logging.getLogger(__name__)

# Import your model
from .models import NDVIProvince

# Zimbabwe Province Representative Points (same as rainfall)
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


def get_ndvi_at_point(lat, lng, start_date, end_date, cloud_cover=30):
    """
    Get NDVI (Sentinel-2) at a specific point for a date range.
    Returns daily NDVI values.
    """
    try:
        point = ee.Geometry.Point([lng, lat])
        
        # Get Sentinel-2 collection with cloud filter
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(point)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
            .select('B4', 'B8')  # Red and NIR bands
        )
        
        # Calculate NDVI
        def add_ndvi(img):
            ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
            return img.addBands(ndvi)
        
        collection = collection.map(add_ndvi)
        
        def extract_ndvi(img):
            date = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd')
            ndvi = img.select('ndvi').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=100,
                maxPixels=1e9
            )
            cloud = img.get('CLOUDY_PIXEL_PERCENTAGE')
            return ee.Feature(None, {
                'date': date,
                'ndvi': ndvi.get('ndvi'),
                'cloud_cover': cloud
            })
        
        features = collection.map(extract_ndvi)
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
        
        return results
        
    except Exception as e:
        logger.error(f"Error in get_ndvi_at_point: {str(e)}")
        raise Exception(f"Failed to extract NDVI: {str(e)}")


# =====================================================
# API: GET NDVI FOR ALL PROVINCES (NO LOGIN)
# =====================================================

def api_ndvi_all_provinces(request):
    """
    Get NDVI data for all Zimbabwe provinces.
    No login required - open access.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - cloud_cover: Maximum cloud cover (default: 30)
    """
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        cloud_cover = int(request.GET.get('cloud_cover', 30))
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        results = {}
        
        for province, coords in ZIMBABWE_PROVINCES.items():
            try:
                ndvi_data = get_ndvi_at_point(
                    coords['lat'], 
                    coords['lng'], 
                    start_date, 
                    end_date,
                    cloud_cover
                )
                
                ndvi_values = [r['ndvi'] for r in ndvi_data if r['ndvi'] is not None]
                avg_ndvi = sum(ndvi_values) / len(ndvi_values) if ndvi_values else 0
                max_ndvi = max(ndvi_values) if ndvi_values else 0
                min_ndvi = min(ndvi_values) if ndvi_values else 0
                
                results[province] = {
                    'coords': coords,
                    'data': ndvi_data,
                    'stats': {
                        'avg': round(avg_ndvi, 4),
                        'max': round(max_ndvi, 4),
                        'min': round(min_ndvi, 4),
                        'data_points': len(ndvi_data),
                        'cloud_cover': cloud_cover
                    }
                }
            except Exception as e:
                logger.error(f"Error processing {province}: {str(e)}")
                results[province] = {
                    'coords': coords,
                    'error': str(e),
                    'data': [],
                    'stats': {
                        'avg': 0,
                        'max': 0,
                        'min': 0,
                        'data_points': 0,
                        'cloud_cover': cloud_cover
                    }
                }
        
        return JsonResponse({
            'success': True,
            'provinces': results,
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'cloud_cover': cloud_cover,
            'metadata': {
                'collection': 'COPERNICUS/S2_SR_HARMONIZED',
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in api_ndvi_all_provinces: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# SAVE NDVI DATA TO DATABASE
# =====================================================

def save_ndvi_to_db(province_name, date_str, ndvi_value, lat=None, lng=None, cloud_cover=None):
    """
    Save NDVI data for a province to the database.
    Returns (success, message)
    """
    try:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        
        obj, created = NDVIProvince.objects.update_or_create(
            province=province_name,
            date=date,
            defaults={
                'ndvi_value': round(ndvi_value, 4),
                'source': 'Sentinel-2',
                'lat': lat,
                'lng': lng,
                'cloud_cover': cloud_cover
            }
        )
        
        return True, f"{'Created' if created else 'Updated'} record for {province_name} on {date_str}"
        
    except Exception as e:
        return False, f"Error saving: {str(e)}"


# =====================================================
# API: SAVE NDVI DATA TO DATABASE
# =====================================================

def api_save_ndvi_data(request):
    """
    Save NDVI data from Earth Engine to database.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - cloud_cover: Maximum cloud cover (default: 30)
    - overwrite: (optional) 'true' to overwrite existing data
    """
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        cloud_cover = int(request.GET.get('cloud_cover', 30))
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
                ndvi_data = get_ndvi_at_point(
                    coords['lat'],
                    coords['lng'],
                    start_date,
                    end_date,
                    cloud_cover
                )
                
                province_results = []
                for item in ndvi_data:
                    date_str = item['date']
                    ndvi_value = item['ndvi']
                    item_cloud_cover = item.get('cloud_cover')
                    
                    if overwrite:
                        NDVIProvince.objects.filter(
                            province=province_name,
                            date=datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        ).delete()
                    
                    success, msg = save_ndvi_to_db(
                        province_name, 
                        date_str, 
                        ndvi_value,
                        coords['lat'],
                        coords['lng'],
                        item_cloud_cover
                    )
                    
                    if success:
                        saved_count += 1
                        province_results.append({
                            'date': date_str,
                            'ndvi': ndvi_value,
                            'cloud_cover': item_cloud_cover,
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
                'collection': 'COPERNICUS/S2_SR_HARMONIZED',
                'cloud_cover': cloud_cover,
                'processed_at': datetime.datetime.now().isoformat()
            }
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error saving NDVI data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# API: GET NDVI DATA FROM DATABASE (FAST)
# =====================================================

def api_ndvi_from_db(request):
    """
    Get NDVI data - ULTRA FAST with single SQL query using JSON aggregation.
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
        table_name = NDVIProvince._meta.db_table
        
        # ============================================================
        # SINGLE SQL QUERY - Everything in one go
        # ============================================================
        sql = """
            WITH filtered_data AS (
                SELECT 
                    date,
                    province,
                    ndvi_value,
                    lat,
                    lng,
                    cloud_cover
                FROM {table_name}
                WHERE date >= %s AND date <= %s
                AND (%s = '' OR province = %s)
            ),
            stats AS (
                SELECT 
                    province,
                    COUNT(*) as total_days,
                    COALESCE(AVG(ndvi_value), 0) as avg_ndvi,
                    COALESCE(MAX(ndvi_value), 0) as max_ndvi,
                    COALESCE(MIN(ndvi_value), 0) as min_ndvi,
                    COALESCE(AVG(cloud_cover), 0) as avg_cloud_cover
                FROM filtered_data
                GROUP BY province
            ),
            paginated AS (
                SELECT 
                    date,
                    province,
                    ndvi_value,
                    lat,
                    lng,
                    cloud_cover
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
                    'ndvi', ndvi_value,
                    'lat', lat,
                    'lng', lng,
                    'cloud_cover', cloud_cover
                )) FROM paginated) as data,
                (SELECT json_agg(json_build_object(
                    'province', province,
                    'total_days', total_days,
                    'avg_ndvi', avg_ndvi,
                    'max_ndvi', max_ndvi,
                    'min_ndvi', min_ndvi,
                    'avg_cloud_cover', avg_cloud_cover
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
                'message': 'No NDVI data found in database for this date range.',
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
                'ndvi': item['ndvi'],
                'cloud_cover': item['cloud_cover']
            })
        
        # Build stats dict
        stats_dict = {}
        for stat in stats_list:
            province = stat['province']
            stats_dict[province] = {
                'total_days': stat['total_days'],
                'avg_ndvi': round(stat['avg_ndvi'], 4),
                'max_ndvi': round(stat['max_ndvi'], 4),
                'min_ndvi': round(stat['min_ndvi'], 4),
                'avg_cloud_cover': round(stat['avg_cloud_cover'], 1)
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
                    'avg': stats.get('avg_ndvi', 0),
                    'max': stats.get('max_ndvi', 0),
                    'min': stats.get('min_ndvi', 0),
                    'total_days': total_days,
                    'avg_cloud_cover': stats.get('avg_cloud_cover', 0)
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
        logger.error(f"Error getting NDVI from DB: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# =====================================================
# EXPORT NDVI DATA AS CSV
# =====================================================

def api_ndvi_export_csv(request):
    """
    Export NDVI records as CSV (default) or JSON.
    
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
        output_format = request.GET.get('format', 'csv').lower()
        
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': 'start_date and end_date are required'}, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        queryset = NDVIProvince.objects.filter(
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
                'ndvi': record.ndvi_value,
                'cloud_cover': record.cloud_cover,
                'lat': record.lat,
                'lng': record.lng
            })
        
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
        
        # Return CSV
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        filename = f"ndvi_{start_date_str}_to_{end_date_str}"
        if province_filter:
            filename += f"_{province_filter}"
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Province', 'NDVI', 'Cloud Cover (%)', 'Lat', 'Lng'])
        
        for record in queryset:
            writer.writerow([
                record.date.strftime('%Y-%m-%d'),
                record.province,
                f"{record.ndvi_value:.4f}",
                f"{record.cloud_cover:.1f}" if record.cloud_cover else '',
                record.lat or '',
                record.lng or ''
            ])
        
        return response
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid date format: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error exporting NDVI data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
#
#
#
# =======================================================================================================================
# =======================================================================================================================
#
#
#
#
##
#
#
# 
#
#
################################################################################################################
############################## ==============================###########################=======================
#################################### DATA AGGREGATION VIEWS WITH lta ########################################
###############################################################################################################
###############################################################################################################
#export_monthly_csv_optimized

# =====================================================
# MONTHLY RAINFALL AGGREGATION WITH CORRECT LTA
# LTA is calculated from the data available in the date range
# =====================================================

import datetime
import calendar
import logging
from django.http import JsonResponse
from django.db import connection
from .models import RainfallProvince

logger = logging.getLogger(__name__)


def api_rainfall_monthly(request):
    """
    Get monthly aggregated rainfall data with Long-Term Average (LTA),
    Anomaly, and Percentage of Average.
    
    LTA is calculated from the data available in the requested date range.
    e.g., if start_date=2000-01-01 and end_date=2001-03-31,
    LTA_Jan = (Jan2000 + Jan2001) / 2
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - province: (optional) Filter by specific province
    - lta_start: (optional) Override start year for LTA
    - lta_end: (optional) Override end year for LTA
    - format: json (default) or csv
    """
    try:
        # Get query parameters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        province_filter = request.GET.get('province')
        lta_start_year = request.GET.get('lta_start')
        lta_end_year = request.GET.get('lta_end')
        output_format = request.GET.get('format', 'json').lower()
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'error': 'start_date and end_date are required',
                'example': '/api/rainfall/monthly/lta/?start_date=2000-01-01&end_date=2020-12-31'
            }, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Determine LTA period
        # If lta_start/lta_end are provided, use them
        # Otherwise, use the years from the requested date range
        if lta_start_year and lta_end_year:
            lta_start = int(lta_start_year)
            lta_end = int(lta_end_year)
        else:
            # Use the years from the requested date range
            lta_start = start_date.year
            lta_end = end_date.year
        
        # ============================================================
        # STEP 1: Get monthly totals for the requested period
        # ============================================================
        
        table_name = RainfallProvince._meta.db_table
        
        where_clause = "date >= %s AND date <= %s"
        params = [start_date, end_date]
        
        if province_filter:
            where_clause += " AND province = %s"
            params.append(province_filter)
        
        sql_monthly = f"""
            SELECT 
                EXTRACT(YEAR FROM date)::int as year,
                EXTRACT(MONTH FROM date)::int as month,
                province,
                SUM(rainfall_mm) as total_rainfall
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date), province
            ORDER BY year, month, province
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql_monthly, params)
            monthly_rows = cursor.fetchall()
        
        if not monthly_rows:
            return JsonResponse({
                'success': False,
                'message': 'No data found for the given date range.',
                'data': []
            }, status=404)
        
        # Get all provinces
        if province_filter:
            provinces = [province_filter]
        else:
            provinces = sorted(set(row[2] for row in monthly_rows))
        
        # ============================================================
        # STEP 2: Calculate LTA for each month using the LTA period
        # LTA = average of monthly totals for each month within LTA period
        # ============================================================
        
        lta_where = f"EXTRACT(YEAR FROM date) BETWEEN {lta_start} AND {lta_end}"
        if province_filter:
            lta_where += f" AND province = '{province_filter}'"
        
        # Get monthly totals for LTA period
        sql_monthly_lta = f"""
            SELECT 
                EXTRACT(YEAR FROM date)::int as year,
                EXTRACT(MONTH FROM date)::int as month,
                province,
                SUM(rainfall_mm) as monthly_total
            FROM {table_name}
            WHERE {lta_where}
            GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date), province
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql_monthly_lta)
            monthly_lta_rows = cursor.fetchall()
        
        # Group monthly totals by month and province
        lta_data = {}
        lta_years_set = set()
        
        for row in monthly_lta_rows:
            year = row[0]
            month = row[1]
            province = row[2]
            monthly_total = row[3]
            
            key = f"{month}-{province}"
            if key not in lta_data:
                lta_data[key] = []
            lta_data[key].append(monthly_total)
            lta_years_set.add(year)
        
        # Calculate LTA as average of monthly totals
        lta_lookup = {}
        lta_count_lookup = {}
        
        for key, values in lta_data.items():
            lta_lookup[key] = round(sum(values) / len(values), 2)
            lta_count_lookup[key] = len(values)
        
        lta_num_years = len(lta_years_set)
        lta_years = sorted(lta_years_set)
        
        # ============================================================
        # STEP 3: Combine data with LTA
        # ============================================================
        
        month_data = {}
        for row in monthly_rows:
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
                for p in provinces:
                    month_data[key][p] = 0.0
                    month_data[key][f"{p}_lta"] = 0.0
                    month_data[key][f"{p}_lta_count"] = 0
                    month_data[key][f"{p}_anomaly"] = 0.0
                    month_data[key][f"{p}_pct_avg"] = 0.0
            
            lta_key = f"{month}-{province}"
            lta_value = lta_lookup.get(lta_key, 0.0)
            lta_count = lta_count_lookup.get(lta_key, 0)
            
            anomaly = total - lta_value
            pct_avg = (total / lta_value * 100) if lta_value > 0 else 0
            
            month_data[key][province] = round(total, 2)
            month_data[key][f"{province}_lta"] = lta_value
            month_data[key][f"{province}_lta_count"] = lta_count
            month_data[key][f"{province}_anomaly"] = round(anomaly, 2)
            month_data[key][f"{province}_pct_avg"] = round(pct_avg, 1)
        
        data = sorted(month_data.values(), key=lambda x: x['sort_key'])
        
        # ============================================================
        # STEP 4: Build response
        # ============================================================
        
        response_data = {
            'success': True,
            'aggregation': 'monthly',
            'aggregation_label': 'Monthly with LTA',
            'lta_period': {
                'start_year': lta_start,
                'end_year': lta_end,
                'num_years': lta_num_years,
                'years': lta_years,
                'description': f"{lta_num_years} years ({lta_start}-{lta_end})",
                'note': 'LTA is calculated from the available data in the LTA period'
            },
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'provinces': provinces,
            'total_months': len(data),
            'fields_explanation': {
                'rainfall': 'Total monthly rainfall (mm)',
                'lta': 'Long-Term Average monthly rainfall (mm)',
                'lta_count': 'Number of years used to calculate LTA',
                'anomaly': 'Rainfall - LTA (mm)',
                'pct_avg': 'Percentage of LTA (%)'
            },
            'data': data,
            'metadata': {
                'source': 'database',
                'exported_at': datetime.datetime.now().isoformat()
            }
        }
        
        if output_format == 'csv':
            return export_monthly_lta_csv(response_data)
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error in monthly LTA aggregation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def export_monthly_csv_optimized(response_data):
    """Export monthly LTA data as CSV."""
    import csv
    from django.http import HttpResponse
    
    data = response_data['data']
    provinces = response_data['provinces']
    
    if not data:
        return JsonResponse({'error': 'No data to export'}, status=404)
    
    csv_response = HttpResponse(content_type='text/csv')
    filename = f"rainfall_monthly_lta_{response_data['date_range']['start']}_to_{response_data['date_range']['end']}.csv"
    csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(csv_response)
    
    header = ['Year', 'Month', 'Period']
    for province in provinces:
        header.extend([
            f'{province}_rainfall',
            f'{province}_lta',
            f'{province}_lta_count',
            f'{province}_anomaly',
            f'{province}_pct_avg'
        ])
    writer.writerow(header)
    
    for row in data:
        row_data = [row['year'], row['month'], row['period']]
        for province in provinces:
            row_data.extend([
                row.get(province, 0.0),
                row.get(f'{province}_lta', 0.0),
                row.get(f'{province}_lta_count', 0),
                row.get(f'{province}_anomaly', 0.0),
                row.get(f'{province}_pct_avg', 0.0)
            ])
        writer.writerow(row_data)
    
    return csv_response

######################################################################################################
#
##
###############################################################################################
                # =====================================================
                # DEKADAL RAINFALL AGGREGATION VIEW (OPTIMIZED)
                # =====================================================
###################################################################################################
# =====================================================
# DEKADAL RAINFALL AGGREGATION WITH LTA
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
    Get dekadal aggregated rainfall data with Long-Term Average (LTA),
    Anomaly, and Percentage of Average.
    
    Dekad 1 = days 01-10
    Dekad 2 = days 11-20
    Dekad 3 = days 21-end of month
    
    LTA is calculated from the data available in the requested date range.
    e.g., if start_date=2000-01-01 and end_date=2001-03-31,
    LTA_Jan_D1 = (Jan_D1_2000 + Jan_D1_2001) / 2
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD) (required)
    - end_date: End date (YYYY-MM-DD) (required)
    - province: (optional) Filter by specific province
    - lta_start: (optional) Override start year for LTA
    - lta_end: (optional) Override end year for LTA
    - format: json (default) or csv
    
    Example:
    /api/rainfall/dekadal/lta/?start_date=2000-01-01&end_date=2024-12-31&province=Harare
    """
    try:
        # Get query parameters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        province_filter = request.GET.get('province')
        lta_start_year = request.GET.get('lta_start')
        lta_end_year = request.GET.get('lta_end')
        output_format = request.GET.get('format', 'json').lower()
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'error': 'start_date and end_date are required',
                'example': '/api/rainfall/dekadal/lta/?start_date=2000-01-01&end_date=2024-12-31'
            }, status=400)
        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Determine LTA period
        if lta_start_year and lta_end_year:
            lta_start = int(lta_start_year)
            lta_end = int(lta_end_year)
        else:
            # Use the years from the requested date range
            lta_start = start_date.year
            lta_end = end_date.year
        
        # ============================================================
        # STEP 1: Get dekadal totals for the requested period
        # ============================================================
        
        table_name = RainfallProvince._meta.db_table
        
        where_clause = "date >= %s AND date <= %s"
        params = [start_date, end_date]
        
        if province_filter:
            where_clause += " AND province = %s"
            params.append(province_filter)
        
        sql_dekadal = f"""
            SELECT 
                EXTRACT(YEAR FROM date)::int as year,
                EXTRACT(MONTH FROM date)::int as month,
                CASE 
                    WHEN EXTRACT(DAY FROM date) <= 10 THEN 1
                    WHEN EXTRACT(DAY FROM date) <= 20 THEN 2
                    ELSE 3
                END as dekad,
                province,
                SUM(rainfall_mm) as total_rainfall
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
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql_dekadal, params)
            dekadal_rows = cursor.fetchall()
        
        if not dekadal_rows:
            return JsonResponse({
                'success': False,
                'message': 'No data found for the given date range.',
                'data': []
            }, status=404)
        
        # Get all provinces
        if province_filter:
            provinces = [province_filter]
        else:
            provinces = sorted(set(row[3] for row in dekadal_rows))
        
        # ============================================================
        # STEP 2: Calculate LTA for each month-dekad using the LTA period
        # LTA = average of dekadal totals for each month-dekad within LTA period
        # ============================================================
        
        lta_where = f"EXTRACT(YEAR FROM date) BETWEEN {lta_start} AND {lta_end}"
        if province_filter:
            lta_where += f" AND province = '{province_filter}'"
        
        # Get dekadal totals for LTA period
        sql_dekadal_lta = f"""
            SELECT 
                EXTRACT(YEAR FROM date)::int as year,
                EXTRACT(MONTH FROM date)::int as month,
                CASE 
                    WHEN EXTRACT(DAY FROM date) <= 10 THEN 1
                    WHEN EXTRACT(DAY FROM date) <= 20 THEN 2
                    ELSE 3
                END as dekad,
                province,
                SUM(rainfall_mm) as dekadal_total
            FROM {table_name}
            WHERE {lta_where}
            GROUP BY 
                EXTRACT(YEAR FROM date),
                EXTRACT(MONTH FROM date),
                CASE 
                    WHEN EXTRACT(DAY FROM date) <= 10 THEN 1
                    WHEN EXTRACT(DAY FROM date) <= 20 THEN 2
                    ELSE 3
                END,
                province
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql_dekadal_lta)
            dekadal_lta_rows = cursor.fetchall()
        
        # Group dekadal totals by month-dekad and province
        lta_data = {}
        lta_years_set = set()
        
        for row in dekadal_lta_rows:
            year = row[0]
            month = row[1]
            dekad = row[2]
            province = row[3]
            dekadal_total = row[4]
            
            key = f"{month}-{dekad}-{province}"
            if key not in lta_data:
                lta_data[key] = []
            lta_data[key].append(dekadal_total)
            lta_years_set.add(year)
        
        # Calculate LTA as average of dekadal totals
        lta_lookup = {}
        lta_count_lookup = {}
        
        for key, values in lta_data.items():
            lta_lookup[key] = round(sum(values) / len(values), 2)
            lta_count_lookup[key] = len(values)
        
        lta_num_years = len(lta_years_set)
        lta_years = sorted(lta_years_set)
        
        # ============================================================
        # STEP 3: Combine data with LTA
        # ============================================================
        
        dekad_data = {}
        for row in dekadal_rows:
            year = row[0]
            month = row[1]
            dekad = row[2]
            province = row[3]
            total = row[4]
            
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
            
            key = f"{year}-{month:02d}-D{dekad}"
            
            if key not in dekad_data:
                month_name = calendar.month_name[month][:3]
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
                for p in provinces:
                    dekad_data[key][p] = 0.0
                    dekad_data[key][f"{p}_lta"] = 0.0
                    dekad_data[key][f"{p}_lta_count"] = 0
                    dekad_data[key][f"{p}_anomaly"] = 0.0
                    dekad_data[key][f"{p}_pct_avg"] = 0.0
            
            lta_key = f"{month}-{dekad}-{province}"
            lta_value = lta_lookup.get(lta_key, 0.0)
            lta_count = lta_count_lookup.get(lta_key, 0)
            
            anomaly = total - lta_value
            pct_avg = (total / lta_value * 100) if lta_value > 0 else 0
            
            dekad_data[key][province] = round(total, 2)
            dekad_data[key][f"{province}_lta"] = lta_value
            dekad_data[key][f"{province}_lta_count"] = lta_count
            dekad_data[key][f"{province}_anomaly"] = round(anomaly, 2)
            dekad_data[key][f"{province}_pct_avg"] = round(pct_avg, 1)
        
        data = sorted(dekad_data.values(), key=lambda x: x['sort_key'])
        
        # ============================================================
        # STEP 4: Build response
        # ============================================================
        
        response_data = {
            'success': True,
            'aggregation': 'dekadal',
            'aggregation_label': 'Dekadal with LTA',
            'dekad_definitions': {
                'Dekad 1': 'Days 01-10',
                'Dekad 2': 'Days 11-20',
                'Dekad 3': 'Days 21-end of month'
            },
            'lta_period': {
                'start_year': lta_start,
                'end_year': lta_end,
                'num_years': lta_num_years,
                'years': lta_years,
                'description': f"{lta_num_years} years ({lta_start}-{lta_end})",
                'note': 'LTA is calculated from the available data in the LTA period'
            },
            'date_range': {
                'start': start_date_str,
                'end': end_date_str
            },
            'provinces': provinces,
            'total_dekads': len(data),
            'fields_explanation': {
                'rainfall': 'Total dekadal rainfall (mm)',
                'lta': 'Long-Term Average dekadal rainfall (mm)',
                'lta_count': 'Number of years used to calculate LTA',
                'anomaly': 'Rainfall - LTA (mm)',
                'pct_avg': 'Percentage of LTA (%)'
            },
            'data': data,
            'metadata': {
                'source': 'database',
                'exported_at': datetime.datetime.now().isoformat()
            }
        }
        
        if output_format == 'csv':
            return export_dekadal_lta_csv(response_data)
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error in dekadal LTA aggregation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def export_dekadal_csv(response_data):
    """Export dekadal LTA data as CSV."""
    import csv
    from django.http import HttpResponse
    
    data = response_data['data']
    provinces = response_data['provinces']
    
    if not data:
        return JsonResponse({'error': 'No data to export'}, status=404)
    
    csv_response = HttpResponse(content_type='text/csv')
    filename = f"rainfall_dekadal_lta_{response_data['date_range']['start']}_to_{response_data['date_range']['end']}.csv"
    csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(csv_response)
    
    # Write header
    header = ['Year', 'Month', 'Dekad', 'Start Date', 'End Date', 'Period']
    for province in provinces:
        header.extend([
            f'{province}_rainfall',
            f'{province}_lta',
            f'{province}_lta_count',
            f'{province}_anomaly',
            f'{province}_pct_avg'
        ])
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
            row_data.extend([
                row.get(province, 0.0),
                row.get(f'{province}_lta', 0.0),
                row.get(f'{province}_lta_count', 0),
                row.get(f'{province}_anomaly', 0.0),
                row.get(f'{province}_pct_avg', 0.0)
            ])
        writer.writerow(row_data)
    
    return csv_response
#################################################################################################################
##
#########################################################################################################
#
################ ANNUAL & SEASONAL RAINFALL AGGREGATION VIEW  ########################
#
#########################################################################################################

#
#
#  
############################################  OLD VIEWS  ###################################################
# ############################# ==============================###########################=======================
# ########################### MONTHLY RAINFALL AGGREGATION VIEW ###########################
# ########################## ==============================###########################=======================
# =====================================================
#  MONTHLY RAINFALL AGGREGATION VIEW
# =====================================================

# import datetime
# import calendar
# import logging
# from django.http import JsonResponse
# from django.db.models import Sum
# from django.db import connection
# from .models import RainfallProvince

# logger = logging.getLogger(__name__)


# def api_rainfall_monthly(request):
#     """
#     Get monthly aggregated rainfall data - OPTIMIZED version.
#     Uses a single SQL query with GROUP BY.
    
#     Query parameters:
#     - start_date: Start date (YYYY-MM-DD) (required)
#     - end_date: End date (YYYY-MM-DD) (required)
#     - province: (optional) Filter by specific province
#     - format: json (default) or csv
#     """
#     try:
#         # Get query parameters
#         start_date_str = request.GET.get('start_date')
#         end_date_str = request.GET.get('end_date')
#         province_filter = request.GET.get('province')
#         output_format = request.GET.get('format', 'json').lower()
        
#         # Validate required parameters
#         if not start_date_str or not end_date_str:
#             return JsonResponse({
#                 'error': 'start_date and end_date are required',
#                 'example': '/api/rainfall/monthly/?start_date=2024-01-01&end_date=2024-12-31'
#             }, status=400)
        
#         # Parse dates
#         start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
#         end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
#         # ============================================================
#         # OPTIMIZED: Single SQL query with GROUP BY
#         # ============================================================
        
#         table_name = RainfallProvince._meta.db_table
        
#         # Build the WHERE clause
#         where_clause = "date >= %s AND date <= %s"
#         params = [start_date, end_date]
        
#         if province_filter:
#             where_clause += " AND province = %s"
#             params.append(province_filter)
        
#         # Single query with GROUP BY year, month, province
#         sql = """
#             SELECT 
#                 EXTRACT(YEAR FROM date)::int as year,
#                 EXTRACT(MONTH FROM date)::int as month,
#                 province,
#                 SUM(rainfall_mm) as total_rainfall
#             FROM {table_name}
#             WHERE {where_clause}
#             GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date), province
#             ORDER BY year, month, province
#         """.format(table_name=table_name, where_clause=where_clause)
        
#         with connection.cursor() as cursor:
#             cursor.execute(sql, params)
#             rows = cursor.fetchall()
        
#         # Check if data exists
#         if not rows:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'No data found in database for the given date range.',
#                 'data': []
#             }, status=404)
        
#         # ============================================================
#         # Process results into the required format
#         # ============================================================
        
#         # Get all provinces from the results
#         if province_filter:
#             provinces = [province_filter]
#         else:
#             provinces = sorted(set(row[2] for row in rows))
        
#         # Group data by year-month
#         month_data = {}
#         for row in rows:
#             year = row[0]
#             month = row[1]
#             province = row[2]
#             total = row[3]
            
#             key = f"{year}-{month:02d}"
            
#             if key not in month_data:
#                 month_data[key] = {
#                     'year': year,
#                     'month': month,
#                     'month_name': calendar.month_name[month],
#                     'month_abbr': calendar.month_abbr[month],
#                     'date': f"{year}-{month:02d}-01",
#                     'period': f"{calendar.month_name[month]} {year}",
#                     'sort_key': f"{year}-{month:02d}",
#                 }
#                 # Initialize all provinces with 0
#                 for p in provinces:
#                     month_data[key][p] = 0.0
            
#             month_data[key][province] = round(total, 2)
        
#         # Convert to list and sort by date
#         data = sorted(month_data.values(), key=lambda x: x['sort_key'])
        
#         # ============================================================
#         # Build response
#         # ============================================================
        
#         response_data = {
#             'success': True,
#             'aggregation': 'monthly',
#             'aggregation_label': 'Monthly',
#             'date_range': {
#                 'start': start_date_str,
#                 'end': end_date_str
#             },
#             'provinces': provinces,
#             'total_months': len(data),
#             'data': data,
#             'metadata': {
#                 'source': 'database',
#                 'exported_at': datetime.datetime.now().isoformat()
#             }
#         }
        
#         # ============================================================
#         # Return as CSV if requested
#         # ============================================================
        
#         if output_format == 'csv':
#             return export_monthly_csv_optimized(response_data)
        
#         return JsonResponse(response_data, status=200)
        
#     except Exception as e:
#         logger.error(f"Error in monthly rainfall aggregation: {str(e)}")
#         return JsonResponse({'error': str(e)}, status=500)


# def export_monthly_csv_optimized(response_data):
#     """Export monthly aggregation data as CSV."""
#     import csv
#     from django.http import HttpResponse
    
#     data = response_data['data']
#     provinces = response_data['provinces']
    
#     if not data:
#         return JsonResponse({'error': 'No data to export'}, status=404)
    
#     csv_response = HttpResponse(content_type='text/csv')
#     filename = f"rainfall_monthly_{response_data['date_range']['start']}_to_{response_data['date_range']['end']}.csv"
#     csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
#     writer = csv.writer(csv_response)
    
#     header = ['Year', 'Month', 'Month Name', 'Period'] + provinces
#     writer.writerow(header)
    
#     for row in data:
#         row_data = [
#             row['year'],
#             row['month'],
#             row['month_name'],
#             row['period']
#         ]
#         for province in provinces:
#             row_data.append(row.get(province, 0.0))
#         writer.writerow(row_data)
    
#     return csv_response
# #
###############################################################################################
                # =====================================================
                # DEKADAL RAINFALL AGGREGATION VIEW (OPTIMIZED)
                # =====================================================
###################################################################################################

# import datetime
# import calendar
# import logging
# from django.http import JsonResponse
# from django.db import connection
# from .models import RainfallProvince

# logger = logging.getLogger(__name__)


# def api_rainfall_dekadal(request):
#     """
#     Get dekadal aggregated rainfall data (10-day periods).
#     Dekad 1 = days 01-10
#     Dekad 2 = days 11-20
#     Dekad 3 = days 21-end of month
    
#     Query parameters:
#     - start_date: Start date (YYYY-MM-DD) (required)
#     - end_date: End date (YYYY-MM-DD) (required)
#     - province: (optional) Filter by specific province
#     - format: json (default) or csv
    
#     Example:
#     /api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31
#     /api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31&province=Harare
#     /api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31&format=csv
#     """
#     try:
#         # Get query parameters
#         start_date_str = request.GET.get('start_date')
#         end_date_str = request.GET.get('end_date')
#         province_filter = request.GET.get('province')
#         output_format = request.GET.get('format', 'json').lower()
        
#         # Validate required parameters
#         if not start_date_str or not end_date_str:
#             return JsonResponse({
#                 'error': 'start_date and end_date are required',
#                 'example': '/api/rainfall/dekadal/?start_date=2024-01-01&end_date=2024-12-31'
#             }, status=400)
        
#         # Parse dates
#         start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
#         end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

#     # ============================================================
#         # OPTIMIZED: Single SQL query with GROUP BY for dekads
#         # ============================================================
       
#         table_name = RainfallProvince._meta.db_table
        
#         # Build the WHERE clause
#         where_clause = "date >= %s AND date <= %s"
#         params = [start_date, end_date]
        
#         if province_filter:
#             where_clause += " AND province = %s"
#             params.append(province_filter)
        
#         # Single query with GROUP BY year, month, dekad, province
#         sql = """
#             SELECT 
#                 EXTRACT(YEAR FROM date)::int as year,
#                 EXTRACT(MONTH FROM date)::int as month,
#                 CASE 
#                     WHEN EXTRACT(DAY FROM date) <= 10 THEN 1
#                     WHEN EXTRACT(DAY FROM date) <= 20 THEN 2
#                     ELSE 3
#                 END as dekad,
#                 province,
#                 SUM(rainfall_mm) as total_rainfall,
#                 COUNT(*) as record_count
#             FROM {table_name}
#             WHERE {where_clause}
#             GROUP BY 
#                 EXTRACT(YEAR FROM date),
#                 EXTRACT(MONTH FROM date),
#                 CASE 
#                     WHEN EXTRACT(DAY FROM date) <= 10 THEN 1
#                     WHEN EXTRACT(DAY FROM date) <= 20 THEN 2
#                     ELSE 3
#                 END,
#                 province
#             ORDER BY year, month, dekad, province
#         """.format(table_name=table_name, where_clause=where_clause)
        
#         with connection.cursor() as cursor:
#             cursor.execute(sql, params)
#             rows = cursor.fetchall()
        
#         # Check if data exists
#         if not rows:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'No data found in database for the given date range.',
#                 'data': []
#             }, status=404)
        
#         # ============================================================
#         # Process results into the required format
#         # ============================================================
        
#         # Get all provinces from the results
#         if province_filter:
#             provinces = [province_filter]
#         else:
#             provinces = sorted(set(row[3] for row in rows))
        
#         # Group data by year-month-dekad
#         dekad_data = {}
#         for row in rows:
#             year = row[0]
#             month = row[1]
#             dekad = row[2]
#             province = row[3]
#             total = row[4]
#             count = row[5]
            
#             # Calculate start and end dates for the dekad
#             if dekad == 1:
#                 start_day = 1
#                 end_day = 10
#             elif dekad == 2:
#                 start_day = 11
#                 end_day = 20
#             else:
#                 start_day = 21
#                 end_day = calendar.monthrange(year, month)[1]
            
#             start_date_str_key = f"{year}-{month:02d}-{start_day:02d}"
#             end_date_str_key = f"{year}-{month:02d}-{end_day:02d}"
            
#             # Create key for grouping
#             key = f"{year}-{month:02d}-D{dekad}"
            
#             if key not in dekad_data:
#                 month_name = calendar.month_name[month][:3]  # Jan, Feb, etc.
#                 dekad_data[key] = {
#                     'year': year,
#                     'month': month,
#                     'month_name': calendar.month_name[month],
#                     'month_abbr': calendar.month_abbr[month],
#                     'dekad': dekad,
#                     'dekad_label': f"D{dekad}",
#                     'date': f"{year}-{month:02d}-{start_day:02d}",
#                     'start_date': f"{year}-{month:02d}-{start_day:02d}",
#                     'end_date': f"{year}-{month:02d}-{end_day:02d}",
#                     'period': f"{month_name} D{dekad}",
#                     'sort_key': f"{year}-{month:02d}-{dekad:02d}",
#                 }
#                 # Initialize all provinces with 0
#                 for p in provinces:
#                     dekad_data[key][p] = 0.0
#                     dekad_data[key][f"{p}_count"] = 0
            
#             dekad_data[key][province] = round(total, 2)
#             dekad_data[key][f"{province}_count"] = count
        
#         # Convert to list and sort by date
#         data = sorted(dekad_data.values(), key=lambda x: x['sort_key'])
        
#         # ============================================================
#         # Build response
#         # ============================================================
        
#         response_data = {
#             'success': True,
#             'aggregation': 'dekadal',
#             'aggregation_label': 'Dekadal (10-day periods)',
#             'dekad_definitions': {
#                 'Dekad 1': 'Days 01-10',
#                 'Dekad 2': 'Days 11-20',
#                 'Dekad 3': 'Days 21-end of month'
#             },
#             'date_range': {
#                 'start': start_date_str,
#                 'end': end_date_str
#             },
#             'provinces': provinces,
#             'total_dekads': len(data),
#             'data': data,
#             'metadata': {
#                 'source': 'database',
#                 'exported_at': datetime.datetime.now().isoformat()
#             }
#         }
        
#         # ============================================================
#         # Return as CSV if requested
#         # ============================================================
        
#         if output_format == 'csv':
#             return export_dekadal_csv(response_data)
        
#         return JsonResponse(response_data, status=200)
        
#     except Exception as e:
#         logger.error(f"Error in dekadal rainfall aggregation: {str(e)}")
#         return JsonResponse({'error': str(e)}, status=500)


# def export_dekadal_csv(response_data):
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
#########################################################################################
#
#
#########################################################################################################
#
################ ANNUAL & SEASONAL RAINFALL AGGREGATION VIEW  ########################
#
#########################################################################################################
# =====================================================
# ANNUAL/SEASONAL RAINFALL AGGREGATION WITH LTA
# =====================================================

import datetime
import calendar
import logging
from django.http import JsonResponse
from django.db import connection
from .models import RainfallProvince

logger = logging.getLogger(__name__)


def api_rainfall_annual(request):
    """
    Get annual and seasonal aggregated rainfall data with Long-Term Average (LTA),
    Anomaly, and Percentage of Average.
    
    Seasons:
    - FULL: January - December (Full Year)
    - OND: October, November, December (Early summer / onset)
    - NDJ: November, December, January (Mid-summer transition)
    - DJF: December, January, February (Peak summer rainy season)
    - JFM: January, February, March (Late summer / tropical cyclone)
    - FMA: February, March, April (End of summer / tail-end)
    - ONDJFM: October, November, December, January, February, March (Cross-year rainy season)
    - ON: October, November (Early onset)
    - ND: November, December (Mid onset)
    - JF: January, February (Peak rains)
    - MA: March, April (Late rains / tail-end)
    
    LTA is calculated from the data available in the requested date range.
    e.g., if start_year=2000 and end_year=2024,
    LTA_DJF = average of all DJF seasons from 2000-2024
    
    Query parameters:
    - start_year: Start year (YYYY) (required)
    - end_year: End year (YYYY) (required)
    - province: (optional) Filter by specific province
    - season: (optional) full, OND, NDJ, DJF, JFM, FMA, ONDJFM, ON, ND, JF, MA (default: full)
    - lta_start: (optional) Override start year for LTA
    - lta_end: (optional) Override end year for LTA
    - format: json (default) or csv
    
    Example:
    /api/rainfall/annual/lta/?start_year=2000&end_year=2024&province=Harare
    /api/rainfall/annual/lta/?start_year=2000&end_year=2024&season=DJF&province=Harare
    """
    try:
        # Get query parameters
        start_year = int(request.GET.get('start_year'))
        end_year = int(request.GET.get('end_year'))
        province_filter = request.GET.get('province')
        season_filter = request.GET.get('season', 'FULL').upper()
        lta_start_year = request.GET.get('lta_start')
        lta_end_year = request.GET.get('lta_end')
        output_format = request.GET.get('format', 'json').lower()
        
        # Validate parameters
        if start_year > end_year:
            return JsonResponse({'error': 'start_year must be less than or equal to end_year'}, status=400)
        
        # ============================================================
        # SEASON DEFINITIONS
        # ============================================================
        
        season_definitions = {
            'FULL': {
                'label': 'Full Year',
                'months': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                'months_abbr': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                'description': 'January - December',
                'year_offset': 0,
                'cross_year': False
            },
            'OND': {
                'label': 'OND (Early Summer)',
                'months': [10, 11, 12],
                'months_abbr': ['Oct', 'Nov', 'Dec'],
                'description': 'October, November, December - Early summer / onset of rainy season',
                'year_offset': 0,
                'cross_year': False
            },
            'NDJ': {
                'label': 'NDJ (Mid-Summer)',
                'months': [11, 12, 1],
                'months_abbr': ['Nov', 'Dec', 'Jan'],
                'description': 'November, December, January - Mid-summer transition',
                'year_offset': 1,
                'cross_year': True
            },
            'DJF': {
                'label': 'DJF (Peak Summer)',
                'months': [12, 1, 2],
                'months_abbr': ['Dec', 'Jan', 'Feb'],
                'description': 'December, January, February - Peak summer rainy season',
                'year_offset': 1,
                'cross_year': True
            },
            'JFM': {
                'label': 'JFM (Late Summer)',
                'months': [1, 2, 3],
                'months_abbr': ['Jan', 'Feb', 'Mar'],
                'description': 'January, February, March - Late summer / peak tropical cyclone season',
                'year_offset': 0,
                'cross_year': False
            },
            'FMA': {
                'label': 'FMA (End of Summer)',
                'months': [2, 3, 4],
                'months_abbr': ['Feb', 'Mar', 'Apr'],
                'description': 'February, March, April - End of summer / tail-end of rains',
                'year_offset': 0,
                'cross_year': False
            },
            'ONDJFM': {
                'label': 'ONDJFM (Rainy Season)',
                'months': [10, 11, 12, 1, 2, 3],
                'months_abbr': ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
                'description': 'October, November, December, January, February, March - Full rainy season (cross-year)',
                'year_offset': 1,
                'cross_year': True
            },
            'ON': {
                'label': 'ON (Early Onset)',
                'months': [10, 11],
                'months_abbr': ['Oct', 'Nov'],
                'description': 'October, November - Early onset of rains',
                'year_offset': 0,
                'cross_year': False
            },
            'ND': {
                'label': 'ND (Mid Onset)',
                'months': [11, 12],
                'months_abbr': ['Nov', 'Dec'],
                'description': 'November, December - Mid onset of rains',
                'year_offset': 0,
                'cross_year': False
            },
            'JF': {
                'label': 'JF (Peak Rains)',
                'months': [1, 2],
                'months_abbr': ['Jan', 'Feb'],
                'description': 'January, February - Peak rains',
                'year_offset': 0,
                'cross_year': False
            },
            'MA': {
                'label': 'MA (Late Rains)',
                'months': [3, 4],
                'months_abbr': ['Mar', 'Apr'],
                'description': 'March, April - Late rains / tail-end',
                'year_offset': 0,
                'cross_year': False
            }
        }
        
        # Validate season
        valid_seasons = list(season_definitions.keys())
        if season_filter not in valid_seasons:
            return JsonResponse({
                'error': f'Invalid season. Use: {", ".join(valid_seasons)}',
                'example': '/api/rainfall/annual/lta/?start_year=2000&end_year=2024&season=DJF'
            }, status=400)
        
        season_info = season_definitions[season_filter]
        months = season_info['months']
        cross_year = season_info['cross_year']
        
        # Determine LTA period
        if lta_start_year and lta_end_year:
            lta_start = int(lta_start_year)
            lta_end = int(lta_end_year)
        else:
            # Use the years from the requested date range
            lta_start = start_year
            lta_end = end_year
        
        # ============================================================
        # STEP 1: Build SQL for the requested period
        # ============================================================
        
        table_name = RainfallProvince._meta.db_table
        
        # Build month condition
        month_conditions = ' OR '.join([f"EXTRACT(MONTH FROM date) = {m}" for m in months])
        
        # Build WHERE clause
        where_clause = f"EXTRACT(YEAR FROM date) BETWEEN %s AND %s AND ({month_conditions})"
        params = [start_year, end_year]
        
        if province_filter:
            where_clause += " AND province = %s"
            params.append(province_filter)
        
        # Build SQL with year adjustment for seasons that cross year boundary
        if cross_year:
            sql_data = f"""
                SELECT 
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
                        ELSE EXTRACT(YEAR FROM date)::int
                    END as season_year,
                    province,
                    SUM(rainfall_mm) as total_rainfall
                FROM {table_name}
                WHERE {where_clause}
                GROUP BY 
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
                        ELSE EXTRACT(YEAR FROM date)::int
                    END,
                    province
                ORDER BY season_year, province
            """
        else:
            sql_data = f"""
                SELECT 
                    EXTRACT(YEAR FROM date)::int as year,
                    province,
                    SUM(rainfall_mm) as total_rainfall
                FROM {table_name}
                WHERE {where_clause}
                GROUP BY EXTRACT(YEAR FROM date), province
                ORDER BY year, province
            """
        
        with connection.cursor() as cursor:
            cursor.execute(sql_data, params)
            data_rows = cursor.fetchall()
        
        if not data_rows:
            return JsonResponse({
                'success': False,
                'message': f'No data found for the given years and season {season_filter}.',
                'data': []
            }, status=404)
        
        # Get all provinces
        if province_filter:
            provinces = [province_filter]
        else:
            provinces = sorted(set(row[1] for row in data_rows))
        
        # ============================================================
        # STEP 2: Calculate LTA for each season using the LTA period
        # LTA = average of seasonal totals for each season within LTA period
        # ============================================================
        
        lta_where = f"EXTRACT(YEAR FROM date) BETWEEN {lta_start} AND {lta_end} AND ({month_conditions})"
        if province_filter:
            lta_where += f" AND province = '{province_filter}'"
        
        # Build LTA SQL
        if cross_year:
            sql_lta = f"""
                SELECT 
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
                        ELSE EXTRACT(YEAR FROM date)::int
                    END as season_year,
                    province,
                    SUM(rainfall_mm) as seasonal_total
                FROM {table_name}
                WHERE {lta_where}
                GROUP BY 
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) IN (1, 2, 3) THEN EXTRACT(YEAR FROM date)::int
                        ELSE EXTRACT(YEAR FROM date)::int
                    END,
                    province
            """
        else:
            sql_lta = f"""
                SELECT 
                    EXTRACT(YEAR FROM date)::int as year,
                    province,
                    SUM(rainfall_mm) as seasonal_total
                FROM {table_name}
                WHERE {lta_where}
                GROUP BY EXTRACT(YEAR FROM date), province
            """
        
        with connection.cursor() as cursor:
            cursor.execute(sql_lta)
            lta_rows = cursor.fetchall()
        
        # Group seasonal totals by province
        lta_data = {}
        lta_years_set = set()
        
        for row in lta_rows:
            if cross_year:
                year = row[0]
                province = row[1]
                seasonal_total = row[2]
            else:
                year = row[0]
                province = row[1]
                seasonal_total = row[2]
            
            key = f"{province}"
            if key not in lta_data:
                lta_data[key] = []
            lta_data[key].append(seasonal_total)
            lta_years_set.add(year)
        
        # Calculate LTA as average of seasonal totals
        lta_lookup = {}
        lta_count_lookup = {}
        
        for key, values in lta_data.items():
            lta_lookup[key] = round(sum(values) / len(values), 2)
            lta_count_lookup[key] = len(values)
        
        lta_num_years = len(lta_years_set)
        lta_years = sorted(lta_years_set)
        
        # ============================================================
        # STEP 3: Combine data with LTA
        # ============================================================
        
        season_data = {}
        for row in data_rows:
            if cross_year:
                year = row[0]
                province = row[1]
                total = row[2]
                # Season year display: e.g., 2020 represents 2019/2020 season
                display_year = year
                season_label = f"{year-1}/{year}"
                season_display = f"{year-1} - {year}"
            else:
                year = row[0]
                province = row[1]
                total = row[2]
                display_year = year
                season_label = str(year)
                season_display = str(year)
            
            if display_year not in season_data:
                season_data[display_year] = {
                    'year': display_year,
                    'season_year': season_label,
                    'season_display': season_display,
                    'season': season_filter,
                    'season_label': season_info['label'],
                    'season_description': season_info['description'],
                    'months': ', '.join(season_info['months_abbr']),
                    'cross_year': cross_year,
                }
                for p in provinces:
                    season_data[display_year][p] = 0.0
                    season_data[display_year][f"{p}_lta"] = 0.0
                    season_data[display_year][f"{p}_lta_count"] = 0
                    season_data[display_year][f"{p}_anomaly"] = 0.0
                    season_data[display_year][f"{p}_pct_avg"] = 0.0
            
            lta_key = province
            lta_value = lta_lookup.get(lta_key, 0.0)
            lta_count = lta_count_lookup.get(lta_key, 0)
            
            anomaly = total - lta_value
            pct_avg = (total / lta_value * 100) if lta_value > 0 else 0
            
            season_data[display_year][province] = round(total, 2)
            season_data[display_year][f"{province}_lta"] = lta_value
            season_data[display_year][f"{province}_lta_count"] = lta_count
            season_data[display_year][f"{province}_anomaly"] = round(anomaly, 2)
            season_data[display_year][f"{province}_pct_avg"] = round(pct_avg, 1)
        
        data = sorted(season_data.values(), key=lambda x: x['year'])
        
        # ============================================================
        # STEP 4: Build response
        # ============================================================
        
        response_data = {
            'success': True,
            'aggregation': 'annual',
            'aggregation_label': 'Annual/Seasonal with LTA',
            'season': season_filter,
            'season_label': season_info['label'],
            'season_description': season_info['description'],
            'season_months': season_info['months_abbr'],
            'cross_year': cross_year,
            'lta_period': {
                'start_year': lta_start,
                'end_year': lta_end,
                'num_years': lta_num_years,
                'years': lta_years,
                'description': f"{lta_num_years} years ({lta_start}-{lta_end})",
                'note': 'LTA is calculated from the available data in the LTA period'
            },
            'year_range': {
                'start': start_year,
                'end': end_year
            },
            'provinces': provinces,
            'total_seasons': len(data),
            'fields_explanation': {
                'rainfall': 'Total seasonal rainfall (mm)',
                'lta': 'Long-Term Average seasonal rainfall (mm)',
                'lta_count': 'Number of years used to calculate LTA',
                'anomaly': 'Rainfall - LTA (mm)',
                'pct_avg': 'Percentage of LTA (%)'
            },
            'data': data,
            'metadata': {
                'source': 'database',
                'exported_at': datetime.datetime.now().isoformat()
            }
        }
        
        if output_format == 'csv':
            return export_annual_lta_csv(response_data)
        
        return JsonResponse(response_data, status=200)
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid parameter: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error in annual LTA aggregation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def export_annual_lta_csv(response_data):
    """Export annual LTA data as CSV."""
    import csv
    from django.http import HttpResponse
    
    data = response_data['data']
    provinces = response_data['provinces']
    cross_year = response_data.get('cross_year', False)
    
    if not data:
        return JsonResponse({'error': 'No data to export'}, status=404)
    
    csv_response = HttpResponse(content_type='text/csv')
    filename = f"rainfall_annual_lta_{response_data['year_range']['start']}_to_{response_data['year_range']['end']}_{response_data['season']}.csv"
    csv_response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(csv_response)
    
    # Write header
    if cross_year:
        header = ['Year', 'Season Year', 'Season', 'Season Description', 'Months']
    else:
        header = ['Year', 'Season', 'Season Description', 'Months']
    
    for province in provinces:
        header.extend([
            f'{province}_rainfall',
            f'{province}_lta',
            f'{province}_lta_count',
            f'{province}_anomaly',
            f'{province}_pct_avg'
        ])
    writer.writerow(header)
    
    # Write data rows
    for row in data:
        if cross_year:
            row_data = [
                row['year'],
                row['season_display'],
                row['season_label'],
                row['season_description'],
                row['months']
            ]
        else:
            row_data = [
                row['year'],
                row['season_label'],
                row['season_description'],
                row['months']
            ]
        
        for province in provinces:
            row_data.extend([
                row.get(province, 0.0),
                row.get(f'{province}_lta', 0.0),
                row.get(f'{province}_lta_count', 0),
                row.get(f'{province}_anomaly', 0.0),
                row.get(f'{province}_pct_avg', 0.0)
            ])
        writer.writerow(row_data)
    
    return csv_response

#
#####################################################################################################

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

def view_ndvi(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/fields_monitoring.html', {})

def ndvi_lookback(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/ndvi_lookback.html', {})

def field_analytics_view(request):
    return render(request, 'fields_admin/field_ndvi_graph.html')


#
#
#



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

def ndvi_to_db(request):
    """Test view for Rainfall API"""
    return render(request, 'fields_admin/save_ndvi_to_db.html', {})





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