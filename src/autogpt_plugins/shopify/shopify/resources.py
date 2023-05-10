from shopify.base import ShopifyResource
from shopify import mixins
import os
import sys
import base64
import shopify
import json
from six.moves import urllib
import re

class Shop(ShopifyResource):
    @classmethod
    def current(cls):
        return cls.find_one(cls.site + "/shop." + cls.format.extension)

    def metafields(self):
        return Metafield.find()

    def add_metafield(self, metafield):
        if self.is_new():
            raise ValueError("You can only add metafields to a resource that has been saved")
        metafield.save()
        return metafield

    def events(self):
        return Event.find()

class AccessScope(ShopifyResource):
    @classmethod
    def override_prefix(cls):
        return "/admin/oauth"

class Address(ShopifyResource):
    pass

class ApiPermission(ShopifyResource):
    @classmethod
    def delete(cls):
        cls.connection.delete(cls.site + "/api_permissions/current." + cls.format.extension, cls.headers)

    destroy = delete

class ApplicationCharge(ShopifyResource):
    def activate(self):
        self._load_attributes_from_response(self.post("activate"))

class ApplicationCredit(ShopifyResource):
    pass

class Article(ShopifyResource, mixins.Metafields, mixins.Events):
    _prefix_source = "/blogs/$blog_id/"

    @classmethod
    def _prefix(cls, options={}):
        blog_id = options.get("blog_id")
        if blog_id:
            return "%s/blogs/%s" % (cls.site, blog_id)
        else:
            return cls.site

    def comments(self):
        return Comment.find(article_id=self.id)

    @classmethod
    def authors(cls, **kwargs):
        return cls.get("authors", **kwargs)

    @classmethod
    def tags(cls, **kwargs):
        return cls.get("tags", **kwargs)


class Asset(ShopifyResource):
    _primary_key = "key"
    _prefix_source = "/themes/$theme_id/"

    @classmethod
    def _prefix(cls, options={}):
        theme_id = options.get("theme_id")
        if theme_id:
            return "%s/themes/%s" % (cls.site, theme_id)
        else:
            return cls.site

    @classmethod
    def _element_path(cls, id, prefix_options={}, query_options=None):
        if query_options is None:
            prefix_options, query_options = cls._split_options(prefix_options)
        return "%s%s.%s%s" % (
            cls._prefix(prefix_options) + "/",
            cls.plural,
            cls.format.extension,
            cls._query_string(query_options),
        )

    @classmethod
    def find(cls, key=None, **kwargs):
        """
        Find an asset by key
        E.g.
            shopify.Asset.find('layout/theme.liquid', theme_id=99)
        """
        if not key:
            return super(Asset, cls).find(**kwargs)

        params = {"asset[key]": key}
        params.update(kwargs)
        theme_id = params.get("theme_id")
        path_prefix = "%s/themes/%s" % (cls.site, theme_id) if theme_id else cls.site

        resource = cls.find_one("%s/assets.%s" % (path_prefix, cls.format.extension), **params)

        if theme_id and resource:
            resource._prefix_options["theme_id"] = theme_id
        return resource

    def __get_value(self):
        data = self.attributes.get("value")
        if data:
            return data
        data = self.attributes.get("attachment")
        if data:
            return base64.b64decode(data).decode()

    def __set_value(self, data):
        self.__wipe_value_attributes()
        self.attributes["value"] = data

    value = property(__get_value, __set_value, None, "The asset's value or attachment")

    def attach(self, data):
        self.attachment = base64.b64encode(data).decode()

    def destroy(self):
        options = {"asset[key]": self.key}
        options.update(self._prefix_options)
        return self.__class__.connection.delete(self._element_path(self.key, options), self.__class__.headers)

    def is_new(self):
        return False

    def __setattr__(self, name, value):
        if name in ("value", "attachment", "src", "source_key"):
            self.__wipe_value_attributes()
        return super(Asset, self).__setattr__(name, value)

    def __wipe_value_attributes(self):
        for attr in ("value", "attachment", "src", "source_key"):
            if attr in self.attributes:
                del self.attributes[attr]


