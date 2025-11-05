import os
import streamlit as st
from langchain_openai import ChatOpenAI
import config


def get_openai_llm(
    model_name=config.DEFAULT_OPENAI_MODEL, temperature=config.DEFAULT_TEMPERATURE
):
    """
    Initialize and return a ChatOpenAI instance

    Args:
        model_name (str): Name of the OpenAI model to use
        temperature (float): Temperature parameter for generation

    Returns:
        ChatOpenAI: Initialized ChatOpenAI instance or None if API key is not available
    """
    # Try to load from Streamlit secrets or environment variables
    api_key = config.get_secret_or_env(config.ENV_OPENAI_API_KEY)

    # If API key is not found, prompt the user
    if not api_key:
        api_key = st.sidebar.text_input(
            "Enter your OpenAI API Key", type="password", key="openai_api_key_input"
        )
        if not api_key:
            st.error("No OpenAI API key provided. Please enter your OpenAI API key.")
            return None

        # Store the API key in session state for future use
        st.session_state[config.STATE_OPENAI_API_KEY] = api_key

    # Return the ChatOpenAI instance
    return ChatOpenAI(
        api_key=api_key,
        model_name=model_name,
        temperature=temperature,
    )
