"""
Results display component for showing extraction results
"""

import streamlit as st
from .export_buttons import ExportButtons
from .progress_tracker import ProgressTracker


class ResultsDisplay:
    """Handles display of extraction results"""

    def __init__(self):
        self.export_buttons = ExportButtons()
        self.progress_tracker = ProgressTracker()

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

    def _get_failed_product_preview(self, config):
        """Get a preview name for a failed product configuration"""
        try:
            # Try to extract a preview from the sources
            if config.pdf_file:
                return f"PDF: {config.pdf_file.name[:25]}..."
            elif config.excel_file:
                return f"Excel: {config.excel_file.name[:25]}..."
            elif config.website_url:
                url = config.website_url.split(",")[0].strip()
                if len(url) > 30:
                    url = url[:27] + "..."
                return f"Web: {url}"
            else:
                return f"{config.product_type.title()} Product"
        except:
            return f"{config.product_type.title()} Product"

    def render_minimalist_results(self, all_configs):
        """Render minimalist results list for side-by-side layout"""
        if not all_configs:
            return

        # Show all results: completed, failed, and processing with product numbers
        for i, config in enumerate(all_configs):
            product_num = i + 1  # Product numbering starts from 1

            if config.has_successful_attempt():
                latest_attempt = config.get_latest_attempt()
                result = latest_attempt.result

                brand = self._get_brand_from_result(result)
                product_name = self._get_product_name_from_result(result)

                # Compact successful result display with product number
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.success(
                        f"Product {product_num}: ✅ {brand} - {product_name}", icon="✅"
                    )
                with col2:
                    if st.button("👁️", key=f"view_min_{config.id}", help="View details"):
                        toggle_key = f"minimalist_expanded_{config.id}"
                        st.session_state[toggle_key] = not st.session_state.get(
                            toggle_key, False
                        )

                # Show details if expanded
                if st.session_state.get(f"minimalist_expanded_{config.id}", False):
                    with st.container():
                        st.markdown("**Export Options:**")
                        export_col1, export_col2 = st.columns(2)

                        with export_col1:
                            self.export_buttons.render_json_download_button_compact(
                                result, config.id
                            )

                        with export_col2:
                            self.export_buttons.render_dropbox_upload_button_compact(
                                result, config.id
                            )

                        # Show JSON in expander
                        with st.expander("View JSON", expanded=False):
                            st.json(result)

                        st.markdown("---")

            elif config.status == "failed":
                # Compact failed result display with product number - show in list but error details only when expanded
                failed_preview = self._get_failed_product_preview(config)

                col1, col2 = st.columns([4, 1])
                with col1:
                    st.error(f"Product {product_num}: ❌ {failed_preview}", icon="❌")
                with col2:
                    if st.button(
                        "👁️", key=f"view_failed_{config.id}", help="View error details"
                    ):
                        toggle_key = f"failed_expanded_{config.id}"
                        st.session_state[toggle_key] = not st.session_state.get(
                            toggle_key, False
                        )

                # Show error details ONLY when expanded
                if st.session_state.get(f"failed_expanded_{config.id}", False):
                    with st.container():
                        st.markdown("**❌ Extraction Failed**")

                        latest_attempt = config.get_latest_attempt()
                        if latest_attempt and latest_attempt.error_message:
                            st.error(f"**Error:** {latest_attempt.error_message}")

                        # Show configuration details
                        st.markdown("**Configuration:**")
                        st.write(f"- Product Type: {config.product_type}")
                        st.write(
                            f"- Model: {config.model_provider}/{config.model_name}"
                        )
                        st.write(f"- Sources: {config.source_summary()}")

                        st.markdown("---")

            elif config.status == "processing":
                # Compact processing display with product number
                processing_preview = self._get_failed_product_preview(
                    config
                )  # Same logic
                st.info(f"Product {product_num}: ⏳ {processing_preview}", icon="⏳")

    def render_minimalist_bulk_export(self, completed_configs):
        """Render minimalist bulk export options - only JSON and Dropbox"""
        st.subheader("📤 Export All Results")

        col1, col2 = st.columns(2)

        with col1:
            # All as JSON button
            all_results = [
                config.get_latest_attempt().result for config in completed_configs
            ]
            json_data, filename = (
                self.export_buttons.export_handler.export_products_as_json(
                    all_results, "all_extracted_products.json"
                )
            )
            st.download_button(
                "📄 Download All as JSON",
                data=json_data,
                file_name=filename,
                mime="application/json",
                use_container_width=True,
            )

        with col2:
            # All to Dropbox button
            if self.export_buttons.export_handler.dropbox_available:
                if st.button(
                    "☁️ Upload All to Dropbox",
                    use_container_width=True,
                    help="Upload all completed products to Dropbox",
                ):
                    self.export_buttons.export_handler.bulk_upload_to_dropbox(
                        completed_configs
                    )
            else:
                st.button(
                    "☁️ Dropbox N/A",
                    disabled=True,
                    use_container_width=True,
                    help="Dropbox integration not available",
                )

    # Keep all original methods for backward compatibility
    def render_all_results(self, all_configs):
        """Render all product results with status"""
        if not all_configs:
            st.info(
                "No product configurations found. Add some configurations in the 'Configure Products' tab first."
            )
            return

        st.markdown("---")
        st.subheader("📊 Extraction Results")

        # Show metrics
        total, completed, failed, pending = (
            self.progress_tracker.render_processing_summary(all_configs)
        )

        # Show ALL products with their current status
        st.markdown("---")
        st.subheader("📋 All Product Results")

        for i, config in enumerate(all_configs):
            self._render_single_result(config, i + 1)

        # Bulk export section for completed products
        completed_configs = [
            config for config in all_configs if config.has_successful_attempt()
        ]
        if completed_configs:
            st.markdown("---")
            self.export_buttons.render_bulk_export_buttons(completed_configs)

            # Show summary if requested
            if st.session_state.get("show_summary", False):
                self._render_extraction_summary(
                    total, completed, failed, pending, completed_configs
                )

    def _render_single_result(self, config, index):
        """Render a single product result"""
        with st.container():
            # Create header with status
            if config.has_successful_attempt():
                status_icon = "✅"
                latest_attempt = config.get_latest_attempt()
                result = latest_attempt.result

                # Use improved product name extraction
                brand = self._get_brand_from_result(result)
                product_name = self._get_product_name_from_result(result)
                product_title = f"{brand} - {product_name}"

            elif config.status == "failed":
                status_icon = "❌"
                product_title = "Failed Extraction"
            else:
                status_icon = "⏳"
                product_title = "Pending Extraction"

            # Product header with expandable details
            col1, col2, col3 = st.columns([8, 1, 1])

            with col1:
                st.markdown(f"**{index}. {status_icon} {product_title}**")
                st.caption(f"Sources: {config.source_summary()}")

            with col2:
                # View JSON button
                if st.button("📄", key=f"view_result_{config.id}", help="View JSON"):
                    toggle_key = f"result_expanded_{config.id}"
                    st.session_state[toggle_key] = not st.session_state.get(
                        toggle_key, False
                    )

            with col3:
                # Mark for reprocessing button (only for completed or failed)
                if config.has_successful_attempt() or config.status == "failed":
                    self._render_reprocess_toggle(config)

            # Show details if expanded
            if st.session_state.get(f"result_expanded_{config.id}", False):
                self._render_expanded_result(config)

            st.markdown("---")

    def _render_reprocess_toggle(self, config):
        """Render reprocessing toggle button"""
        reprocess_key = f"mark_reprocess_{config.id}"
        current_marked = st.session_state.get(reprocess_key, False)

        if st.button(
            "🔄" if not current_marked else "✅",
            key=f"mark_btn_{config.id}",
            help=(
                "Mark for reprocessing"
                if not current_marked
                else "Marked for reprocessing"
            ),
        ):
            st.session_state[reprocess_key] = not current_marked
            st.rerun()

    def _render_expanded_result(self, config):
        """Render expanded result details"""
        st.markdown("---")

        if config.has_successful_attempt():
            # Show successful result
            latest_attempt = config.get_latest_attempt()
            result = latest_attempt.result

            # Mark for reprocessing checkbox
            reprocess_key = f"mark_reprocess_{config.id}"
            is_marked = st.checkbox(
                "Mark for reprocessing",
                value=st.session_state.get(reprocess_key, False),
                key=f"reprocess_check_{config.id}",
            )
            st.session_state[reprocess_key] = is_marked

            # Export options for this product
            self.export_buttons.render_single_product_buttons(
                result, config.id, is_reprocessed=False
            )

            # Show/Hide JSON button
            export_col1, export_col2, export_col3 = st.columns(3)
            with export_col3:
                self.export_buttons.render_show_hide_json_button(config.id)

            # Show JSON if toggled
            if st.session_state.get(f"show_json_{config.id}", False):
                st.json(result)

        elif config.status == "failed":
            # Show failed result
            st.error("❌ **Extraction Failed**")

            latest_attempt = config.get_latest_attempt()
            if latest_attempt and latest_attempt.error_message:
                st.write(f"**Error:** {latest_attempt.error_message}")

            # Mark for reprocessing
            reprocess_key = f"mark_reprocess_{config.id}"
            is_marked = st.checkbox(
                "Mark for reprocessing",
                value=st.session_state.get(reprocess_key, False),
                key=f"reprocess_check_failed_{config.id}",
            )
            st.session_state[reprocess_key] = is_marked

        else:
            # Show pending result
            st.info("⏳ **Processing Pending**")
            st.write("This product configuration is waiting to be processed.")

    def _render_extraction_summary(
        self, total, completed, failed, pending, completed_configs
    ):
        """Render extraction summary"""
        st.markdown("---")
        st.subheader("📈 Extraction Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Overall Statistics:**")
            st.write(f"- Total Products: {total}")
            st.write(f"- Successfully Extracted: {completed}")
            st.write(f"- Failed Extractions: {failed}")
            st.write(f"- Pending: {pending}")

            marked_count = sum(
                1
                for config in completed_configs
                if st.session_state.get(f"mark_reprocess_{config.id}", False)
            )
            st.write(f"- Marked for Reprocessing: {marked_count}")

        with col2:
            st.write("**Product Types:**")
            product_types = {}
            for config in completed_configs:
                ptype = config.product_type
                product_types[ptype] = product_types.get(ptype, 0) + 1

            for ptype, count in product_types.items():
                st.write(f"- {ptype.title()}: {count}")

    def render_config_summary(self, configs):
        """Render configuration summary"""
        st.write(f"**Ready to extract {len(configs)} product configurations:**")

        # Show quick summary of each config
        for i, config in enumerate(configs):
            sources = []
            if config.pdf_file and config.pdf_pages:
                sources.append(f"PDF({len(config.pdf_pages)})")
            if config.excel_file and config.excel_rows:
                sources.append(f"Excel({len(config.excel_rows)})")
            if config.website_url:
                url_count = len(
                    [
                        url.strip()
                        for url in config.website_url.split(",")
                        if url.strip()
                    ]
                )
                if url_count == 1:
                    sources.append("Website")
                else:
                    sources.append(f"Websites({url_count})")

            source_text = " + ".join(sources) if sources else "No sources"
            st.write(
                f"  {i+1}. **{config.product_type.title()}** - {source_text} - {config.model_provider}/{config.model_name}"
            )

    def render_config_list(self, configs):
        """Render list of existing configurations"""
        if not configs:
            st.info(
                "No product configurations added yet. Use the form below to add your first configuration."
            )
            return

        st.write(f"Total configurations: {len(configs)}")

        # Display each configuration
        for i, config in enumerate(configs):
            with st.container():
                config_key = f"config_expanded_{config.id}"
                if config_key not in st.session_state:
                    st.session_state[config_key] = False

                col1, col2, col3 = st.columns([8, 1, 1])

                with col1:
                    st.write(f"**Product {i+1}:** {config.source_summary()}")

                with col2:
                    if st.button(
                        "👁️", key=f"view_config_{config.id}", help="View details"
                    ):
                        st.session_state[config_key] = not st.session_state[config_key]

                with col3:
                    if st.button("🗑️", key=f"remove_{config.id}", help="Remove"):
                        from utils.product_config import remove_product_config

                        remove_product_config(config.id)
                        st.rerun()

                # Show details if toggled
                if st.session_state[config_key]:
                    self._render_config_details(config)

                st.markdown("---")

    def _render_config_details(self, config):
        """Render detailed configuration information"""
        st.write(f"**Product Type:** {config.product_type}")
        st.write(f"**Model:** {config.model_provider} / {config.model_name}")
        st.write(f"**Status:** {config.status}")

        # Show all data sources
        sources = []
        if config.pdf_file and config.pdf_pages:
            sources.append(
                f"📄 PDF: {config.pdf_file.name} ({len(config.pdf_pages)} pages)"
            )
        if config.excel_file and config.excel_rows:
            file_type = (
                "CSV" if config.excel_file.name.lower().endswith(".csv") else "Excel"
            )
            sources.append(
                f"📊 {file_type}: {config.excel_file.name} ({len(config.excel_rows)} rows)"
            )
        if config.website_url:
            url_count = len(
                [url.strip() for url in config.website_url.split(",") if url.strip()]
            )
            if url_count == 1:
                sources.append(f"🌐 Website: {config.website_url.strip()}")
            else:
                sources.append(f"🌐 Websites: {url_count} URLs")

        if sources:
            st.write("**Data Sources:**")
            for source in sources:
                st.write(f"  • {source}")
        else:
            st.warning("No data sources configured")

        # Display custom instructions if they exist
        if hasattr(config, "custom_instructions") and config.custom_instructions:
            st.write("**Custom Instructions:**")
            st.code(config.custom_instructions)