class Balance(ShopifyResource, mixins.Metafields):
    _prefix_source = "/shopify_payments/"
    _singular = _plural = "balance"

class BillingAddress(ShopifyResource):
    pass


class Blog(ShopifyResource, mixins.Metafields, mixins.Events):
    def articles(self):
        return shopify.Article.find(blog_id=self.id)


class CarrierService(ShopifyResource):
    def __get_format(self):
        return self.attributes.get("format")

    def __set_format(self, data):
        self.attributes["format"] = data

    format = property(__get_format, __set_format, None, "Format attribute")

class Cart(ShopifyResource):
    pass

class Checkout(ShopifyResource):
    pass

class Collect(ShopifyResource):
    pass

class CollectionListing(ShopifyResource):
    _primary_key = "collection_id"

    def product_ids(cls, **kwargs):
        return cls.get("product_ids", **kwargs)

class CollectionPublication(ShopifyResource):
    _prefix_source = "/publications/$publication_id/"


class Comment(ShopifyResource):
    def remove(self):
        self._load_attributes_from_response(self.post("remove"))

    def spam(self):
        self._load_attributes_from_response(self.post("spam"))

    def approve(self):
        self._load_attributes_from_response(self.post("approve"))

    def restore(self):
        self._load_attributes_from_response(self.post("restore"))

    def not_spam(self):
        self._load_attributes_from_response(self.post("not_spam"))


class Country(ShopifyResource):
    pass

class Currency(ShopifyResource):
    pass

class CustomCollection(ShopifyResource, mixins.Metafields, mixins.Events):
    def products(self):
        return shopify.Product.find(collection_id=self.id)

    def add_product(self, product):
        return shopify.Collect.create({"collection_id": self.id, "product_id": product.id})

    def remove_product(self, product):
        collect = shopify.Collect.find_first(collection_id=self.id, product_id=product.id)
        if collect:
            collect.destroy()

class CustomerSavedSearch(ShopifyResource):
    def customers(cls, **kwargs):
        return Customer._build_collection(cls.get("customers", **kwargs))

class CustomerGroup(CustomerSavedSearch):
    pass

class CustomerInvite(ShopifyResource):
    pass

class Customer(ShopifyResource, mixins.Metafields):
    @classmethod
    def search(cls, **kwargs):
        """
        Search for customers matching supplied query

        Args:
           order: Field and direction to order results by (default: last_order_date DESC)
           query: Text to search for customers
           page: Page to show (default: 1)
           limit: Amount of results (default: 50) (maximum: 250)
           fields: comma-separated list of fields to include in the response
        Returns:
           A Collection of customers.
        """
        return cls._build_collection(cls.get("search", **kwargs))

    def send_invite(self, customer_invite=CustomerInvite()):
        resource = self.post("send_invite", customer_invite.encode())
        return CustomerInvite(Customer.format.decode(resource.body))

    def orders(self):
        return Order.find(customer_id=self.id)

class DiscountCodeCreation(ShopifyResource):
    _prefix_source = "/price_rules/$price_rule_id/"

    def discount_codes(self):
        return DiscountCode.find(
            from_="%s/price_rules/%s/batch/%s/discount_codes.%s"
            % (
                ShopifyResource.site,
                self._prefix_options["price_rule_id"],
                self.id,
                DiscountCodeCreation.format.extension,
            )
        )

class DiscountCode(ShopifyResource):
    _prefix_source = "/price_rules/$price_rule_id/"

class Disputes(ShopifyResource, mixins.Metafields):
    _prefix_source = "/shopify_payments/"

class DraftOrderInvoice(ShopifyResource):
    pass

