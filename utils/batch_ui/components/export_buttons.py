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
        """Render bulk JSON export button"""
        all_results = [
            config.get_latest_attempt().result for config in completed_configs
        ]
        json_data, filename = self.export_handler.export_products_as_json(
            all_results, "all_extracted_products.json"
        )
        st.download_button(
            "📄 Download All as JSON",
            data=json_data,
            file_name=filename,
            mime="application/json",
            use_container_width=True,
            help="Download all products in a single JSON file",
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
        """Extract brand name from result with fallback logic (copied from ResultsDisplay)"""
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

            # Handle flat structure
            value = result.get(field)
            if (
                value
                and value.strip()
                and value.lower() not in ["", "null", "none", "unknown"]
            ):
                return value.strip()

        return "Unknown"

    def _get_product_name_from_result(self, result):
        """Extract product name from result with fallback logic (copied from ResultsDisplay)"""
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

            # Handle flat structure
            value = result.get(field)
            if (
                value
                and value.strip()
                and value.lower() not in ["", "null", "none", "unknown"]
            ):
                return value.strip()

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
