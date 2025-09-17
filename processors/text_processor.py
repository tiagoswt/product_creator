import re
import json
import streamlit as st
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langsmith import traceable
from models.model_factory import get_llm
import config


def detect_response_format(response_json):
    """
    Detect the format of the LLM response to determine processing logic

    Args:
        response_json: Parsed JSON response from LLM

    Returns:
        str: Format type ('subtype', 'cosmetics', 'legacy', 'unknown')
    """
    if isinstance(response_json, list):
        # Array format = subtype
        return "subtype"
    elif isinstance(response_json, dict):
        if "Subtypes" in response_json:
            # Object with Subtypes array = cosmetics
            return "cosmetics"
        elif "catalogA" in response_json or "catalogB" in response_json:
            # Legacy nested structure
            return "legacy"
        else:
            # Could be fragrance or other flat structure
            return "flat"
    else:
        return "unknown"


def get_hscode_from_product_data(product_data):
    """
    Get HScode from product data, handling multiple structures

    Args:
        product_data: Product data in various formats

    Returns:
        str: HScode if found, None otherwise
    """
    # Handle array format (subtype)
    if isinstance(product_data, list):
        if len(product_data) > 0:
            return product_data[0].get("HSCode") or product_data[0].get("hscode")
        return None

    # Handle object format
    if isinstance(product_data, dict):
        # Check new HSCode field first
        hscode = product_data.get("HSCode")
        if hscode:
            return hscode

        # Check legacy hscode field
        hscode = product_data.get("hscode")
        if hscode:
            return hscode

        # Check in Subtypes array (cosmetics)
        if "Subtypes" in product_data and product_data["Subtypes"]:
            first_subtype = product_data["Subtypes"][0]
            return first_subtype.get("HSCode") or first_subtype.get("hscode")

        # Check legacy catalogB structure
        if "catalogB" in product_data and isinstance(product_data["catalogB"], dict):
            return product_data["catalogB"].get("hscode") or product_data[
                "catalogB"
            ].get("HSCode")

    return None


def set_hscode_in_product_data(product_data, hscode, product_type=None):
    """
    Set HScode in product data at the correct location

    Args:
        product_data: Product data dictionary (modified in place)
        hscode (str): HScode to set
        product_type (str): Product type to determine placement
    """
    if isinstance(product_data, list):
        # Array format (subtype)
        for item in product_data:
            item["HSCode"] = hscode  # Legacy format
            item["hsCode"] = hscode  # New format
    elif isinstance(product_data, dict):
        if "Subtypes" in product_data:
            # Cosmetics format - set only in subtypes, not root
            for subtype in product_data["Subtypes"]:
                subtype["HSCode"] = hscode
        elif "catalogB" in product_data:
            # Legacy format
            product_data["catalogB"]["hscode"] = hscode
        else:
            # Flat format (fragrance or other)
            product_data["hscode"] = hscode


def place_hscode_in_correct_location(product_data, hscode, product_type):
    """
    Place HScode in the correct location based on product type and new structure

    Args:
        product_data: The product data (modified in place)
        hscode (str): The HScode to place
        product_type (str): The type of product

    Returns:
        product_data: Modified product data with HScode placed correctly
    """
    if product_type == "subtype":
        # For subtypes (array format)
        if isinstance(product_data, list):
            for item in product_data:
                item["HSCode"] = hscode
        elif isinstance(product_data, dict):
            # Single subtype object or legacy format
            if "catalogB" in product_data:
                # Legacy format
                product_data["catalogB"]["hscode"] = hscode
            else:
                # New flat format
                product_data["HSCode"] = hscode

    elif product_type == "cosmetics":
        # For cosmetics (flat structure with Subtypes array)
        if isinstance(product_data, dict):
            if "Subtypes" in product_data:
                # New format - set HSCode only in subtypes, not root level
                for subtype in product_data["Subtypes"]:
                    subtype["HSCode"] = hscode
            elif "catalogB" in product_data:
                # Legacy format
                product_data["catalogB"]["hscode"] = hscode
            else:
                # Fallback
                product_data["HSCode"] = hscode

    elif product_type == "fragrance":
        # Fragrance has flat structure, no catalogB
        if isinstance(product_data, dict):
            product_data["hscode"] = hscode

    else:
        # Unknown product type, use safe fallback
        if isinstance(product_data, list):
            for item in product_data:
                item["HSCode"] = hscode
        elif isinstance(product_data, dict):
            product_data["HSCode"] = hscode

    return product_data


