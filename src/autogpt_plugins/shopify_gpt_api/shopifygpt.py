import shopify
import os
from collections import defaultdict
from datetime import datetime, timedelta
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

def get_product(product_identifier: Union[str, int]) -> Union[shopify.Product, None]:
    """Fetch a product from Shopify using either its ID or its title.

    Args:
        product_identifier (Union[str, int]): The ID or the title of the product to fetch.

    Returns:
        Union[shopify.Product, None]: The requested product if found, or None otherwise.
    """
    # If the identifier is numeric, it's treated as an ID.
    if str(product_identifier).isdigit():
        return shopify.Product.find(int(product_identifier))

    # If not, it's treated as a title.
    else:
        all_products = shopify.Product.find()
        for product in all_products:
            if product.title == product_identifier:
                return product
    
    # Return None if no matching product was found.
    return None

def get_all_products() -> List[Tuple[int, str]]:
    """Fetch all products from Shopify and return their IDs and names.

    Returns:
        List[Tuple[int, str]]: List of all products represented as tuples (id, name).
    """
    products = shopify.Product.find()
    product_info = [(product.id, product.title) for product in products]
    return product_info

def get_all_product_names():
    """Fetch all product names from Shopify.

    Returns:
        List[Any]: List of all products by name.
    """
    products = get_all_products()
    product_names = [product.title for product in products]
    return product_names

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

def get_all_orders() -> List[Dict[str, Any]]:
    """Fetch all orders from Shopify and return insights."""

    orders = shopify.Order.find()  # Fetch all orders
    all_orders = []

    for order in orders:
        order_details = {
            "order_id": order.id,
            "order_date": order.created_at,
            "customer": order.customer.id if order.customer else None,
            "line_items": [{
                "product_id": item.product_id,
                "product_name": shopify.Product.find(item.product_id).title if item.product_id else None,
                "quantity": item.quantity,
                "price": item.price
            } for item in order.line_items],
            "total_price": order.total_price,
        }
        all_orders.append(order_details)

    return all_orders

def analyze_sales() -> Dict[str, Any]:
    """Analyze sales data and return insights."""

    # Get all orders and total sales
    orders = shopify.Order.find(status="any")
    total_sales = sum(order.total_price for order in orders)

    # Initialize defaultdict to count sales per product
    product_sales = defaultdict(int)

    for order in orders:
        for line_item in order.line_items:
            product_sales[line_item.title] += line_item.price * line_item.quantity

    # Calculate the percentage contribution of each product to total sales
    product_percentage_contribution = {product: str(round((sales / total_sales) * 100, 2)) + '%' for product, sales in product_sales.items()}
    for product, sales in product_sales.items():
        percentage = round((sales / total_sales) * 100, 2)  # round to 2 decimal places
        product_percentage_contribution[product] = f"{percentage}%"

    # Find out the slow-moving products
    slow_moving_products = []
    all_products = shopify.Product.find()
    for product in all_products:
        if product.title not in product_sales or product_sales[product.title] / total_sales * 100 <= 5:
            slow_moving_products.append(product.title)

    return {
        "total_sales": f"${total_sales:.2f}",
        "product_sales": {product: f"${sales:.2f}" for product, sales in product_sales.items()},
        "product_percentage_contribution": product_percentage_contribution,
        "slow_moving_products": slow_moving_products,
    }


