"""
Export handler for product data and Dropbox operations
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

# Import Dropbox utilities
try:
    from utils.dropbox_utils import get_dropbox_client, upload_json_to_dropbox

    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False


class ExportHandler:
    """Handles all export operations including Dropbox uploads"""

    def __init__(self):
        self.dropbox_available = DROPBOX_AVAILABLE

    def upload_single_product_to_dropbox(self, result, config_id, is_reprocessed=False):
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
            # Create filename
            product_name = result.get("product_name", "product")
            brand = result.get("brand", "unknown_brand")

            # Clean filename components
            clean_brand = "".join(
                c for c in brand if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            clean_product_name = "".join(
                c for c in product_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()

            filename_parts = []
            if clean_brand and clean_brand.lower() != "unknown_brand":
                filename_parts.append(clean_brand)
            filename_parts.append(clean_product_name)

            # Create base filename
            base_filename = "_".join(filename_parts).replace(" ", "_")[:50]

            # Add reprocessed suffix if applicable
            if is_reprocessed:
                base_filename += "_reprocessed"

            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base_filename}_{timestamp}.json"

            # Determine folder based on product type
            product_type = result.get("product_type", "unknown")
            folder_mapping = {
                "cosmetics": "/E-commerce_Products/Cosmetics",
                "fragrance": "/E-commerce_Products/Fragrances",
                "subtype": "/E-commerce_Products/Subtypes",
            }

            folder_path = folder_mapping.get(product_type, "/E-commerce_Products/Other")

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

        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        successful_uploads = 0
        failed_uploads = 0

        try:
            for i, config in enumerate(completed_configs):
                # Update progress
                progress_percentage = i / len(completed_configs)
                progress_bar.progress(progress_percentage)

                latest_attempt = config.get_latest_attempt()
                result = latest_attempt.result

                product_name = result.get("product_name", "unknown")
                brand = result.get("brand", "unknown")

                status_text.text(
                    f"Uploading {i+1}/{len(completed_configs)}: {brand} - {product_name}"
                )

                try:
                    # Create filename
                    clean_brand = "".join(
                        c for c in brand if c.isalnum() or c in (" ", "-", "_")
                    ).strip()
                    clean_product_name = "".join(
                        c for c in product_name if c.isalnum() or c in (" ", "-", "_")
                    ).strip()

                    filename_parts = []
                    if clean_brand and clean_brand.lower() != "unknown":
                        filename_parts.append(clean_brand)
                    filename_parts.append(clean_product_name)

                    base_filename = "_".join(filename_parts).replace(" ", "_")[:50]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{base_filename}_{timestamp}.json"

                    # Determine folder based on product type
                    product_type = result.get("product_type", "unknown")
                    folder_mapping = {
                        "cosmetics": "/E-commerce_Products/Cosmetics",
                        "fragrance": "/E-commerce_Products/Fragrances",
                        "subtype": "/E-commerce_Products/Subtypes",
                    }

                    folder_path = folder_mapping.get(
                        product_type, "/E-commerce_Products/Other"
                    )

                    # Upload to Dropbox
                    success, message, file_path = upload_json_to_dropbox(
                        dbx, result, filename, folder_path
                    )

                    if success:
                        successful_uploads += 1
                    else:
                        failed_uploads += 1
                        st.warning(
                            f"⚠️ Failed to upload {brand} - {product_name}: {message}"
                        )

                except Exception as e:
                    failed_uploads += 1
                    st.error(f"❌ Error uploading {brand} - {product_name}: {str(e)}")

                # Update progress
                progress_bar.progress((i + 1) / len(completed_configs))

            # Final progress update
            progress_bar.progress(1.0)
            status_text.empty()

            # Show completion summary
            if failed_uploads > 0:
                st.warning(
                    f"🔄 Bulk upload completed: {successful_uploads} successful, {failed_uploads} failed"
                )
            else:
                st.success(
                    f"🎉 Bulk upload completed: All {successful_uploads} products uploaded successfully to Dropbox!"
                )

            # Show upload summary
            if successful_uploads > 0:
                st.info(
                    f"📁 Uploaded files are organized by product type in your Dropbox /E-commerce_Products/ folder"
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

    def create_product_filename(self, result, suffix=""):
        """Create a clean filename for a product"""
        product_name = result.get("product_name", "product")
        brand = result.get("brand", "")

        filename_parts = [brand, product_name] if brand else [product_name]
        base_filename = "_".join(filename_parts).replace(" ", "_")[:50]

        if suffix:
            base_filename += f"_{suffix}"

        return f"{base_filename}.json"

    def create_copy_format_text(self, result):
        """Create formatted text for copying product information"""
        brand = result.get("brand", "N/A")
        product_name = result.get("product_name", "N/A")

        copy_text = f"""Product: {brand} {product_name}
Brand: {brand}
Price: {result.get('price', 'N/A')} {result.get('currency', '')}
Type: {result.get('product_type', 'N/A')}
Size: {result.get('size', 'N/A')} {result.get('unit', '')}
HScode: {result.get('hscode', 'N/A')}
EAN: {result.get('EAN', 'N/A')}
CNP: {result.get('CNP', 'N/A')}"""

        return copy_text
