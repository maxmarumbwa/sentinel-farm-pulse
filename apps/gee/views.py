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
        "satellite/sentinel_truecolour.html",
        
        context
    )





#######################################################################################################
######################################### OLD CODE#####################################################
#######################################################################################################
# #Sentinel view
# import ee
# import datetime
# import calendar
# from django.shortcuts import render


# def sentinel_truecolour(request):
#     """Sentinel-2 True Colour Composite"""

#     try:

#         # -------------------------------
#         # User inputs
#         # -------------------------------
#         start_year = int(request.GET.get("start_year", 2025))
#         start_month = int(request.GET.get("start_month", 1))

#         end_year = int(request.GET.get("end_year", 2025))
#         end_month = int(request.GET.get("end_month", 1))

#         cloud_cover = int(request.GET.get("cloud", 20))

#         cloud_cover = max(0, min(100, cloud_cover))

#         # -------------------------------
#         # Dates
#         # -------------------------------
#         start = datetime.date(start_year, start_month, 1)

#         if end_month == 12:
#             end = datetime.date(end_year + 1, 1, 1)
#         else:
#             end = datetime.date(end_year, end_month + 1, 1)

#         # -------------------------------
#         # Zimbabwe
#         # -------------------------------
#         zimbabwe = ee.Geometry.Polygon(
#             [[
#                 [25.24, -22.42],
#                 [33.07, -22.42],
#                 [33.07, -15.61],
#                 [25.24, -15.61],
#                 [25.24, -22.42],
#             ]]
#         )

#         # -------------------------------
#         # Sentinel Composite
#         # -------------------------------
#         image = (
#             ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
#             .filterBounds(zimbabwe)
#             .filterDate(str(start), str(end))
#             .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
#             .median()
#             .clip(zimbabwe)
#         )

#         vis_params = {
#             "bands": ["B4", "B3", "B2"],
#             "min": 0,
#             "max": 3000,
#             "gamma": 1.2,
#         }

#         tile_url = image.getMapId(vis_params)["tile_fetcher"].url_format

#         context = {
#             "tile_url": tile_url,

#             "start_year": start_year,
#             "start_month": start_month,

#             "end_year": end_year,
#             "end_month": end_month,

#             "cloud_cover": cloud_cover,

#             "date": (
#                 f"{calendar.month_name[start_month]} {start_year}"
#                 f" - "
#                 f"{calendar.month_name[end_month]} {end_year}"
#             ),

#             "years": list(range(2017, datetime.date.today().year + 1)),
#             "months": [
#                 (1, "January"),
#                 (2, "February"),
#                 (3, "March"),
#                 (4, "April"),
#                 (5, "May"),
#                 (6, "June"),
#                 (7, "July"),
#                 (8, "August"),
#                 (9, "September"),
#                 (10, "October"),
#                 (11, "November"),
#                 (12, "December"),
#             ],
#         }

#     except Exception as e:

#         context = {
#             "error": str(e),
#             "years": list(range(2017, datetime.date.today().year + 1)),
#             "months": [
#                 (1, "January"),
#                 (2, "February"),
#                 (3, "March"),
#                 (4, "April"),
#                 (5, "May"),
#                 (6, "June"),
#                 (7, "July"),
#                 (8, "August"),
#                 (9, "September"),
#                 (10, "October"),
#                 (11, "November"),
#                 (12, "December"),
#             ],
#         }

#     return render(
#         request,
#         "satellite/sentinel_truecolour.html",
#         context,
#     )


# # Sentinel-2 NDVI view
# import ee
# import datetime
# import calendar
# from django.shortcuts import render


# def sentinel_truecolour(request, year=2025, month=1):
#     """Monthly Sentinel-2 True Colour Composite"""

#     # Read cloud cover from URL, default = 30%
#     try:
#         cloud_cover = float(request.GET.get("cloud", 30))
#     except ValueError:
#         cloud_cover = 30

#     # Keep within valid range
#     cloud_cover = max(0, min(100, cloud_cover))

