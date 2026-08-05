# apps/fields_admin/services/climatology.py
"""
Climatology module - calculates Long-Term Averages (LTA).
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ClimatologyService:
    """
    Calculates climatological statistics (LTA).
    """
    
    def __init__(self):
        pass
    
    def calculate_lta(self, data, period, lta_start, lta_end):
        """
        Calculate Long-Term Average for each period and province.
        """
        # Filter data to LTA period
        lta_data = self._filter_by_year(data, lta_start, lta_end)
        
        if not lta_data:
            return {}
        
        # Group by period and province
        grouped = self._group_by_period_and_province(lta_data, period)
        
        # Calculate average for each period-province
        lta_lookup = {}
        lta_count_lookup = {}
        
        for group_key, group_data in grouped.items():
            values = [item.get('value', 0) for item in group_data if item.get('value') is not None]
            if values:
                lta_lookup[group_key] = round(sum(values) / len(values), 2)
                lta_count_lookup[group_key] = len(values)
            else:
                lta_lookup[group_key] = 0
                lta_count_lookup[group_key] = 0
        
        return {
            'lta': lta_lookup,
            'count': lta_count_lookup,
            'years': sorted(set(self._extract_years(lta_data))),
            'num_years': len(set(self._extract_years(lta_data)))
        }
    
    def _filter_by_year(self, data, start_year, end_year):
        """Filter data by year range."""
        filtered = []
        for item in data:
            year = None
            if 'year' in item:
                year = item['year']
            elif 'season_year' in item:
                year = item['season_year']
            elif 'period_key' in item:
                try:
                    parts = item['period_key'].split('-')
                    year = int(parts[0])
                except:
                    pass
            
            if year and start_year <= year <= end_year:
                filtered.append(item)
        
        return filtered
    
    def _group_by_period_and_province(self, data, period):
        """Group data by period and province."""
        groups = defaultdict(list)
        
        for item in data:
            province = item.get('province', 'Unknown')
            key = None
            
            if period == 'monthly':
                if 'month' in item:
                    key = f"M{item['month']:02d}|{province}"
                elif 'period_key' in item:
                    parts = item['period_key'].split('-')
                    if len(parts) >= 2:
                        key = f"M{int(parts[1]):02d}|{province}"
            
            elif period == 'dekad':
                if 'dekad' in item and 'month' in item:
                    key = f"M{item['month']:02d}-D{item['dekad']}|{province}"
                elif 'period_key' in item:
                    parts = item['period_key'].split('-')
                    if len(parts) >= 3:
                        month = int(parts[1])
                        dekad = int(parts[2].replace('D', ''))
                        key = f"M{month:02d}-D{dekad}|{province}"
            
            elif period == 'annual':
                key = f"ANNUAL|{province}"
            
            elif period == 'seasonal':
                key = f"SEASONAL|{province}"
            
            else:
                key = f"{item.get('period_key', 'UNKNOWN')}|{province}"
            
            if key:
                groups[key].append(item)
        
        return dict(groups)
    
    def _extract_years(self, data):
        """Extract years from data."""
        years = []
        for item in data:
            if 'year' in item:
                years.append(item['year'])
            elif 'season_year' in item:
                years.append(item['season_year'])
            elif 'period_key' in item:
                try:
                    parts = item['period_key'].split('-')
                    years.append(int(parts[0]))
                except:
                    pass
        return years
    
    def add_lta_to_data(self, data, lta_data):
        """Add LTA values to data points."""
        lta_lookup = lta_data.get('lta', {})
        lta_count = lta_data.get('count', {})
        
        result = []
        for item in data:
            item_copy = item.copy()
            key = self._get_lta_key(item)
            
            item_copy['lta'] = lta_lookup.get(key, 0)
            item_copy['lta_count'] = lta_count.get(key, 0)
            
            result.append(item_copy)
        
        return result
    
    def _get_lta_key(self, item):
        """Get the key to use for LTA lookup."""
        province = item.get('province', 'Unknown')
        
        if 'month' in item and 'dekad' in item:
            return f"M{item['month']:02d}-D{item['dekad']}|{province}"
        elif 'month' in item:
            return f"M{item['month']:02d}|{province}"
        elif 'period_key' in item:
            parts = item['period_key'].split('-')
            if len(parts) >= 2:
                month = int(parts[1]) if parts[1].replace('-', '').isdigit() else None
                if month:
                    if 'D' in parts[1]:
                        dekad_parts = parts[1].split('D')
                        if len(dekad_parts) == 2:
                            return f"M{int(dekad_parts[0]):02d}-D{int(dekad_parts[1])}|{province}"
                    else:
                        return f"M{month:02d}|{province}"
        elif 'season' in item:
            return f"SEASONAL|{province}"
        
        return f"UNKNOWN|{province}"


# Singleton instance
climatology = ClimatologyService()


def calculate_lta(data, period, lta_start, lta_end):
    """Convenience function to calculate LTA."""
    return climatology.calculate_lta(data, period, lta_start, lta_end)


def add_lta_to_data(data, lta_data):
    """Convenience function to add LTA to data."""
    return climatology.add_lta_to_data(data, lta_data)