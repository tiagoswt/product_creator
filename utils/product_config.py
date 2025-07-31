"""
Enhanced ProductConfig module with PHASE 3 USER TRACKING
ADDED: User attribution support for product creation tracking
"""

import uuid
import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime


class ProcessingAttempt:
    """Class to represent a single processing attempt with user attribution"""

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
        user_context: Dict = None,  # PHASE 3: User attribution
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

        # PHASE 3: User attribution
        self.user_context = user_context or {}
        self.user_id = self.user_context.get("user_id")
        self.username = self.user_context.get("username", "unknown")
        self.user_name = self.user_context.get("user_name", "Unknown User")

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
            # PHASE 3: User attribution
            "user_id": self.user_id,
            "username": self.username,
            "user_name": self.user_name,
            "user_context": self.user_context,
        }


class ProductConfig:
    """Enhanced class to represent a single product configuration with PHASE 3 user attribution"""

    def __init__(
        self,
        product_type: str = "cosmetics",
        base_product: str = "",
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
        user_context: Dict = None,  # PHASE 3: User attribution
    ):
        self.id = str(uuid.uuid4())
        self.product_type = product_type
        self.base_product = base_product
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

        # PHASE 3: User attribution
        self.user_context = user_context or self._get_current_user_context()
        self.created_by_user_id = self.user_context.get("user_id")
        self.created_by_username = self.user_context.get("username", "unknown")
        self.created_by_name = self.user_context.get("user_name", "Unknown User")
        self.created_at = datetime.now()

    def _get_current_user_context(self) -> Dict:
        """
        PHASE 3: Get current user context from session state.

        Returns:
            Dict with user_id, username, and user_name, or defaults if not found
        """
        if "current_user" in st.session_state:
            current_user = st.session_state["current_user"]
            return {
                "user_id": current_user.get("id"),
                "username": current_user.get("username", "unknown"),
                "user_name": current_user.get("name", "Unknown User"),
            }
        else:
            # Fallback for systems without authentication
            return {"user_id": None, "username": "system", "user_name": "System"}

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
        user_context: Dict = None,  # PHASE 3: User attribution
    ) -> ProcessingAttempt:
        """Add a new processing attempt to the history with user attribution"""

        # PHASE 3: Use provided user context or get from session state
        if not user_context:
            user_context = self._get_current_user_context()

        attempt = ProcessingAttempt(
            model_provider=model_provider,
            model_name=model_name,
            temperature=temperature,
            custom_instructions=custom_instructions,
            result=result,
            status=status,
            processing_time=processing_time,
            error_message=error_message,
            user_context=user_context,  # PHASE 3: User attribution
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

    def get_creator_info(self) -> Dict[str, str]:
        """
        PHASE 3: Get creator information for this product configuration.

        Returns:
            Dict with creator details
        """
        return {
            "user_id": self.created_by_user_id,
            "username": self.created_by_username,
            "user_name": self.created_by_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def get_latest_processor_info(self) -> Dict[str, str]:
        """
        PHASE 3: Get information about who processed the latest attempt.

        Returns:
            Dict with processor details from the latest attempt
        """
        latest = self.get_latest_attempt()
        if latest:
            return {
                "user_id": latest.user_id,
                "username": latest.username,
                "user_name": latest.user_name,
                "processed_at": (
                    latest.timestamp.isoformat() if latest.timestamp else None
                ),
            }
        return {}

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
        """Convert the configuration to a dictionary with user attribution"""
        return {
            "id": self.id,
            "product_type": self.product_type,
            "base_product": self.base_product,
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
            # PHASE 3: User attribution
            "created_by_user_id": self.created_by_user_id,
            "created_by_username": self.created_by_username,
            "created_by_name": self.created_by_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_context": self.user_context,
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

    def creator_summary(self) -> str:
        """
        PHASE 3: Get a summary of who created this configuration.

        Returns:
            String summary of creator information
        """
        if self.created_by_username != "system":
            return f"Created by: {self.created_by_name} ({self.created_by_username})"
        else:
            return "Created by: System"

    def full_summary(self) -> str:
        """
        PHASE 3: Get a full summary including sources and creator.

        Returns:
            String with complete configuration summary
        """
        source_summary = self.source_summary()
        creator_summary = self.creator_summary()
        return f"{source_summary} | {creator_summary}"


def migrate_product_configs():
    """
    PHASE 3: Migrate existing product configurations to include user attribution
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
                # Get current user context for migration
                user_context = (
                    config._get_current_user_context()
                    if hasattr(config, "_get_current_user_context")
                    else {
                        "user_id": None,
                        "username": "migrated",
                        "user_name": "Migrated User",
                    }
                )

                attempt = ProcessingAttempt(
                    model_provider=getattr(config, "model_provider", "groq"),
                    model_name=getattr(config, "model_name", ""),
                    temperature=getattr(config, "temperature", 0.2),
                    custom_instructions=getattr(config, "custom_instructions", ""),
                    result=config.result,
                    status=getattr(config, "status", "completed"),
                    user_context=user_context,  # PHASE 3: User attribution
                )
                config.processing_attempts.append(attempt)

        if not hasattr(config, "is_reprocessing"):
            config.is_reprocessing = False

        if not hasattr(config, "reprocess_type"):
            config.reprocess_type = "full"

        # PHASE 3: Add user attribution attributes if they don't exist
        if not hasattr(config, "user_context"):
            config.user_context = {
                "user_id": None,
                "username": "migrated",
                "user_name": "Migrated User",
            }

        if not hasattr(config, "created_by_user_id"):
            config.created_by_user_id = None

        if not hasattr(config, "created_by_username"):
            config.created_by_username = "migrated"

        if not hasattr(config, "created_by_name"):
            config.created_by_name = "Migrated User"

        if not hasattr(config, "created_at"):
            config.created_at = datetime.now()

        # Add methods if they don't exist
        if not hasattr(config, "_get_current_user_context"):
            config._get_current_user_context = lambda: {
                "user_id": None,
                "username": "migrated",
                "user_name": "Migrated User",
            }

        if not hasattr(config, "get_creator_info"):
            config.get_creator_info = lambda: {
                "user_id": getattr(config, "created_by_user_id", None),
                "username": getattr(config, "created_by_username", "migrated"),
                "user_name": getattr(config, "created_by_name", "Migrated User"),
                "created_at": getattr(config, "created_at", datetime.now()).isoformat(),
            }

        if not hasattr(config, "creator_summary"):
            config.creator_summary = (
                lambda: f"Created by: {getattr(config, 'created_by_name', 'Migrated User')} ({getattr(config, 'created_by_username', 'migrated')})"
            )

        if not hasattr(config, "full_summary"):
            config.full_summary = (
                lambda: f"{config.source_summary()} | {config.creator_summary()}"
            )

    # Optional: Log that migration has been performed
    print(
        "PHASE 3: Migrated existing product configurations with user attribution support"
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


# PHASE 3: New helper functions for user attribution


def get_configs_by_user(
    user_id: str = None, username: str = None
) -> List[ProductConfig]:
    """
    PHASE 3: Get product configurations created by a specific user.

    Args:
        user_id: User UUID to filter by
        username: Username to filter by (alternative to user_id)

    Returns:
        List of product configurations created by the user
    """
    configs = get_product_configs()

    if user_id:
        return [
            config
            for config in configs
            if getattr(config, "created_by_user_id", None) == user_id
        ]
    elif username:
        return [
            config
            for config in configs
            if getattr(config, "created_by_username", "unknown") == username
        ]
    else:
        return []


def get_current_user_configs() -> List[ProductConfig]:
    """
    PHASE 3: Get product configurations for the current user.

    Returns:
        List of product configurations created by the current user
    """
    if "current_user" in st.session_state:
        current_user = st.session_state["current_user"]
        user_id = current_user.get("id")
        if user_id:
            return get_configs_by_user(user_id=user_id)

    return []


def get_config_creators_summary() -> Dict[str, Dict]:
    """
    PHASE 3: Get summary of all users who have created configurations.

    Returns:
        Dict mapping usernames to their configuration counts and details
    """
    configs = get_product_configs()
    creators = {}

    for config in configs:
        username = getattr(config, "created_by_username", "unknown")
        user_name = getattr(config, "created_by_name", "Unknown User")

        if username not in creators:
            creators[username] = {
                "user_name": user_name,
                "config_count": 0,
                "completed_count": 0,
                "failed_count": 0,
                "pending_count": 0,
            }

        creators[username]["config_count"] += 1

        if config.status == "completed":
            creators[username]["completed_count"] += 1
        elif config.status == "failed":
            creators[username]["failed_count"] += 1
        else:
            creators[username]["pending_count"] += 1

    return creators
