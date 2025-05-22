import streamlit as st
from models.groq_model import get_groq_llm
from models.openai_model import get_openai_llm
import config


def get_llm(model_name=None, temperature=config.DEFAULT_TEMPERATURE, provider="groq"):
    """
    Factory function to get the appropriate LLM based on provider

    Args:
        model_name (str): Name of the model to use
        temperature (float): Temperature parameter for generation
        provider (str): Provider of the LLM ("groq" or "openai")

    Returns:
        LLM: Initialized LLM instance from the appropriate provider
    """
    if provider == "groq":
        if model_name is None:
            model_name = config.DEFAULT_GROQ_MODEL
        return get_groq_llm(model_name, temperature)
    elif provider == "openai":
        if model_name is None:
            model_name = config.DEFAULT_OPENAI_MODEL
        return get_openai_llm(model_name, temperature)
    else:
        st.error(f"Unknown provider: {provider}")
        return None