class DraftOrder(ShopifyResource, mixins.Metafields):
    def send_invoice(self, draft_order_invoice=DraftOrderInvoice()):
        resource = self.post("send_invoice", draft_order_invoice.encode())
        return DraftOrderInvoice(DraftOrder.format.decode(resource.body))

    def complete(self, params={}):
        if params.get("payment_pending", False):
            self._load_attributes_from_response(self.put("complete", payment_pending="true"))
        else:
            self._load_attributes_from_response(self.put("complete"))

class Event(ShopifyResource):
    _prefix_source = "/$resource/$resource_id/"

    @classmethod
    def _prefix(cls, options={}):
        resource = options.get("resource")
        if resource:
            return "%s/%s/%s" % (cls.site, resource, options["resource_id"])
        else:
            return cls.site

class FulfillmentEvent(ShopifyResource):
    _prefix_source = "/orders/$order_id/fulfillments/$fulfillment_id/"
    _singular = "event"
    _plural = "events"

    @classmethod
    def _prefix(cls, options={}):
        order_id = options.get("order_id")
        fulfillment_id = options.get("fulfillment_id")
        event_id = options.get("event_id")

        return "%s/orders/%s/fulfillments/%s" % (cls.site, order_id, fulfillment_id)

    def save(self):
        status = self.attributes["status"]
        if status not in [
            "label_printed",
            "label_purchased",
            "attempted_delivery",
            "ready_for_pickup",
            "picked_up",
            "confirmed",
            "in_transit",
            "out_for_delivery",
            "delivered",
            "failure",
        ]:
            raise AttributeError("Invalid status")
        return super(ShopifyResource, self).save()

class FulfillmentService(ShopifyResource):
    def __get_format(self):
        return self.attributes.get("format")

    def __set_format(self, data):
        self.attributes["format"] = data

    format = property(__get_format, __set_format, None, "Format attribute")

class Fulfillment(ShopifyResource):
    _prefix_source = "/orders/$order_id/"

    def cancel(self):
        self._load_attributes_from_response(self.post("cancel"))

    def complete(self):
        self._load_attributes_from_response(self.post("complete"))

    def open(self):
        self._load_attributes_from_response(self.post("open"))

    def update_tracking(self, tracking_info, notify_customer):
        fulfill = FulfillmentV2()
        fulfill.id = self.id
        self._load_attributes_from_response(fulfill.update_tracking(tracking_info, notify_customer))


class FulfillmentOrders(ShopifyResource):
    _prefix_source = "/orders/$order_id/"


class FulfillmentV2(ShopifyResource):
    _singular = "fulfillment"
    _plural = "fulfillments"

    def update_tracking(self, tracking_info, notify_customer):
        body = {"fulfillment": {"tracking_info": tracking_info, "notify_customer": notify_customer}}
        return self.post("update_tracking", json.dumps(body).encode())

class GiftCardAdjustment(ShopifyResource):
    _prefix_source = "/admin/gift_cards/$gift_card_id/"
    _plural = "adjustments"
    _singular = "adjustment"


class GiftCard(ShopifyResource):
    def disable(self):
        self._load_attributes_from_response(self.post("disable"))

    @classmethod
    def search(cls, **kwargs):
        """
        Search for gift cards matching supplied query

        Args:
           order: Field and direction to order results by (default: disabled_at DESC)
           query: Text to search for gift cards
           page: Page to show (default: 1)
           limit: Amount of results (default: 50) (maximum: 250)
           fields: comma-separated list of fields to include in the response
        Returns:
           An array of gift cards.
        """
        return cls._build_collection(cls.get("search", **kwargs))

    def add_adjustment(self, adjustment):
        """
        Create a new Gift Card Adjustment
        """
        resource = self.post("adjustments", adjustment.encode())
        return GiftCardAdjustment(GiftCard.format.decode(resource.body))

