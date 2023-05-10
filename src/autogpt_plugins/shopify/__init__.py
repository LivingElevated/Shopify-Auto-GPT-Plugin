"""This is a Shopify integration plugin for Auto-GPT."""
import os
import os.path
import shopify
from typing import Any, Dict, List, Optional, Tuple, TypeVar, TypedDict
from auto_gpt_plugin_template import AutoGPTPluginTemplate


PromptGenerator = TypeVar("PromptGenerator")

shopify_api_key = os.getenv('SHOPIFY_API_Key')
shopify_api_secret = os.getenv('SHOPIFY_API_SECRET')
shopify_password = os.getenv('SHOPIFY_PASSWORD')
store_url = os.getenv('STORE_URL')
api_version = os.getenv('API_VERSION')

class Message(TypedDict):
    role: str
    content: str


class ShopifyAutoGPT(AutoGPTPluginTemplate):
    """
    Auto GPT integrations using ShopifyAPI
    """

    def __init__(self):
        super().__init__()
        self._name = "Shopify-AutoGPT"
        self._version = "0.0.1"
        self._description = "AutoGPT integrations using ShopifyAPI."


        # Initialize Shopify API
        if (
            shopify_api_key
            and shopify_api_secret
            and shopify_password
            and store_url
            and api_version

        ) is not None:
            session = shopify.Session(store_url, api_version, shopify_password)
            self.client = shopify.ShopifyResource.activate_session(session)
            print('Starting Shopify Connection...')
            self.shop = shopify.Shop
            self.shop.current()

        else:
            print("Shopify credentials not found in .env file.")

    def can_handle_on_response(self) -> bool:
        """This method is called to check that the plugin can
        handle the on_response method.

        Returns:
            bool: True if the plugin can handle the on_response method."""
        return False


    def on_response(self, response: str, *args, **kwargs) -> str:
        """This method is called when a response is received from the model."""
        pass


    def can_handle_post_prompt(self) -> bool:
        """This method is called to check that the plugin can
        handle the post_prompt method.

        Returns:
            bool: True if the plugin can handle the post_prompt method."""
        return False

 
    def post_prompt(self, prompt: PromptGenerator) -> PromptGenerator:
        """This method is called just after the generate_prompt is called,
            but actually before the prompt is generated.

        Args:
            prompt (PromptGenerator): The prompt generator.

        Returns:
            PromptGenerator: The prompt generator.
        """

        if self.api:
            from .shopifygpt import (
                create_product,
                get_product,
                get_all_products,
                update_product,
                delete_product,
                create_collection,
                add_product_to_collection,
                get_all_collections,
                update_collection,
                delete_collection,
                search_products_by_title,
                get_all_themes,
                get_active_theme,
                get_theme_assets,
                get_theme_asset,
                update_theme_asset,
                delete_theme_asset,

            )

            
            prompt.add_command(
                "Create Product",
                "create_product",
                {
                    "title": "<title>",
                    "description": "<description>"
                },
                create_product
            ),

            prompt.add_command(
                "Get Product",
                "get_product",
                {
                    "product_id": "<product_id>"
                },
                get_product
            ),

            prompt.add_command(
                "Get All Products",
                "get_all_products",
                {},
                get_all_products
            ),

            prompt.add_command(
                "Update Product",
                "update_product",
                {
                    "product_id": "<product_id>",
                    "title": "<title>",
                    "description": "<description>"
                },
                update_product
            ),

            prompt.add_command(
                "Delete Product",
                "delete_product",
                {
                    "product_id": "<product_id>"
                },
                delete_product
            ),
            
            prompt.add_command(
                "Create Collection",
                "create_collection",
                {
                    "title": "<title>",
                    "collection_type": "<collection_type>"
                },
                create_collection
            ),

            prompt.add_command(
                "Create Collection",
                "create_collection",
                {
                    "title": "<title>",
                    "collection_type": "<collection_type>"
                },
                create_collection
            ),

            prompt.add_command(
                "Add Product to Collection",
                "add_product_to_collection",
                {
                    "product_id": "<product_id>",
                    "collection_id": "<collection_id>"
                },
                add_product_to_collection
            ),

            prompt.add_command(
                "Get All Collections",
                "get_all_collections",
                {
                    "collection_type": "<collection_type>"
                },
                get_all_collections
            ),

            prompt.add_command(
                "Update Collection",
                "update_collection",
                {
                    "collection_id": "<collection_id>",
                    "title": "<title>",
                    "collection_type": "<collection_type>"
                },
                update_collection
            ),

            prompt.add_command(
                "Delete Collection",
                "delete_collection",
                {
                    "collection_id": "<collection_id>",
                    "collection_type": "<collection_type>"
                },
                delete_collection
            ),

            prompt.add_command(
                "Search Products by Title",
                "search_products_by_title",
                {
                    "title": "<title>"
                },
                search_products_by_title
            ),

            prompt.add_command(
                "Get All Themes",
                "get_all_themes",
                {},
                get_all_themes
            ),

            prompt.add_command(
                "Get Active Theme",
                "get_active_theme",
                {},
                get_active_theme
            ),

            prompt.add_command(
                "Get Theme Assets",
                "get_theme_assets",
                {
                    "theme_id": "<theme_id>"
                },
                get_theme_assets
            ),

            prompt.add_command(
                "Get Theme Asset",
                "get_theme_asset",
                {
                    "theme_id": "<theme_id>",
                    "asset_key": "<asset_key>"
                },
                get_theme_asset
            ),

            prompt.add_command(
                "Update Theme Asset",
                "update_theme_asset",
                {
                    "theme_id": "<theme_id>",
                    "asset_key": "<asset_key>",
                    "new_asset_value": "<new_asset_value>"
                },
                update_theme_asset
            ),

            prompt.add_command(
                "Delete Theme Asset",
                "delete_theme_asset",
                {
                    "theme_id": "<theme_id>",
                    "asset_key": "<asset_key>"
                },
                delete_theme_asset
            ),
        return prompt


    def can_handle_on_planning(self) -> bool:
        """This method is called to check that the plugin can
        handle the on_planning method.

        Returns:
            bool: True if the plugin can handle the on_planning method."""
        return False


    def on_planning(
        self, prompt: PromptGenerator, messages: List[Message]
    ) -> Optional[str]:
        """This method is called before the planning chat completion is done.

        Args:
            prompt (PromptGenerator): The prompt generator.
            messages (List[str]): The list of messages.
        """
        pass


    def can_handle_post_planning(self) -> bool:
        """This method is called to check that the plugin can
        handle the post_planning method.

        Returns:
            bool: True if the plugin can handle the post_planning method."""
        return False


    def post_planning(self, response: str) -> str:
        """This method is called after the planning chat completion is done.

        Args:
            response (str): The response.

        Returns:
            str: The resulting response.
        """
        pass


    def can_handle_pre_instruction(self) -> bool:
        """This method is called to check that the plugin can
        handle the pre_instruction method.

        Returns:
            bool: True if the plugin can handle the pre_instruction method."""
        return False

    def pre_instruction(self, messages: List[Message]) -> List[Message]:
        """This method is called before the instruction chat is done.

        Args:
            messages (List[Message]): The list of context messages.

        Returns:
            List[Message]: The resulting list of messages.
        """
        pass


    def can_handle_on_instruction(self) -> bool:
        """This method is called to check that the plugin can
        handle the on_instruction method.

        Returns:
            bool: True if the plugin can handle the on_instruction method."""
        return False


    def on_instruction(self, messages: List[Message]) -> Optional[str]:
        """This method is called when the instruction chat is done.

        Args:
            messages (List[Message]): The list of context messages.

        Returns:
            Optional[str]: The resulting message.
        """
        pass

    def can_handle_post_instruction(self) -> bool:
        """This method is called to check that the plugin can
        handle the post_instruction method.

        Returns:
            bool: True if the plugin can handle the post_instruction method."""
        return False

    def post_instruction(self, response: str) -> str:
        """This method is called after the instruction chat is done.

        Args:
            response (str): The response.

        Returns:
            str: The resulting response.
        """
        pass

    def can_handle_pre_command(self) -> bool:
        """This method is called to check that the plugin can
        handle the pre_command method.

        Returns:
            bool: True if the plugin can handle the pre_command method."""
        return False

    def pre_command(
        self, command_name: str, arguments: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """This method is called before the command is executed.

        Args:
            command_name (str): The command name.
            arguments (Dict[str, Any]): The arguments.

        Returns:
            Tuple[str, Dict[str, Any]]: The command name and the arguments.
        """
        pass

    def can_handle_post_command(self) -> bool:
        """This method is called to check that the plugin can
        handle the post_command method.

        Returns:
            bool: True if the plugin can handle the post_command method."""
        return False


    def post_command(self, command_name: str, response: str) -> str:
        """This method is called after the command is executed.

        Args:
            command_name (str): The command name.
            response (str): The response.

        Returns:
            str: The resulting response.
        """
        pass


    def can_handle_chat_completion(
        self, messages: Dict[Any, Any], model: str, temperature: float, max_tokens: int
    ) -> bool:
        """This method is called to check that the plugin can
          handle the chat_completion method.

        Args:
            messages (List[Message]): The messages.
            model (str): The model name.
            temperature (float): The temperature.
            max_tokens (int): The max tokens.

          Returns:
              bool: True if the plugin can handle the chat_completion method."""
        return False

    def handle_chat_completion(
        self, messages: List[Message], model: str, temperature: float, max_tokens: int
    ) -> str:
        """This method is called when the chat completion is done.

        Args:
            messages (List[Message]): The messages.
            model (str): The model name.
            temperature (float): The temperature.
            max_tokens (int): The max tokens.

        Returns:
            str: The resulting response.
        """
        pass

    def can_handle_text_embedding(
        self, text: str
    ) -> bool:
        """This method is called to check that the plugin can
          handle the text_embedding method.
        Args:
            text (str): The text to be convert to embedding.
          Returns:
              bool: True if the plugin can handle the text_embedding method."""
        return False

    def handle_text_embedding(
        self, text: str
    ) -> list:
        """This method is called when the chat completion is done.
        Args:
            text (str): The text to be convert to embedding.
        Returns:
            list: The text embedding.
        """
        pass

    def can_handle_user_input(self, user_input: str) -> bool:
        """This method is called to check that the plugin can
        handle the user_input method.

        Args:
            user_input (str): The user input.

        Returns:
            bool: True if the plugin can handle the user_input method."""
        return False


    def user_input(self, user_input: str) -> str:
        """This method is called to request user input to the user.

        Args:
            user_input (str): The question or prompt to ask the user.

        Returns:
            str: The user input.
        """

        pass

    def can_handle_report(self) -> bool:
        """This method is called to check that the plugin can
        handle the report method.

        Returns:
            bool: True if the plugin can handle the report method."""
        return False

    def report(self, message: str) -> None:
        """This method is called to report a message to the user.

        Args:
            message (str): The message to report.
        """
        pass
