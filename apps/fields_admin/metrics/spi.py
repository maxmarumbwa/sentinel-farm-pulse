# fields_admin/metrics/spi.py
"""
SPI (Standardized Precipitation Index) metric calculation.
Placeholder - to be implemented later.
"""


def calculate_spi(observed, lta, **kwargs):
    """
    Calculate SPI.
    
    This is a placeholder implementation.
    Full implementation would involve gamma distribution fitting.
    
    Args:
        observed: Observed value
        lta: Long-Term Average
    
    Returns:
        SPI value
    """
    # TODO: Implement SPI calculation
    # Need to fit gamma distribution to historical data
    # Then transform to standard normal distribution
    return None


def apply_spi_to_data(data):
    """
    Apply SPI calculation to a dataset.
    
    Args:
        data: List of data points
    
    Returns:
        Data with spi added
    """
    # TODO: Implement SPI calculation
    result = []
    for item in data:
        item_copy = item.copy()
        item_copy['spi'] = calculate_spi(
            item.get('value'),
            item.get('lta')
        )
        result.append(item_copy)
    
    return result