class GraphQL:
    def __init__(self):
        self.endpoint = shopify.ShopifyResource.get_site() + "/graphql.json"
        self.headers = shopify.ShopifyResource.get_headers()

    def merge_headers(self, *headers):
        merged_headers = {}
        for header in headers:
            merged_headers.update(header)
        return merged_headers

    def execute(self, query, variables=None, operation_name=None):
        endpoint = self.endpoint
        default_headers = {"Accept": "application/json", "Content-Type": "application/json"}
        headers = self.merge_headers(default_headers, self.headers)
        data = {"query": query, "variables": variables, "operationName": operation_name}

        req = urllib.request.Request(self.endpoint, json.dumps(data).encode("utf-8"), headers)

        try:
            response = urllib.request.urlopen(req)
            return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            print((e.read()))
            print("")
            raise e

class InventoryItem(ShopifyResource):
    pass

class InventoryLevel(ShopifyResource):
    def __repr__(self):
        return "%s(inventory_item_id=%s, location_id=%s)" % (self._singular, self.inventory_item_id, self.location_id)

    @classmethod
    def _element_path(cls, prefix_options={}, query_options=None):
        if query_options is None:
            prefix_options, query_options = cls._split_options(prefix_options)

        return "%s%s.%s%s" % (
            cls._prefix(prefix_options) + "/",
            cls.plural,
            cls.format.extension,
            cls._query_string(query_options),
        )

    @classmethod
    def adjust(cls, location_id, inventory_item_id, available_adjustment):
        body = {
            "inventory_item_id": inventory_item_id,
            "location_id": location_id,
            "available_adjustment": available_adjustment,
        }
        resource = cls.post("adjust", body=json.dumps(body).encode())
        return InventoryLevel(InventoryLevel.format.decode(resource.body))

    @classmethod
    def connect(cls, location_id, inventory_item_id, relocate_if_necessary=False, **kwargs):
        body = {
            "inventory_item_id": inventory_item_id,
            "location_id": location_id,
            "relocate_if_necessary": relocate_if_necessary,
        }
        resource = cls.post("connect", body=json.dumps(body).encode())
        return InventoryLevel(InventoryLevel.format.decode(resource.body))

    @classmethod
    def set(cls, location_id, inventory_item_id, available, disconnect_if_necessary=False, **kwargs):
        body = {
            "inventory_item_id": inventory_item_id,
            "location_id": location_id,
            "available": available,
            "disconnect_if_necessary": disconnect_if_necessary,
        }
        resource = cls.post("set", body=json.dumps(body).encode())
        return InventoryLevel(InventoryLevel.format.decode(resource.body))

    def is_new(self):
        return False

    def destroy(self):
        options = {"inventory_item_id": self.inventory_item_id, "location_id": self.location_id}
        return self.__class__.connection.delete(self._element_path(query_options=options), self.__class__.headers)

class LineItem(ShopifyResource):
    class Property(ShopifyResource):
        pass

class Location(ShopifyResource):
    def inventory_levels(self, **kwargs):
        return InventoryLevel.find(
            from_="%s/locations/%s/inventory_levels.json" % (ShopifyResource.site, self.id), **kwargs
        )

class MarketingEvent(ShopifyResource):
    def add_engagements(self, engagements):
        engagements_json = json.dumps({"engagements": engagements})
        return self.post("engagements", engagements_json.encode())

class Metafield(ShopifyResource):
    _prefix_source = "/$resource/$resource_id/"

    @classmethod
    def _prefix(cls, options={}):
        resource = options.get("resource")
        if resource:
            return "%s/%s/%s" % (cls.site, resource, options["resource_id"])
        else:
            return cls.site

class NoteAttribute(ShopifyResource):
    pass

class Option(ShopifyResource):
    pass

class OrderRisk(ShopifyResource):
    _prefix_source = "/orders/$order_id/"
    _singular = "risk"
    _plural = "risks"

