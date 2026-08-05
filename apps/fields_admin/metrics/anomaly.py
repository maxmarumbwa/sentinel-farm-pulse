# fields_admin/metrics/anomaly.py
"""
Anomaly metric calculation.
"""


def calculate_anomaly(observed, lta, **kwargs):
    """
    Calculate anomaly (observed - LTA).
    
    Args:
        observed: Observed value
        lta: Long-Term Average
    
    Returns:
        Anomaly value
    """
    if observed is None or lta is None:
        return None
    
    return round(observed - lta, 2)


def apply_anomaly_to_data(data):
    """
    Apply anomaly calculation to a dataset.
    
    Args:
        data: List of data points with 'value' and 'lta' fields
    
    Returns:
        Data with anomaly added
    """
    result = []
    for item in data:
        item_copy = item.copy()
        item_copy['anomaly'] = calculate_anomaly(
            item.get('value'),
            item.get('lta')
        )
        result.append(item_copy)
    
    return result