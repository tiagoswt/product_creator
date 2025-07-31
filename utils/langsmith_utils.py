import os
import streamlit as st
import dropbox
from dropbox.exceptions import AuthError, ApiError
import json
from datetime import datetime
import config
from processors.text_processor import get_hscode_from_product_data


def get_dropbox_client():
    """
    Get authenticated Dropbox client

    Returns:
        dropbox.Dropbox: Authenticated Dropbox client or None if failed
    """
    # Try to get access token from environment variables first
    access_token = os.getenv(config.ENV_DROPBOX_ACCESS_TOKEN)

    # If not in environment, get from session state or prompt user
    if not access_token:
        access_token = st.session_state.get(config.STATE_DROPBOX_ACCESS_TOKEN)

        if not access_token:
            # Prompt user for access token in sidebar
            access_token = st.sidebar.text_input(
                "Enter your Dropbox Access Token",
                type="password",
                key="dropbox_access_token_input",
                help="Create an app at https://www.dropbox.com/developers/apps and get your access token",
            )

            if not access_token:
                return None

            # Store in session state
            st.session_state[config.STATE_DROPBOX_ACCESS_TOKEN] = access_token

    try:
        # Create and test the Dropbox client
        dbx = dropbox.Dropbox(access_token)

        # Test the connection by getting account info
        dbx.users_get_current_account()

        return dbx
    except AuthError as e:
        st.error(f"Dropbox authentication failed: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error connecting to Dropbox: {str(e)}")
        return None


def upload_json_to_dropbox(dbx, json_data, filename, folder_path=None):
    """
    Upload JSON data to Dropbox

    Args:
        dbx (dropbox.Dropbox): Authenticated Dropbox client
        json_data (dict): JSON data to upload
        filename (str): Name for the file
        folder_path (str): Dropbox folder path (defaults to config.DROPBOX_BASE_FOLDER)

    Returns:
        tuple: (success: bool, message: str, file_path: str)
    """
    try:
        # Use default folder if none specified
        if folder_path is None:
            folder_path = config.DROPBOX_BASE_FOLDER

        # Ensure filename ends with .json
        if not filename.endswith(".json"):
            filename += ".json"

        # Create the full path
        full_path = f"{folder_path}/{filename}"

        # Convert JSON data to string
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        json_bytes = json_str.encode("utf-8")

        # Upload the file
        try:
            result = dbx.files_upload(
                json_bytes,
                full_path,
                mode=dropbox.files.WriteMode("overwrite"),
                autorename=True,
            )

            return (
                True,
                f"Successfully uploaded to {result.path_display}",
                result.path_display,
            )

        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                # Folder doesn't exist, try to create it
                try:
                    dbx.files_create_folder_v2(folder_path)
                    # Retry upload
                    result = dbx.files_upload(
                        json_bytes,
                        full_path,
                        mode=dropbox.files.WriteMode("overwrite"),
                        autorename=True,
                    )
                    return (
                        True,
                        f"Created folder and uploaded to {result.path_display}",
                        result.path_display,
                    )
                except Exception as folder_error:
                    return False, f"Failed to create folder: {str(folder_error)}", ""
            else:
                return False, f"Upload failed: {str(e)}", ""

    except Exception as e:
        return False, f"Error uploading to Dropbox: {str(e)}", ""


def create_folder_structure(dbx, base_folder=None):
    """
    Create folder structure in Dropbox (simplified to use single folder)

    Args:
        dbx (dropbox.Dropbox): Authenticated Dropbox client
        base_folder (str): Base folder path (defaults to config.DROPBOX_BASE_FOLDER)

    Returns:
        dict: Dictionary of created folders
    """
    if base_folder is None:
        base_folder = config.DROPBOX_BASE_FOLDER

    folders = {
        "base": base_folder,
        "daily": f"{base_folder}/Daily_Exports/{datetime.now().strftime('%Y-%m-%d')}",
    }

    created_folders = {}

    for folder_type, folder_path in folders.items():
        try:
            # Check if folder exists
            try:
                dbx.files_get_metadata(folder_path)
                created_folders[folder_type] = folder_path
            except:
                # Folder doesn't exist, create it
                try:
                    dbx.files_create_folder_v2(folder_path)
                    created_folders[folder_type] = folder_path
                except Exception as e:
                    st.warning(f"Could not create folder {folder_path}: {str(e)}")

        except Exception as e:
            st.warning(f"Error checking folder {folder_path}: {str(e)}")

    return created_folders


