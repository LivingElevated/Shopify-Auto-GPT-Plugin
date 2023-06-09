import shopify
from google.ads.googleads.client import GoogleAdsClient
import requests
from bs4 import BeautifulSoup
import time
import os
from collections import defaultdict
from datetime import datetime, timedelta
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

def get_product(product_identifier: Union[str, int]) -> Optional[Dict[str, Union[str, List[Dict[str, str]]]]]:
    """Fetch a product from Shopify using either its ID or its title.

    Args:
        product_identifier (Union[str, int]): The ID or the title of the product to fetch.

    Returns:
        Union[Dict[str, Any], None]: A dictionary containing the product attributes if found, or None otherwise.
    """
    # If the identifier is numeric, it's treated as an ID.
    if str(product_identifier).isdigit():
        product_id = int(product_identifier)
        product = shopify.Product.find(product_id)
    else:
        all_products = shopify.Product.find()
        product = next((p for p in all_products if p.title.lower() == product_identifier.lower()), None)

    if product:
        metafields = shopify.Metafield.find(resource_id=product.id)
        metafields_list = []
        for metafield in metafields:
            metafield_info = {
                "namespace": metafield.namespace,
                "key": metafield.key,
                "value": metafield.value
            }
            if hasattr(metafield, 'value_type'):
                metafield_info["value_type"] = metafield.value_type
            metafields_list.append(metafield_info)

        attributes = {
            "id": str(product.id),  # Convert product.id to a string
            "title": product.title,
            "description": product.body_html,
            "tags": product.tags,
            "metafields": metafields_list  # Add the metafields
        }

        print(f"Product Details:")
        print(f"ID: {product.id}")
        print(f"Title: {product.title}")
        print(f"Description: {product.body_html}")
        print("Metafields:")
        for metafield in metafields_list:
            print(f"Namespace: {metafield['namespace']}")
            print(f"Key: {metafield['key']}")
            print(f"Value: {metafield['value']}")
            if 'value_type' in metafield:
                print(f"Value Type: {metafield['value_type']}")
            print("----")

        return attributes

    return None

def get_products(sort_by: Optional[str] = None, tags: Optional[List[str]] = None) -> List[shopify.Product]:
    """Get products from Shopify with optional sorting qualifiers.

    Args:
        sort_by (Optional[str], optional): The field to sort the products by. Defaults to None.
        tags (Optional[List[str]], optional): The tags to filter the products by. Defaults to None.

    Returns:
        List[shopify.Product]: List of products matching the specified criteria.
    """
    products = shopify.Product.find()

    if tags:
        products = [product for product in products if all(tag in product.tags for tag in tags)]

    if sort_by:
        products = sorted(products, key=lambda product: getattr(product, sort_by))

    return products

def get_all_products() -> List[Tuple[int, str]]:
    """Fetch all products from Shopify and return their IDs and names.

    Returns:
        List[Tuple[int, str]]: List of all products represented as tuples (id, name).
    """
    limit = 100
    get_next_page = True
    since_id = 0
    products = []

    while get_next_page:
        products_page = shopify.Product.find(since_id=since_id, limit=limit)
        products.extend(products_page)

        if len(products_page) < limit:
            get_next_page = False
        else:
            since_id = products_page[-1].id

    print(f"Found {len(products)} products.")

    product_info = [(product.id, product.title) for product in products]

    return product_info

def get_all_product_names() -> List[str]:
    """Fetch all product names from Shopify.

    Returns:
        List[Any]: List of all products by name.
    """
    products = shopify.Product.find()
    product_names = [product.title for product in products]
    return product_names

#Search products by title:
def search_products_by_title(title: str) -> List[Tuple[int, str]]:
    """Search products by title in Shopify.

    Args:
        title (str): Title of the products to search for.

    Returns:
        List[Tuple[int, shopify.Product]]: List of products that match the title.
    """
    lowercase_title = title.casefold()
    matching_products = []

    # Set the initial values for pagination
    get_next_page = True
    limit = 100
    since_id = 0

    while get_next_page:
        # Retrieve the products using the Shopify API with pagination parameters
        products = shopify.Product.find(limit=limit, since_id=since_id)
        
        for product in products:
            if lowercase_title in product.title.casefold():
                matching_products.append((product.id, product.title))

        # Check if there are more pages of results
        if len(products) < limit:
            get_next_page = False
        else:
            since_id = products[-1].id

    return matching_products

def map_locations_ids_to_resource_names(client, location_ids):
    """Converts a list of location IDs to resource names.
    Args:
        client: an initialized GoogleAdsClient instance.
        location_ids: a list of location ID strings.
    Returns:
        a list of resource name strings using the given location IDs.
    """
    build_resource_name = client.get_service(
        "GeoTargetConstantService"
    ).geo_target_constant_path
    return [build_resource_name(location_id) for location_id in location_ids]

