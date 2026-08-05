# fields_admin/metrics/zscore.py
"""
Z-Score metric calculation.
"""

import statistics


def calculate_zscore(value, mean, std_dev, **kwargs):
    """
    Calculate Z-Score.
    
    Args:
        value: Value to standardize
        mean: Mean of the distribution
        std_dev: Standard deviation of the distribution
    
    Returns:
        Z-Score
    """
    if value is None or mean is None or std_dev is None:
        return None
    
    if std_dev == 0:
        return None
    
    return round((value - mean) / std_dev, 2)


def calculate_zscore_from_lta(value, lta_values):
    """
    Calculate Z-Score using LTA values.
    
    Args:
        value: Value to standardize
        lta_values: List of values used for LTA
    
    Returns:
        Z-Score
    """
    if not lta_values or len(lta_values) < 2:
        return None
    
    mean = statistics.mean(lta_values)
    std_dev = statistics.stdev(lta_values)
    
    return calculate_zscore(value, mean, std_dev)


def apply_zscore_to_data(data, lta_values_by_period):
    """
    Apply Z-Score calculation to a dataset.
    
    Args:
        data: List of data points with 'value' and 'period_key'
        lta_values_by_period: Dict mapping period_key to list of LTA values
    
    Returns:
        Data with zscore added
    """
    result = []
    for item in data:
        item_copy = item.copy()
        period_key = item.get('period_key', '')
        lta_values = lta_values_by_period.get(period_key, [])
        
        item_copy['zscore'] = calculate_zscore_from_lta(
            item.get('value'),
            lta_values
        )
        result.append(item_copy)
    
    return result