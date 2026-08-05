# apps/fields_admin/services/loader.py
"""
Data loader - handles database queries for raw data.
"""

import logging
from django.db import connection

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads raw data from the database.
    """
    
    def __init__(self):
        pass
    
    def load_data_with_sql(self, model, start_date, end_date, filters=None):
        """
        Load raw data using raw SQL for better performance.
        
        Args:
            model: Django model class
            start_date: Start date
            end_date: End date
            filters: Optional filters
            
        Returns:
            List of dicts with date, value, and province fields
        """
        try:
            table_name = model._meta.db_table
            
            # Determine the value field
            if model.__name__ == 'RainfallProvince':
                value_field = 'rainfall_mm'
            elif model.__name__ == 'NdviProvince':
                value_field = 'ndvi_value'
            elif model.__name__ == 'TemperatureProvince':
                value_field = 'temp_celsius'
            else:
                # Try to auto-detect
                field_names = [f.name for f in model._meta.fields]
                skip_fields = ['id', 'date', 'province', 'lat', 'lng', 'longitude', 
                              'latitude', 'source', 'created_at', 'updated_at', 'geom', 'geometry']
                value_fields = [f for f in field_names if f not in skip_fields]
                value_field = value_fields[0] if value_fields else None
            
            if not value_field:
                raise ValueError(f"No value field found for model {model.__name__}")
            
            # Build the WHERE clause
            where_parts = ["date >= %s", "date <= %s"]
            params = [start_date, end_date]
            
            if filters:
                for field, value in filters.items():
                    if value:
                        where_parts.append(f"{field} = %s")
                        params.append(value)
            
            where_clause = " AND ".join(where_parts)
            
            # SQL query with province included
            sql = f"""
                SELECT 
                    id,
                    date,
                    province,
                    {value_field} as value
                FROM {table_name}
                WHERE {where_clause}
                ORDER BY date, province
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # Convert to list of dicts
                results = []
                for row in rows:
                    province_value = row[2] if row[2] else 'Unknown'
                    
                    results.append({
                        'id': row[0],
                        'date': row[1],
                        'province': province_value,
                        'value': float(row[3]) if row[3] is not None else 0.0
                    })
                
                logger.info(f"Loaded {len(results)} records from {table_name}")
                return results
            
        except Exception as e:
            logger.error(f"Error loading data with SQL: {str(e)}")
            raise


# Singleton instance
loader = DataLoader()


def load_data(model, start_date, end_date, filters=None):
    """
    Convenience function to load data.
    """
    return loader.load_data_with_sql(model, start_date, end_date, filters)