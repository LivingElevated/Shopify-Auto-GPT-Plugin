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
from typing import Union, Any, Dict, List, Optional, Tuple, TypeVar, TypedDict


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

#Search products by title:

def search_products_by_title(title: str) -> List[shopify.Product]:
    """Search products by title in Shopify.

    Args:
        title (str): Title of the products to search for.

    Returns:
        List[shopify.Product]: List of products that match the title.
    """
    return shopify.Product.find(title=title)

def update_product(product_id: str, title: Optional[str] = None, description: Optional[str] = None) -> shopify.Product:
    """Update a product on Shopify.

    Args:
        product_id (str): The ID of the product to update.
        title (Optional[str], optional): The new title of the product. Defaults to None.
        description (Optional[str], optional): The new description of the product. Defaults to None.

    Returns:
        shopify.Product: The updated product.
    """
    product = get_product(product_id)

    if title:
        product.title = title

    if description:
        product.body_html = description

    product.save()
    return product

def delete_product(product_id: str) -> None:
    """Delete a product from Shopify.

    Args:
        product_id (str): The ID of the product to delete.
    """
    product = get_product(product_id)
    product.destroy()


#Create a collection
def create_collection(title: str, collection_type: str = "custom") -> Union[shopify.CustomCollection, shopify.SmartCollection]:
    """Create a new collection on Shopify.

    Args:
        title (str): The title of the new collection.
        collection_type (str, optional): The type of the collection. Can be either 'custom' or 'smart'. Defaults to "custom".

    Returns:
        Union[shopify.CustomCollection, shopify.SmartCollection]: The newly created collection.
    """
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
def add_product_to_collection(product_id: int, collection_id: int) -> shopify.Collect:
    """Add a product to a collection.

    Args:
        product_id (int): The ID of the product to add.
        collection_id (int): The ID of the collection.

    Returns:
        shopify.Collect: The created Collect object.
    """
    collect = shopify.Collect()
    collect.product_id = product_id
    collect.collection_id = collection_id
    collect.save()
    return collect

#Get all collections
def get_all_collections(collection_type: Optional[str] = None) -> Union[List[shopify.CustomCollection], List[shopify.SmartCollection], List[Union[shopify.CustomCollection, shopify.SmartCollection]]]:
    """Fetch all collections of a specified type.

    Args:
        collection_type (str, optional): The type of the collection. 
            It must be 'custom', 'smart', or None. Defaults to None.

    Returns:
        Union[List[shopify.CustomCollection], List[shopify.SmartCollection], List[Union[shopify.CustomCollection, shopify.SmartCollection]]]:
            The collections of the specified type.
    """
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
def update_collection(collection_id: int, title: Optional[str] = None, collection_type: Optional[str] = None) -> Union[shopify.CustomCollection, shopify.SmartCollection]:
    """Update a collection.

    Args:
        collection_id (int): The ID of the collection.
        title (str, optional): The new title of the collection. Defaults to None.
        collection_type (str, optional): The type of the collection. 
            It must be 'custom', 'smart', or None. Defaults to None.

    Returns:
        Union[shopify.CustomCollection, shopify.SmartCollection]: The updated collection.
    """
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
def delete_collection(collection_id: int, collection_type: Optional[str] = None) -> None:
    """Delete a collection.

    Args:
        collection_id (int): The ID of the collection.
        collection_type (str, optional): The type of the collection. 
            It must be 'custom', 'smart', or None. Defaults to None.
    """
    if collection_type == "custom" or collection_type is None:
        collection = shopify.CustomCollection.find(collection_id)
    elif collection_type == "smart":
        collection = shopify.SmartCollection.find(collection_id)
    else:
        raise ValueError("Invalid collection type. Must be 'custom', 'smart', or None.")
    
    collection.destroy()

#Get all themes:
def get_all_themes() -> List[shopify.Theme]:
    """Fetch all themes.

    Returns:
        List[shopify.Theme]: List of all themes.
    """
    return shopify.Theme.find()

#Get the active theme:
def get_active_theme() -> Optional[shopify.Theme]:
    """Fetch the active theme.

    Returns:
        Optional[shopify.Theme]: The active theme, if any.
    """
    themes = get_all_themes()
    active_theme = [theme for theme in themes if theme.role == "main"]
    return active_theme[0] if active_theme else None

#Get theme assets:
def get_theme_assets(theme_id: int) -> List[shopify.Asset]:
    """Fetch all assets of a theme.

    Args:
        theme_id (int): The ID of the theme.

    Returns:
        List[shopify.Asset]: List of all assets of the theme.
    """
    return shopify.Asset.find(theme_id=theme_id)


#Get a specific theme asset:
def get_theme_asset(theme_id: int, asset_key: str) -> shopify.Asset:
    """Fetch a specific asset of a theme.

    Args:
        theme_id (int): The ID of the theme.
        asset_key (str): The key of the asset.

    Returns:
        shopify.Asset: The specified asset.
    """
    return shopify.Asset.find(asset_key, theme_id=theme_id)

#Update a theme asset:
def update_theme_asset(theme_id: int, asset_key: str, new_asset_value: str) -> shopify.Asset:
    """Update a theme asset.

    Args:
        theme_id (int): The ID of the theme.
        asset_key (str): The key of the asset.
        new_asset_value (str): The new value of the asset.

    Returns:
        shopify.Asset: The updated asset.
    """
    asset = get_theme_asset(theme_id, asset_key)
    asset.value = new_asset_value
    asset.save()
    return asset

#Delete a theme asset:
def delete_theme_asset(theme_id: int, asset_key: str) -> None:
    """Delete a theme asset.

    Args:
        theme_id (int): The ID of the theme.
        asset_key (str): The key of the asset.
    """
    asset = get_theme_asset(theme_id, asset_key)
    asset.destroy()