def analyze_customer_behavior() -> Dict[str, Any]:
    """Analyze customer behavior data and return insights."""

    customers = shopify.Customer.find()  # Fetch all customers
    customer_behavior = []

    all_orders = shopify.Order.find()  # Fetch all orders
    order_dict = defaultdict(list)

    for order in all_orders:
        order_dict[order.customer.id].append(order)

    for customer in customers:
        orders = order_dict.get(customer.id)

        if orders:
            total_spent_customer = 0  # Total amount spent by the customer
            total_orders = len(orders)  # Total number of orders by the customer
            order_details_list = []  # List to store details of each order

            for order in orders:
                total_spent_order = 0  # Total amount spent in this order
                categories = []  # List to store the categories of products in this order

                for line_item in order.line_items:
                    total_spent_order += line_item.price
                    product = shopify.Product.find(line_item.product_id)

                    if product and product.product_type not in categories:
                        categories.append(product.product_type)

                order_details = {
                    'order_id': order.id,
                    'date': order.created_at,
                    'categories': categories,
                    'total_spent': total_spent_order
                }

                order_details_list.append(order_details)
                total_spent_customer += total_spent_order

            # If customer has no first name or last name, use "" instead
            first_name = customer.first_name if customer.first_name else ""
            last_name = customer.last_name if customer.last_name else ""

            # If customer has no email, use "" instead
            email = customer.email if customer.email else ""

            customer_behavior.append(
                {
                    "name": first_name + " " + last_name,
                    "email": email,
                    "total_spent": total_spent_customer,
                    "total_orders": total_orders,
                    "order_details": order_details_list
                }
            )

    return {"customer_behavior": customer_behavior}


def analyze_customer_behavior_old() -> Dict[str, Any]:
    """Analyze customer behavior data and return insights."""

    customers = shopify.Customer.find()  # Fetch all customers
    customer_behavior = []

    for customer in customers:
        # Get all orders by this customer
        orders = shopify.Order.find(customer_id=customer.id)

        total_spent_customer = 0  # Total amount spent by the customer
        total_orders = len(orders)  # Total number of orders by the customer
        order_details_list = []  # List to store details of each order

        for order in orders:
            total_spent_order = 0  # Total amount spent in this order
            categories = []  # List to store the categories of products in this order

            for line_item in order.line_items:
                total_spent_order += line_item.price
                product = shopify.Product.find(line_item.product_id)

                if product and product.product_type not in categories:
                    categories.append(product.product_type)

            order_details = {
                'order_id': order.id,
                'date': order.created_at,
                'categories': categories,
                'total_spent': total_spent_order
            }

            order_details_list.append(order_details)
            total_spent_customer += total_spent_order

        # If customer has no first name or last name, use "" instead
        first_name = customer.first_name if customer.first_name else ""
        last_name = customer.last_name if customer.last_name else ""

        # If customer has no email, use "" instead
        email = customer.email if customer.email else ""

        customer_behavior.append(
            {
                "name": first_name + " " + last_name,
                "email": email,
                "total_spent": total_spent_customer,
                "total_orders": total_orders,
                "order_details": order_details_list
            }
        )

    return {"customer_behavior": customer_behavior}

def stock_management() -> Dict[str, Any]:
    """Manage stock and identify low stock products."""

    # Fetch all products
    products = shopify.Product.find()

    # Initialize a list to store low stock products
    low_stock_products = []

    # Check inventory quantity for each variant of each product
    for product in products:
        for variant in product.variants:
            if variant.inventory_quantity <= 10:
                low_stock_product = {
                    "product_id": product.id,
                    "product_name": product.title,
                    "variant_id": variant.id,
                    "variant_name": variant.title,
                    "inventory_quantity": variant.inventory_quantity,
                }
                low_stock_products.append(low_stock_product)

    return {"low_stock_products": low_stock_products}

def order_fulfillment() -> Dict[str, Any]:
    """Fulfill all unfulfilled orders."""

    # Fetch all orders
    orders = shopify.Order.find(status="any")

    # Initialize a list to store fulfilled orders
    fulfilled_orders = []

    # Check each order and fulfill it if it's not already fulfilled
    for order in orders:
        if not order.fulfillment_status or order.fulfillment_status == "partial":
            for line_item in order.line_items:
                fulfillment = shopify.Fulfillment(
                    {
                        "order_id": order.id,
                        "line_items": [{"id": line_item.id}],
                        "tracking_company": None,  # Optional: add tracking company here
                        "tracking_number": None,  # Optional: add tracking number here
                        "notify_customer": True,  # Optional: set to False if you don't want to notify the customer
                    }
                )
                fulfillment.save()
                fulfilled_order = {
                    "order_id": order.id,
                    "order_name": order.name,
                    "fulfillment_status": order.fulfillment_status,
                }
                fulfilled_orders.append(fulfilled_order)

    return {"fulfilled_orders": fulfilled_orders}

