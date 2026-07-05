from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Admin1, Admin2, Admin3, Field


# =====================================================
# ADMIN1 (Provinces) - Simple Manual Entry
# =====================================================

@admin.register(Admin1)
class Admin1Admin(admin.ModelAdmin):
    list_display = ['name', 'pcode']
    search_fields = ['name', 'pcode']
    ordering = ['name']
    
    # Optional: Add bulk actions if needed
    actions = ['delete_selected']


# =====================================================
# ADMIN2 (Districts) - Simple Manual Entry
# =====================================================

@admin.register(Admin2)
class Admin2Admin(admin.ModelAdmin):
    list_display = ['name', 'admin1', 'pcode']
    list_filter = ['admin1']
    search_fields = ['name', 'pcode']
    ordering = ['admin1', 'name']
    autocomplete_fields = ['admin1']  # Better UX for foreign key


# =====================================================
# ADMIN3 (Wards) - Simple Manual Entry
# =====================================================

@admin.register(Admin3)
class Admin3Admin(admin.ModelAdmin):
    list_display = ['name', 'admin2', 'pcode']
    list_filter = ['admin2']
    search_fields = ['name', 'pcode']
    ordering = ['admin2', 'name']
    autocomplete_fields = ['admin2']


# =====================================================
# FIELD GIS ADMIN - Simple Manual Entry
# =====================================================

@admin.register(Field)
class FieldAdmin(GISModelAdmin):
    list_display = [
        "field_name",
        "user",
        "crop",
        "production_system",
        "area_ha",
        "created_at"
    ]
    list_filter = ["crop", "production_system", "user"]
    search_fields = ["field_name", "user__username"]
    readonly_fields = ["area_ha", "created_at", "updated_at"]
    ordering = ['-created_at']
    
    # GIS settings
    default_lon = 28.0
    default_lat = -19.0
    default_zoom = 6
    
    # Autocomplete for better UX
    autocomplete_fields = ['adm1', 'adm2', 'adm3']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)
    
    # Add inline help for geometry field
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['geometry'].help_text = 'Draw a polygon on the map or paste WKT (e.g., POLYGON((28.0 -19.0, 28.1 -19.0, 28.1 -19.1, 28.0 -19.1, 28.0 -19.0)))'
        return form