def analyze_and_suggest_keywords(product_title: Optional[str] = None, product_description: Optional[str] = None, tags: Optional[str] = None, meta_data: Optional[str] = None) -> List[str]:
    
    customer_id = os.getenv("CLIENT-CUSTOMER-ID")

    # If the Google Ads client is not initialized, return an empty list
    if plugin.googleads_client is None:
        print("Debug: googleads_client is ot initialized, returning an empty list")
        return []
    
    # Define the location IDs and language ID
    _DEFAULT_LOCATION_IDS = ["21167"]  # location ID for Austin, Texas
    _DEFAULT_LANGUAGE_ID = "1000"  # language ID for English
    location_ids = ["21167"]
    language_id = "1000"

    keyword_plan_idea_service = plugin.googleads_client.get_service("KeywordPlanIdeaService")
    keyword_competition_level_enum = (
        plugin.googleads_client.enums.KeywordPlanCompetitionLevelEnum
    )
    keyword_plan_network = (
        plugin.googleads_client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    )
    location_rns = map_locations_ids_to_resource_names(plugin.googleads_client, location_ids)
    language_rn = plugin.googleads_client.get_service("GoogleAdsService").language_constant_path(
        language_id
    )

    # Construct the keyword text which includes product title, description, tags and meta data
    keyword_texts = [product_title, product_description, tags, meta_data]
    keyword_texts = list(filter(None, keyword_texts))

    if not keyword_texts:
        raise ValueError(
            "At least one of product_title, product_description, tags, or meta_data is required, "
            "but none were specified."
        )
    print("Debug: keyword_texts =", keyword_texts)

    # Get the KeywordPlanIdeaService client
    request = plugin.googleads_client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = customer_id  # Use the customer_id from the environment variable
    request.language = plugin.googleads_client.get_service("GoogleAdsService").language_constant_path(
        _DEFAULT_LANGUAGE_ID
    )
    request.geo_target_constants = [
        plugin.googleads_client.get_service("GeoTargetConstantService").geo_target_constant_path(id)
        for id in _DEFAULT_LOCATION_IDS
    ]
    request.include_adult_keywords = False
    request.keyword_plan_network = plugin.googleads_client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    request.keyword_seed.keywords.extend(keyword_texts)

    print("Debug: request =", request)

    try:
        keyword_ideas = plugin.googleads_client.get_service("KeywordPlanIdeaService").generate_keyword_ideas(
            request=request
        )
    except Exception as e:
        print("Debug: Exception occurred while calling generate_keyword_ideas:", e)
        raise e

    keyword_suggestions = []
    for idea in keyword_ideas:
        keyword_suggestions.append(idea.text.value)
        competition_value = idea.keyword_idea_metrics.competition.name
        print(
            f'Keyword idea text "{idea.text}" has '
            f'"{idea.keyword_idea_metrics.avg_monthly_searches}" '
            f'average monthly searches and "{competition_value}" '
            "competition.\n"
        )
    return keyword_suggestions

def analyze_and_suggest_keywordsbug(product_title: Optional[str] = None, product_description: Optional[str] = None, tags: Optional[str] = None, meta_data: Optional[str] = None):
    # Define the URL for the Google Keyword Planner
    url = 'https://ads.google.com/aw/keywordplanner/home'

    # Define the headers for the HTTP request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
    }

    # Send an HTTP GET request to the Google Keyword Planner
    response = requests.get(url, headers=headers)

    # Parse the HTML response using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the search box element
    search_box = soup.find('input', {'aria-label': 'Search for new keywords'})

    # Construct the search query
    search_query = ""
    if product_title:
        search_query += product_title + " "
    if product_description:
        search_query += product_description + " "
    if tags:
        search_query += tags + " "
    if meta_data:
        search_query += meta_data

    # Enter the search query into the search box
    search_box['value'] = search_query

    # Find the search button element
    search_button = soup.find('button', {'aria-label': 'Get keyword ideas'})

    # Click the search button
    search_button.click()

    # Wait for the page to load
    time.sleep(5)

    # Get the updated response after clicking the search button
    response = requests.get(search_button['href'], headers=headers)

    # Parse the HTML response again
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the keyword ideas table
    keyword_table = soup.find('table', {'class': 'aw-di-table'})

    # Extract the keyword ideas
    keyword_ideas = []
    for row in keyword_table.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) > 1:
            keyword_ideas.append(cells[1].text.strip())

    # Print the keyword ideas
    print("Keyword ideas:", keyword_ideas)
    return keyword_ideas

