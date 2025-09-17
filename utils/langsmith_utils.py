import os
import streamlit as st
from langsmith import Client, traceable
import config


def initialize_langsmith():
    """
    Initialize LangSmith tracing for better monitoring and debugging
    Uses modern LangSmith approach with environment variables

    Returns:
        bool: True if LangSmith was successfully initialized, False otherwise
    """
    api_key = os.getenv(config.ENV_LANGSMITH_API_KEY)
    tracing_enabled = os.getenv(config.ENV_LANGSMITH_TRACING, "").lower() == "true"

    if api_key and tracing_enabled:
        # Set additional environment variables for LangSmith
        os.environ[config.ENV_LANGSMITH_ENDPOINT] = config.LANGSMITH_ENDPOINT
        os.environ[config.ENV_LANGSMITH_PROJECT] = config.LANGSMITH_PROJECT

        try:
            # Test client connection
            client = Client()
            # LangSmith is properly configured - automatic tracing will work
            return True
        except Exception as e:
            if hasattr(st, '_is_running_with_streamlit') and st._is_running_with_streamlit:
                st.sidebar.warning(f"Failed to initialize LangSmith: {str(e)}")
            else:
                print(f"Failed to initialize LangSmith: {str(e)}")
            return False
    else:
        missing = []
        if not api_key:
            missing.append("LANGSMITH_API_KEY")
        if not tracing_enabled:
            missing.append("LANGSMITH_TRACING=true")

        if hasattr(st, '_is_running_with_streamlit') and st._is_running_with_streamlit:
            st.sidebar.info(f"LangSmith not configured. Missing: {', '.join(missing)}")
        else:
            print(f"LangSmith not configured. Missing: {', '.join(missing)}")
        return False
