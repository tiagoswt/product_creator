import re
import json
import streamlit as st
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from models.model_factory import get_llm
import config


def load_prompt_from_file(prompt_file):
    """
    Load prompt template from a markdown file

    Args:
        prompt_file (str): Name of the prompt file in the prompts directory

    Returns:
        str: Content of the prompt file
    """
    prompt_path = Path(config.PROMPT_DIRECTORY) / prompt_file

    if not prompt_path.exists():
        st.error(f"Prompt file not found: {prompt_path}")
        return None

    try:
        with open(prompt_path, "r", encoding="utf-8") as file:
            prompt_content = file.read()
        return prompt_content
    except Exception as e:
        st.error(f"Error loading prompt file: {e}")
        return None


def process_hscode_with_deepseek(product_data):
    """
    Process product data with Deepseek model specifically for HScode classification

    Args:
        product_data (dict): Extracted product data

    Returns:
        str: HScode for the product
    """
    # Load the HScode prompt template
    prompt_content = load_prompt_from_file(config.HSCODE_PROMPT)
    if not prompt_content:
        st.error("Failed to load HScode prompt template")
        return None

    # Create the formatted prompt template with product data
    prompt_template = PromptTemplate.from_template(prompt_content)

    try:
        # Get the Deepseek model specifically for HScode processing
        hscode_llm = get_llm(
            model_name=config.HSCODE_MODEL,
            temperature=config.HSCODE_TEMPERATURE,
            provider=config.HSCODE_PROVIDER,
        )

        if not hscode_llm:
            st.warning(
                "Could not initialize Deepseek model for HScode processing. Using original HScode."
            )
            return product_data.get("hscode")

        st.info("Processing HScode with specialized Deepseek model...")
        chain = prompt_template | hscode_llm

        # Prepare input variables for the HScode prompt
        hscode_input = {
            "product_name": product_data.get("product_name", ""),
            "brand": product_data.get("brand", ""),
            "product_type": product_data.get("product_type", ""),
            "description": product_data.get("description", ""),
            "ingredients": (
                ", ".join(product_data.get("ingredients", []))
                if isinstance(product_data.get("ingredients", []), list)
                else product_data.get("ingredients", "")
            ),
            "how_to_use": product_data.get("how_to_use", ""),
        }

        # Invoke the chain with HScode variables
        response = chain.invoke(hscode_input)

        # Parse JSON from response
        try:
            # Check if response is a string or an object with content attribute
            if hasattr(response, "content"):
                response_text = response.content
            else:
                response_text = response

            # Find JSON in the response
            json_match = re.search(r"```json\n(.*?)```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text

            hscode_data = json.loads(json_str)
            return hscode_data.get("hscode")
        except Exception as e:
            st.error(f"Error parsing HScode data: {e}")
            return product_data.get("hscode")  # Fall back to original HScode
    except Exception as e:
        st.error(f"Error while processing HScode with Deepseek: {e}")
        return product_data.get("hscode")  # Fall back to original HScode


def process_with_llm(text, product_type, llm, run_name=None):
    """
    Process text with LLM to extract product information

    Args:
        text (str): Text to process
        product_type (str): Type of product to extract
        llm: Language model to use
        run_name (str): Name for the LangSmith run

    Returns:
        dict: Extracted product data as a dictionary
    """
    # Load the appropriate prompt template based on product type
    if product_type == "cosmetics":
        prompt_content = load_prompt_from_file(config.COSMETICS_PROMPT)
    elif product_type == "fragrance":
        prompt_content = load_prompt_from_file(config.FRAGRANCE_PROMPT)
    elif product_type == "subtype":
        prompt_content = load_prompt_from_file(config.SUBTYPE_PROMPT)
    else:
        st.error(f"Unknown product type: {product_type}")
        return None

    if not prompt_content:
        st.error(f"Failed to load {product_type} prompt template")
        return None

    # Create the formatted prompt template
    prompt_template = PromptTemplate.from_template(prompt_content)

    try:
        # Use the newer RunnableSequence approach (prompt | llm)
        st.info("Sending data to LLM for processing...")
        chain = prompt_template | llm

        # Configure tracing with run name if LangSmith is enabled
        run_params = {}
        if (
            "langsmith_enabled" in st.session_state
            and st.session_state.langsmith_enabled
        ):
            if run_name:
                run_params["tags"] = [product_type, "product-extraction"]
                run_params["name"] = run_name

        # Invoke the chain with optional tracing parameters
        response = chain.invoke({"text": text}, run_params)

        # Parse JSON from response
        try:
            # Check if response is a string or an object with content attribute
            if hasattr(response, "content"):
                response_text = response.content
            else:
                response_text = response

            # Find JSON in the response
            json_match = re.search(r"```json\n(.*?)```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text

            product_data = json.loads(json_str)

            # Post-process HScode with Deepseek for all product types
            hscode = process_hscode_with_deepseek(product_data)
            if hscode:
                product_data["hscode"] = hscode

            return product_data
        except Exception as e:
            st.error(f"Error parsing product data: {e}")
            st.text(
                f"Raw response: {response_text if 'response_text' in locals() else response}"
            )
            return None
    except Exception as e:
        st.error(f"Error while processing with LLM: {e}")
        # If the error is related to token limits, we could implement a fallback chunking strategy
        if "maximum context length" in str(e) or "token limit" in str(e):
            st.warning(
                "The combined data exceeds the model's token limit. Attempting to process with chunking..."
            )
            # Could implement fallback chunking strategy here if needed
            return None
        return None


def process_consolidated_data(consolidated_text, product_type, llm):
    """
    Process consolidated text data to extract product information

    Args:
        consolidated_text (str): Combined text from all sources
        product_type (str): Type of product to extract
        llm: Language model to use

    Returns:
        list: List of extracted product data dictionaries
    """
    # Process the entire consolidated text at once without chunking
    st.info(f"Processing {len(consolidated_text)} characters of consolidated data")

    # Generate run name for LangSmith tracking
    source_types = []
    if "pdf" in consolidated_text.lower():
        source_types.append("PDF")
    if "excel" in consolidated_text.lower():
        source_types.append("Excel")
    if "website" in consolidated_text.lower():
        source_types.append("Website")

    run_name = f"{product_type.capitalize()} extraction from {'+'.join(source_types)}"

    # Process as a single input to make the most of context
    product_data = process_with_llm(
        consolidated_text, product_type, llm, run_name=run_name
    )

    if product_data:
        return [product_data]
    return []
