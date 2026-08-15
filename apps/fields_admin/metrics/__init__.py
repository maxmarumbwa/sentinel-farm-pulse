# apps/fields_admin/metrics/__init__.py
"""
Metrics module for climate data analysis.
"""

from .anomaly import apply_anomaly_to_data
from .percent_average import apply_percent_average_to_data
# from .zscore import apply_zscore_to_data
# from .spi import apply_spi_to_data
# from .vci import apply_vci_to_data
# from .tci import apply_tci_to_data
# from .vhi import apply_vhi_to_data

__all__ = [
    'apply_anomaly_to_data',
    'apply_percent_average_to_data',
    # 'apply_zscore_to_data',
    # 'apply_spi_to_data',
    # 'apply_vci_to_data',
    # 'apply_tci_to_data',
    # 'apply_vhi_to_data',
]