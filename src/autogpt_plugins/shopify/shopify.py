import shopify
import code
import sys
import os
import os.path
import glob
import subprocess
import functools
import yaml
import six
from . import AutoGPTShopify
from six.moves import input, map
import requests


class Shopify():
    def start_interpreter(**variables):
        # add the current working directory to the sys paths
        sys.path.append(os.getcwd())
        console = type("shopify " + shopify.version.VERSION, (code.InteractiveConsole, object), {})
        import readline

        console(variables).interact()

    def on_message(self, message, data):
        if "shopify" in message.lower():
            # Add your desired functionality here
            # e.g., Generate a product description for a specific product
            product_title = "Sample Product"
            prompt = f"Write a captivating product description for a {product_title}."
            description = self.chatgpt_response(prompt)
            return description

        return None

    def help(self):
        return "This plugin integrates with the Shopify API to generate product descriptions, analyze store data, and more."

    def name(self):
        return "ShopifyPlugin"

    def version(self):
        return "1.0.0"

    def usage(usage_string):
        """Decorator to add a usage string to a function"""

        def decorate(func):
            func.usage = usage_string
            return func

        return decorate

    def create_product(self, title, description=None):
        product = shopify.Product()
        product.title = title

        if not description:
            prompt = f"Write a captivating product description for a {title}."
            description = self.chatgpt_response(prompt)

        product.body_html = description
        product.save()
        return product

    def get_product(self, product_id):
        return shopify.Product.find(product_id)

    def get_all_products(self):
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

    def start_interpreter(**variables):
        # add the current working directory to the sys paths
        sys.path.append(os.getcwd())
        console = type("shopify " + shopify.version.VERSION, (code.InteractiveConsole, object), {})
        import readline

        console(variables).interact()

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


class ConfigFileError(Exception):
    pass


class TasksMeta(type):
    _prog = os.path.basename(sys.argv[0])

    def __new__(mcs, name, bases, new_attrs):
        cls = type.__new__(mcs, name, bases, new_attrs)

        tasks = list(new_attrs.keys())
        tasks.append("help")

        def filter_func(item):
            return not item.startswith("_") and hasattr(getattr(cls, item), "__call__")

        tasks = filter(filter_func, tasks)
        cls._tasks = sorted(tasks)

        return cls

    def run_task(cls, task=None, *args):
        if task in [None, "-h", "--help"]:
            cls.help()
            return

        # Allow unambiguous abbreviations of tasks
        if task not in cls._tasks:
            matches = filter(lambda item: item.startswith(task), cls._tasks)
            list_of_matches = list(matches)
            if len(list_of_matches) == 1:
                task = list_of_matches[0]
            else:
                sys.stderr.write('Could not find task "%s".\n' % (task))

        task_func = getattr(cls, task)
        task_func(*args)

    @usage("help [TASK]")
    def help(cls, task=None):
        """Describe available tasks or one specific task"""
        if task is None:
            usage_list = []
            for task in iter(cls._tasks):
                task_func = getattr(cls, task)
                usage_string = "  %s %s" % (cls._prog, task_func.usage)
                desc = task_func.__doc__.splitlines()[0]
                usage_list.append((usage_string, desc))
            max_len = functools.reduce(lambda m, item: max(m, len(item[0])), usage_list, 0)
            print("Tasks:")
            cols = int(os.environ.get("COLUMNS", 80))
            for line, desc in usage_list:
                task_func = getattr(cls, task)
                if desc:
                    line = "%s%s  # %s" % (line, " " * (max_len - len(line)), desc)
                if len(line) > cols:
                    line = line[: cols - 3] + "..."
                print(line)
        else:
            task_func = getattr(cls, task)
            print("Usage:")
            print("  %s %s" % (cls._prog, task_func.usage))
            print("")
            print(task_func.__doc__)


