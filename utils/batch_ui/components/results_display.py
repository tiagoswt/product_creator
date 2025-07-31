"""
Results display component for showing extraction results with PHASE 3 USER ATTRIBUTION
SIMPLIFIED: Removed filtering - focus on product creation and user activity registration only
Analytics and filtering moved to tabbed_analytics_dashboard.py
"""

import streamlit as st
import re
from .export_buttons import ExportButtons
from .progress_tracker import ProgressTracker

# ADD this import for HScode helper function
from processors.text_processor import get_hscode_from_product_data


class ResultsDisplay:
    """Handles display of extraction results with PHASE 3 user attribution (no filtering)"""

    def __init__(self):
        self.export_buttons = ExportButtons()
        self.progress_tracker = ProgressTracker()

    def _parse_ai_reasoning(self, llm_reasoning: str) -> dict:
        """
        Parse concatenated AI reasoning into separate metric components.

        Args:
            llm_reasoning (str): Concatenated reasoning from all metrics

        Returns:
            dict: Separated reasoning for each metric
        """
        if not llm_reasoning or llm_reasoning.strip() == "":
            return {
                "structure": "No reasoning available",
                "content": "No reasoning available",
                "translation": "No reasoning available",
            }

        # Initialize with defaults
        parsed_reasoning = {
            "structure": "No specific reasoning provided",
            "content": "No specific reasoning provided",
            "translation": "No specific reasoning provided",
        }

        # Try to parse OpenEvals format: "metric_name: reasoning | metric_name: reasoning"
        if " | " in llm_reasoning:
            parts = llm_reasoning.split(" | ")
            for part in parts:
                if ":" in part:
                    metric_part, reasoning_part = part.split(":", 1)
                    metric_part = metric_part.strip().lower()
                    reasoning_part = reasoning_part.strip()

                    # Map different metric naming conventions
                    if "structure" in metric_part:
                        parsed_reasoning["structure"] = reasoning_part
                    elif "content" in metric_part or "accuracy" in metric_part:
                        parsed_reasoning["content"] = reasoning_part
                    elif "translation" in metric_part or "completeness" in metric_part:
                        parsed_reasoning["translation"] = reasoning_part

        # Try to parse fallback format or single reasoning
        elif any(
            keyword in llm_reasoning.lower()
            for keyword in ["structure", "content", "translation"]
        ):
            # Try to find individual metric reasoning within a longer text
            lines = llm_reasoning.split("\n")
            current_metric = None
            current_reasoning = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check if line starts a new metric section
                if line.lower().startswith("structure"):
                    if current_metric and current_reasoning:
                        parsed_reasoning[current_metric] = " ".join(current_reasoning)
                    current_metric = "structure"
                    current_reasoning = (
                        [line.split(":", 1)[-1].strip()] if ":" in line else [line]
                    )
                elif line.lower().startswith("content") or line.lower().startswith(
                    "accuracy"
                ):
                    if current_metric and current_reasoning:
                        parsed_reasoning[current_metric] = " ".join(current_reasoning)
                    current_metric = "content"
                    current_reasoning = (
                        [line.split(":", 1)[-1].strip()] if ":" in line else [line]
                    )
                elif line.lower().startswith("translation") or line.lower().startswith(
                    "completeness"
                ):
                    if current_metric and current_reasoning:
                        parsed_reasoning[current_metric] = " ".join(current_reasoning)
                    current_metric = "translation"
                    current_reasoning = (
                        [line.split(":", 1)[-1].strip()] if ":" in line else [line]
                    )
                else:
                    # Continue current reasoning
                    if current_metric:
                        current_reasoning.append(line)

            # Don't forget the last metric
            if current_metric and current_reasoning:
                parsed_reasoning[current_metric] = " ".join(current_reasoning)

        else:
            # Single reasoning block - use for all metrics
            parsed_reasoning = {
                "structure": llm_reasoning,
                "content": llm_reasoning,
                "translation": llm_reasoning,
            }

        return parsed_reasoning

    def _render_enhanced_ai_reasoning(self, llm_reasoning: str, unique_key: str):
        """
        Render AI reasoning in 3 separate columns for better readability.

        Args:
            llm_reasoning (str): The concatenated AI reasoning
            unique_key (str): Unique key for Streamlit components
        """
        st.markdown("**🤖 AI Quality Assessment Reasoning**")

        # Parse the reasoning into components
        parsed_reasoning = self._parse_ai_reasoning(llm_reasoning)

        # Display in 3 columns
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**🏗️ Structure Evaluation**")
            st.markdown("*JSON format and schema compliance*")
            st.text_area(
                "Structure Reasoning",
                value=parsed_reasoning["structure"],
                height=120,
                key=f"structure_reasoning_{unique_key}",
                disabled=True,
                label_visibility="collapsed",
            )

        with col2:
            st.markdown("**📝 Content Evaluation**")
            st.markdown("*Accuracy vs input, hallucination detection*")
            st.text_area(
                "Content Reasoning",
                value=parsed_reasoning["content"],
                height=120,
                key=f"content_reasoning_{unique_key}",
                disabled=True,
                label_visibility="collapsed",
            )

        with col3:
            st.markdown("**🌍 Translation Evaluation**")
            st.markdown("*Portuguese translation quality*")
            st.text_area(
                "Translation Reasoning",
                value=parsed_reasoning["translation"],
                height=120,
                key=f"translation_reasoning_{unique_key}",
                disabled=True,
                label_visibility="collapsed",
            )

    def _get_product_name_from_result(self, result):
        """Extract product name from result, trying multiple possible field names"""
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
        """Extract brand from result, handling nested structures"""
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

    def _format_creator_info(self, config) -> str:
        """
        PHASE 3: Format creator information for display.

        Args:
            config: Product configuration with user attribution

        Returns:
            Formatted creator string
        """
        try:
            if hasattr(config, "creator_summary"):
                return config.creator_summary()
            elif hasattr(config, "created_by_username"):
                username = getattr(config, "created_by_username", "unknown")
                user_name = getattr(config, "created_by_name", "Unknown User")
                if username != "system" and username != "unknown":
                    return f"Created by: {user_name} ({username})"
                else:
                    return "Created by: System"
            else:
                return "Creator: Unknown"
        except:
            return "Creator: Unknown"

    def render_minimalist_results(self, all_configs):
        """Render minimalist results list with PHASE 3 user attribution (no filtering)"""
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

                # Get evaluation data for quality badge
                try:
                    from evaluations.evaluation_core import get_evaluation_for_config
                    from evaluations.evaluation_ui import render_quality_badge

                    evaluation = get_evaluation_for_config(config.id)
                    quality_badge = render_quality_badge(evaluation)
                except (ImportError, Exception):
                    quality_badge = ""

                # PHASE 3: Get creator info
                creator_info = self._format_creator_info(config)

                # Compact successful result display with product number, quality, and creator
                col1, col2 = st.columns([4, 1])
                with col1:
                    success_text = f"Product {product_num}: ✅ {brand} - {product_name}"
                    if quality_badge:
                        success_text += f" | {quality_badge}"
                    # PHASE 3: Add creator info
                    success_text += f" | {creator_info}"
                    st.success(success_text, icon="✅")
                with col2:
                    if st.button("👁️", key=f"view_min_{config.id}", help="View details"):
                        toggle_key = f"minimalist_expanded_{config.id}"
                        st.session_state[toggle_key] = not st.session_state.get(
                            toggle_key, False
                        )

                # Show details if expanded - ENHANCED AI REASONING SECTION
                if st.session_state.get(f"minimalist_expanded_{config.id}", False):
                    with st.container():

                        # PHASE 3: CREATOR INFORMATION (FIRST)
                        st.markdown("**👤 Creator Information**")
                        creator_col1, creator_col2 = st.columns(2)

                        with creator_col1:
                            username = getattr(config, "created_by_username", "unknown")
                            user_name = getattr(
                                config, "created_by_name", "Unknown User"
                            )
                            st.write(f"**Created by:** {user_name}")
                            st.write(f"**Username:** {username}")

                        with creator_col2:
                            created_at = getattr(config, "created_at", None)
                            if created_at:
                                st.write(
                                    f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}"
                                )

                            # Show processor info if different from creator
                            processor_info = (
                                config.get_latest_processor_info()
                                if hasattr(config, "get_latest_processor_info")
                                else {}
                            )
                            if (
                                processor_info.get("username")
                                and processor_info.get("username") != username
                            ):
                                st.write(
                                    f"**Processed by:** {processor_info.get('user_name', 'Unknown')} ({processor_info.get('username')})"
                                )

                        st.markdown("---")

                        # ============================================
                        # 1. VIEW JSON DROPDOWN (SECOND)
                        # ============================================
                        with st.expander("📄 View JSON Data", expanded=False):
                            st.json(result)

                        st.markdown("---")  # Separator

                        # ============================================
                        # 2. HUMAN FEEDBACK (THIRD)
                        # ============================================
                        st.markdown("**👥 Human Feedback**")
                        try:
                            from evaluations.evaluation_core import (
                                get_evaluation_for_config,
                            )

                            evaluation = get_evaluation_for_config(config.id)
                            if evaluation:
                                # Import the human feedback component specifically
                                from evaluations.evaluation_ui import (
                                    _render_human_feedback_section,
                                )

                                _render_human_feedback_section(evaluation)
                            else:
                                st.info(
                                    "Complete an AI evaluation first to provide human feedback"
                                )
                        except (ImportError, Exception):
                            st.info("Human feedback system not available")

                        st.markdown("---")  # Separator

                        # ============================================
                        # 3. AI EVALUATION WITH ENHANCED REASONING (FOURTH)
                        # ============================================
                        st.markdown("**🧠 AI Quality Assessment**")
                        try:
                            from evaluations.evaluation_core import (
                                get_evaluation_for_config,
                            )

                            evaluation = get_evaluation_for_config(config.id)
                            if evaluation:
                                # Show metrics in compact format
                                col1, col2, col3, col4 = st.columns(4)

                                with col1:
                                    # Structure Correctness
                                    st.metric(
                                        "Structure",
                                        f"{evaluation.get('structure_score', 0)}/5",
                                        help="JSON structure and schema compliance",
                                    )
                                with col2:
                                    # Content Correctness
                                    st.metric(
                                        "Content",
                                        f"{evaluation.get('accuracy_score', 0)}/5",
                                        help="Accuracy vs input, hallucination detection",
                                    )
                                with col3:
                                    # Translation Correctness
                                    st.metric(
                                        "Translation",
                                        f"{evaluation.get('translation_score', 0)}/5",
                                        help="Portuguese translation quality",
                                    )
                                with col4:
                                    overall = evaluation.get("overall_score", 0)
                                    delta = (
                                        "Excellent"
                                        if overall >= 4.0
                                        else (
                                            "Good"
                                            if overall >= 3.0
                                            else "Fair" if overall >= 2.0 else "Poor"
                                        )
                                    )
                                    st.metric("Overall", f"{overall}/5", delta=delta)

                                # ENHANCED: Show AI reasoning in 3 columns instead of single text area
                                reasoning = evaluation.get("llm_reasoning", "")
                                if reasoning:
                                    with st.expander(
                                        "🤔 AI Assessment Details", expanded=False
                                    ):
                                        self._render_enhanced_ai_reasoning(
                                            reasoning, f"eval_{config.id}"
                                        )

                                # Show evaluator type
                                eval_model = evaluation.get("evaluation_model", "")
                                if "openevals" in eval_model.lower():
                                    st.caption(
                                        "🔬 Evaluated using OpenEvals 3-Metric System"
                                    )
                                elif "fallback" in eval_model.lower():
                                    st.caption("⚡ Evaluated using Fallback System")

                            else:
                                st.info(
                                    "🤖 No AI evaluation available for this product"
                                )
                        except (ImportError, Exception):
                            st.info("🤖 AI evaluation system not available")

                        st.markdown("---")  # Separator

                        # ============================================
                        # 4. EXPORT OPTIONS (LAST)
                        # ============================================
                        st.markdown("**📤 Export Options**")
                        export_col1, export_col2 = st.columns(2)

                        with export_col1:
                            self.export_buttons.render_json_download_button_compact(
                                result, config.id
                            )

                        with export_col2:
                            self.export_buttons.render_dropbox_upload_button_compact(
                                result, config.id
                            )

                        st.markdown("---")

            elif config.status == "failed":
                # PHASE 3: Add creator info to failed products
                failed_preview = self._get_failed_product_preview(config)
                creator_info = self._format_creator_info(config)

                col1, col2 = st.columns([4, 1])
                with col1:
                    # PHASE 3: Include creator info
                    st.error(
                        f"Product {product_num}: ❌ {failed_preview} | {creator_info}",
                        icon="❌",
                    )
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

                        # PHASE 3: Show creator information
                        st.markdown("**👤 Creator Information**")
                        username = getattr(config, "created_by_username", "unknown")
                        user_name = getattr(config, "created_by_name", "Unknown User")
                        st.write(f"**Created by:** {user_name} ({username})")

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
                # PHASE 3: Add creator info to processing products
                processing_preview = self._get_failed_product_preview(config)
                creator_info = self._format_creator_info(config)
                st.info(
                    f"Product {product_num}: ⏳ {processing_preview} | {creator_info}",
                    icon="⏳",
                )

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

    # Keep all other existing methods unchanged for backward compatibility
    def render_all_results(self, all_configs):
        """Render all product results with status and PHASE 3 user attribution (no filtering)"""
        if not all_configs:
            st.info(
                "No product configurations found. Add some configurations in the 'Configure Products' tab first."
            )
            return

        st.markdown("---")
        st.subheader("📊 Extraction Results")

        # Show metrics for all results (no filtering)
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

    def _render_single_result(self, config, index):
        """Render a single product result with PHASE 3 user attribution"""
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

            # PHASE 3: Get creator info
            creator_info = self._format_creator_info(config)

            # Product header with expandable details
            col1, col2, col3 = st.columns([8, 1, 1])

            with col1:
                st.markdown(f"**{index}. {status_icon} {product_title}**")
                # PHASE 3: Show creator and source info
                st.caption(f"Sources: {config.source_summary()} | {creator_info}")

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

    def _render_expanded_result(self, config):
        """Render expanded result details with PHASE 3 user attribution"""
        st.markdown("---")

        # PHASE 3: Show creator information first
        st.markdown("**👤 Creator Information**")
        creator_col1, creator_col2 = st.columns(2)

        with creator_col1:
            username = getattr(config, "created_by_username", "unknown")
            user_name = getattr(config, "created_by_name", "Unknown User")
            st.write(f"**Created by:** {user_name}")
            st.write(f"**Username:** {username}")

        with creator_col2:
            created_at = getattr(config, "created_at", None)
            if created_at:
                st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}")

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

    def render_config_list(self, configs):
        """Render list of existing configurations with PHASE 3 user attribution (no filtering)"""
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
                    # PHASE 3: Include creator info
                    creator_info = self._format_creator_info(config)
                    st.write(
                        f"**Product {i+1}:** {config.source_summary()} | {creator_info}"
                    )

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
        """Render detailed configuration information with PHASE 3 user attribution"""
        # PHASE 3: Show creator information first
        st.write("**👤 Creator Information**")
        username = getattr(config, "created_by_username", "unknown")
        user_name = getattr(config, "created_by_name", "Unknown User")
        created_at = getattr(config, "created_at", None)

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Created by:** {user_name} ({username})")
        with col2:
            if created_at:
                st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}")

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

