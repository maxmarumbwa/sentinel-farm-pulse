from django.contrib.gis.db import models
from django.contrib.auth.models import User


# =====================================================
# ADMIN UNITS
# =====================================================

class Admin1(models.Model):
    name = models.CharField(max_length=100)
    pcode = models.CharField(max_length=20, unique=True)
    class Meta:
        verbose_name_plural = "Admin Level 1"
    def __str__(self):
        return self.name

class Admin2(models.Model):
    admin1 = models.ForeignKey(Admin1, on_delete=models.CASCADE, related_name='admin2s')
    name = models.CharField(max_length=100)
    pcode = models.CharField(max_length=20, unique=True)
    class Meta:
        verbose_name_plural = "Admin Level 2"
    def __str__(self):
        return f"{self.name} ({self.admin1.name})"


# =====================================================
# FIELD GIS MODEL
# =====================================================

class Field(models.Model):

    CROP_CHOICES = [
        ("Maize", "Maize"),
        ("Groundnuts", "Groundnuts"),
        ("Soybeans", "Soybeans"),
        ("Cotton", "Cotton"),
        ("Tobacco", "Tobacco"),
        ("Sunflower", "Sunflower"),
        ("Sorghum", "Sorghum"),
        ("Millet", "Millet"),
        ("Beans", "Beans"),
        ("Potatoes", "Potatoes"),
        ("Tomatoes", "Tomatoes"),
        ("Other", "Other"),
    ]

    PRODUCTION_CHOICES = [
        ("Rainfed", "Rainfed"),
        ("Irrigated", "Irrigated"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=200)

    crop = models.CharField(max_length=50, choices=CROP_CHOICES, default="Maize")
    production_system = models.CharField(max_length=20, choices=PRODUCTION_CHOICES, default="Rainfed")

    adm1 = models.ForeignKey(Admin1, on_delete=models.PROTECT, null=True, blank=True)
    adm2 = models.ForeignKey(Admin2, on_delete=models.PROTECT, null=True, blank=True)

    geometry = models.PolygonField(srid=4326)

    area_ha = models.FloatField(default=0, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.geometry:
            geom = self.geometry.clone()
            geom.transform(32735)  # Zimbabwe UTM
            self.area_ha = round(geom.area / 10000, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.field_name
    
    
# Rainfall Data Model for storing rainfall data for provinces
# =====================================================
# RAINFALL DATA MODEL
# =====================================================
class RainfallProvince(models.Model):
    """
    Stores daily rainfall data for Zimbabwe provinces/towns.
    Independent table - no foreign keys.
    """
    province = models.CharField(max_length=100, db_index=True, help_text="Province or town name")
    date = models.DateField(db_index=True)
    rainfall_mm = models.FloatField(default=0.0, help_text="Rainfall in millimeters")
    lat = models.FloatField(null=True, blank=True, help_text="Latitude")
    lng = models.FloatField(null=True, blank=True, help_text="Longitude")
    source = models.CharField(max_length=50, default='CHIRPS', help_text="Data source")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Rainfall Data"
        ordering = ['-date', 'province']
        unique_together = ['province', 'date']  # Prevent duplicate entries per province/date
        
    def __str__(self):
        return f"{self.province} - {self.date} ({self.rainfall_mm}mm)"
     
     
     
     
     
# Model for saving ndvi for fields
# =====================================================
# FIELD NDVI DATA MODEL
# =====================================================

class FieldNDVI(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='ndvi_records')
    date = models.DateField()
    ndvi_value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['field', 'date']  # Prevents duplicate dates
        ordering = ['-date']
        verbose_name_plural = "Field NDVI Records"
    
    def __str__(self):
        return f"{self.field.field_name} - {self.date} ({self.ndvi_value})"
    
    
# =====================================================
# Model for saving ndvi for provinces (lat/lon points)
# NDVI PROVINCE MODEL
# =====================================================
class NDVIProvince(models.Model):
    """
    Stores NDVI data for Zimbabwe provinces/towns.
    Independent table - no foreign keys.
    """
    province = models.CharField(max_length=100, db_index=True, help_text="Province or town name")
    date = models.DateField(db_index=True)
    ndvi_value = models.FloatField(default=0.0, help_text="NDVI value (-1 to 1)")
    lat = models.FloatField(null=True, blank=True, help_text="Latitude")
    lng = models.FloatField(null=True, blank=True, help_text="Longitude")
    cloud_cover = models.FloatField(null=True, blank=True, help_text="Cloud cover percentage")
    source = models.CharField(max_length=50, default='Sentinel-2', help_text="Data source")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "NDVI Data"
        ordering = ['-date', 'province']
        unique_together = ['province', 'date']  # Prevent duplicate entries per province/date
        
    def __str__(self):
        return f"{self.province} - {self.date} (NDVI: {self.ndvi_value})"