import os
import streamlit as st
from langchain_groq import ChatGroq
import config


def get_groq_llm(
    model_name=config.DEFAULT_GROQ_MODEL, temperature=config.DEFAULT_TEMPERATURE
):
    """
    Initialize and return a ChatGroq instance

    Args:
        model_name (str): Name of the Groq model to use
        temperature (float): Temperature parameter for generation

    Returns:
        ChatGroq: Initialized ChatGroq instance or None if API key is not available
    """
    # Try to load from environment variables directly
    api_key = os.getenv(config.ENV_GROQ_API_KEY)

    # If API key is not found in environment, prompt the user
    if not api_key:
        api_key = st.sidebar.text_input(
            "Enter your Groq API Key", type="password", key="groq_api_key_input"
        )
        if not api_key:
            st.error("No Groq API key provided. Please enter your Groq API key.")
            return None

        # Store the API key in session state for future use
        st.session_state[config.STATE_GROQ_API_KEY] = api_key

    # Return the ChatGroq instance
    return ChatGroq(
        api_key=api_key,
        model_name=model_name,
        temperature=temperature,
    )