def clean_filename_component(text):
    """
    Clean text for use in filenames - more aggressive cleaning

    Args:
        text (str): Text to clean

    Returns:
        str: Cleaned text suitable for filenames
    """
    if not text or not isinstance(text, str):
        return ""

    # Remove extra whitespace and convert to string
    text = str(text).strip()

    # Replace common special characters and accents
    replacements = {
        "'": "",
        '"': "",
        "'": "",
        "'": "",
        """: "", """: "",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "á": "a",
        "â": "a",
        "ã": "a",
        "ä": "a",
        "ç": "c",
        "ñ": "n",
        "ü": "u",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "ô": "o",
        "õ": "o",
        "ö": "o",
        "&": "and",
        "%": "percent",
        "@": "at",
        "#": "hash",
        "(": "",
        ")": "",
        "[": "",
        "]": "",
        "{": "",
        "}": "",
        "/": "_",
        "\\": "_",
        "|": "_",
        "?": "",
        "*": "",
        "<": "",
        ">": "",
        ":": "",
        ";": "",
        "=": "",
        "+": "",
        "!": "",
        "~": "",
        "`": "",
        "^": "",
        "$": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Keep only alphanumeric, spaces, hyphens, and underscores
    cleaned = "".join(c for c in text if c.isalnum() or c in (" ", "-", "_"))

    # Replace multiple spaces/underscores with single underscore
    import re

    cleaned = re.sub(r"[-_\s]+", "_", cleaned)

    # Remove leading/trailing underscores
    cleaned = cleaned.strip("_")

    return cleaned


def _get_product_name_from_result(result_data):
    """
    Extract product name from result, trying multiple possible field names

    Args:
        result_data (dict): Product result data

    Returns:
        str: Product name
    """
    # Try different field names in order of preference
    name_fields = [
        "itemDescriptionEN",  # For cosmetics and subtype
        "product_name",  # For fragrance
        "product_title_EN",  # Alternative from catalogA
        "itemDescriptionPT",  # Portuguese fallback
        "product_title_PT",  # Portuguese fallback
    ]

    for field in name_fields:
        # Handle nested catalogB structure
        if "catalogB" in result_data and isinstance(result_data["catalogB"], dict):
            value = result_data["catalogB"].get(field)
            if (
                value
                and value.strip()
                and value.lower() not in ["", "null", "none", "unknown"]
            ):
                return value.strip()

        # Handle flat structure
        value = result_data.get(field)
        if (
            value
            and value.strip()
            and value.lower() not in ["", "null", "none", "unknown"]
        ):
            return value.strip()

    return "Unknown Product"


def _get_brand_from_result(result_data):
    """
    Extract brand from result, handling nested structures

    Args:
        result_data (dict): Product result data

    Returns:
        str: Brand name
    """
    # Try different field names and structures
    brand_fields = ["brand", "Brand", "BRAND"]

    for field in brand_fields:
        # Handle nested catalogA or catalogB structure
        for catalog in ["catalogA", "catalogB"]:
            if catalog in result_data and isinstance(result_data[catalog], dict):
                value = result_data[catalog].get(field)
                if (
                    value
                    and value.strip()
                    and value.lower() not in ["", "null", "none", "unknown"]
                ):
                    return value.strip()

        # Handle flat structure
        value = result_data.get(field)
        if (
            value
            and value.strip()
            and value.lower() not in ["", "null", "none", "unknown"]
        ):
            return value.strip()

    return "Unknown"


def create_product_filename_custom(
    product_config, result_data, is_reprocessed=False, debug=False
):
    """
    Create a custom filename based on product type and configuration

    Args:
        product_config:  object containing product type and base_product
        result_data (dict): Product result data
        is_reprocessed (bool): Whether this is a reprocessed file
        debug (bool): Whether to show debug information

    Returns:
        str: Complete filename with timestamp
    """
    # Get current timestamp
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M")

    if debug:
        print(
            f"Debug: product_type='{product_config.product_type}', base_product='{product_config.base_product}'"
        )

    if product_config.product_type == "subtype":
        # For subtype: subtype_{base_product}_{date}_{time}.json
        base_product = product_config.base_product or "unknown"
        base_filename = f"subtype_{base_product}_{date_str}_{time_str}"

    else:
        # For cosmetics/fragrance: {product_type}_{brand}_{date}_{time}.json
        brand = _get_brand_from_result(result_data)

        # Clean brand for filename
        clean_brand = clean_filename_component(brand)
        if not clean_brand or clean_brand.lower() in [
            "unknown",
            "unknown_brand",
            "n_a",
            "na",
            "null",
            "none",
            "",
        ]:
            clean_brand = "unknown"

        base_filename = (
            f"{product_config.product_type}_{clean_brand}_{date_str}_{time_str}"
        )

    # Add reprocessed suffix if applicable
    if is_reprocessed:
        base_filename += "_reprocessed"

    filename = f"{base_filename}.json"

    if debug:
        print(f"Debug: Custom filename='{filename}'")

    return filename


def create_product_filename(
    result_data, i=None, is_reprocessed=False, debug=False, product_config=None
):
    """
    Create a filename for a product using brand name as primary identifier (legacy function)
    This maintains backward compatibility while supporting the new custom naming

    Args:
        result_data (dict): Product result data
        i (int): Optional index for fallback naming
        is_reprocessed (bool): Whether this is a reprocessed file
        debug (bool): Whether to show debug information
        product_config: ProductConfig object for custom naming (new parameter)

    Returns:
        str: Complete filename with timestamp
    """
    # If product_config is provided, use the new custom naming
    if product_config:
        return create_product_filename_custom(
            product_config, result_data, is_reprocessed, debug
        )

    # Otherwise, use the original logic for backward compatibility
    # Use the improved helper functions
    brand = _get_brand_from_result(result_data)
    product_name = _get_product_name_from_result(result_data)

    if debug:
        print(f"Debug: Extracted brand='{brand}', product_name='{product_name}'")

    # Clean brand and product names
    clean_brand = clean_filename_component(brand)
    clean_product_name = clean_filename_component(product_name)

    if debug:
        print(
            f"Debug: Cleaned brand='{clean_brand}', product_name='{clean_product_name}'"
        )

    # Create filename - be more lenient with brand acceptance
    excluded_brands = ["unknown", "unknown_brand", "n_a", "na", "null", "none", ""]

    if clean_brand and clean_brand.lower() not in excluded_brands:
        # Use brand as primary identifier
        base_filename = clean_brand

        # Add product name if available and meaningfully different from brand
        if clean_product_name and clean_product_name.lower() != clean_brand.lower():
            # Only add if product name adds meaningful information
            if len(clean_product_name) > 2:  # Avoid single letters or very short names
                base_filename += f"_{clean_product_name}"

    elif clean_product_name and clean_product_name.lower() not in excluded_brands:
        # Use product name if brand is not available
        base_filename = clean_product_name

    else:
        # Final fallback - use index if provided, otherwise generic name
        if i is not None:
            base_filename = f"product_{i+1}"
        else:
            base_filename = "product"

    if debug:
        print(f"Debug: Base filename='{base_filename}'")

    # Limit filename length but be more generous
    base_filename = base_filename[:60]  # Increased from 50

    # Add reprocessed suffix if applicable
    if is_reprocessed:
        base_filename += "_reprocessed"

    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_filename}_{timestamp}.json"

    if debug:
        print(f"Debug: Final filename='{filename}'")

    return filename


