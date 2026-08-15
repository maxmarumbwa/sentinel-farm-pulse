# # apps/fields_admin/metrics/zscore.py
# """
# Z-Score metric calculation.

# Z-Score = (observed - mean) / standard_deviation

# Where:
# - mean = LTA (Long-Term Average) calculated from historical data
# - standard_deviation = calculated from the same historical data used for LTA

# Interpretation:
# - Z-Score = 0: Value equals the average
# - Z-Score > 0: Value is above average (positive anomaly)
# - Z-Score < 0: Value is below average (negative anomaly)
# - |Z-Score| > 2: Statistically significant anomaly

# The standard deviation is calculated from the historical values used to compute the LTA.
# """

# import math
# import statistics
# import logging

# logger = logging.getLogger(__name__)


# def calculate_zscore(observed, mean, std_dev, **kwargs):
#     """
#     Calculate Z-Score (observed - mean) / std_dev.
    
#     Args:
#         observed: Observed value
#         mean: Mean of the distribution (LTA)
#         std_dev: Standard deviation of the distribution
    
#     Returns:
#         Z-Score value rounded to 2 decimal places, or None if invalid
#     """
#     if observed is None or mean is None or std_dev is None:
#         return None
    
#     if std_dev == 0:
#         # If standard deviation is 0, all values are identical
#         return 0 if observed == mean else None
    
#     zscore = (observed - mean) / std_dev
#     return round(zscore, 2)


# def calculate_std_dev_from_values(values):
#     """
#     Calculate standard deviation from a list of values.
    
#     Uses population standard deviation (ddof=0) for consistency with climate data.
    
#     Args:
#         values: List of numerical values
    
#     Returns:
#         Standard deviation rounded to 2 decimal places, or None if insufficient data
#     """
#     if not values or len(values) < 2:
#         return None
    
#     try:
#         # Use population standard deviation (ddof=0)
#         # For sample standard deviation use ddof=1
#         std_dev = statistics.stdev(values) if len(values) > 1 else 0
#         return round(std_dev, 2)
#     except Exception as e:
#         logger.error(f"Error calculating standard deviation: {str(e)}")
#         return None


# def calculate_mean_from_values(values):
#     """
#     Calculate mean from a list of values.
    
#     Args:
#         values: List of numerical values
    
#     Returns:
#         Mean rounded to 2 decimal places, or None if no values
#     """
#     if not values:
#         return None
    
#     try:
#         mean = statistics.mean(values)
#         return round(mean, 2)
#     except Exception as e:
#         logger.error(f"Error calculating mean: {str(e)}")
#         return None


# def apply_zscore_to_data(data):
#     """
#     Apply Z-Score calculation to a dataset.
    
#     This function:
#     1. Groups data by period_key and province
#     2. Collects all values for each group
#     3. Calculates mean and standard deviation for each group
#     4. Computes Z-Score for each item: (value - mean) / std_dev
    
#     Args:
#         data: List of data points with 'period_key', 'province', and 'value' fields
    
#     Returns:
#         Data with zscore added
#     """
#     if not data:
#         return data
    
#     logger.info(f"Calculating Z-Score for {len(data)} records")
    
#     # ============================================================
#     # STEP 1: Group data by period_key and province
#     # ============================================================
#     groups = {}
#     group_items = {}
    
#     for idx, item in enumerate(data):
#         period_key = item.get('period_key', 'unknown')
#         province = item.get('province', 'Unknown')
#         group_key = f"{period_key}|{province}"
        
#         # Store item index
#         if group_key not in group_items:
#             group_items[group_key] = []
#         group_items[group_key].append(idx)
        
#         # Store value for statistical calculation
#         value = item.get('value')
#         if value is not None:
#             if group_key not in groups:
#                 groups[group_key] = []
#             groups[group_key].append(value)
    
#     logger.info(f"Created {len(groups)} groups for Z-Score calculation")
    
#     # ============================================================
#     # STEP 2: Calculate statistics for each group
#     # ============================================================
#     group_stats = {}
    
#     for group_key, values in groups.items():
#         if len(values) >= 2:
#             # Calculate mean and standard deviation
#             mean = calculate_mean_from_values(values)
#             std_dev = calculate_std_dev_from_values(values)
            
#             group_stats[group_key] = {
#                 'mean': mean,
#                 'std_dev': std_dev,
#                 'count': len(values),
#                 'values': values  # Keep for reference
#             }
            
#             logger.debug(f"Group {group_key}: mean={mean}, std_dev={std_dev}, count={len(values)}")
#         else:
#             logger.debug(f"Group {group_key}: insufficient data for Z-Score (only {len(values)} values)")
#             group_stats[group_key] = {
#                 'mean': None,
#                 'std_dev': None,
#                 'count': len(values),
#                 'values': values
#             }
    
#     # ============================================================
#     # STEP 3: Apply Z-Score to each item
#     # ============================================================
#     result = []
#     zscore_count = 0
    
#     for idx, item in enumerate(data):
#         item_copy = item.copy()
        
#         period_key = item.get('period_key', 'unknown')
#         province = item.get('province', 'Unknown')
#         group_key = f"{period_key}|{province}"
        
#         observed = item.get('value')
#         stats = group_stats.get(group_key, {})
        
#         mean = stats.get('mean')
#         std_dev = stats.get('std_dev')
        
