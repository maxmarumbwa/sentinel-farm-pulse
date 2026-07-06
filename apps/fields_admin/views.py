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