class Order(ShopifyResource, mixins.Metafields, mixins.Events):
    _prefix_source = "/customers/$customer_id/"

    @classmethod
    def _prefix(cls, options={}):
        customer_id = options.get("customer_id")
        if customer_id:
            return "%s/customers/%s" % (cls.site, customer_id)
        else:
            return cls.site

    def close(self):
        self._load_attributes_from_response(self.post("close"))

    def open(self):
        self._load_attributes_from_response(self.post("open"))

    def cancel(self, **kwargs):
        self._load_attributes_from_response(self.post("cancel", **kwargs))

    def transactions(self):
        return Transaction.find(order_id=self.id)

    def capture(self, amount=""):
        return Transaction.create({"amount": amount, "kind": "capture", "order_id": self.id})

class Page(ShopifyResource, mixins.Metafields, mixins.Events):
    pass

class PaymentDetails(ShopifyResource):
    pass

class Payouts(ShopifyResource, mixins.Metafields):
    _prefix_source = "/shopify_payments/"

class Policy(ShopifyResource, mixins.Metafields, mixins.Events):
    pass


class PriceRule(ShopifyResource):
    def add_discount_code(self, discount_code=DiscountCode()):
        resource = self.post("discount_codes", discount_code.encode())
        return DiscountCode(PriceRule.format.decode(resource.body))

    def discount_codes(self):
        return DiscountCode.find(price_rule_id=self.id)

    def create_batch(self, codes=[]):
        codes_json = json.dumps({"discount_codes": codes})

        response = self.post("batch", codes_json.encode())
        return DiscountCodeCreation(PriceRule.format.decode(response.body))

    def find_batch(self, batch_id):
        return DiscountCodeCreation.find_one(
            "%s/price_rules/%s/batch/%s.%s" % (ShopifyResource.site, self.id, batch_id, PriceRule.format.extension)
        )

class ProductListing(ShopifyResource):
    _primary_key = "product_id"

    @classmethod
    def product_ids(cls, **kwargs):
        return cls.get("product_ids", **kwargs)

class ProductPublication(ShopifyResource):
    _prefix_source = "/publications/$publication_id/"

class Product(ShopifyResource, mixins.Metafields, mixins.Events):
    def price_range(self):
        prices = [float(variant.price) for variant in self.variants]
        f = "%0.2f"
        min_price = min(prices)
        max_price = max(prices)
        if min_price != max_price:
            return "%s - %s" % (f % min_price, f % max_price)
        else:
            return f % min_price

    def collections(self):
        return shopify.CustomCollection.find(product_id=self.id)

    def smart_collections(self):
        return shopify.SmartCollection.find(product_id=self.id)

    def add_to_collection(self, collection):
        return collection.add_product(self)

    def remove_from_collection(self, collection):
        return collection.remove_product(self)

    def add_variant(self, variant):
        variant.attributes["product_id"] = self.id
        return variant.save()

    def save(self):
        start_api_version = "201910"
        api_version = ShopifyResource.version
        if api_version and (api_version.strip("-") >= start_api_version) and api_version != "unstable":
            if "variants" in self.attributes:
                for variant in self.variants:
                    if "inventory_quantity" in variant.attributes:
                        del variant.attributes["inventory_quantity"]
                    if "old_inventory_quantity" in variant.attributes:
                        del variant.attributes["old_inventory_quantity"]
        return super(ShopifyResource, self).save()

class Province(ShopifyResource):
    _prefix_source = "/admin/countries/$country_id/"

class Publication(ShopifyResource):
    pass

class Receipt(ShopifyResource):
    pass

def _get_first_by_status(resources, status):
    for resource in resources:
        if resource.status == status:
            return resource
    return None


class RecurringApplicationCharge(ShopifyResource):
    def usage_charges(self):
        return UsageCharge.find(recurring_application_charge_id=self.id)

    def customize(self, **kwargs):
        self._load_attributes_from_response(self.put("customize", recurring_application_charge=kwargs))

    @classmethod
    def current(cls):
        """
        Returns first RecurringApplicationCharge object with status=active.
        If not found, None will be returned.
        """
        return _get_first_by_status(cls.find(), "active")

    def activate(self):
        self._load_attributes_from_response(self.post("activate"))