def manage_discounts_and_offers() -> Dict[str, Any]:
    """Manage discounts and offers."""
    # Fetch all active discounts
    active_discounts = shopify.PriceRule.find()

    # Initialize variables
    expired_discounts = []
    upcoming_discounts = []

    # Check the start and end dates for each discount
    for discount in active_discounts:
        if discount.ends_at and discount.ends_at < datetime.now():
            expired_discounts.append(discount)
        elif discount.starts_at and discount.starts_at > datetime.now():
            upcoming_discounts.append(discount)

    # Delete expired discounts
    for discount in expired_discounts:
        discount.destroy()

    # Prepare details about active and upcoming discounts
    active_discounts_details = [
        {"id": discount.id, "name": discount.title, "ends_at": discount.ends_at}
        for discount in active_discounts if discount not in expired_discounts
    ]
    upcoming_discounts_details = [
        {"id": discount.id, "name": discount.title, "starts_at": discount.starts_at}
        for discount in upcoming_discounts
    ]

    return {
        "active_discounts": active_discounts_details,
        "upcoming_discounts": upcoming_discounts_details,
    }

def customer_service() -> Dict[str, Any]:
    """Handle customer inquiries or complaints."""
    """This assumes that you have a system in place for categorizing and tagging inquiries or complaints from customers."""
    """Please note that this is a very simplified example. In reality, your customer inquiries could be stored elsewhere (for example, in a separate customer service software or a database), and resolving inquiries could involve much more than just updating a status field."""

    # Fetch all customers
    customers = shopify.Customer.find()
    customer_inquiries = []

    for customer in customers:
        # This is a hypothetical example assuming there's a system in place to categorize and tag inquiries
        if customer.metafields_global['inquiry_status'] == 'pending':
            response = {}  # Here would be the logic for generating a response based on the inquiry details

            # Update the customer inquiry status
            customer.metafields_global['inquiry_status'] = 'resolved'
            customer.save()

            # Add response to the list
            customer_inquiries.append({
                "customer_id": customer.id,
                "customer_name": f"{customer.first_name} {customer.last_name}",
                "response": response
            })

    return {"customer_inquiries": customer_inquiries}

def analyze_stock_levels() -> Dict[str, int]:
    """Analyze stock levels for all products and return the product ID and quantity."""
    stock_levels = {}

    products = shopify.Product.find()
    for product in products:
        for variant in product.variants:
            stock_levels[variant.id] = variant.inventory_quantity

    return stock_levels

def get_unfulfilled_orders() -> List[Dict[str, object]]:
    """Get a list of all orders that have not yet been fulfilled."""
    unfulfilled_orders = []

    orders = shopify.Order.find(fulfillment_status='unfulfilled')
    for order in orders:
        unfulfilled_orders.append({
            'order_id': order.id,
            'customer_id': order.customer.id,
            'name': order.customer.first_name + ' ' + order.customer.last_name,
            'order_value': sum(line_item.price for line_item in order.line_items),
        })

    return unfulfilled_orders

def get_customers_with_returns() -> List[Dict[str, object]]:
    """Get a list of all customers who have made returns."""
    customers_with_returns = []

    orders = shopify.Order.find()
    for order in orders:
        for refund in order.refunds:
            if refund:
                customers_with_returns.append({
                    'customer_id': order.customer.id,
                    'name': order.customer.first_name + ' ' + order.customer.last_name,
                    'order_id': order.id,
                    'refund_amount': sum(line_item.price for line_item in refund.refund_line_items),
                })

    return customers_with_returns

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

