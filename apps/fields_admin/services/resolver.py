# apps/fields_admin/services/resolver.py
"""
Product resolver - maps product names to their corresponding models.
"""

from django.apps import apps
from apps.fields_admin.config import PRODUCTS


class ProductResolver:
    """
    Resolves product names to Django models.
    """
    
    def __init__(self):
        self.products = PRODUCTS
    
    def resolve_product(self, product_name):
        """
        Resolve a single product to its model.
        
        Args:
            product_name: String product name (e.g., 'rainfall', 'ndvi')
            
        Returns:
            Django model class or None if not found
        """
        if product_name not in self.products:
            return None
        
        product_config = self.products[product_name]
        model_name = product_config.get('model')
        
        if not model_name:
            return None
        
        try:
            # Try to get the model from the app registry
            # Assuming models are in the current app
            model = apps.get_model('fields_admin', model_name)
            return model
        except LookupError:
            # Try to get from the fields_admin app
            try:
                model = apps.get_model('fields_admin', model_name)
                return model
            except LookupError:
                return None
    
    def resolve_products(self, product_name):
        """
        Resolve product(s) to their models.
        
        Args:
            product_name: String product name or 'all'
            
        Returns:
            List of model classes or None if invalid
        """
        if product_name == 'all':
            # Return all products
            models = []
            for product_key in self.products:
                model = self.resolve_product(product_key)
                if model:
                    models.append({
                        'product': product_key,
                        'model': model,
                        'config': self.products[product_key]
                    })
            return models if models else None
        
        # Single product
        model = self.resolve_product(product_name)
        if model:
            return [{
                'product': product_name,
                'model': model,
                'config': self.products[product_name]
            }]
        
        return None
    
    def get_product_config(self, product_name):
        """
        Get configuration for a product.
        
        Args:
            product_name: String product name
            
        Returns:
            Product configuration dict or None
        """
        return self.products.get(product_name)


# Singleton instance
resolver = ProductResolver()


def resolve_product(product_name):
    """
    Convenience function to resolve a product.
    
    Args:
        product_name: String product name or 'all'
        
    Returns:
        List of product model configs
    """
    return resolver.resolve_products(product_name)