def batch_upload_to_dropbox(dbx, completed_configs, folder_structure=None):
    """
    Upload all completed configurations to Dropbox in the single target folder

    Args:
        dbx (dropbox.Dropbox): Authenticated Dropbox client
        completed_configs (list): List of completed ProductConfig objects or mock objects
        folder_structure (dict): Pre-created folder structure

    Returns:
        dict: Upload results summary
    """
    if not folder_structure:
        folder_structure = create_folder_structure(dbx)

    results = {"successful": [], "failed": [], "total": len(completed_configs)}

    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Use the base folder for all uploads (no product type organization)
    target_folder = folder_structure.get("base", config.DROPBOX_BASE_FOLDER)

    for i, config in enumerate(completed_configs):
        try:
            # Get the result data - handle both ProductConfig objects and mock objects
            if hasattr(config, "result") and config.result:
                # Mock object with direct result attribute
                result_data = config.result
                config_id = config.id
            else:
                # Real ProductConfig object - get result from latest attempt
                latest_attempt = config.get_latest_attempt()
                if not latest_attempt or not latest_attempt.result:
                    results["failed"].append(
                        {
                            "config_id": getattr(config, "id", f"config_{i}"),
                            "filename": f"product_{i+1}.json",
                            "error": "No result data available",
                            "product_name": "Unknown",
                            "brand": "Unknown",
                        }
                    )
                    continue

                result_data = latest_attempt.result
                config_id = config.id

            # Debug the result data to see what we're working with
            brand = _get_brand_from_result(result_data)
            product_name = _get_product_name_from_result(result_data)

            # Show what data we have for debugging
            st.info(
                f"Processing product {i+1}: brand='{brand}', product_name='{product_name}'"
            )

            # Create filename using the new function with debug enabled
            filename = create_product_filename(
                result_data, i, debug=True, product_config=config
            )

            # Update progress
            status_text.text(f"Uploading {i+1}/{len(completed_configs)}: {filename}")

            # Upload to Dropbox using the single target folder
            success, message, file_path = upload_json_to_dropbox(
                dbx, result_data, filename, target_folder
            )

            if success:
                results["successful"].append(
                    {
                        "config_id": config_id,
                        "filename": filename,
                        "path": file_path,
                        "product_name": product_name,
                        "brand": brand,
                    }
                )
                st.success(f"✅ Uploaded: {filename}")
            else:
                results["failed"].append(
                    {
                        "config_id": config_id,
                        "filename": filename,
                        "error": message,
                        "product_name": product_name,
                        "brand": brand,
                    }
                )
                st.error(f"❌ Failed to upload: {filename} - {message}")

        except Exception as e:
            # Handle errors gracefully
            product_name = "Unknown"
            brand = "Unknown"

            try:
                if hasattr(config, "result") and config.result:
                    product_name = _get_product_name_from_result(config.result)
                    brand = _get_brand_from_result(config.result)
                else:
                    latest_attempt = config.get_latest_attempt()
                    if latest_attempt and latest_attempt.result:
                        product_name = _get_product_name_from_result(
                            latest_attempt.result
                        )
                        brand = _get_brand_from_result(latest_attempt.result)
            except:
                pass

            results["failed"].append(
                {
                    "config_id": getattr(config, "id", f"config_{i}"),
                    "filename": f"product_{i+1}.json",
                    "error": str(e),
                    "product_name": product_name,
                    "brand": brand,
                }
            )

        # Update progress
        progress_bar.progress((i + 1) / len(completed_configs))

    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()

    return results


