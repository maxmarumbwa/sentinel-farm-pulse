# apps/fields_admin/services/aggregator.py
"""
Temporal aggregator - aggregates data into different time periods.
"""

import calendar
import logging
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class Aggregator:
    """
    Aggregates daily data into various temporal periods.
    Groups by period AND province.
    """
    
    def __init__(self):
        self.aggregation_functions = {
            'sum': self._sum_values,
            'mean': self._mean_values,
            'median': self._median_values,
            'max': self._max_values,
            'min': self._min_values,
            'std': self._std_values
        }
    
    def aggregate(self, data, period, aggregation_method='sum', **kwargs):
        """
        Main aggregation method - groups by period AND province.
        
        For seasonal data, the season is added to each result item
        so that LTA can be calculated per season type.
        """
        if not data:
            logger.warning("No data to aggregate")
            return []
        
        # Log sample data for debugging
        logger.info(f"Total records to aggregate: {len(data)}")
        if data:
            provinces = set()
            for item in data:
                prov = item.get('province', 'Unknown')
                if prov:
                    provinces.add(prov)
            logger.info(f"Provinces found in data: {provinces}")
        
        # Group data by period AND province
        grouped = self._group_by_period_and_province(data, period, **kwargs)
        
        logger.info(f"Number of groups created: {len(grouped)}")
        
        # Apply aggregation function
        agg_func = self.aggregation_functions.get(aggregation_method, self._mean_values)
        
        result = []
        for group_key, group_data in grouped.items():
            values = [item['value'] for item in group_data]
            aggregated_value = agg_func(values)
            
            # Parse group key to get period and province
            period_key, province = self._parse_group_key(group_key)
            
            item = {
                'period_key': period_key,
                'province': province,
                'value': aggregated_value,
                'count': len(values),
                'dates': [item['date'] for item in group_data],
                'metadata': self._get_period_metadata(period_key, period, **kwargs)
            }
            
            # CRITICAL: For seasonal data, add the season to the item
            if period == 'seasonal':
                season = kwargs.get('season', 'UNKNOWN')
                item['season'] = season
                if 'metadata' in item and item['metadata']:
                    item['metadata']['season'] = season
            
            result.append(item)
        
        # For seasonal data, add additional season info to metadata
        if period == 'seasonal':
            season = kwargs.get('season', 'UNKNOWN')
            season_def = kwargs.get('season_def', {})
            cross_year = kwargs.get('cross_year', False)
            
            for item in result:
                if 'metadata' in item and item['metadata']:
                    item['metadata']['season_label'] = season_def.get('label', '')
                    item['metadata']['season_description'] = season_def.get('description', '')
                    item['metadata']['months_abbr'] = season_def.get('months_abbr', [])
                    item['metadata']['cross_year'] = cross_year
                    
                    # Add season year and display info
                    period_key = item['period_key']
                    if cross_year:
                        try:
                            year_int = int(period_key)
                            item['metadata']['season_year'] = f"{year_int-1}/{year_int}"
                            item['metadata']['season_display'] = f"{year_int-1}/{year_int}"
                            item['metadata']['display_year'] = f"{year_int-1} - {year_int}"
                        except ValueError:
                            item['metadata']['season_year'] = period_key
                            item['metadata']['season_display'] = period_key
                            item['metadata']['display_year'] = period_key
                    else:
                        item['metadata']['season_year'] = period_key
                        item['metadata']['season_display'] = period_key
                        item['metadata']['display_year'] = period_key
        
        # Sort by period then province
        result.sort(key=lambda x: (x['period_key'], x['province']))
        
        logger.info(f"Number of aggregated results: {len(result)}")
        if result:
            logger.info(f"Sample result: period={result[0]['period_key']}, province={result[0]['province']}, value={result[0]['value']}")
            if 'season' in result[0]:
                logger.info(f"Sample season: {result[0]['season']}")
        
        return result
    
    def _group_by_period_and_province(self, data, period, **kwargs):
        """Group data by period AND province."""
        if period == 'daily':
            return self._group_daily_by_province(data)
        elif period == 'dekad':
            return self._group_dekad_by_province(data)
        elif period == 'monthly':
            return self._group_monthly_by_province(data)
        elif period == 'annual':
            return self._group_annual_by_province(data)
        elif period == 'seasonal':
            return self._group_seasonal_by_province(data, **kwargs)
        else:
            raise ValueError(f"Unsupported period: {period}")
    
    def _group_daily_by_province(self, data):
        """Group data by date and province."""
        groups = defaultdict(list)
        for item in data:
            date = item['date']
            province = item.get('province', 'Unknown')
            if not province or province.strip() == '':
                province = 'Unknown'
            key = f"{date.strftime('%Y-%m-%d')}|{province}"
            groups[key].append(item)
        return dict(groups)
    
    def _group_dekad_by_province(self, data):
        """Group data by dekad and province."""
        groups = defaultdict(list)
        for item in data:
            date = item['date']
            province = item.get('province', 'Unknown')
            if not province or province.strip() == '':
                province = 'Unknown'
            day = date.day
            
            if day <= 10:
                dekad = 1
            elif day <= 20:
                dekad = 2
            else:
                dekad = 3
            
            period_key = f"{date.year}-{date.month:02d}-D{dekad}"
            key = f"{period_key}|{province}"
            groups[key].append(item)
        
        return dict(groups)
    
    def _group_monthly_by_province(self, data):
        """Group data by month and province."""
        groups = defaultdict(list)
        for item in data:
            date = item['date']
            province = item.get('province', 'Unknown')
            if not province or province.strip() == '':
                province = 'Unknown'
            period_key = f"{date.year}-{date.month:02d}"
            key = f"{period_key}|{province}"
            groups[key].append(item)
        
        return dict(groups)
    
    def _group_annual_by_province(self, data):
        """Group data by year and province."""
        groups = defaultdict(list)
        for item in data:
            date = item['date']
            province = item.get('province', 'Unknown')
            if not province or province.strip() == '':
                province = 'Unknown'
            period_key = str(date.year)
            key = f"{period_key}|{province}"
            groups[key].append(item)
        
        return dict(groups)
    
    def _group_seasonal_by_province(self, data, season_def=None, **kwargs):
        """
        Group data by season and province.
        
        For cross-year seasons (like ONDJFM, DJF), the season year is calculated
        based on the starting year of the season.
        """
        if not season_def:
            raise ValueError("Season definition required for seasonal aggregation")
        
        months = season_def.get('months', [])
        cross_year = season_def.get('cross_year', False)
        
        groups = defaultdict(list)
        
        for item in data:
            date = item['date']
            province = item.get('province', 'Unknown')
            if not province or province.strip() == '':
                province = 'Unknown'
            
            if date.month in months:
                if cross_year:
                    # For cross-year seasons (ONDJFM: Oct, Nov, Dec, Jan, Feb, Mar)
                    # The season year is the year of the starting month (Oct)
                    if date.month >= 10:  # Oct, Nov, Dec
                        season_year = date.year
                    else:  # Jan, Feb, Mar
                        season_year = date.year - 1
                else:
                    season_year = date.year
                
                period_key = str(season_year)
                key = f"{period_key}|{province}"
                groups[key].append(item)
        
        return dict(groups)
    
    def _parse_group_key(self, group_key):
        """Parse group key into period_key and province."""
        if '|' in group_key:
            parts = group_key.split('|')
            return parts[0], parts[1]
        return group_key, 'Unknown'
    
    def _get_period_metadata(self, period_key, period, **kwargs):
        """Get metadata for a specific period."""
        metadata = {
            'period': period,
            'period_key': period_key
        }
        
        if period == 'dekad':
            parts = period_key.split('-D')
            if len(parts) == 2:
                date_parts = parts[0].split('-')
                if len(date_parts) == 2:
                    year = int(date_parts[0])
                    month = int(date_parts[1])
                    dekad = int(parts[1])
                    
                    metadata['year'] = year
                    metadata['month'] = month
                    metadata['dekad'] = dekad
                    metadata['month_name'] = calendar.month_name[month]
                    
                    if dekad == 1:
                        start_day = 1
                        end_day = 10
                    elif dekad == 2:
                        start_day = 11
                        end_day = 20
                    else:
                        start_day = 21
                        end_day = calendar.monthrange(year, month)[1]
                    
                    metadata['start_date'] = f"{year}-{month:02d}-{start_day:02d}"
                    metadata['end_date'] = f"{year}-{month:02d}-{end_day:02d}"
        
        elif period == 'monthly':
            parts = period_key.split('-')
            if len(parts) == 2:
                year = int(parts[0])
                month = int(parts[1])
                metadata['year'] = year
                metadata['month'] = month
                metadata['month_name'] = calendar.month_name[month]
        
        elif period == 'annual':
            metadata['year'] = int(period_key)
        
        elif period == 'seasonal':
            try:
                metadata['year'] = int(period_key)
            except ValueError:
                metadata['year'] = period_key
        
        return metadata
    
    def _sum_values(self, values):
        """Sum all values - USE THIS FOR RAINFALL."""
        return sum(values) if values else 0
    
    def _mean_values(self, values):
        """Mean of values - USE THIS FOR NDVI/TEMPERATURE."""
        return round(sum(values) / len(values), 2) if values else 0
    
    def _median_values(self, values):
        return round(statistics.median(values), 2) if values else 0
    
    def _max_values(self, values):
        return max(values) if values else 0
    
    def _min_values(self, values):
        return min(values) if values else 0
    
    def _std_values(self, values):
        return round(statistics.stdev(values), 2) if len(values) > 1 else 0


# Singleton instance
aggregator = Aggregator()


def aggregate(data, period, aggregation_method='sum', **kwargs):
    """Convenience function to aggregate data."""
    return aggregator.aggregate(data, period, aggregation_method, **kwargs)