def extract_hscode_fields(product_data, product_type=None):
    """
    Extract HScode-relevant fields from product data, handling new structures

    Args:
        product_data: Product data from LLM processing
        product_type (str): Type of product for context

    Returns:
        dict: Standardized fields for HScode processing
    """
    # Initialize with empty defaults
    hscode_input = {
        "product_name": "",
        "brand": "",
        "product_type": "",
        "description": "",
        "ingredients": "",
        "how_to_use": "",
    }

    # Detect format and extract accordingly
    response_format = detect_response_format(product_data)

    if response_format == "subtype":
        # Handle array format - use first item for HSCode input
        if isinstance(product_data, list) and len(product_data) > 0:
            item = product_data[0]
            hscode_input["product_name"] = item.get("ItemDescriptionEN", "")
            hscode_input["brand"] = item.get(
                "brand", ""
            )  # May not be present in subtypes
            hscode_input["product_type"] = item.get("product_type", "")

            # Handle ingredients
            ingredients = item.get("ingredients", [])
            if isinstance(ingredients, list):
                hscode_input["ingredients"] = ", ".join(str(ing) for ing in ingredients)
            else:
                hscode_input["ingredients"] = str(ingredients) if ingredients else ""

    elif response_format == "cosmetics":
        # Handle new cosmetics format (flat structure with Subtypes)
        if isinstance(product_data, dict):
            hscode_input["product_name"] = product_data.get("TitleEN", "")
            hscode_input["brand"] = product_data.get(
                "brand", ""
            )  # May be in first subtype
            hscode_input["description"] = product_data.get("DescriptionEN", "")
            hscode_input["how_to_use"] = product_data.get("HowToEN", "")

            # Get additional info from first subtype if available
            if "Subtypes" in product_data and len(product_data["Subtypes"]) > 0:
                first_subtype = product_data["Subtypes"][0]
                if not hscode_input["product_name"]:
                    hscode_input["product_name"] = first_subtype.get(
                        "ItemDescriptionEN", ""
                    )

                # Extract product_type and ingredients from subtype
                hscode_input["product_type"] = first_subtype.get("product_type", "")
                ingredients = first_subtype.get("ingredients", [])
                if isinstance(ingredients, list):
                    hscode_input["ingredients"] = ", ".join(
                        str(ing) for ing in ingredients
                    )
                else:
                    hscode_input["ingredients"] = (
                        str(ingredients) if ingredients else ""
                    )

    elif response_format == "legacy":
        # Handle legacy catalogA/catalogB structure
        if isinstance(product_data, dict):
            # Extract from catalogA (marketing content)
            if "catalogA" in product_data:
                catalog_a = product_data["catalogA"]
                hscode_input["product_name"] = catalog_a.get(
                    "TitleEN"
                ) or catalog_a.get("product_title_EN", "")
                hscode_input["brand"] = catalog_a.get("brand", "")
                hscode_input["description"] = catalog_a.get("description", "")
                hscode_input["how_to_use"] = catalog_a.get("HowToEN") or catalog_a.get(
                    "how_to_use", ""
                )

            # Extract from catalogB (technical data)
            if "catalogB" in product_data:
                catalog_b = product_data["catalogB"]
                if not hscode_input["product_name"]:
                    hscode_input["product_name"] = catalog_b.get(
                        "itemDescriptionEN", ""
                    )
                hscode_input["product_type"] = catalog_b.get("product_type", "")

                ingredients = catalog_b.get("ingredients", [])
                if isinstance(ingredients, list):
                    hscode_input["ingredients"] = ", ".join(
                        str(ing) for ing in ingredients
                    )
                else:
                    hscode_input["ingredients"] = (
                        str(ingredients) if ingredients else ""
                    )

    elif response_format == "flat":
        # Handle flat structure (fragrance or other)
        if isinstance(product_data, dict):
            hscode_input["product_name"] = product_data.get("product_name", "")
            hscode_input["brand"] = product_data.get("brand", "")
            hscode_input["product_type"] = product_data.get("product_type", "")
            hscode_input["description"] = product_data.get(
                "description"
            ) or product_data.get("meta_description", "")
            hscode_input["how_to_use"] = product_data.get("how_to_use", "")

            ingredients = product_data.get("ingredients", [])
            if isinstance(ingredients, list):
                hscode_input["ingredients"] = ", ".join(str(ing) for ing in ingredients)
            else:
                hscode_input["ingredients"] = str(ingredients) if ingredients else ""

    return hscode_input


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