def update_product(product_id: str, title: Optional[str] = None, description: Optional[str] = None, tags: Optional[str] = None, metafields: Optional[List[Dict[str, Union[str, int, float, bool]]]] = None) -> Optional[shopify.Product]:
    """Update a product on Shopify.

    Args:
        product_id (str): The ID of the product to update.
        title (Optional[str], optional): The new title of the product. Defaults to None.
        description (Optional[str], optional): The new description of the product. Defaults to None.
        tags (Optional[str], optional): The new tags for the product. Defaults to None.
        metafields (Optional[List[Dict[str, Union[str, int, float, bool]]]], optional): The new metafields for the product. Defaults to None.
        print_details (bool, optional): Whether to print the updated product details. Defaults to False.

    Returns:
        Optional[shopify.Product]: The updated product if successful, or None if the product is not found.
    """
    product = shopify.Product.find(product_id)

    if product:
        if title:
            product.title = title

        if description:
            product.body_html = description

        if tags:
            product.tags = tags

        if metafields:
            for metafield_data in metafields:
                product.add_metafield(shopify.Metafield(**metafield_data))

        product.save()


        print(f"Product {product_id} updated successfully.")
        print("Updated Product Details:")
        print(f"ID: {product.id}")
        print(f"Title: {product.title}")
        print(f"Description: {product.body_html}")
        print("Metafields:")
        metafields = shopify.Metafield.find(resource_id=product.id)
        for metafield in product.metafields:
            print(f"Namespace: {metafield.namespace}")
            print(f"Key: {metafield.key}")
            print(f"Value: {metafield.value}")
            print(f"Value Type: {metafield.value_type}")
            print("----")

        # Get the updated product details using get_product
        updated_product = get_product(product_id)
        return updated_product

    return None

def delete_product(product_id: str) -> None:
    """Delete a product from Shopify.

    Args:
        product_id (str): The ID of the product to delete.
    """
    product = get_product(product_id)
    product.destroy()

def get_all_orders() -> List[Dict[str, Any]]:
    """Fetch all orders from Shopify and return insights."""

    orders = shopify.Order.find(status="any")  # Fetch all orders

    try:
        orders = shopify.Order.find(status="any")  # Fetch all orders
        print(f"Fetched {len(orders)} orders.")  # Print number of fetched orders
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return []
    
    all_orders = []

    for order in orders:
        try:
            line_items = []
            for item in order.line_items:
                product_name = None
                if item.product_id:
                    product = shopify.Product.find(item.product_id)
                    product_name = product.title if product else None

                line_items.append({
                    "product_id": item.product_id,
                    "product_name": product_name,
                    "quantity": item.quantity,
                    "price": item.price
                })

            customer_id = order.customer.id if order.customer else None

            order_details = {
                "order_id": order.id,
                "order_date": order.created_at,
                "customer": customer_id,
                "line_items": line_items,
                "total_price": order.total_price,
            }
            all_orders.append(order_details)
        except Exception as e:
            print(f"Error processing order {order.id}: {e}")

    return all_orders

def get_all_orders_old() -> List[Dict[str, Any]]:
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

    # Fetch all orders and all products
    orders = shopify.Order.find(status="any")
    all_products = shopify.Product.find()
    
    total_sales = sum(float(order.total_price) for order in orders)  # Compute total sales
    total_sales = f"${total_sales:.2f}"

    # Initialize product sales, product sold count, and product percentage contribution
    product_data = defaultdict(lambda: {"sales": 0, "count": 0, "contribution": "0%"})

    for order in orders:
        for line_item in order.line_items:
            product_data[line_item.title]["sales"] += float(line_item.price)
            product_data[line_item.title]["count"] += line_item.quantity  # Assuming line_item has a 'quantity' attribute

    total_products_sold = sum(data["count"] for data in product_data.values())

    # Calculate the percentage contribution of each product to total sales
    for product, data in product_data.items():
        if data["count"] > 0:
            data["contribution"] = f"{round((data['count'] / total_products_sold) * 100, 2)}%"

    # Find out the slow-moving products (products that contribute 5% or less to total sales)
    slow_moving_products = [product.title for product in all_products if product.title not in product_data or float(product_data[product.title]["contribution"].replace('%', '')) <= 5]

    # Format sales as currency
    for data in product_data.values():
        data["sales"] = f"${data['sales']:.2f}"

    return {
        "total_sales": total_sales,
        "product_data": dict(product_data),
        "slow_moving_products": slow_moving_products,
    }

