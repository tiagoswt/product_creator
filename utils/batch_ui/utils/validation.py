"""
Validation utilities for batch UI components
"""

import re
from typing import List, Tuple, Dict, Any
from urllib.parse import urlparse


class URLValidator:
    """Handles URL validation and cleaning"""

    @staticmethod
    def validate_urls(website_urls: str) -> Tuple[bool, List[str], str]:
        """
        Validate and clean up URLs

        Args:
            website_urls (str): Single URL or multiple URLs separated by commas

        Returns:
            tuple: (is_valid: bool, cleaned_urls: list, error_message: str)
        """
        if not website_urls:
            return False, [], "No URLs provided"

        url_list = [url.strip() for url in website_urls.split(",") if url.strip()]

        if not url_list:
            return False, [], "No valid URLs found"

        cleaned_urls = []
        invalid_urls = []

        for url in url_list:
            cleaned_url = URLValidator._clean_url(url)
            if URLValidator._is_valid_url(cleaned_url):
                cleaned_urls.append(cleaned_url)
            else:
                invalid_urls.append(url)

        if invalid_urls:
            error_msg = f"Invalid URLs found: {', '.join(invalid_urls)}"
            if cleaned_urls:
                return (
                    True,
                    cleaned_urls,
                    f"Some URLs are invalid: {', '.join(invalid_urls)}",
                )
            else:
                return False, [], error_msg

        return True, cleaned_urls, ""

    @staticmethod
    def _clean_url(url: str) -> str:
        """Clean and normalize a URL"""
        url = url.strip()

        # Add https if no protocol is specified
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        return url

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Basic URL validation"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and "." in result.netloc
        except:
            return False

    @staticmethod
    def get_url_preview(website_urls: str) -> str:
        """
        Get a preview of what URLs will be processed

        Args:
            website_urls (str): Single URL or multiple URLs separated by commas

        Returns:
            str: Formatted preview string
        """
        is_valid, cleaned_urls, error_msg = URLValidator.validate_urls(website_urls)

        if not is_valid:
            return f"❌ {error_msg}"

        if len(cleaned_urls) == 1:
            return f"✅ 1 URL ready: {cleaned_urls[0]}"
        else:
            preview = f"✅ {len(cleaned_urls)} URLs ready:\n"
            for i, url in enumerate(cleaned_urls[:3], 1):  # Show first 3 URLs
                preview += f"  {i}. {url}\n"

            if len(cleaned_urls) > 3:
                preview += f"  ... and {len(cleaned_urls) - 3} more"

            if error_msg:
                preview += f"\n⚠️ {error_msg}"

            return preview


