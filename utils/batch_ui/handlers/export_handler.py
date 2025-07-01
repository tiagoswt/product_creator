"""
Export handler for product data and Dropbox operations
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
import config

# Import Dropbox utilities
try:
    from utils.dropbox_utils import (
        get_dropbox_client,
        upload_json_to_dropbox,
        create_product_filename,
    )

    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False


class ExportHandler:
    """Handles all export operations including Dropbox uploads"""

    def __init__(self):
        self.dropbox_available = DROPBOX_AVAILABLE

    def _get_product_name_from_result(self, result):
        """
        Extract product name from result, trying multiple possible field names

        Args:
            result (dict): Product result data

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
            if "catalogB" in result and isinstance(result["catalogB"], dict):
                value = result["catalogB"].get(field)
                if (
                    value
                    and value.strip()
                    and value.lower() not in ["", "null", "none", "unknown"]
                ):
                    return value.strip()

            # Handle flat structure
            value = result.get(field)
            if (
                value
                and value.strip()
                and value.lower() not in ["", "null", "none", "unknown"]
            ):
                return value.strip()

        return "Unknown Product"

    def _get_brand_from_result(self, result):
        """
        Extract brand from result, handling nested structures

        Args:
            result (dict): Product result data

        Returns:
            str: Brand name
        """
        # Try different field names and structures
        brand_fields = ["brand", "Brand", "BRAND"]

        for field in brand_fields:
            # Handle nested catalogA or catalogB structure
            for catalog in ["catalogA", "catalogB"]:
                if catalog in result and isinstance(result[catalog], dict):
                    value = result[catalog].get(field)
                    if (
                        value
                        and value.strip()
                        and value.lower() not in ["", "null", "none", "unknown"]
                    ):
                        return value.strip()

            # Handle flat structure
            value = result.get(field)
            if (
                value
                and value.strip()
                and value.lower() not in ["", "null", "none", "unknown"]
            ):
                return value.strip()

        return "Unknown"

    def upload_single_product_to_dropbox(
        self, result, config_id, is_reprocessed=False, product_config=None
    ):
        """Upload a single product JSON to Dropbox"""

        if not self.dropbox_available:
            st.error(
                "❌ Dropbox integration not available. Please install the dropbox package."
            )
            return False

        # Get Dropbox client
        dbx = get_dropbox_client()
        if not dbx:
            st.error("❌ Could not connect to Dropbox. Please check your access token.")
            return False

        try:
            # Debug the result data to see what we're working with
            brand = self._get_brand_from_result(result)
            product_name = self._get_product_name_from_result(result)

            # Show what data we have for debugging
            st.info(f"Single upload: brand='{brand}', product_name='{product_name}'")

            # Create filename using the improved function with optional product_config
            filename = create_product_filename(
                result,
                is_reprocessed=is_reprocessed,
                debug=True,
                product_config=product_config,
            )

            # Use the single target folder for all products
            folder_path = config.DROPBOX_BASE_FOLDER

            # Upload to Dropbox
            success, message, file_path = upload_json_to_dropbox(
                dbx, result, filename, folder_path
            )

            if success:
                st.success(f"✅ Uploaded to Dropbox: {file_path}")
                return True
            else:
                st.error(f"❌ Upload failed: {message}")
                return False

        except Exception as e:
            st.error(f"❌ Error uploading to Dropbox: {str(e)}")
            return False

    def bulk_upload_to_dropbox(self, completed_configs):
        """Upload multiple product JSONs to Dropbox"""

        if not self.dropbox_available:
            st.error(
                "❌ Dropbox integration not available. Please install the dropbox package."
            )
            return

        # Get Dropbox client
        dbx = get_dropbox_client()
        if not dbx:
            st.error("❌ Could not connect to Dropbox. Please check your access token.")
            return

        if not completed_configs:
            st.warning("⚠️ No completed products to upload.")
            return

        st.info(
            f"🔄 Starting bulk upload of {len(completed_configs)} products to Dropbox..."
        )

        # Create single progress tracking elements that will be updated
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

        successful_uploads = 0
        failed_uploads = 0

        # Use the single target folder for all products
        target_folder = config.DROPBOX_BASE_FOLDER

        try:
            for i, product_config in enumerate(
                completed_configs
            ):  # Changed 'config' to 'product_config'
                current_num = i + 1

                latest_attempt = (
                    product_config.get_latest_attempt()
                )  # Changed 'config' to 'product_config'
                result = latest_attempt.result

                # Get product info for status display
                brand = self._get_brand_from_result(result)
                product_name = self._get_product_name_from_result(result)

                # Update single status line
                status_text.info(
                    f"☁️ Uploading {current_num}/{len(completed_configs)}: {brand} - {product_name}"
                )

                # Update progress bar
                progress_bar.progress((current_num - 0.5) / len(completed_configs))

                # Create filename using the new custom function with product_config
                filename = create_product_filename(
                    result, i, debug=False, product_config=product_config
                )

                try:
                    # Upload to Dropbox using the single target folder
                    success, message, file_path = upload_json_to_dropbox(
                        dbx, result, filename, target_folder
                    )

                    if success:
                        successful_uploads += 1
                        # Brief success status
                        status_text.success(
                            f"✅ Uploaded {current_num}/{len(completed_configs)}: {brand} - {product_name}"
                        )
                    else:
                        failed_uploads += 1
                        # Brief failure status
                        status_text.error(
                            f"❌ Failed {current_num}/{len(completed_configs)}: {brand} - {product_name}"
                        )

                except Exception as e:
                    failed_uploads += 1
                    status_text.error(
                        f"❌ Error {current_num}/{len(completed_configs)}: {brand} - {product_name}"
                    )

                # Update progress bar to full for this item
                progress_bar.progress(current_num / len(completed_configs))

            # Final progress update
            progress_bar.progress(1.0)

            # Show final summary
            if failed_uploads > 0:
                status_text.warning(
                    f"🔄 Bulk upload completed: {successful_uploads} successful, {failed_uploads} failed"
                )
            else:
                status_text.success(
                    f"🎉 Bulk upload completed: All {successful_uploads} products uploaded successfully to Dropbox!"
                )

            # Show upload summary
            if successful_uploads > 0:
                st.info(
                    f"📁 All uploaded files are organized in your Dropbox {config.DROPBOX_BASE_FOLDER} folder"
                )

        except Exception as e:
            st.error(f"❌ Bulk upload error: {str(e)}")
            progress_bar.empty()
            status_text.empty()

    def export_products_as_json(self, results, filename="products.json"):
        """Export products as JSON file"""
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        return json_data, filename

    def export_products_as_csv(self, results, filename="products.csv"):
        """Export products as CSV file"""
        df_data = []
        for result in results:
            flat_result = {}
            for key, value in result.items():
                if isinstance(value, list):
                    flat_result[key] = ", ".join(str(item) for item in value)
                else:
                    flat_result[key] = value
            df_data.append(flat_result)

        df = pd.DataFrame(df_data)
        csv_data = df.to_csv(index=False)
        return csv_data, filename

    def create_product_filename(self, result, suffix="", product_config=None):
        """Create a clean filename for a product (backward compatibility)"""
        try:
            # Use the improved function from dropbox_utils with new custom naming
            if suffix:
                # For backward compatibility, add suffix before timestamp
                filename = create_product_filename(
                    result,
                    is_reprocessed=(suffix == "reprocessed"),
                    product_config=product_config,
                )
                if suffix != "reprocessed":
                    # Insert custom suffix before timestamp
                    if "_" in filename:
                        parts = filename.rsplit(
                            "_", 2
                        )  # Split from right to get timestamp parts
                        if len(parts) >= 3:
                            base = parts[0]
                            timestamp = f"{parts[1]}_{parts[2]}"
                            filename = f"{base}_{suffix}_{timestamp}"
                return filename
            else:
                return create_product_filename(
                    result, debug=True, product_config=product_config
                )
        except:
            # Fallback to simple method if import fails
            brand = self._get_brand_from_result(result)
            product_name = self._get_product_name_from_result(result)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{brand}_{product_name}_{timestamp}.json"

    def create_copy_format_text(self, result):
        """Create formatted text for copying product information"""
        brand = self._get_brand_from_result(result)
        product_name = self._get_product_name_from_result(result)

        copy_text = f"""Product: {brand} {product_name}
Brand: {brand}
Price: {result.get('price', 'N/A')} {result.get('currency', '')}
Type: {result.get('product_type', 'N/A')}
Size: {result.get('size', 'N/A')} {result.get('unit', '')}
HScode: {result.get('hscode', 'N/A')}
EAN: {result.get('EAN', 'N/A')}
CNP: {result.get('CNP', 'N/A')}"""

        return copy_text