def analyze_customer_behavior() -> Dict[str, Any]:
    """Analyze customer behavior data and return insights."""

    # Fetch all customers and orders
    customers = shopify.Customer.find()
    orders = shopify.Order.find(status="any")

    # Build a map from customer_id to customer details
    customers_by_id = {customer.id: customer for customer in customers}

    # Initialize a dictionary to hold customer behavior data
    customer_behavior = {customer_id: {
        "id": customer_id,
        "name": f'{customer.first_name or ""} {customer.last_name or ""}'.strip(),
        "email": customer.email or "",
        "total_spent": 0,
        "total_orders": 0,
        "order_details": [],
    } for customer_id, customer in customers_by_id.items()}

    # Iterate through all orders
    for order in orders:
        customer_id = order.customer.id if order.customer else None
        if customer_id is None:
            continue

        customer_data = customer_behavior.get(customer_id)
        if customer_data is None:
            continue

        total_spent_order = 0
        purchases = []
        for item in order.line_items:
            product_name = None
            if item.product_id:
                product = shopify.Product.find(item.product_id)
                product_name = product.title if product else None
            total_spent_order += float(item.price)
            purchases.append(product_name)

        order_details = {
            'order_id': order.id,
            'date': order.created_at,
            'purchases': purchases,
            'total_spent': total_spent_order
        }

        # Update customer data
        customer_data['order_details'].append(order_details)
        customer_data['total_spent'] += total_spent_order
        customer_data['total_orders'] += 1

        # Debug line to print the number of orders for each customer
        print(f'Fetched {customer_data["total_orders"]} orders for customer {customer_id} - {customer_data["name"]}')

    return {"customer_behavior": list(customer_behavior.values())}

def analyze_customer_behavior_old() -> Dict[str, Any]:
    """Analyze customer behavior data and return insights."""

    customers = shopify.Customer.find()  # Fetch all customers
    customer_behavior = []

    all_orders = get_all_orders()  # Fetch all orders using the get_all_orders() function
    orders_by_customer = defaultdict(list)  # Create an empty dictionary to map customer IDs to orders

    for order in all_orders:
        customer_id = order["customer"]  # Get the customer ID from the order
        if customer_id is not None:
            orders_by_customer[customer_id].append(order)  # Append the order to the list of orders for this customer

    for customer in customers:
        # Get all orders for this customer using the dictionary
        orders = orders_by_customer.get(customer.id, [])
        print(f'Fetched {len(orders)} orders for customer {customer.id}')  # Debug line

        total_spent_customer = 0  # Total amount spent by the customer
        total_orders = len(orders)  # Total number of orders by the customer
        order_details_list = []  # List to store details of each order

        for order in orders:
            total_spent_order = float(order["total_price"])  # Total amount spent in this order
            categories = [item["product_name"] for item in order["line_items"]]  # List to store the categories of products in this order

            order_details = {
                'order_id': order["order_id"],
                'date': order["order_date"],
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
                "id": customer.id,
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

def analyze_shopify_store() -> Dict[str, Any]:
    """Analyze the Shopify store and return insights."""

    # Initialize a dictionary to store the analysis results
    results = {}

    # Analyze sales
    sales_analysis = analyze_sales()
    results["sales_analysis"] = sales_analysis

    # Analyze customer behavior
    customer_behavior_analysis = analyze_customer_behavior()
    results["customer_behavior_analysis"] = customer_behavior_analysis

    # Fetch all orders
    all_orders = get_all_orders()
    results["all_orders"] = all_orders

    # Analyze stock management
    # stock_analysis = stock_management()
    # results["stock_analysis"] = stock_analysis

    return results

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

def manage_discounts_and_offers(product_identifiers: Union[List[int], List[str]], discount_value: float) -> Dict[str, Any]:
    """Manage discounts and offers for specific products."""

    if not product_identifiers or not discount_value:
        return {"error": "product_identifiers and discount_value are required"}

    # Fetch all products
    products = shopify.Product.find()

    # Filter products based on identifiers
    if isinstance(product_identifiers[0], int):
        # If product_identifiers are IDs
        filtered_products = [product for product in products if product.id in product_identifiers]
    else:
        # If product_identifiers are names
        filtered_products = [product for product in products if product.title in product_identifiers]

    # Create a price rule and discount code for each product
    for product in filtered_products:
        price_rule = shopify.PriceRule.create({
            "title": f"{discount_value * 100}% off {product.title}",
            "target_type": "line_item",
            "target_selection": "entitled",
            "allocation_method": "across",
            "value_type": "percentage",
            "value": -discount_value,  # Note: value is negative
            "customer_selection": "all",
            "starts_at": "2023-05-14T00:00:00Z",  # Set start date
        })

        # Add product to entitled product ids
        price_rule.entitled_product_ids.append(product.id)
        price_rule.save()

        # Create a discount code
        shopify.DiscountCode.create({
            "price_rule_id": price_rule.id,
            "code": f"{discount_value * 100}OFF{product.title.upper().replace(' ', '')}"
        })

    return {"status": "Discounts and offers created successfully"}

def manage_discounts_and_offers_old() -> Dict[str, Any]:
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

