# fields_admin/metrics/tci.py
"""
TCI (Temperature Condition Index) metric calculation.
"""


def calculate_tci(temp, temp_min, temp_max, **kwargs):
    """
    Calculate TCI.
    
    Args:
        temp: Current temperature
        temp_min: Minimum temperature
        temp_max: Maximum temperature
    
    Returns:
        TCI value (0-100)
    """
    if temp is None or temp_min is None or temp_max is None:
        return None
    
    if temp_max == temp_min:
        return None
    
    tci = ((temp_max - temp) / (temp_max - temp_min)) * 100
    return round(tci, 2)


def apply_tci_to_data(data):
    """
    Apply TCI calculation to a dataset.
    
    Args:
        data: List of data points with 'temp', 'temp_min', 'temp_max'
    
    Returns:
        Data with tci added
    """
    result = []
    for item in data:
        item_copy = item.copy()
        item_copy['tci'] = calculate_tci(
            item.get('temp'),
            item.get('temp_min'),
            item.get('temp_max')
        )
        result.append(item_copy)
    
    return result