class ConfigValidator:
    """Handles product configuration validation"""

    @staticmethod
    def validate_data_sources(
        pdf_file,
        pdf_pages: List[int],
        excel_file,
        excel_rows: List[int],
        website_url: str,
    ) -> Tuple[bool, str]:
        """
        Validate that at least one data source is configured

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        has_pdf = pdf_file and pdf_pages
        has_excel = excel_file and excel_rows
        has_website = website_url and website_url.strip()

        if not (has_pdf or has_excel or has_website):
            return (
                False,
                "Please select at least one data source (PDF pages, Excel rows, or Website URL).",
            )

        return True, ""

    @staticmethod
    def validate_page_numbers(
        page_input: str, max_pages: int
    ) -> Tuple[bool, List[int], str]:
        """
        Validate and parse page number input

        Returns:
            tuple: (is_valid: bool, page_list: List[int], error_message: str)
        """
        if not page_input.strip():
            return False, [], "No page numbers provided"

        try:
            page_numbers = [int(p.strip()) for p in page_input.split(",")]
            valid_pages = [p - 1 for p in page_numbers if 1 <= p <= max_pages]

            if len(valid_pages) != len(page_numbers):
                invalid_pages = [p for p in page_numbers if p < 1 or p > max_pages]
                return (
                    False,
                    [],
                    f"Invalid page numbers: {invalid_pages}. Pages must be between 1 and {max_pages}.",
                )

            return True, valid_pages, ""
        except ValueError:
            return (
                False,
                [],
                "Invalid page numbers. Please use comma-separated numbers.",
            )

    @staticmethod
    def validate_row_numbers(
        row_input: str, max_rows: int
    ) -> Tuple[bool, List[int], str]:
        """
        Validate and parse row number input

        Returns:
            tuple: (is_valid: bool, row_list: List[int], error_message: str)
        """
        if not row_input.strip():
            return False, [], "No row numbers provided"

        try:
            row_numbers = [int(r.strip()) for r in row_input.split(",")]
            valid_rows = [r for r in row_numbers if 0 <= r < max_rows]

            if len(valid_rows) != len(row_numbers):
                invalid_rows = [r for r in row_numbers if r < 0 or r >= max_rows]
                return (
                    False,
                    [],
                    f"Invalid row numbers: {invalid_rows}. Rows must be between 0 and {max_rows - 1}.",
                )

            return True, valid_rows, ""
        except ValueError:
            return False, [], "Invalid row numbers. Please use comma-separated numbers."

    @staticmethod
    def validate_model_config(
        model_provider: str, model_name: str, temperature: float
    ) -> Tuple[bool, str]:
        """
        Validate model configuration

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if model_provider not in ["groq", "openai"]:
            return False, f"Invalid model provider: {model_provider}"

        if not model_name or not model_name.strip():
            return False, "Model name is required"

        if not (0.0 <= temperature <= 1.0):
            return False, "Temperature must be between 0.0 and 1.0"

        return True, ""

    @staticmethod
    def validate_product_type(product_type: str) -> Tuple[bool, str]:
        """
        Validate product type

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        valid_types = ["cosmetics", "fragrance", "subtype"]

        if product_type not in valid_types:
            return (
                False,
                f"Invalid product type: {product_type}. Must be one of: {valid_types}",
            )

        return True, ""


class FileValidator:
    """Handles file validation"""

    @staticmethod
    def validate_pdf_file(pdf_file) -> Tuple[bool, str]:
        """
        Validate PDF file

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not pdf_file:
            return False, "No PDF file provided"

        if not pdf_file.name.lower().endswith(".pdf"):
            return False, "File must be a PDF"

        # Check file size (max 50MB)
        if pdf_file.size > 50 * 1024 * 1024:
            return False, "PDF file too large (max 50MB)"

        return True, ""

    @staticmethod
    def validate_excel_file(excel_file) -> Tuple[bool, str]:
        """
        Validate Excel/CSV file

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not excel_file:
            return False, "No Excel/CSV file provided"

        valid_extensions = [".xlsx", ".xls", ".csv"]
        if not any(excel_file.name.lower().endswith(ext) for ext in valid_extensions):
            return False, f"File must be Excel or CSV ({', '.join(valid_extensions)})"

        # Check file size (max 25MB)
        if excel_file.size > 25 * 1024 * 1024:
            return False, "Excel/CSV file too large (max 25MB)"

        return True, ""


class FormValidator:
    """Handles form validation"""

    @staticmethod
    def validate_custom_instructions(instructions: str) -> Tuple[bool, str]:
        """
        Validate custom instructions

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if instructions and len(instructions) > 2000:
            return False, "Custom instructions too long (max 2000 characters)"

        return True, ""

    @staticmethod
    def validate_complete_form(form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete form data

        Returns:
            tuple: (is_valid: bool, error_messages: List[str])
        """
        errors = []

        # Validate data sources
        is_valid, error = ConfigValidator.validate_data_sources(
            form_data.get("pdf_file"),
            form_data.get("pdf_pages", []),
            form_data.get("excel_file"),
            form_data.get("excel_rows", []),
            form_data.get("website_url", ""),
        )
        if not is_valid:
            errors.append(error)

        # Validate model config
        is_valid, error = ConfigValidator.validate_model_config(
            form_data.get("model_provider", ""),
            form_data.get("model_name", ""),
            form_data.get("temperature", 0.0),
        )
        if not is_valid:
            errors.append(error)

        # Validate product type
        is_valid, error = ConfigValidator.validate_product_type(
            form_data.get("product_type", "")
        )
        if not is_valid:
            errors.append(error)

        # Validate custom instructions
        is_valid, error = FormValidator.validate_custom_instructions(
            form_data.get("custom_instructions", "")
        )
        if not is_valid:
            errors.append(error)

        # Validate files if provided
        if form_data.get("pdf_file"):
            is_valid, error = FileValidator.validate_pdf_file(form_data["pdf_file"])
            if not is_valid:
                errors.append(f"PDF: {error}")

        if form_data.get("excel_file"):
            is_valid, error = FileValidator.validate_excel_file(form_data["excel_file"])
            if not is_valid:
                errors.append(f"Excel: {error}")

        # Validate URLs if provided
        if form_data.get("website_url"):
            is_valid, _, error = URLValidator.validate_urls(form_data["website_url"])
            if not is_valid:
                errors.append(f"Website: {error}")

        return len(errors) == 0, errors
