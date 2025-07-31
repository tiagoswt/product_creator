import os
import streamlit as st
from langsmith import Client
import config


def initialize_langsmith():
    """
    Initialize LangSmith tracing for better monitoring and debugging

    Returns:
        bool: True if LangSmith was successfully initialized, False otherwise
    """
    api_key = os.getenv(config.ENV_LANGSMITH_API_KEY)

    if api_key:
        os.environ[config.ENV_LANGSMITH_TRACING] = "true"
        os.environ[config.ENV_LANGSMITH_ENDPOINT] = config.LANGSMITH_ENDPOINT
        os.environ[config.ENV_LANGSMITH_PROJECT] = config.LANGSMITH_PROJECT

        try:
            client = Client()
            return True
        except Exception as e:
            st.sidebar.warning(f"Failed to initialize LangSmith: {str(e)}")
            return False
    else:
        return False
