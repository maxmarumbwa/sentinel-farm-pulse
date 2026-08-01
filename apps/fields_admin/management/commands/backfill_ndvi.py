# python manage.py backfill_ndvi --start_date 2015-01-01 --end_date 2026-07-31
from django.core.management.base import BaseCommand
from apps.fields_admin.models import Field, FieldNDVI
import datetime
import json
import time
import ee

# Import your existing init function
from apps.gee.ee_auth import initialize_earth_engine 

class Command(BaseCommand):
    help = 'Backfill NDVI data for all fields within a specific date range'

    def add_arguments(self, parser):
        # Allow the user to specify start and end dates when running the command
        parser.add_argument('--start_date', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end_date', type=str, help='End date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        # 1. Initialize Earth Engine
        try:
            initialize_earth_engine()
            self.stdout.write(self.style.SUCCESS('✅ Earth Engine initialized successfully.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to initialize EE: {e}'))
            return

        # 2. Parse the dates from command line arguments
        start_date_str = options.get('start_date')
        end_date_str = options.get('end_date')

        # Default to full Sentinel-2 history if not provided
        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = datetime.date(2015, 6, 1)  # Sentinel-2 start

        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.date.today()

        if start_date > end_date:
            self.stdout.write(self.style.ERROR('❌ start_date must be before end_date'))
            return

        fields = Field.objects.all()
        total_fields = fields.count()
        self.stdout.write(f"📡 Starting backfill for {total_fields} fields from {start_date} to {end_date}...")

        # 3. Loop through each field
        for index, field in enumerate(fields, start=1):
            self.stdout.write(f"\n[{index}/{total_fields}] Processing: {field.field_name} (ID: {field.id})...")
            
            if not field.geometry:
                self.stdout.write("  ⚠️ Skipped: No geometry found.")
                continue
            
            try:
                geom_json = json.loads(field.geometry.geojson)
                coords = geom_json.get('coordinates', [])
                if not coords or len(coords) == 0:
                    self.stdout.write("  ⚠️ Skipped: Invalid geometry.")
                    continue
                ee_geom = ee.Geometry.Polygon(coords)
            except Exception as e:
                self.stdout.write(f"  ❌ Error parsing geometry: {e}")
                continue

            try:
                # 🔥 THE FAST FIX: We ask Earth Engine to return a LIST of [date, ndvi]
                # This avoids the "5000 elements" crash by using a native server-side reducer.
                
                collection = (
                    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(ee_geom)
                    .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
                )

                # Calculate NDVI
                def add_ndvi(img):
                    ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
                    return img.addBands(ndvi)
                
                collection = collection.map(add_ndvi)

                # 🔥 Instead of extracting features one by one, we extract them ALL at once
                # using reduceColumns. This returns a server-side array of dates and NDVIs.
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

                # Map over the entire collection (Stays on GEE servers)
                features = collection.map(extract_ndvi)
                
                # ✅ Filter out nulls (clouds) BEFORE sending to Python
                features = features.filter(ee.Filter.notNull(['ndvi']))
                
                # ✅ Get the results ONCE - this is a single API call
                feature_list = features.getInfo()
                
                if not feature_list or len(feature_list['features']) == 0:
                    self.stdout.write("  ⚠️ No valid NDVI data found for this field.")
                    continue

                # Aggregate duplicates
                date_dict = {}
                for feature in feature_list['features']:
                    props = feature['properties']
                    date_str = props['date']
                    ndvi_val = props['ndvi']
                    
                    if date_str in date_dict:
                        existing = date_dict[date_str]
                        date_dict[date_str] = round((existing + ndvi_val) / 2, 4)
                    else:
                        date_dict[date_str] = round(ndvi_val, 4)

                # Save to database
                records_to_create = []
                for date_str, ndvi_val in date_dict.items():
                    records_to_create.append(
                        FieldNDVI(
                            field=field,
                            date=datetime.datetime.strptime(date_str, '%Y-%m-%d').date(),
                            ndvi_value=ndvi_val
                        )
                    )

                if records_to_create:
                    FieldNDVI.objects.bulk_create(
                        records_to_create,
                        ignore_conflicts=True
                    )
                    self.stdout.write(f"  ✅ Saved {len(records_to_create)} records.")
                else:
                    self.stdout.write("  ⚠️ No data to save.")
            
            except Exception as e:
                self.stdout.write(f"  ❌ Error querying Earth Engine: {e}")

            time.sleep(1)

        self.stdout.write(self.style.SUCCESS('\n🎉 Backfill completed successfully!'))