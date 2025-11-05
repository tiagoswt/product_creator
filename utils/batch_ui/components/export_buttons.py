"""
Reusable export buttons component
"""

import streamlit as st
import json
import zipfile
import io
from ..handlers.export_handler import ExportHandler


class ExportButtons:
    """Reusable export buttons for product results"""

    def __init__(self):
        self.export_handler = ExportHandler()

    def render_json_download_button_compact(
        self, result, config_id, is_reprocessed=False
    ):
        """Render compact JSON download button"""
        suffix = "reprocessed" if is_reprocessed else ""
        filename = self.export_handler.create_product_filename(result, suffix)

        json_data = json.dumps(result, indent=2, ensure_ascii=False)
        st.download_button(
            "📄 JSON",
            data=json_data,
            file_name=filename,
            mime="application/json",
            key=f"download_json_compact_{config_id}{'_reprocessed' if is_reprocessed else ''}",
            use_container_width=True,
        )

    def render_dropbox_upload_button_compact(
        self, result, config_id, is_reprocessed=False
    ):
        """Render compact Dropbox upload button"""
        if self.export_handler.dropbox_available:
            if st.button(
                "☁️ Dropbox",
                key=f"dropbox_compact_{config_id}{'_reprocessed' if is_reprocessed else ''}",
                use_container_width=True,
                help="Upload to Dropbox",
            ):
                self.export_handler.upload_single_product_to_dropbox(
                    result, config_id, is_reprocessed
                )
        else:
            st.button(
                "☁️ N/A",
                disabled=True,
                use_container_width=True,
                help="Dropbox not available",
            )

    def render_single_product_buttons(self, result, config_id, is_reprocessed=False):
        """Render export buttons for a single product"""
        st.write("**📤 Export Options:**")
        export_col1, export_col2, export_col3 = st.columns(3)

        with export_col1:
            self._render_json_download_button(result, config_id, is_reprocessed)

        with export_col2:
            self._render_dropbox_upload_button(result, config_id, is_reprocessed)

        with export_col3:
            self._render_copy_format_button(result, config_id)

    def render_bulk_export_buttons(self, completed_configs):
        """Render bulk export buttons with new individual JSON option"""
        st.subheader("📤 Bulk Export Options")
        col1, col2, col3 = st.columns(3)

        with col1:
            self._render_bulk_json_button(completed_configs)

        with col2:
            self._render_individual_json_export_button(completed_configs)

        with col3:
            self._render_bulk_dropbox_button(completed_configs)

    def _render_json_download_button(self, result, config_id, is_reprocessed=False):
        """Render JSON download button"""
        suffix = "reprocessed" if is_reprocessed else ""
        filename = self.export_handler.create_product_filename(result, suffix)

        json_data = json.dumps(result, indent=2, ensure_ascii=False)
        st.download_button(
            "📄 Download JSON",
            data=json_data,
            file_name=filename,
            mime="application/json",
            key=f"download_json_{config_id}{'_reprocessed' if is_reprocessed else ''}",
            use_container_width=True,
        )

    def _render_dropbox_upload_button(self, result, config_id, is_reprocessed=False):
        """Render Dropbox upload button"""
        if self.export_handler.dropbox_available:
            if st.button(
                "☁️ Upload to Dropbox",
                key=f"dropbox_upload_{config_id}{'_reprocessed' if is_reprocessed else ''}",
                use_container_width=True,
                help="Upload JSON to Dropbox folder",
            ):
                self.export_handler.upload_single_product_to_dropbox(
                    result, config_id, is_reprocessed
                )
        else:
            st.button(
                "☁️ Dropbox N/A",
                disabled=True,
                use_container_width=True,
                help="Dropbox integration not available",
            )

    def _render_copy_format_button(self, result, config_id):
        """Render copy format button"""
        if st.button(
            "📋 Copy Format",
            key=f"copy_format_{config_id}",
            use_container_width=True,
        ):
            copy_text = self.export_handler.create_copy_format_text(result)
            st.code(copy_text)

    def _render_bulk_json_button(self, completed_configs):
        """Render single JSON export button"""
        if not completed_configs:
            return
            
        # Get the latest/first product result instead of all products
        latest_config = completed_configs[0]  # Take the first completed config
        single_result = latest_config.get_latest_attempt().result
        
        # Create filename for single product
        brand = self._get_brand_from_result(single_result)
        product_name = self._get_product_name_from_result(single_result)
        filename = f"{brand}_{product_name}.json".replace(" ", "_").replace("/", "_")
        
        json_data = json.dumps(single_result, indent=2, ensure_ascii=False)
        st.download_button(
            "📄 Download as JSON",
            data=json_data,
            file_name=filename,
            mime="application/json",
            use_container_width=True,
            help="Download the product as JSON file",
        )

    def _render_individual_json_export_button(self, completed_configs):
        """Render button to export each product as individual JSON files in a ZIP"""
        if not completed_configs:
            return

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for config in completed_configs:
                result = config.get_latest_attempt().result

                # Extract brand and product name using proper nested structure logic
                brand = self._get_brand_from_result(result)
                product_name = self._get_product_name_from_result(result)

                # Create base filename without extension first
                if brand != "Unknown" and product_name != "Unknown Product":
                    base_filename = f"{brand}_{product_name}"
                elif product_name != "Unknown Product":
                    base_filename = f"{product_name}"
                elif brand != "Unknown":
                    base_filename = f"{brand}_product"
                else:
                    base_filename = f"product_{config.id}"

                # Clean base filename (remove invalid characters) - DON'T include .json yet
                base_filename = "".join(
                    c for c in base_filename if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                base_filename = base_filename.replace(" ", "_")

                # Ensure base filename isn't too long (save room for .json extension)
                if len(base_filename) > 95:
                    base_filename = base_filename[:95]

                # NOW add the .json extension
                filename = f"{base_filename}.json"

                # Add JSON data to ZIP
                json_data = json.dumps(result, indent=2, ensure_ascii=False)
                zip_file.writestr(filename, json_data)

        zip_buffer.seek(0)

        st.download_button(
            "📦 Download Individual JSONs (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="individual_products.zip",
            mime="application/zip",
            use_container_width=True,
            help=f"Download {len(completed_configs)} individual JSON files in a ZIP archive",
        )

    def _get_brand_from_result(self, result):
        """Extract brand name from result with fallback logic"""
        # Handle array format (subtype)
        if isinstance(result, list) and len(result) > 0:
            result = result[0]  # Use first item for brand extraction
        
        # Handle dict format
        if not isinstance(result, dict):
            return "Product"  # Generic fallback for subtype without brand
            
        # Try to find brand in standard locations
        for field in ["brand", "Brand", "BRAND"]:
            # Check catalogA/catalogB structure
            for catalog in ["catalogA", "catalogB"]:
                if catalog in result and isinstance(result[catalog], dict):
                    value = result[catalog].get(field)
                    if (
                        value
                        and value.strip()
                        and value.lower() not in ["", "null", "none", "unknown"]
                    ):
                        return value.strip()

            # Handle flat structure - but only if brand field exists
            if field in result:
                value = result[field]
                if (
                    value
                    and str(value).strip()
                    and str(value).lower() not in ["", "null", "none", "unknown"]
                ):
                    return str(value).strip()

        # For subtype format, try to extract brand from product name
        product_name = self._get_product_name_from_result(result)
        if product_name and product_name != "Unknown Product":
            # Try to extract brand from product name (first word often is brand)
            words = product_name.split()
            if len(words) > 0:
                return words[0]
        
        return "Product"  # Generic fallback

    def _get_product_name_from_result(self, result):
        """Extract product name from result with fallback logic (copied from ResultsDisplay)"""
        # Handle array format (subtype)
        if isinstance(result, list) and len(result) > 0:
            result = result[0]  # Use first item for name extraction
        
        # Handle dict format
        if not isinstance(result, dict):
            return "Unknown Product"
            
        # Try different field names in order of preference
        name_fields = [
            "UrlEN",  # Primary preference - SEO URL slug
            "ItemDescriptionEN",  # For cosmetics and subtype (updated case)
            "itemDescriptionEN",  # For cosmetics and subtype (legacy case)
            "product_name",  # For fragrance
            "product_title_EN",  # Alternative from catalogA
            "ItemDescriptionPT",  # Portuguese fallback (updated case)
            "itemDescriptionPT",  # Portuguese fallback (legacy case)
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

            # Check catalogA/catalogB structure
            for catalog in ["catalogA", "catalogB"]:
                if catalog in result and isinstance(result[catalog], dict):
                    value = result[catalog].get(field)
                    if (
                        value
                        and value.strip()
                        and value.lower() not in ["", "null", "none", "unknown"]
                    ):
                        return value.strip()

            # Handle flat structure - but only if field exists
            if field in result:
                value = result[field]
                if (
                    value
                    and str(value).strip()
                    and str(value).lower() not in ["", "null", "none", "unknown"]
                ):
                    return str(value).strip()

        return "Unknown Product"

    def _render_bulk_dropbox_button(self, completed_configs):
        """Render bulk Dropbox upload button"""
        if self.export_handler.dropbox_available:
            if st.button(
                "☁️ Upload All to Dropbox",
                use_container_width=True,
                help="Upload all completed products to Dropbox",
            ):
                self.export_handler.bulk_upload_to_dropbox(completed_configs)
        else:
            st.button(
                "☁️ Dropbox N/A",
                disabled=True,
                use_container_width=True,
                help="Dropbox integration not available",
            )

    def render_show_hide_json_button(self, config_id):
        """Render show/hide JSON button"""
        if st.button(
            "🔍 Show/Hide JSON",
            key=f"toggle_json_{config_id}",
            use_container_width=True,
        ):
            st.session_state[f"show_json_{config_id}"] = not st.session_state.get(
                f"show_json_{config_id}", False
            )
