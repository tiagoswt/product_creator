"""
Main entry point for the Batch Extraction UI
"""

import streamlit as st
from utils.product_config import migrate_product_configs, get_product_configs
from .tabs.configure_tab import render_configure_tab
from .tabs.execute_tab import render_execute_tab
from .tabs.reprocess_tab import render_reprocess_tab


def render_batch_extraction_ui():
    """Render the main UI for batch extraction of products"""

    # Migrate existing product configurations to ensure they have all required attributes
    migrate_product_configs()

    # Check if a reset was triggered - this is a signal from app.py
    reset_triggered = st.session_state.get("reset_triggered", False)

    # Handle form reset logic before rendering the form
    if (
        "clear_batch_form" in st.session_state and st.session_state.clear_batch_form
    ) or reset_triggered:
        # Reset all form-related session state variables
        st.session_state["batch_form_data"] = {}

        # Clear PDF preview data
        if "pdf_preview" in st.session_state:
            del st.session_state["pdf_preview"]
        if "last_pdf_name" in st.session_state:
            del st.session_state["last_pdf_name"]
        if "pdf_pages_selected" in st.session_state:
            del st.session_state["pdf_pages_selected"]

        # Clear Excel related data
        if "raw_excel_df" in st.session_state:
            del st.session_state["raw_excel_df"]
        if "processed_excel_df" in st.session_state:
            del st.session_state["processed_excel_df"]
        if "excel_rows_selected" in st.session_state:
            del st.session_state["excel_rows_selected"]
        if "last_excel_name" in st.session_state:
            del st.session_state["last_excel_name"]
        if "header_row_last_used" in st.session_state:
            del st.session_state["header_row_last_used"]

        # Clear the flags
        st.session_state.clear_batch_form = False
        if reset_triggered:
            st.session_state.reset_triggered = False

    # Initialize form data storage
    if "batch_form_data" not in st.session_state:
        st.session_state.batch_form_data = {}

    # Create tabs for configuration management and execution only
    tab1, tab2 = st.tabs(["Configure Products", "Execute Batch"])

    with tab1:
        render_configure_tab()

    with tab2:
        render_execute_tab()
