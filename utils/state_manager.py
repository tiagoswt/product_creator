import streamlit as st
import config


def initialize_state():
    """
    Initialize necessary session state variables
    """
    if config.STATE_PRODUCTS not in st.session_state:
        st.session_state[config.STATE_PRODUCTS] = []

    if config.STATE_EXCEL_HEADER_ROW not in st.session_state:
        st.session_state[config.STATE_EXCEL_HEADER_ROW] = 0

    # Initialize product configurations for batch processing
    if "product_configs" not in st.session_state:
        st.session_state.product_configs = []


def reset_application():
    """
    Reset application cache and session state while preserving API keys
    """
    # Preserve API keys
    groq_api_key = st.session_state.get(config.STATE_GROQ_API_KEY, None)
    openai_api_key = st.session_state.get(config.STATE_OPENAI_API_KEY, None)

    # Create a list of keys to explicitly keep
    keys_to_keep = [config.STATE_GROQ_API_KEY, config.STATE_OPENAI_API_KEY]

    # Store values of keys we want to keep
    preserved_values = {}
    for key in keys_to_keep:
        if key in st.session_state:
            preserved_values[key] = st.session_state[key]

    # Clear ALL session state - this ensures every product, file, and setting is removed
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Restore only the API keys we want to preserve
    for key, value in preserved_values.items():
        st.session_state[key] = value

    # Reinitialize required session state variables
    initialize_state()

    # Clear function cache
    st.cache_resource.clear()
