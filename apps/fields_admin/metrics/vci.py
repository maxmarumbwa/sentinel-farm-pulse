# fields_admin/metrics/vci.py
"""
VCI (Vegetation Condition Index) metric calculation.
"""


def calculate_vci(ndvi, ndvi_min, ndvi_max, **kwargs):
    """
    Calculate VCI.
    
    Args:
        ndvi: Current NDVI value
        ndvi_min: Minimum NDVI value
        ndvi_max: Maximum NDVI value
    
    Returns:
        VCI value (0-100)
    """
    if ndvi is None or ndvi_min is None or ndvi_max is None:
        return None
    
    if ndvi_max == ndvi_min:
        return None
    
    vci = ((ndvi - ndvi_min) / (ndvi_max - ndvi_min)) * 100
    return round(vci, 2)


def apply_vci_to_data(data):
    """
    Apply VCI calculation to a dataset.
    
    Args:
        data: List of data points with 'ndvi', 'ndvi_min', 'ndvi_max'
    
    Returns:
        Data with vci added
    """
    result = []
    for item in data:
        item_copy = item.copy()
        item_copy['vci'] = calculate_vci(
            item.get('ndvi'),
            item.get('ndvi_min'),
            item.get('ndvi_max')
        )
        result.append(item_copy)
    
    return result