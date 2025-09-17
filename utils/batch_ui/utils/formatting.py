"""
Formatting utilities for batch UI components
"""

import re
from typing import Dict, Any, List
from datetime import datetime
from processors.text_processor import get_hscode_from_product_data


class ResultFormatter:
    """Handles formatting of extraction results"""

    @staticmethod
    def _get_product_name_from_result(result):
        """
        Extract product name from result, trying multiple possible field names

        Args:
            result (dict): Product result data

        Returns:
            str: Product name
        """
        # Try different field names in order of preference
        name_fields = [
            "ItemDescriptionEN",  # For cosmetics and subtype (updated case)
            "itemDescriptionEN",  # For cosmetics and subtype (legacy case)
            "product_name",  # For fragrance
            "product_title_EN",  # Alternative from catalogA
            "ItemDescriptionPT",  # Portuguese fallback (updated case)
            "itemDescriptionPT",  # Portuguese fallback (legacy case)
            "product_title_PT",  # Portuguese fallback
        ]

        for field in name_fields:
            # Handle nested catalogB structure
            if "catalogB" in result and isinstance(result["catalogB"], dict):
                value = result["catalogB"].get(field)
                if (
                    value
                    and value.strip()
                    and value.lower() not in ["", "null", "none", "unknown"]
                ):
                    return value.strip()

            # Handle flat structure
            value = result.get(field)
            if (
                value
                and value.strip()
                and value.lower() not in ["", "null", "none", "unknown"]
            ):
                return value.strip()

        return "Unknown Product"

    @staticmethod
    def _get_brand_from_result(result):
        """
        Extract brand from result, handling nested structures

        Args:
            result (dict): Product result data

        Returns:
            str: Brand name
        """
        # Try different field names and structures
        brand_fields = ["brand", "Brand", "BRAND"]

        for field in brand_fields:
            # Handle nested catalogA or catalogB structure
            for catalog in ["catalogA", "catalogB"]:
                if catalog in result and isinstance(result[catalog], dict):
                    value = result[catalog].get(field)
                    if (
                        value
                        and value.strip()
                        and value.lower() not in ["", "null", "none", "unknown"]
                    ):
                        return value.strip()

            # Handle flat structure
            value = result.get(field)
            if (
                value
                and value.strip()
                and value.lower() not in ["", "null", "none", "unknown"]
            ):
                return value.strip()

        return "Unknown"

    @staticmethod
    def format_product_title(result: Dict[str, Any]) -> str:
        """Format a product title for display"""
        brand = ResultFormatter._get_brand_from_result(result)
        product_name = ResultFormatter._get_product_name_from_result(result)
        return f"{brand} - {product_name}"

    @staticmethod
    def format_price_display(result: Dict[str, Any]) -> str:
        """Format price for display"""
        # Try different possible price fields and nested structures
        price_fields = ["priceSale", "priceRecommended", "price"]
        currency_fields = ["currency"]

        price = None
        currency = ""

        # Check for nested structure
        for catalog in ["catalogB", "catalogA"]:
            if catalog in result and isinstance(result[catalog], dict):
                for field in price_fields:
                    if field in result[catalog]:
                        price = result[catalog][field]
                        break
                for field in currency_fields:
                    if field in result[catalog]:
                        currency = result[catalog][field]
                        break
                if price is not None:
                    break

        # Check flat structure if not found in nested
        if price is None:
            price = result.get("price")
        if not currency:
            currency = result.get("currency", "")

        if price is None:
            return "N/A"

        if currency:
            return f"{price} {currency}"
        else:
            return str(price)

    @staticmethod
    def format_size_display(result: Dict[str, Any]) -> str:
        """Format size for display"""
        # Try different possible size fields and nested structures
        size_fields = ["itemCapacity", "size"]
        unit_fields = ["itemCapacityUnits", "unit"]

        size = None
        unit = ""

        # Check for nested structure
        for catalog in ["catalogB", "catalogA"]:
            if catalog in result and isinstance(result[catalog], dict):
                for field in size_fields:
                    if field in result[catalog]:
                        size = result[catalog][field]
                        break
                for field in unit_fields:
                    if field in result[catalog]:
                        unit = result[catalog][field]
                        break
                if size is not None:
                    break

        # Check flat structure if not found in nested
        if size is None:
            for field in size_fields:
                if field in result:
                    size = result[field]
                    break
        if not unit:
            for field in unit_fields:
                if field in result:
                    unit = result[field]
                    break

        if size is None:
            return "N/A"

        if unit:
            return f"{size} {unit}"
        else:
            return str(size)

    @staticmethod
    def format_ingredients_display(result: Dict[str, Any]) -> str:
        """Format ingredients for display"""
        # Try different possible ingredients fields and nested structures
        ingredients_fields = ["ingredients"]

        ingredients = None

        # Check for nested structure
        for catalog in ["catalogB", "catalogA"]:
            if catalog in result and isinstance(result[catalog], dict):
                for field in ingredients_fields:
                    if field in result[catalog]:
                        ingredients = result[catalog][field]
                        break
                if ingredients is not None:
                    break

        # Check flat structure if not found in nested
        if ingredients is None:
            ingredients = result.get("ingredients", [])

        if not ingredients:
            return "N/A"

        if isinstance(ingredients, list):
            return ", ".join(
                str(ingredient) for ingredient in ingredients[:5]
            )  # Show first 5
        else:
            return str(ingredients)

    @staticmethod
    def create_product_summary(result: Dict[str, Any]) -> Dict[str, str]:
        """Create a formatted summary of product information"""
        return {
            "title": ResultFormatter.format_product_title(result),
            "price": ResultFormatter.format_price_display(result),
            "size": ResultFormatter.format_size_display(result),
            "type": result.get("product_type", "N/A"),
            "hscode": get_hscode_from_product_data(result)
            or "N/A",  # CHANGED THIS LINE
            "ean": result.get("EAN", "N/A"),
            "cnp": result.get("CNP", "N/A"),
        }

    @staticmethod
    def create_copy_text(result: Dict[str, Any]) -> str:
        """Create formatted text for copying product information"""
        brand = ResultFormatter._get_brand_from_result(result)
        product_name = ResultFormatter._get_product_name_from_result(result)

        copy_text = f"""Product: {brand} {product_name}
    Brand: {brand}
    Price: {ResultFormatter.format_price_display(result)}
    Type: {result.get('product_type', 'N/A')}
    Size: {ResultFormatter.format_size_display(result)}
    HScode: {get_hscode_from_product_data(result) or 'N/A'}
    EAN: {result.get('EAN', 'N/A')}
    CNP: {result.get('CNP', 'N/A')}"""

        return copy_text


