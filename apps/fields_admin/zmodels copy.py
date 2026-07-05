from django.contrib.gis.db import models
from django.contrib.auth.models import User


# =====================================================
# ADMIN UNITS
# =====================================================

class Admin1(models.Model):
    name = models.CharField(max_length=100, unique=True)
    pcode = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Admin2(models.Model):
    admin1 = models.ForeignKey(Admin1, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    pcode = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Admin3(models.Model):
    admin2 = models.ForeignKey(Admin2, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    pcode = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


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
    adm3 = models.ForeignKey(Admin3, on_delete=models.PROTECT, null=True, blank=True)

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