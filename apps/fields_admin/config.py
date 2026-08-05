# apps/fields_admin/config.py
"""
Global configuration settings for the Climate API.
"""

# Default Long-Term Average period
DEFAULT_LTA = (1991, 2020)

# Product configurations
PRODUCTS = {
    "rainfall": {
        "model": "RainfallProvince",  # Will be resolved to actual model
        "value_field": "rainfall_mm",
        "default_aggregation": "sum",
        "default_lta": (2000, 2025),
        "display_name": "Rainfall",
        "unit": "mm"
    },
    "ndvi": {
        "model": "NdviProvince",  # Assuming model name
        "value_field": "ndvi_value",
        "default_aggregation": "mean",
        "default_lta": (2018, 2025),
        "display_name": "NDVI",
        "unit": "index"
    },
    "temperature": {
        "model": "TemperatureProvince",  # Assuming model name
        "value_field": "temp_celsius",
        "default_aggregation": "mean",
        "default_lta": (2000, 2025),
        "display_name": "Temperature",
        "unit": "°C"
    }
}

# Aggregation methods
AGGREGATION_METHODS = {
    "sum": "SUM",
    "mean": "AVG",
    "median": "PERCENTILE_CONT(0.5)",
    "max": "MAX",
    "min": "MIN",
    "std": "STDDEV"
}

# Temporal aggregation periods
TEMPORAL_PERIODS = {
    "daily": {
        "label": "Daily",
        "group_by": ["year", "month", "day"]
    },
    "dekad": {
        "label": "Dekadal (10-day)",
        "group_by": ["year", "month", "dekad"]
    },
    "monthly": {
        "label": "Monthly",
        "group_by": ["year", "month"]
    },
    "annual": {
        "label": "Annual",
        "group_by": ["year"]
    }
}

# Season definitions
SEASON_DEFINITIONS = {
    'FULL': {
        'label': 'Full Year',
        'months': list(range(1, 13)),
        'months_abbr': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'description': 'January - December',
        'year_offset': 0,
        'cross_year': False
    },
    'OND': {
        'label': 'OND (Early Summer)',
        'months': [10, 11, 12],
        'months_abbr': ['Oct', 'Nov', 'Dec'],
        'description': 'October, November, December - Early summer / onset of rainy season',
        'year_offset': 0,
        'cross_year': False
    },
    'NDJ': {
        'label': 'NDJ (Mid-Summer)',
        'months': [11, 12, 1],
        'months_abbr': ['Nov', 'Dec', 'Jan'],
        'description': 'November, December, January - Mid-summer transition',
        'year_offset': 1,
        'cross_year': True
    },
    'DJF': {
        'label': 'DJF (Peak Summer)',
        'months': [12, 1, 2],
        'months_abbr': ['Dec', 'Jan', 'Feb'],
        'description': 'December, January, February - Peak summer rainy season',
        'year_offset': 1,
        'cross_year': True
    },
    'JFM': {
        'label': 'JFM (Late Summer)',
        'months': [1, 2, 3],
        'months_abbr': ['Jan', 'Feb', 'Mar'],
        'description': 'January, February, March - Late summer / peak tropical cyclone season',
        'year_offset': 0,
        'cross_year': False
    },
    'FMA': {
        'label': 'FMA (End of Summer)',
        'months': [2, 3, 4],
        'months_abbr': ['Feb', 'Mar', 'Apr'],
        'description': 'February, March, April - End of summer / tail-end of rains',
        'year_offset': 0,
        'cross_year': False
    },
    'ONDJFM': {
        'label': 'ONDJFM (Rainy Season)',
        'months': [10, 11, 12, 1, 2, 3],
        'months_abbr': ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
        'description': 'October, November, December, January, February, March - Full rainy season (cross-year)',
        'year_offset': 1,
        'cross_year': True
    }
}

# Available derived metrics
METRICS = {
    "anomaly": {
        "module": "metrics.anomaly",
        "function": "calculate_anomaly",
        "label": "Anomaly",
        "description": "Observed - LTA"
    },
    "pct_average": {
        "module": "metrics.percent_average",
        "function": "calculate_percent_average",
        "label": "Percentage of Average",
        "description": "(Observed / LTA) * 100"
    },
    "zscore": {
        "module": "metrics.zscore",
        "function": "calculate_zscore",
        "label": "Z-Score",
        "description": "Standardized anomaly"
    },
    "spi": {
        "module": "metrics.spi",
        "function": "calculate_spi",
        "label": "SPI",
        "description": "Standardized Precipitation Index"
    },
    "vci": {
        "module": "metrics.vci",
        "function": "calculate_vci",
        "label": "VCI",
        "description": "Vegetation Condition Index"
    },
    "tci": {
        "module": "metrics.tci",
        "function": "calculate_tci",
        "label": "TCI",
        "description": "Temperature Condition Index"
    },
    "vhi": {
        "module": "metrics.vhi",
        "function": "calculate_vhi",
        "label": "VHI",
        "description": "Vegetation Health Index"
    }
}