class DisplayFormatter:
    """Handles display formatting for UI components"""

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size for display"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    @staticmethod
    def format_processing_time(seconds: float) -> str:
        """Format processing time for display"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    @staticmethod
    def format_timestamp(timestamp: datetime) -> str:
        """Format timestamp for display"""
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def format_source_summary(config) -> str:
        """Format data source summary for configuration display"""
        sources = []

        if config.pdf_file and config.pdf_pages:
            sources.append(
                f"PDF: {config.pdf_file.name} (Pages: {', '.join(str(p+1) for p in config.pdf_pages)})"
            )

        if config.excel_file and config.excel_rows:
            file_type = (
                "CSV" if config.excel_file.name.lower().endswith(".csv") else "Excel"
            )
            sources.append(
                f"{file_type}: {config.excel_file.name} (Rows: {', '.join(str(r) for r in config.excel_rows)})"
            )

        if config.website_url:
            url_count = len(
                [url.strip() for url in config.website_url.split(",") if url.strip()]
            )
            if url_count == 1:
                sources.append(f"Website: {config.website_url.strip()}")
            else:
                sources.append(f"Websites: {url_count} URLs")

        if not sources:
            return "No data sources selected"

        return " | ".join(sources)

    @staticmethod
    def format_model_display(config) -> str:
        """Format model information for display"""
        return f"{config.model_provider}/{config.model_name}"

    @staticmethod
    def format_status_icon(status: str) -> str:
        """Get status icon for display"""
        status_icons = {
            "completed": "✅",
            "failed": "❌",
            "processing": "⏳",
            "pending": "⏳",
        }
        return status_icons.get(status, "❓")

    @staticmethod
    def format_progress_message(
        current: int, total: int, item_name: str = "item"
    ) -> str:
        """Format progress message"""
        return f"Processing {current}/{total} {item_name}s..."

    @staticmethod
    def truncate_text(text: str, max_length: int = 50) -> str:
        """Truncate text for display"""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


class FilenameFormatter:
    """Handles filename formatting for exports"""

    @staticmethod
    def clean_filename_component(text: str) -> str:
        """Clean text for use in filenames"""
        # Remove or replace invalid filename characters
        text = re.sub(r'[<>:"/\\|?*]', "", text)
        # Replace spaces with underscores
        text = text.replace(" ", "_")
        # Remove multiple underscores
        text = re.sub(r"_+", "_", text)
        # Strip leading/trailing underscores
        text = text.strip("_")
        return text

    @staticmethod
    def create_product_filename(
        result: Dict[str, Any], suffix: str = "", extension: str = ".json"
    ) -> str:
        """Create a clean filename for a product"""
        product_name = ResultFormatter._get_product_name_from_result(result)
        brand = ResultFormatter._get_brand_from_result(result)

        # Clean components
        clean_brand = FilenameFormatter.clean_filename_component(brand)
        clean_product_name = FilenameFormatter.clean_filename_component(product_name)

        # Build filename parts
        filename_parts = []
        if clean_brand and clean_brand.lower() != "unknown":
            filename_parts.append(clean_brand)
        filename_parts.append(clean_product_name)

        # Create base filename
        base_filename = "_".join(filename_parts)[:50]  # Limit length

        if suffix:
            base_filename += f"_{suffix}"

        return f"{base_filename}{extension}"

    @staticmethod
    def create_bulk_filename(
        prefix: str = "products", suffix: str = "", extension: str = ".json"
    ) -> str:
        """Create filename for bulk exports"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        parts = [prefix]
        if suffix:
            parts.append(suffix)
        parts.append(timestamp)

        filename = "_".join(parts)
        return f"{filename}{extension}"

    @staticmethod
    def create_timestamped_filename(base_name: str, extension: str = ".json") -> str:
        """Create a timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_base = FilenameFormatter.clean_filename_component(base_name)
        return f"{clean_base}_{timestamp}{extension}"


class TableFormatter:
    """Handles table formatting for display"""

    @staticmethod
    def format_results_for_table(results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Format results for table display"""
        formatted_results = []

        for result in results:
            formatted_result = {
                "Brand": ResultFormatter._get_brand_from_result(result),
                "Product": ResultFormatter._get_product_name_from_result(result),
                "Type": result.get("product_type", "N/A"),
                "Price": ResultFormatter.format_price_display(result),
                "Size": ResultFormatter.format_size_display(result),
                "HScode": get_hscode_from_product_data(result)
                or "N/A",  # CHANGED THIS LINE
                "EAN": result.get("EAN", "N/A"),
            }
            formatted_results.append(formatted_result)

        return formatted_results

    @staticmethod
    def format_config_for_table(configs: List) -> List[Dict[str, str]]:
        """Format configurations for table display"""
        formatted_configs = []

        for i, config in enumerate(configs):
            formatted_config = {
                "ID": str(i + 1),
                "Product Type": config.product_type.title(),
                "Model": DisplayFormatter.format_model_display(config),
                "Status": config.status.title(),
                "Sources": DisplayFormatter.format_source_summary(config),
            }
            formatted_configs.append(formatted_config)

        return formatted_configs


class URLFormatter:
    """Handles URL formatting for display"""

    @staticmethod
    def format_url_list(urls: str) -> List[str]:
        """Format comma-separated URLs into a clean list"""
        if not urls:
            return []

        url_list = [url.strip() for url in urls.split(",") if url.strip()]
        return url_list

    @staticmethod
    def format_url_preview(urls: str, max_display: int = 3) -> str:
        """Format URL preview for display"""
        url_list = URLFormatter.format_url_list(urls)

        if not url_list:
            return "No URLs"

        if len(url_list) == 1:
            return f"1 URL: {url_list[0]}"

        preview_urls = url_list[:max_display]
        preview = f"{len(url_list)} URLs:\n"

        for i, url in enumerate(preview_urls, 1):
            preview += f"  {i}. {DisplayFormatter.truncate_text(url, 60)}\n"

        if len(url_list) > max_display:
            preview += f"  ... and {len(url_list) - max_display} more"

        return preview.strip()

