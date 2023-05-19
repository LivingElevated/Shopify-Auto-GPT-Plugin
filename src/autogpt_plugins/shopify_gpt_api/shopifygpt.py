import shopify
import os
from shopify.version import VERSION
from shopify.session import Session, ValidationException
from shopify.resources import *
from shopify.limits import Limits
from shopify.api_version import *
from shopify.api_access import *
from shopify.collection import PaginatedIterator
from . import ShopifyAutoGPT
from auto_gpt_plugin_template import AutoGPTPluginTemplate
from typing import Any, Dict, List, Optional, Tuple, TypeVar, TypedDict


plugin = ShopifyAutoGPT()


def create_product(title: str, description: Optional[str] = None) -> shopify.Product:
    """Create a new product on Shopify.

    Args:
        title (str): Title of the product.
        description (Optional[str], optional): Description of the product. If None, an AI-generated description will be used. Defaults to None.

    Returns:
        shopify.Product: The newly created product.
    """
    product = shopify.Product()
    product.title = title

    if not description:
        prompt = f"Write a captivating product description for a {title}."
        description = plugin.chatgpt_response(prompt)

    product.body_html = description
    product.save()

    return product


def get_product(product_id: str) -> shopify.Product:
    """Fetch a product from Shopify.

    Args:
        product_id (str): The ID of the product to fetch.

    Returns:
        shopify.Product: The requested product.
    """
    return shopify.Product.find(product_id)


def get_all_products() -> List[Any]:
    """Fetch all products from Shopify.

    Returns:
        List[Any]: List of all products.
    """
    return shopify.Product.find()


def update_product(self, product_id, title=None, description=None):
    product = self.get_product(product_id)

    if title:
        product.title = title

    if description:
        product.body_html = description

    product.save()
    return product

def delete_product(self, product_id):
    product = self.get_product(product_id)
    product.destroy()

#Create a collection
def create_collection(self, title, collection_type="custom"):
    if collection_type == "custom":
        collection = shopify.CustomCollection()
    elif collection_type == "smart":
        collection = shopify.SmartCollection()
    else:
        raise ValueError("Invalid collection type. Must be 'custom' or 'smart'.")

    collection.title = title
    collection.save()
    return collection

#Add a product to a collection:
def add_product_to_collection(self, product_id, collection_id):
    collect = shopify.Collect()
    collect.product_id = product_id
    collect.collection_id = collection_id
    collect.save()
    return collect

#Get all collections
def get_all_collections(self, collection_type=None):
    if collection_type == "custom":
        return shopify.CustomCollection.find()
    elif collection_type == "smart":
        return shopify.SmartCollection.find()
    elif collection_type is None:
        custom_collections = shopify.CustomCollection.find()
        smart_collections = shopify.SmartCollection.find()
        return custom_collections + smart_collections
    else:
        raise ValueError("Invalid collection type. Must be 'custom', 'smart', or None.")

#Update a collection
def update_collection(self, collection_id, title=None, collection_type=None):
    if collection_type == "custom" or collection_type is None:
        collection = shopify.CustomCollection.find(collection_id)
    elif collection_type == "smart":
        collection = shopify.SmartCollection.find(collection_id)
    else:
        raise ValueError("Invalid collection type. Must be 'custom', 'smart', or None.")

    if title:
        collection.title = title

    collection.save()
    return collection

#Delete a collection
def delete_collection(self, collection_id, collection_type=None):
    if collection_type == "custom" or collection_type is None:
        collection = shopify.CustomCollection.find(collection_id)
    elif collection_type == "smart":
        collection = shopify.SmartCollection.find(collection_id)
    else:
        raise ValueError("Invalid collection type. Must be 'custom', 'smart', or None.")

    collection.destroy()

#Search products by title:
def search_products_by_title(self, title):
    return shopify.Product.find(title=title)

#Get all themes:
def get_all_themes(self):
    return shopify.Theme.find()

#Get the active theme:
def get_active_theme(self):
    themes = self.get_all_themes()
    active_theme = [theme for theme in themes if theme.role == "main"]
    return active_theme[0] if active_theme else None

#Get theme assets:
def get_theme_assets(self, theme_id):
    return shopify.Asset.find(theme_id=theme_id)

#Get a specific theme asset:
def get_theme_asset(self, theme_id, asset_key):
    return shopify.Asset.find(asset_key, theme_id=theme_id)

#Update a theme asset:
def update_theme_asset(self, theme_id, asset_key, new_asset_value):
    asset = self.get_theme_asset(theme_id, asset_key)
    asset.value = new_asset_value
    asset.save()
    return asset

#Delete a theme asset:
def delete_theme_asset(self, theme_id, asset_key):
    asset = self.get_theme_asset(theme_id, asset_key)
    asset.destroy()
