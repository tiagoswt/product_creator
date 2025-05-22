import streamlit as st
import os
import json
import pandas as pd
from models.model_factory import get_llm
from utils.state_manager import initialize_state, reset_application
from utils.langsmith_utils import initialize_langsmith
import config

# Update the import path to use the fixed version, with a direct import
# to ensure it's found correctly
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.batch_ui_fixed import render_batch_extraction_ui


def main():
    st.title("E-commerce Product Extractor")

    # Initialize app state
    initialize_state()

    # Initialize LangSmith if possible and store status in session state
    if "langsmith_enabled" not in st.session_state:
        st.session_state.langsmith_enabled = initialize_langsmith()

    if st.session_state.langsmith_enabled:
        st.sidebar.success("LangSmith tracing enabled")

    # Sidebar layout
    with st.sidebar:
        st.header("Configuration")

        # Removed the Product Type selection from sidebar

        st.markdown("---")
        st.markdown("### Data Sources")
        st.info("Select one or more data sources to extract product information.")

        st.markdown("---")
        st.markdown("### Application Management")

        # Reset application button
        if st.button(
            "Reset Application", help="Clear all cache and session data to start fresh"
        ):
            reset_application()
            # Set a flag to indicate that a reset was triggered
            st.session_state.reset_triggered = True
            st.rerun()

        # Clear products button
        if st.button("Clear Products", help="Remove all extracted products"):
            st.session_state.products = []
            st.success("All products cleared!")
            st.rerun()

    # Initialize LLM with default parameters
    llm = get_llm(provider="groq")
    if not llm:
        st.error("Unable to initialize the language model. Please check your API key.")
        st.stop()

    # Always render batch processing UI
    render_batch_extraction_ui()


if __name__ == "__main__":
    main()