@six.add_metaclass(TasksMeta)
class Tasks(object):
    _shop_config_dir = os.path.join(os.environ["HOME"], ".shopify", "shops")
    _default_symlink = os.path.join(_shop_config_dir, "default")
    _default_api_version = "unstable"

    @classmethod
    @usage("list")
    def list(cls):
        """list available connections"""
        for c in cls._available_connections():
            prefix = " * " if cls._is_default(c) else "   "
            print(prefix + c)

    @classmethod
    @usage("add CONNECTION")
    def add(cls, connection):
        """create a config file for a connection named CONNECTION"""
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            raise ConfigFileError("There is already a config file at " + filename)
        else:
            config = dict(protocol="https")
            domain = input("Domain? (leave blank for %s.myshopify.com) " % (connection))
            if not domain.strip():
                domain = "%s.myshopify.com" % (connection)
            config["domain"] = domain
            print("")
            print("open https://%s/admin/apps/private in your browser to generate API credentials" % (domain))
            config["api_key"] = input("API key? ")
            config["password"] = input("Password? ")
            config["api_version"] = input("API version? (leave blank for %s) " % (cls._default_api_version))
            if not config["api_version"].strip():
                config["api_version"] = cls._default_api_version

            if not os.path.isdir(cls._shop_config_dir):
                os.makedirs(cls._shop_config_dir)
            with open(filename, "w") as f:
                f.write(yaml.dump(config, default_flow_style=False, explicit_start="---"))
        if len(list(cls._available_connections())) == 1:
            cls.default(connection)

    @classmethod
    @usage("remove CONNECTION")
    def remove(cls, connection):
        """remove the config file for CONNECTION"""
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            if cls._is_default(connection):
                os.remove(cls._default_symlink)
            os.remove(filename)
        else:
            cls._no_config_file_error(filename)

    @classmethod
    @usage("edit [CONNECTION]")
    def edit(cls, connection=None):
        """open the config file for CONNECTION with you default editor"""
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            editor = os.environ.get("EDITOR")
            if editor:
                subprocess.call([editor, filename])
            else:
                print("Please set an editor in the EDITOR environment variable")
        else:
            cls._no_config_file_error(filename)

    @classmethod
    @usage("show [CONNECTION]")
    def show(cls, connection=None):
        """output the location and contents of the CONNECTION's config file"""
        if connection is None:
            connection = cls._default_connection()
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            print(filename)
            with open(filename) as f:
                print(f.read())
        else:
            cls._no_config_file_error(filename)

    @classmethod
    @usage("default [CONNECTION]")
    def default(cls, connection=None):
        """show the default connection, or make CONNECTION the default"""
        if connection is not None:
            target = cls._get_config_filename(connection)
            if os.path.exists(target):
                if os.path.exists(cls._default_symlink):
                    os.remove(cls._default_symlink)
                os.symlink(target, cls._default_symlink)
            else:
                cls._no_config_file_error(target)
        if os.path.exists(cls._default_symlink):
            print("Default connection is " + cls._default_connection())
        else:
            print("There is no default connection set")

    @classmethod
    @usage("console [CONNECTION]")
    def console(cls, connection=None):
        """start an API console for CONNECTION"""
        filename = cls._get_config_filename(connection)
        if not os.path.exists(filename):
            cls._no_config_file_error(filename)

        with open(filename) as f:
            config = yaml.safe_load(f.read())
        print("using %s" % (config["domain"]))
        session = cls._session_from_config(config)
        shopify.ShopifyResource.activate_session(session)

        start_interpreter(shopify=shopify)

    @classmethod
    @usage("version")
    def version(cls):
        """output the shopify library version"""
        print(shopify.version.VERSION)

    @classmethod
    def _available_connections(cls):
        return map(
            lambda item: os.path.splitext(os.path.basename(item))[0],
            glob.glob(os.path.join(cls._shop_config_dir, "*.yml")),
        )

    @classmethod
    def _default_connection_target(cls):
        if not os.path.exists(cls._default_symlink):
            return None
        target = os.readlink(cls._default_symlink)
        return os.path.join(cls._shop_config_dir, target)

    @classmethod
    def _default_connection(cls):
        target = cls._default_connection_target()
        if not target:
            return None
        return os.path.splitext(os.path.basename(target))[0]

    @classmethod
    def _get_config_filename(cls, connection):
        if connection is None:
            return cls._default_symlink
        else:
            return os.path.join(cls._shop_config_dir, connection + ".yml")

    @classmethod
    def _session_from_config(cls, config):
        session = shopify.Session(config.get("domain"), config.get("api_version", cls._default_api_version))
        session.protocol = config.get("protocol", "https")
        session.api_key = config.get("api_key")
        session.token = config.get("password")
        return session

    @classmethod
    def _is_default(cls, connection):
        return connection == cls._default_connection()

    @classmethod
    def _no_config_file_error(cls, filename):
        raise ConfigFileError("There is no config file at " + filename)


try:
    Tasks.run_task(*sys.argv[1:])
except ConfigFileError as e:
    print(e)