class Redirect(ShopifyResource):
    pass


class Refund(ShopifyResource):
    _prefix_source = "/orders/$order_id/"

    @classmethod
    def calculate(cls, order_id, shipping=None, refund_line_items=None):
        """
        Calculates refund transactions based on line items and shipping.
        When you want to create a refund, you should first use the calculate
        endpoint to generate accurate refund transactions.

        Args:
           order_id: Order ID for which the Refund has to created.
           shipping: Specify how much shipping to refund.
           refund_line_items: A list of line item IDs and quantities to refund.
        Returns:
           Unsaved refund record
        """
        data = {}
        if shipping:
            data["shipping"] = shipping
        data["refund_line_items"] = refund_line_items or []
        body = {"refund": data}
        resource = cls.post("calculate", order_id=order_id, body=json.dumps(body).encode())
        return cls(cls.format.decode(resource.body), prefix_options={"order_id": order_id})

class Report(ShopifyResource):
    pass

class ResourceFeedback(ShopifyResource):
    _prefix_source = "/products/$product_id/"
    _plural = "resource_feedback"

    @classmethod
    def _prefix(cls, options={}):
        product_id = options.get("product_id")
        if product_id:
            return "%s/products/%s" % (cls.site, product_id)
        else:
            return cls.site

class Rule(ShopifyResource):
    pass

class ScriptTag(ShopifyResource):
    pass

class ShippingAddress(ShopifyResource):
    pass

class ShippingLine(ShopifyResource):
    pass

class ShippingZone(ShopifyResource):
    pass

class SmartCollection(ShopifyResource, mixins.Metafields, mixins.Events):
    def products(self):
        return shopify.Product.find(collection_id=self.id)

class StorefrontAccessToken(ShopifyResource):
    pass

class TaxLine(ShopifyResource):
    pass

class TenderTransaction(ShopifyResource):
    pass

class Theme(ShopifyResource):
    pass

class Transaction(ShopifyResource):
    _prefix_source = "/orders/$order_id/"

class Transactions(ShopifyResource, mixins.Metafields):
    _prefix_source = "/shopify_payments/balance/"

class UsageCharge(ShopifyResource):
    _prefix_source = "/recurring_application_charge/$recurring_application_charge_id/"

    @classmethod
    def _prefix(cls, options={}):
        recurring_application_charge_id = options.get("recurring_application_charge_id")
        if recurring_application_charge_id:
            return "%s/recurring_application_charges/%s" % (cls.site, recurring_application_charge_id)
        else:
            return cls.site

class User(ShopifyResource):
    @classmethod
    def current(cls):
        return User(cls.get("current"))

class Variant(ShopifyResource, mixins.Metafields):
    _prefix_source = "/products/$product_id/"

    @classmethod
    def _prefix(cls, options={}):
        product_id = options.get("product_id")
        if product_id:
            return "%s/products/%s" % (cls.site, product_id)
        else:
            return cls.site

    def save(self):
        if "product_id" not in self._prefix_options:
            self._prefix_options["product_id"] = self.product_id

        start_api_version = "201910"
        api_version = ShopifyResource.version
        if api_version and (api_version.strip("-") >= start_api_version) and api_version != "unstable":
            if "inventory_quantity" in self.attributes:
                del self.attributes["inventory_quantity"]
            if "old_inventory_quantity" in self.attributes:
                del self.attributes["old_inventory_quantity"]

        return super(ShopifyResource, self).save()

class Webhook(ShopifyResource):
    def __get_format(self):
        return self.attributes.get("format")

    def __set_format(self, data):
        self.attributes["format"] = data

    format = property(__get_format, __set_format, None, "Format attribute")