#     try:
#         start = datetime.date(year, month, 1)

#         if month == 12:
#             end = datetime.date(year + 1, 1, 1)
#         else:
#             end = datetime.date(year, month + 1, 1)

#         # Zimbabwe bounding box
#         zimbabwe = ee.Geometry.Polygon(
#             [[
#                 [25.24, -22.42],
#                 [33.07, -22.42],
#                 [33.07, -15.61],
#                 [25.24, -15.61],
#                 [25.24, -22.42],
#             ]]
#         )

#         image = (
#             ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
#             .filterBounds(zimbabwe)
#             .filterDate(str(start), str(end))
#             .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover))
#             .median()
#             .clip(zimbabwe)
#         )

#         vis_params = {
#             "bands": ["B4", "B3", "B2"],
#             "min": 0,
#             "max": 3000,
#             "gamma": 1.2,
#         }

#         tile_url = image.getMapId(vis_params)["tile_fetcher"].url_format

#         context = {
#             "tile_url": tile_url,
#             "date": f"{calendar.month_name[month]} {year}",
#             "year": year,
#             "month": month,
#             "cloud_cover": cloud_cover,
#         }

#     except Exception as e:
#         context = {
#             "error": str(e),
#             "cloud_cover": cloud_cover,
#         }

#     return render(request, "satellite/sentinel_truecolour.html", context)


# import calendar
# import datetime
# import ee
# from django.shortcuts import render


# def sentinel_truecolour(request, year=2025, month=1):
#     """Monthly Sentinel-2 True Colour Composite"""

#     try:
#         start = datetime.date(year, month, 1)

#         if month == 12:
#             end = datetime.date(year + 1, 1, 1)
#         else:
#             end = datetime.date(year, month + 1, 1)

#         # Zimbabwe
#         zimbabwe = ee.Geometry.Polygon(
#             [[
#                 [25.24, -22.42],
#                 [33.07, -22.42],
#                 [33.07, -15.61],
#                 [25.24, -15.61],
#                 [25.24, -22.42],
#             ]]
#         )

#         image = (
#             ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
#             .filterBounds(zimbabwe)
#             .filterDate(str(start), str(end))
#             .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
#             .median()
#             .clip(zimbabwe)
#         )

#         vis_params = {
#             "bands": ["B4", "B3", "B2"],
#             "min": 0,
#             "max": 3000,
#             "gamma": 1.2,
#         }

#         tile_url = image.getMapId(vis_params)["tile_fetcher"].url_format

#         context = {
#             "tile_url": tile_url,
#             "date": f"{calendar.month_name[month]} {year}",
#             "year": year,
#             "month": month,
#         }

#     except Exception as e:
#         context = {"error": str(e)}

#     return render(request, "satellite/sentinel_truecolour.html", context)

## Sentinel fixed
# import ee
# from django.shortcuts import render


# def sentinel_truecolour(request):
#     """Display monthly Sentinel-2 True Colour composite over Zimbabwe"""

#     try:
#         # Zimbabwe bounding box
#         zimbabwe = ee.Geometry.Polygon(
#             [[
#                 [25.24, -22.42],
#                 [33.07, -22.42],
#                 [33.07, -15.61],
#                 [25.24, -15.61],
#                 [25.24, -22.42],
#             ]]
#         )

#         # Monthly composite
#         image = (
#             ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
#             .filterBounds(zimbabwe)
#             .filterDate("2025-08-01", "2025-10-01")
#             .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
#             .median()
#             .clip(zimbabwe)
#         )

#         # True colour visualization
#         vis_params = {
#             "bands": ["B4", "B3", "B2"],
#             "min": 0,
#             "max": 3000,
#             "gamma": 1.2,
#         }

#         map_id = image.getMapId(vis_params)
#         tile_url = map_id["tile_fetcher"].url_format

#         context = {
#             "tile_url": tile_url,
#             "date": "January 2025",
#         }

#     except Exception as e:
#         context = {"error": str(e)}

#     return render(request, "satellite/sentinel_truecolour.html", context)






