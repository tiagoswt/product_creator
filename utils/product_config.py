"""
Module for handling product configurations in batch processing mode
"""

import uuid
import streamlit as st
from typing import Dict, List, Any, Optional


class ProductConfig:
    """Class to represent a single product configuration for extraction"""

    def __init__(
        self,
        product_type: str = "cosmetics",
        prompt_file: str = None,
        pdf_file=None,
        pdf_pages: List[int] = None,
        excel_file=None,
        excel_rows: List[int] = None,
        website_url: str = None,
        model_provider: str = "groq",
        model_name: str = None,
        temperature: float = 0.2,
        custom_instructions: str = "",  # Add custom instructions field
    ):
        self.id = str(uuid.uuid4())
        self.product_type = product_type
        self.prompt_file = prompt_file
        self.pdf_file = pdf_file
        self.pdf_pages = pdf_pages or []
        self.excel_file = excel_file
        self.excel_rows = excel_rows or []
        self.website_url = website_url
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self.custom_instructions = custom_instructions  # Store custom instructions
        self.status = "pending"  # pending, processing, completed, failed
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary"""
        return {
            "id": self.id,
            "product_type": self.product_type,
            "prompt_file": self.prompt_file,
            "pdf_file_name": self.pdf_file.name if self.pdf_file else None,
            "pdf_pages": self.pdf_pages,
            "excel_file_name": self.excel_file.name if self.excel_file else None,
            "excel_rows": self.excel_rows,
            "website_url": self.website_url,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "custom_instructions": self.custom_instructions,  # Include in dictionary
            "status": self.status,
        }

    def has_data_source(self) -> bool:
        """Check if the configuration has at least one data source"""
        return (
            (self.pdf_file is not None and self.pdf_pages)
            or (self.excel_file is not None and self.excel_rows)
            or (self.website_url is not None and self.website_url.strip() != "")
        )

    def source_summary(self) -> str:
        """Get a summary of the data sources for this configuration"""
        sources = []

        if self.pdf_file is not None and self.pdf_pages:
            sources.append(
                f"PDF: {self.pdf_file.name} (Pages: {', '.join(str(p+1) for p in self.pdf_pages)})"
            )

        if self.excel_file is not None and self.excel_rows:
            # Determine if it's CSV or Excel based on file extension
            file_type = (
                "CSV" if self.excel_file.name.lower().endswith(".csv") else "Excel"
            )
            sources.append(
                f"{file_type}: {self.excel_file.name} (Rows: {', '.join(str(r) for r in self.excel_rows)})"
            )

        if self.website_url:
            sources.append(f"Website: {self.website_url}")

        if not sources:
            return "No data sources selected"

        return " | ".join(sources)


def migrate_product_configs():
    """
    Migrate existing product configurations to include new attributes
    This ensures backward compatibility with older configurations in session state
    """
    if "product_configs" not in st.session_state:
        return

    # Update all existing configs
    for config in st.session_state.product_configs:
        # Add custom_instructions attribute if it doesn't exist
        if not hasattr(config, "custom_instructions"):
            config.custom_instructions = ""

    # Optional: Log that migration has been performed
    print("Migrated existing product configurations")


def get_product_configs() -> List[ProductConfig]:
    """Get the list of product configurations from session state"""
    if "product_configs" not in st.session_state:
        st.session_state.product_configs = []
    return st.session_state.product_configs


def add_product_config(config: ProductConfig) -> None:
    """Add a product configuration to the session state"""
    if "product_configs" not in st.session_state:
        st.session_state.product_configs = []
    st.session_state.product_configs.append(config)


def update_product_config(config: ProductConfig) -> None:
    """Update an existing product configuration"""
    if "product_configs" not in st.session_state:
        st.session_state.product_configs = []
        return

    for i, existing_config in enumerate(st.session_state.product_configs):
        if existing_config.id == config.id:
            st.session_state.product_configs[i] = config
            break


def remove_product_config(config_id: str) -> None:
    """Remove a product configuration from the session state"""
    if "product_configs" not in st.session_state:
        return

    st.session_state.product_configs = [
        config for config in st.session_state.product_configs if config.id != config_id
    ]


def clear_product_configs() -> None:
    """Clear all product configurations"""
    st.session_state.product_configs = []
