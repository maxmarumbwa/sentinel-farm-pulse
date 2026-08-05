# fields_admin/metrics/percent_average.py
"""
Percentage of Average metric calculation.
"""


def calculate_percent_average(observed, lta, **kwargs):
    """
    Calculate percentage of average.
    
    Args:
        observed: Observed value
        lta: Long-Term Average
    
    Returns:
        Percentage of average (observed/lta * 100)
    """
    if observed is None or lta is None:
        return None
    
    if lta == 0:
        return None
    
    return round((observed / lta) * 100, 1)


def apply_percent_average_to_data(data):
    """
    Apply percentage average calculation to a dataset.
    
    Args:
        data: List of data points with 'value' and 'lta' fields
    
    Returns:
        Data with pct_average added
    """
    result = []
    for item in data:
        item_copy = item.copy()
        item_copy['pct_average'] = calculate_percent_average(
            item.get('value'),
            item.get('lta')
        )
        result.append(item_copy)
    
    return result