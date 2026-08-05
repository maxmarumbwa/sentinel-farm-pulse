# fields_admin/metrics/vhi.py
"""
VHI (Vegetation Health Index) metric calculation.
"""


def calculate_vhi(vci, tci, **kwargs):
    """
    Calculate VHI.
    
    Args:
        vci: Vegetation Condition Index
        tci: Temperature Condition Index
    
    Returns:
        VHI value (0-100)
    """
    if vci is None or tci is None:
        return None
    
    vhi = (vci + tci) / 2
    return round(vhi, 2)


def apply_vhi_to_data(data):
    """
    Apply VHI calculation to a dataset.
    
    Args:
        data: List of data points with 'vci' and 'tci'
    
    Returns:
        Data with vhi added
    """
    result = []
    for item in data:
        item_copy = item.copy()
        item_copy['vhi'] = calculate_vhi(
            item.get('vci'),
            item.get('tci')
        )
        result.append(item_copy)
    
    return result