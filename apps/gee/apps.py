from django.apps import AppConfig


class EarthEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gee"

    def ready(self):
        # Initialize Earth Engine when Django starts
        from .ee_auth import initialize_earth_engine

        initialize_earth_engine()
