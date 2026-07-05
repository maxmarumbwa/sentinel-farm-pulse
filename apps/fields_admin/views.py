from django.shortcuts import render
from .models import Field


from django.shortcuts import render
import ee
from datetime import datetime

def satellite_view(request):
    """Display a satellite image from Earth Engine"""
    image = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate("2025-01-01", "2025-12-31")
        .filterBounds(ee.Geometry.Point([30.0, -1.0]))
        .sum()
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