def test_dropbox_connection():
    """
    Test Dropbox connection and display account info

    Returns:
        bool: True if connection successful
    """
    dbx = get_dropbox_client()

    if not dbx:
        return False

    try:
        account_info = dbx.users_get_current_account()
        st.success(f"Connected to Dropbox as: {account_info.name.display_name}")

        # Show available space
        try:
            space_usage = dbx.users_get_space_usage()
            used_gb = space_usage.used / (1024**3)

            # Handle different allocation types
            allocation = space_usage.allocation
            if hasattr(allocation, "get_individual") and allocation.get_individual():
                allocated_gb = allocation.get_individual().allocated / (1024**3)
                st.info(
                    f"Storage: {used_gb:.2f} GB used of {allocated_gb:.2f} GB allocated"
                )
            elif hasattr(allocation, "get_team") and allocation.get_team():
                allocated_gb = allocation.get_team().allocated / (1024**3)
                st.info(
                    f"Storage: {used_gb:.2f} GB used of {allocated_gb:.2f} GB allocated (Team)"
                )
            else:
                st.info(f"Storage: {used_gb:.2f} GB used")
        except Exception as space_error:
            st.info(f"Storage info unavailable: {str(space_error)}")

        # Show the current target folder
        st.info(f"All JSON files will be uploaded to: {config.DROPBOX_BASE_FOLDER}")

        return True

    except Exception as e:
        st.error(f"Dropbox connection test failed: {str(e)}")
        return False