#         # Calculate Z-Score
#         if observed is not None and mean is not None and std_dev is not None and std_dev != 0:
#             zscore = (observed - mean) / std_dev
#             item_copy['zscore'] = round(zscore, 2)
#             zscore_count += 1
#         else:
#             item_copy['zscore'] = None
        
#         # Add statistics for reference
#         item_copy['std_dev'] = std_dev
#         item_copy['group_mean'] = mean
#         item_copy['group_count'] = stats.get('count', 0)
        
#         result.append(item_copy)
    
#     logger.info(f"Z-Score calculated for {zscore_count} out of {len(result)} records")
    
#     return result


# def apply_zscore_by_period(data):
#     """
#     Apply Z-Score calculation grouping only by period (not by province).
    
#     This is useful when you want to calculate Z-Scores across all provinces
#     for a given period.
    
#     Args:
#         data: List of data points with 'period_key' and 'value' fields
    
#     Returns:
#         Data with zscore added
#     """
#     if not data:
#         return data
    
#     # Group by period_key only
#     groups = {}
#     group_items = {}
    
#     for idx, item in enumerate(data):
#         period_key = item.get('period_key', 'unknown')
        
#         if period_key not in group_items:
#             group_items[period_key] = []
#         group_items[period_key].append(idx)
        
#         value = item.get('value')
#         if value is not None:
#             if period_key not in groups:
#                 groups[period_key] = []
#             groups[period_key].append(value)
    
#     # Calculate statistics and apply Z-Score
#     result = []
#     zscore_count = 0
    
#     for period_key, values in groups.items():
#         if len(values) >= 2:
#             mean = calculate_mean_from_values(values)
#             std_dev = calculate_std_dev_from_values(values)
#         else:
#             mean = None
#             std_dev = None
        
#         for idx in group_items.get(period_key, []):
#             item = data[idx]
#             item_copy = item.copy()
            
#             observed = item.get('value')
            
#             if observed is not None and mean is not None and std_dev is not None and std_dev != 0:
#                 zscore = (observed - mean) / std_dev
#                 item_copy['zscore'] = round(zscore, 2)
#                 zscore_count += 1
#             else:
#                 item_copy['zscore'] = None
            
#             item_copy['std_dev'] = std_dev
#             item_copy['group_mean'] = mean
#             item_copy['group_count'] = len(values) if values else 0
            
#             result.append(item_copy)
    
#     logger.info(f"Z-Score calculated for {zscore_count} out of {len(result)} records (by period only)")
    
#     return result


# def calculate_zscore_with_lta_and_values(observed, historical_values, lta=None):
#     """
#     Calculate Z-Score using historical values for standard deviation.
    
#     This is the most accurate method when you have the historical values.
    
#     Args:
#         observed: Observed value
#         historical_values: List of historical values for the same period
#         lta: Optional pre-calculated LTA (if not provided, calculated from historical_values)
    
#     Returns:
#         Z-Score value rounded to 2 decimal places, or None if invalid
#     """
#     if not historical_values or len(historical_values) < 2:
#         return None
    
#     # Calculate mean from historical values
#     if lta is None:
#         mean = calculate_mean_from_values(historical_values)
#     else:
#         mean = lta
    
#     # Calculate standard deviation from historical values
#     std_dev = calculate_std_dev_from_values(historical_values)
    
#     if mean is None or std_dev is None or std_dev == 0:
#         return None
    
#     return calculate_zscore(observed, mean, std_dev)


# # ============================================================
# # Enhanced version for views.py that uses LTA period data
# # ============================================================

# def apply_zscore_with_lta_data(data, lta_historical_values=None):
#     """
#     Apply Z-Score using LTA historical values for standard deviation.
    
#     This function expects historical values grouped by period_key and province.
    
#     Args:
#         data: List of data points with 'period_key', 'province', 'value'
#         lta_historical_values: Dict mapping period_key|province to list of historical values
    
#     Returns:
#         Data with zscore added
#     """
#     if not data:
#         return data
    
#     result = []
#     zscore_count = 0
    
#     for item in data:
#         item_copy = item.copy()
        
#         period_key = item.get('period_key', 'unknown')
#         province = item.get('province', 'Unknown')
#         group_key = f"{period_key}|{province}"
        
#         observed = item.get('value')
#         lta = item.get('lta')
        
#         # Get historical values for this group
#         historical_values = None
#         if lta_historical_values:
#             historical_values = lta_historical_values.get(group_key)
        
#         # Calculate Z-Score
#         if historical_values and len(historical_values) >= 2:
#             # Use historical values for accurate std_dev
#             std_dev = calculate_std_dev_from_values(historical_values)
#             mean = lta if lta is not None else calculate_mean_from_values(historical_values)
            
#             if mean is not None and std_dev is not None and std_dev != 0:
#                 zscore = (observed - mean) / std_dev
#                 item_copy['zscore'] = round(zscore, 2)
#                 zscore_count += 1
#             else:
#                 item_copy['zscore'] = None
#         else:
#             # Fallback: Use values from the data itself
#             # Group by period_key and province to calculate std_dev
#             item_copy['zscore'] = None
        
#         result.append(item_copy)
    
#     logger.info(f"Z-Score calculated for {zscore_count} out of {len(result)} records")
    
#     return result