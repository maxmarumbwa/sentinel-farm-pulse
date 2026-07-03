from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('core/', include('apps.core.urls')),
    path('gee/', include('apps.gee.urls')),
    path('indicators/', include('apps.indicators.urls')),
    path('reports/', include('apps.reports.urls')),
]