@traceable(name="hscode_processing", tags=["hscode", "deepseek", "classification"])
def process_hscode_with_deepseek(product_data, product_type=None):
    """
    Process product data with Deepseek model specifically for HScode classification
    Updated for new JSON structures

    Args:
        product_data: Extracted product data in any format
        product_type (str): Type of product for context

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
            return get_hscode_from_product_data(product_data)

        st.info("Processing HScode with specialized Deepseek model...")
        chain = prompt_template | hscode_llm

        # Extract HScode-relevant fields using new extraction logic
        hscode_input = extract_hscode_fields(product_data, product_type)

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
            json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text

            hscode_data = json.loads(json_str)
            return hscode_data.get("hscode")
        except Exception as e:
            st.error(f"Error parsing HScode data: {e}")
            return get_hscode_from_product_data(product_data)  # Fallback to existing
    except Exception as e:
        st.error(f"Error while processing HScode with Deepseek: {e}")
        return get_hscode_from_product_data(product_data)  # Fallback to existing


@traceable(name="product_extraction", tags=["llm-processing", "product-extraction"])
def process_with_llm(text, product_type, llm, run_name=None):
    """
    Process text with LLM to extract product information
    Updated to handle new JSON structures (array for subtypes, flat+Subtypes for cosmetics)

    Args:
        text (str): Text to process
        product_type (str): Type of product to extract
        llm: Language model to use
        run_name (str): Name for the LangSmith run

    Returns:
        dict or list: Extracted product data (list for subtypes, dict for cosmetics)
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

    try:
        # Use simple string replacement for cosmetics to avoid JSON braces conflict
        if product_type == "cosmetics":
            # Replace {text} manually to avoid LangChain PromptTemplate issues with JSON braces
            formatted_prompt = prompt_content.replace("{text}", text)
            st.info("Sending data to LLM for processing...")
            # Directly invoke LLM with formatted prompt
            response = llm.invoke(formatted_prompt)
        else:
            # Use PromptTemplate for other product types (fragrance, subtype, hscode)
            prompt_template = PromptTemplate.from_template(prompt_content)
            st.info("Sending data to LLM for processing...")
            chain = prompt_template | llm

            # Invoke the chain with text input
            response = chain.invoke({"text": text})

        # Parse JSON from response
        try:
            # Check if response is a string or an object with content attribute
            if hasattr(response, "content"):
                response_text = response.content
            else:
                response_text = response

            # Find JSON in the response
            json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text

            product_data = json.loads(json_str)

            # Validate the expected structure based on product type
            if product_type == "subtype":
                if not isinstance(product_data, list):
                    st.warning(
                        f"Expected array format for subtype, got {type(product_data)}. Attempting to fix..."
                    )
                    # Try to extract from legacy catalogB structure if present
                    if isinstance(product_data, dict) and "catalogB" in product_data:
                        product_data = [product_data["catalogB"]]
                    else:
                        st.error(
                            "Cannot convert response to expected subtype array format"
                        )
                        return None

            elif product_type == "cosmetics":
                if not isinstance(product_data, dict):
                    st.error(
                        f"Expected object format for cosmetics, got {type(product_data)}"
                    )
                    return None

                # Check if it's legacy format and needs conversion
                if "catalogA" in product_data or "catalogB" in product_data:
                    st.warning(
                        "Received legacy catalogA/catalogB format. Please update prompts to new format."
                    )
                    # For now, process as legacy format but warn about migration needed

            # Post-process HScode with Deepseek for all product types
            hscode = process_hscode_with_deepseek(product_data, product_type)
            if hscode:
                product_data = place_hscode_in_correct_location(
                    product_data, hscode, product_type
                )

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


@traceable(name="consolidated_data_processing", tags=["batch-processing", "multi-source"])
def process_consolidated_data(consolidated_text, product_type, llm):
    """
    Process consolidated text data to extract product information
    Updated to handle new JSON structures

    Args:
        consolidated_text (str): Combined text from all sources
        product_type (str): Type of product to extract
        llm: Language model to use

    Returns:
        list: List of extracted product data (may contain single item for cosmetics, multiple for subtypes)
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
        # Handle different return formats by product type
        if product_type == "subtype":
            # Subtype should already be a list from LLM, don't double-wrap
            if isinstance(product_data, list):
                return product_data  # Already a list (subtype format)
            else:
                # If LLM returned single object for subtype, wrap it
                return [product_data]
        else:
            # For cosmetics/fragrance, always return as list for consistency
            if isinstance(product_data, list):
                return product_data  # Already a list
            else:
                return [product_data]  # Wrap single item in list
    return []
