import os
import streamlit as st
from langsmith import Client, traceable
import config


def initialize_langsmith():
    """
    Initialize LangSmith tracing for better monitoring and debugging
    Uses both Streamlit secrets (for Cloud) and environment variables (for local)

    Returns:
        bool: True if LangSmith was successfully initialized, False otherwise
    """
    # Get API key from secrets or environment
    api_key = config.get_secret_or_env(config.ENV_LANGSMITH_API_KEY)

    # Get tracing setting - default to "true" if API key exists but tracing not explicitly set
    tracing_setting = config.get_secret_or_env(config.ENV_LANGSMITH_TRACING, "true" if api_key else "false")
    tracing_enabled = str(tracing_setting).lower() == "true"

    if api_key and tracing_enabled:
        # Set API key in environment for langsmith client
        os.environ[config.ENV_LANGSMITH_API_KEY] = api_key

        # Get additional settings from secrets or environment
        endpoint = config.get_secret_or_env(config.ENV_LANGSMITH_ENDPOINT, config.LANGSMITH_ENDPOINT)
        project = config.get_secret_or_env(config.ENV_LANGSMITH_PROJECT, config.LANGSMITH_PROJECT)

        # Set additional environment variables for LangSmith
        os.environ[config.ENV_LANGSMITH_ENDPOINT] = endpoint
        os.environ[config.ENV_LANGSMITH_PROJECT] = project

        try:
            # Test client connection
            client = Client(api_key=api_key)
            # LangSmith is properly configured - automatic tracing will work
            return True
        except Exception as e:
            if hasattr(st, '_is_running_with_streamlit') and st._is_running_with_streamlit:
                st.sidebar.warning(f"⚠️ Failed to initialize LangSmith: {str(e)}")
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
            # Don't show info message if just missing tracing flag (since we default to true)
            if not api_key:
                st.sidebar.info(f"💡 LangSmith not configured. Add {', '.join(missing)} to secrets or .env")
        else:
            print(f"LangSmith not configured. Missing: {', '.join(missing)}")
        return False
