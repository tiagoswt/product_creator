"""
Enhanced ProductConfig module with reprocessing and parameter modification support
"""

import uuid
import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime


class ProcessingAttempt:
    """Class to represent a single processing attempt with its parameters and result"""

    def __init__(
        self,
        model_provider: str,
        model_name: str,
        temperature: float,
        custom_instructions: str,
        result: Dict = None,
        status: str = "pending",
        timestamp: datetime = None,
        processing_time: float = None,
        error_message: str = None,
    ):
        self.attempt_id = str(uuid.uuid4())
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self.custom_instructions = custom_instructions
        self.result = result
        self.status = status  # pending, processing, completed, failed
        self.timestamp = timestamp or datetime.now()
        self.processing_time = processing_time
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert the processing attempt to a dictionary"""
        return {
            "attempt_id": self.attempt_id,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "custom_instructions": self.custom_instructions,
            "result": self.result,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
        }


class ProductConfig:
    """Enhanced class to represent a single product configuration for extraction with reprocessing support"""

    def __init__(
        self,
        product_type: str = "cosmetics",
        base_product: str = "",  # New field for subtype
        prompt_file: str = None,
        pdf_file=None,
        pdf_pages: List[int] = None,
        excel_file=None,
        excel_rows: List[int] = None,
        website_url: str = None,
        model_provider: str = "groq",
        model_name: str = None,
        temperature: float = 0.2,
        custom_instructions: str = "",
    ):
        self.id = str(uuid.uuid4())
        self.product_type = product_type
        self.base_product = base_product  # New field for subtype filename
        self.prompt_file = prompt_file
        self.pdf_file = pdf_file
        self.pdf_pages = pdf_pages or []
        self.excel_file = excel_file
        self.excel_rows = excel_rows or []
        self.website_url = website_url

        # Current processing parameters (can be modified for reprocessing)
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self.custom_instructions = custom_instructions

        # Processing history
        self.processing_attempts: List[ProcessingAttempt] = []

        # Current status and result (from latest attempt)
        self.status = "pending"  # pending, processing, completed, failed
        self.result = None

        # Reprocessing state
        self.is_reprocessing = False
        self.reprocess_type = "full"  # "full", "hscode_only"

    def add_processing_attempt(
        self,
        model_provider: str,
        model_name: str,
        temperature: float,
        custom_instructions: str,
        result: Dict = None,
        status: str = "pending",
        processing_time: float = None,
        error_message: str = None,
    ) -> ProcessingAttempt:
        """Add a new processing attempt to the history"""
        attempt = ProcessingAttempt(
            model_provider=model_provider,
            model_name=model_name,
            temperature=temperature,
            custom_instructions=custom_instructions,
            result=result,
            status=status,
            processing_time=processing_time,
            error_message=error_message,
        )
        self.processing_attempts.append(attempt)

        # Update current status and result
        self.status = status
        self.result = result

        return attempt

    def get_latest_attempt(self) -> Optional[ProcessingAttempt]:
        """Get the most recent processing attempt"""
        return self.processing_attempts[-1] if self.processing_attempts else None

    def get_successful_attempts(self) -> List[ProcessingAttempt]:
        """Get all successful processing attempts"""
        return [
            attempt
            for attempt in self.processing_attempts
            if attempt.status == "completed"
        ]

    def has_successful_attempt(self) -> bool:
        """Check if there's at least one successful processing attempt"""
        return len(self.get_successful_attempts()) > 0

    def update_current_parameters(
        self,
        model_provider: str = None,
        model_name: str = None,
        temperature: float = None,
        custom_instructions: str = None,
    ):
        """Update current processing parameters for reprocessing"""
        if model_provider is not None:
            self.model_provider = model_provider
        if model_name is not None:
            self.model_name = model_name
        if temperature is not None:
            self.temperature = temperature
        if custom_instructions is not None:
            self.custom_instructions = custom_instructions

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary"""
        return {
            "id": self.id,
            "product_type": self.product_type,
            "base_product": self.base_product,  # Include base_product
            "prompt_file": self.prompt_file,
            "pdf_file_name": self.pdf_file.name if self.pdf_file else None,
            "pdf_pages": self.pdf_pages,
            "excel_file_name": self.excel_file.name if self.excel_file else None,
            "excel_rows": self.excel_rows,
            "website_url": self.website_url,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "custom_instructions": self.custom_instructions,
            "status": self.status,
            "processing_attempts": [
                attempt.to_dict() for attempt in self.processing_attempts
            ],
            "is_reprocessing": self.is_reprocessing,
            "reprocess_type": self.reprocess_type,
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

        # Add base_product attribute if it doesn't exist
        if not hasattr(config, "base_product"):
            config.base_product = ""

        # Add new reprocessing attributes if they don't exist
        if not hasattr(config, "processing_attempts"):
            config.processing_attempts = []

            # If this config has a result, convert it to a processing attempt
            if hasattr(config, "result") and config.result is not None:
                attempt = ProcessingAttempt(
                    model_provider=getattr(config, "model_provider", "groq"),
                    model_name=getattr(config, "model_name", ""),
                    temperature=getattr(config, "temperature", 0.2),
                    custom_instructions=getattr(config, "custom_instructions", ""),
                    result=config.result,
                    status=getattr(config, "status", "completed"),
                )
                config.processing_attempts.append(attempt)

        if not hasattr(config, "is_reprocessing"):
            config.is_reprocessing = False

        if not hasattr(config, "reprocess_type"):
            config.reprocess_type = "full"

    # Optional: Log that migration has been performed
    print(
        "Migrated existing product configurations with reprocessing support and base_product field"
    )


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


def prepare_for_reprocessing(
    config: ProductConfig, reprocess_type: str = "full"
) -> None:
    """Prepare a configuration for reprocessing"""
    config.is_reprocessing = True
    config.reprocess_type = reprocess_type
    config.status = "pending"
    update_product_config(config)
