# apps/fields_admin/services/serializer.py
"""
Data serializer - formats data for API responses.
"""

import datetime
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class DataSerializer:
    """
    Serializes data into API response format.
    Supports both row format and pivot format.
    """
    
    def __init__(self):
        pass
    
    def serialize(self, data, metadata=None, pivot=True):
        """
        Serialize data for API response.
        
        Args:
            data: List of data points
            metadata: Optional metadata dict
            pivot: If True, pivot data by province (like old view)
        
        Returns:
            Serialized data dict
        """
        if pivot:
            return self._serialize_pivot(data, metadata)
        else:
            return self._serialize_rows(data, metadata)
    
    def _serialize_rows(self, data, metadata=None):
        """Serialize as rows (one row per period-province)."""
        serialized_data = []
        
        for item in data:
            serialized_item = self._serialize_item(item)
            serialized_data.append(serialized_item)
        
        response = {'data': serialized_data}
        if metadata:
            response['metadata'] = metadata
        
        return response
    
    def _serialize_pivot(self, data, metadata=None):
        """
        Serialize as pivot table (one row per period, provinces as columns).
        Like the old view format.
        """
        if not data:
            return {'data': []}
        
        # Group by period_key
        grouped = defaultdict(list)
        for item in data:
            period_key = item.get('period_key', 'unknown')
            grouped[period_key].append(item)
        
        # Get all unique provinces
        provinces = sorted(set(item.get('province', 'Unknown') for item in data))
        
        # Build pivot data
        pivot_data = []
        for period_key, items in sorted(grouped.items()):
            row = {
                'period': self._format_period(period_key),
                'period_key': period_key,
            }
            
            # Get metadata from first item
            if items and 'metadata' in items[0]:
                meta = items[0]['metadata']
                # Serialize metadata - this will include season_year and season_display for seasonal
                serialized_meta = self._serialize_metadata(meta)
                row.update(serialized_meta)
                
                # For seasonal data, add additional season fields
                if meta.get('period') == 'seasonal':
                    # Add season_year and season_display if they exist in metadata
                    if 'season_year' in meta:
                        row['season_year'] = meta['season_year']
                    if 'season_display' in meta:
                        row['season_display'] = meta['season_display']
                    if 'display_year' in meta:
                        row['display_year'] = meta['display_year']
            
            # Add data for each province
            for province in provinces:
                # Find the item for this province
                province_item = next((item for item in items if item.get('province') == province), None)
                
                if province_item:
                    row[province] = province_item.get('value', 0)
                    if 'lta' in province_item:
                        row[f'{province}_lta'] = province_item.get('lta', 0)
                    if 'lta_count' in province_item:
                        row[f'{province}_lta_count'] = province_item.get('lta_count', 0)
                    if 'anomaly' in province_item:
                        row[f'{province}_anomaly'] = province_item.get('anomaly', 0)
                    if 'pct_average' in province_item:
                        row[f'{province}_pct_avg'] = province_item.get('pct_average', 0)
                    if 'zscore' in province_item:
                        row[f'{province}_zscore'] = province_item.get('zscore', 0)
                    if 'spi' in province_item:
                        row[f'{province}_spi'] = province_item.get('spi', 0)
                    if 'vci' in province_item:
                        row[f'{province}_vci'] = province_item.get('vci', 0)
                    if 'tci' in province_item:
                        row[f'{province}_tci'] = province_item.get('tci', 0)
                    if 'vhi' in province_item:
                        row[f'{province}_vhi'] = province_item.get('vhi', 0)
                else:
                    # No data for this province in this period
                    row[province] = 0
                    row[f'{province}_lta'] = 0
                    row[f'{province}_lta_count'] = 0
                    row[f'{province}_anomaly'] = 0
                    row[f'{province}_pct_avg'] = 0
            
            pivot_data.append(row)
        
        response = {
            'data': pivot_data,
            'provinces': provinces
        }
        
        if metadata:
            response['metadata'] = metadata
        
        return response
    
    def _serialize_item(self, item):
        """Serialize a single item."""
        serialized = {}
        
        # Always include province for row format
        if 'province' in item:
            serialized['province'] = item['province']
        
        if 'period_key' in item:
            serialized['period'] = self._format_period(item['period_key'])
        
        if 'value' in item:
            serialized['observed'] = item['value']
        
        if 'lta' in item:
            serialized['lta'] = item['lta']
        
        if 'lta_count' in item:
            serialized['lta_count'] = item['lta_count']
        
        # Metrics
        if 'anomaly' in item:
            serialized['anomaly'] = item['anomaly']
        
        if 'pct_average' in item:
            serialized['pct_average'] = item['pct_average']
        
        if 'zscore' in item:
            serialized['zscore'] = item['zscore']
        
        if 'spi' in item:
            serialized['spi'] = item['spi']
        
        if 'vci' in item:
            serialized['vci'] = item['vci']
        
        if 'tci' in item:
            serialized['tci'] = item['tci']
        
        if 'vhi' in item:
            serialized['vhi'] = item['vhi']
        
        # Metadata
        if 'metadata' in item:
            serialized.update(self._serialize_metadata(item['metadata']))
        
        if 'count' in item:
            serialized['count'] = item['count']
        
        return serialized
    
    def _format_period(self, period_key):
        """Format period key for display."""
        if '-D' in period_key:
            parts = period_key.split('-D')
            if len(parts) == 2:
                date_parts = parts[0].split('-')
                if len(date_parts) == 2:
                    return f"{date_parts[0]}-{date_parts[1]}-D{parts[1]}"
        
        if '-' in period_key:
            parts = period_key.split('-')
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1]}"
        
        if period_key.isdigit():
            return period_key
        
        return period_key
    
    def _serialize_metadata(self, metadata):
        """
        Serialize metadata.
        For seasonal data, this includes season_year and season_display.
        """
        serialized = {}
        
        if 'year' in metadata:
            serialized['year'] = metadata['year']
        
        if 'month' in metadata:
            serialized['month'] = metadata['month']
            if 'month_name' in metadata:
                serialized['month_name'] = metadata['month_name']
                serialized['month_abbr'] = metadata['month_name'][:3]
        
        if 'dekad' in metadata:
            serialized['dekad'] = metadata['dekad']
            serialized['dekad_label'] = f"D{metadata['dekad']}"
        
        if 'season' in metadata:
            serialized['season'] = metadata['season']
            if 'season_label' in metadata:
                serialized['season_label'] = metadata['season_label']
            if 'season_description' in metadata:
                serialized['season_description'] = metadata['season_description']
            if 'months_abbr' in metadata:
                serialized['months'] = ', '.join(metadata['months_abbr'])
            if 'cross_year' in metadata:
                serialized['cross_year'] = metadata['cross_year']
        
        # For seasonal data - add season_year and season_display
        if 'season_year' in metadata:
            serialized['season_year'] = metadata['season_year']
        
        if 'season_display' in metadata:
            serialized['season_display'] = metadata['season_display']
        
        if 'display_year' in metadata:
            serialized['display_year'] = metadata['display_year']
        
        if 'start_date' in metadata:
            serialized['start_date'] = metadata['start_date']
        
        if 'end_date' in metadata:
            serialized['end_date'] = metadata['end_date']
        
        return serialized
    
    def build_response(self, data, product, period, aggregation, include_lta=False, metrics=None):
        """Build complete API response."""
        metadata = {
            'product': product,
            'temporal': period,
            'aggregation': aggregation,
            'include_lta': include_lta,
            'metrics': metrics or [],
            'exported_at': datetime.datetime.now().isoformat()
        }
        
        return {
            'success': True,
            'metadata': metadata,
            'data': data
        }


# Singleton instance
serializer = DataSerializer()


def serialize(data, metadata=None, pivot=True):
    """Convenience function to serialize data."""
    return serializer.serialize(data, metadata, pivot)


def build_response(data, product, period, aggregation, include_lta=False, metrics=None):
    """Convenience function to build API response."""
    return serializer.build_response(data, product, period, aggregation, include_lta, metrics)