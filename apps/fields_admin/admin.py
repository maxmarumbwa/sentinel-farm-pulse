from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Admin1, Admin2, Field, FieldNDVI


@admin.register(Admin1)
class Admin1Admin(admin.ModelAdmin):
    list_display = ['id', 'name', 'pcode']  # Added id to see the reference
    search_fields = ['name', 'pcode']
    ordering = ['name']


@admin.register(Admin2)
class Admin2Admin(admin.ModelAdmin):
    list_display = ['id', 'name', 'admin1', 'pcode']  # Added id
    list_filter = ['admin1']
    search_fields = ['name', 'pcode', 'admin1__name']
    ordering = ['admin1', 'name']
    autocomplete_fields = ['admin1']
    list_select_related = ['admin1']
    
    # Customize the form to show admin1 name clearly
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "admin1":
            kwargs["queryset"] = Admin1.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Field)
class FieldAdmin(GISModelAdmin):
    list_display = [
        "id",
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
    
    default_lon = 28.0
    default_lat = -19.0
    default_zoom = 6
    
    autocomplete_fields = ['adm1', 'adm2']
    list_select_related = ['adm1', 'adm2', 'user']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['geometry'].help_text = 'Draw a polygon on the map or paste WKT'
        return form
    
#register rainfall model
from .models import Admin1, Admin2, Field, RainfallProvince


@admin.register(RainfallProvince)
class RainfallProvinceAdmin(admin.ModelAdmin):
    list_display = ['province', 'date', 'rainfall_mm', 'lat', 'lng', 'source', 'created_at']
    list_filter = ['province', 'date', 'source']
    search_fields = ['province']
    ordering = ['-date', 'province']
    date_hierarchy = 'date'
    list_per_page = 50
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ['province', 'date', 'source', 'lat', 'lng', 'created_at']
        return ['created_at']
    
    
@admin.register(FieldNDVI)
class FieldNDVIAdmin(admin.ModelAdmin):
    list_display = ['field', 'date', 'ndvi_value', 'created_at']
    list_filter = ['date', 'field__crop']
    search_fields = ['field__field_name']
    ordering = ['-date']
    date_hierarchy = 'date'
    list_select_related = ['field']