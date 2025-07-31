"""
Results display component for showing extraction results with PHASE 3 USER ATTRIBUTION
SIMPLIFIED: Removed filtering - focus on product creation and user activity registration only
Analytics and filtering moved to tabbed_analytics_dashboard.py
"""

import streamlit as st
import re
import json
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

        # Try to parse different formats of AI reasoning
        reasoning_text = llm_reasoning.strip()

        # Format 1: OpenEvals format with separators
        if " | " in reasoning_text:
            parts = reasoning_text.split(" | ")
            for part in parts:
                if ":" in part:
                    metric_part, reasoning_part = part.split(":", 1)
                    metric_part = metric_part.strip().lower()
                    reasoning_part = reasoning_part.strip()

                    # Map different metric naming conventions
                    if any(
                        keyword in metric_part
                        for keyword in ["structure", "json", "schema"]
                    ):
                        parsed_reasoning["structure"] = reasoning_part
                    elif any(
                        keyword in metric_part
                        for keyword in ["content", "accuracy", "hallucination"]
                    ):
                        parsed_reasoning["content"] = reasoning_part
                    elif any(
                        keyword in metric_part
                        for keyword in ["translation", "portuguese", "language"]
                    ):
                        parsed_reasoning["translation"] = reasoning_part

        # Format 2: Try to parse by evaluation keywords
        elif any(
            keyword in reasoning_text.lower()
            for keyword in ["structure", "content", "translation"]
        ):
            # Split by common patterns
            sections = []

            # Look for section headers
            import re

            section_pattern = r"(Structure|Content|Translation|structure|content|translation).*?(?=(?:Structure|Content|Translation|structure|content|translation)|$)"
            matches = re.findall(
                section_pattern, reasoning_text, re.DOTALL | re.IGNORECASE
            )

            for match in matches:
                if match:
                    section_text = match.strip()
                    if any(
                        keyword in section_text.lower()[:20]
                        for keyword in ["structure", "json", "schema"]
                    ):
                        parsed_reasoning["structure"] = section_text
                    elif any(
                        keyword in section_text.lower()[:20]
                        for keyword in ["content", "accuracy"]
                    ):
                        parsed_reasoning["content"] = section_text
                    elif any(
                        keyword in section_text.lower()[:20]
                        for keyword in ["translation", "portuguese"]
                    ):
                        parsed_reasoning["translation"] = section_text

        # Format 3: Fallback - use entire reasoning for content if no proper parsing possible
        if all(
            v in ["No specific reasoning provided", "No reasoning available"]
            for v in parsed_reasoning.values()
        ):
            # If it's short, put it in all categories, if long put it in content
            if len(reasoning_text) < 200:
                parsed_reasoning = {
                    "structure": reasoning_text,
                    "content": reasoning_text,
                    "translation": reasoning_text,
                }
            else:
                parsed_reasoning["content"] = reasoning_text

        return parsed_reasoning

    def render_bulk_export_section(self, completed_configs):
        """Render the Export All Results section with all three options"""
        if not completed_configs:
            return

        st.subheader("📤 Export All Results")

        col1, col2, col3 = st.columns(3)

        with col1:
            # All as JSON button (single file)
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
                help="Download all products in a single JSON file",
            )

        with col2:
            # Individual JSON files as ZIP
            self.export_buttons._render_individual_json_export_button(completed_configs)

        with col3:
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
            self.render_bulk_export_section(completed_configs)

    def render_results(self, all_configs):
        """Alternative entry point - renders results with enhanced layout"""
        if not all_configs:
            st.info("No product configurations found.")
            return

        # Show summary metrics
        total = len(all_configs)
        completed = sum(1 for config in all_configs if config.has_successful_attempt())
        failed = sum(1 for config in all_configs if config.status == "failed")
        pending = total - completed - failed

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", total)
        with col2:
            st.metric("Completed", completed, delta="✅" if completed > 0 else None)
        with col3:
            st.metric("Failed", failed, delta="❌" if failed > 0 else None)
        with col4:
            st.metric("Pending", pending, delta="⏳" if pending > 0 else None)

        st.markdown("---")

        # Render each product result
        for i, config in enumerate(all_configs):
            with st.container():
                # Create header with status
                if config.has_successful_attempt():
                    status_icon = "✅"
                    latest_attempt = config.get_latest_attempt()
                    result = latest_attempt.result
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
                    st.markdown(f"**{i+1}. {status_icon} {product_title}**")
                    # PHASE 3: Show creator and source info
                    source_summary = getattr(
                        config, "source_summary", lambda: "No sources"
                    )()
                    st.caption(f"Sources: {source_summary} | {creator_info}")

                with col2:
                    # View JSON button
                    if st.button(
                        "📄", key=f"view_result_{config.id}", help="View JSON"
                    ):
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
                st.markdown(
                    f"**{index}. {status_icon} {product_title}** | {creator_info}"
                )

            with col2:
                # Toggle button for detailed view
                if st.button("👁️", key=f"toggle_{config.id}", help="View details"):
                    toggle_key = f"expanded_{config.id}"
                    st.session_state[toggle_key] = not st.session_state.get(
                        toggle_key, False
                    )

            with col3:
                # Quick export for successful results
                if config.has_successful_attempt():
                    self.export_buttons.render_json_download_button_compact(
                        result, config.id
                    )

            # Detailed view (expandable)
            if st.session_state.get(f"expanded_{config.id}", False):
                self._render_detailed_view(config)

            st.markdown("---")

    def _render_detailed_view(self, config):
        """Render detailed view of a single configuration"""
        if config.has_successful_attempt():
            latest_attempt = config.get_latest_attempt()
            result = latest_attempt.result

            # Show data sources
            self._render_data_sources(config)

            # Show extraction results in tabs
            tab1, tab2, tab3, tab4 = st.tabs(
                ["📋 Product Info", "📊 Raw JSON", "🧠 AI Evaluation", "📤 Export"]
            )

            with tab1:
                self._render_product_info_tab(result)

            with tab2:
                st.json(result)

            with tab3:
                # AI EVALUATION TAB
                st.markdown("### 🧠 AI Quality Evaluation")
                try:
                    from evaluations.evaluation_core import get_evaluation_for_config

                    evaluation = get_evaluation_for_config(config.id)
                    if evaluation:
                        # Show evaluation scores in metrics
                        eval_col1, eval_col2, eval_col3, eval_col4 = st.columns(4)

                        with eval_col1:
                            st.metric(
                                "Structure", f"{evaluation.get('structure_score', 0)}/5"
                            )
                        with eval_col2:
                            # FIX: Try multiple possible field names for content score
                            content_score = evaluation.get(
                                "content_score", 0
                            ) or evaluation.get("accuracy_score", 0)
                            st.metric("Content", f"{content_score}/5")
                        with eval_col3:
                            st.metric(
                                "Translation",
                                f"{evaluation.get('translation_score', 0)}/5",
                            )
                        with eval_col4:
                            overall = evaluation.get("overall_score", 0)
                            st.metric("Overall", f"{overall}/5")

                        # Show detailed evaluation with reasoning
                        st.markdown("---")
                        st.markdown("### 🤔 AI Assessment Details")

                        reasoning = evaluation.get("llm_reasoning", "")
                        if reasoning:
                            # Parse reasoning into components
                            parsed_reasoning = self._parse_ai_reasoning(reasoning)

                            eval_reason_col1, eval_reason_col2, eval_reason_col3 = (
                                st.columns(3)
                            )

                            with eval_reason_col1:
                                st.markdown("**📐 Structure**")
                                st.write(
                                    parsed_reasoning.get(
                                        "structure", "No reasoning available"
                                    )
                                )

                            with eval_reason_col2:
                                st.markdown("**📝 Content**")
                                st.write(
                                    parsed_reasoning.get(
                                        "content", "No reasoning available"
                                    )
                                )

                            with eval_reason_col3:
                                st.markdown("**🗣️ Translation**")
                                st.write(
                                    parsed_reasoning.get(
                                        "translation", "No reasoning available"
                                    )
                                )
                        else:
                            st.info(
                                "No detailed reasoning available for this evaluation"
                            )

                        # Show evaluation metadata
                        st.markdown("---")
                        st.markdown("**📋 Evaluation Metadata:**")
                        metadata_col1, metadata_col2 = st.columns(2)
                        with metadata_col1:
                            st.write(
                                f"• **Model Used:** {evaluation.get('evaluation_model', 'Unknown')}"
                            )
                            st.write(
                                f"• **Product Type:** {evaluation.get('product_type', 'Unknown')}"
                            )
                        with metadata_col2:
                            st.write(
                                f"• **Evaluated:** {evaluation.get('created_at', 'Unknown')}"
                            )
                            st.write(
                                f"• **Evaluation ID:** {evaluation.get('id', 'Unknown')}"
                            )

                        # Human feedback section
                        st.markdown("---")
                        st.markdown("### 👥 Human Feedback")
                        try:
                            from evaluations.evaluation_ui import (
                                _render_human_feedback_section,
                            )

                            _render_human_feedback_section(evaluation)
                        except (ImportError, Exception):
                            st.info("Human feedback system not available")

                    else:
                        st.info(
                            "🤖 No AI quality evaluation available for this product"
                        )
                        st.markdown("**Why no evaluation?**")
                        st.write(
                            "• Evaluations are automatically generated after extraction"
                        )
                        st.write("• Check if the evaluation system is enabled")
                        st.write(
                            "• Try re-running the extraction to trigger evaluation"
                        )

                except (ImportError, Exception) as e:
                    st.error(f"AI evaluation system not available: {str(e)}")

            with tab4:
                self.export_buttons.render_single_product_buttons(result, config.id)

        elif config.status == "failed":
            # Show error details
            failed_preview = self._get_failed_product_preview(config)
            st.error(f"❌ {failed_preview}")

            if hasattr(config, "error_message") and config.error_message:
                st.code(config.error_message)

            # Show data sources for context
            self._render_data_sources(config)

        else:
            # Pending/processing status
            st.info("⏳ Processing in progress...")
            self._render_data_sources(config)

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

    def _render_data_sources(self, config):
        """Render data sources information"""
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

    def _render_product_info_tab(self, result):
        """Render formatted product information"""
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Basic Information:**")
            st.write(f"• **Brand:** {self._get_brand_from_result(result)}")
            st.write(f"• **Product:** {self._get_product_name_from_result(result)}")
            st.write(f"• **Type:** {result.get('product_type', 'N/A')}")
            st.write(f"• **EAN:** {result.get('EAN', 'N/A')}")

            # HScode using the imported function
            hscode = get_hscode_from_product_data(result) or "N/A"
            st.write(f"• **HScode:** {hscode}")

        with col2:
            st.write("**Pricing & Details:**")
            price = self._format_price_display(result)
            st.write(f"• **Price:** {price}")
            size = self._format_size_display(result)
            st.write(f"• **Size:** {size}")

            # Additional fields
            if result.get("description"):
                st.write(f"• **Description:** {result.get('description')[:100]}...")

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

                        st.markdown("---")

                        # ============================================
                        # JSON DROPDOWN (SECOND)
                        # ============================================
                        with st.expander("📄 View JSON Data", expanded=False):
                            st.json(result)

                        # ============================================
                        # HUMAN EVALUATION (THIRD) - MOVED UP
                        # ============================================
                        st.markdown("**👥 Human Feedback**")
                        try:
                            from evaluations.evaluation_core import (
                                get_evaluation_for_config,
                            )
                            from evaluations.evaluation_ui import (
                                _render_human_feedback_section,
                            )

                            evaluation = get_evaluation_for_config(config.id)
                            if evaluation:
                                _render_human_feedback_section(evaluation)
                            else:
                                st.info(
                                    "Complete an AI evaluation first to provide human feedback"
                                )

                        except (ImportError, Exception):
                            st.info("Human feedback system not available")

                        st.markdown("---")

                        # ============================================
                        # AI EVALUATION RESULTS (FOURTH) - MOVED DOWN
                        # ============================================
                        st.markdown("**🧠 AI Quality Evaluation**")
                        try:
                            from evaluations.evaluation_core import (
                                get_evaluation_for_config,
                            )
                            from evaluations.evaluation_ui import (
                                render_evaluation_details,
                            )

                            evaluation = get_evaluation_for_config(config.id)
                            if evaluation:
                                # Show evaluation scores in metrics - FIXED CONTENT SCORE FIELD
                                eval_col1, eval_col2, eval_col3, eval_col4 = st.columns(
                                    4
                                )

                                with eval_col1:
                                    st.metric(
                                        "Structure",
                                        f"{evaluation.get('structure_score', 0)}/5",
                                    )
                                with eval_col2:
                                    # FIX: Try multiple possible field names for content score
                                    content_score = evaluation.get(
                                        "content_score", 0
                                    ) or evaluation.get("accuracy_score", 0)
                                    st.metric("Content", f"{content_score}/5")
                                with eval_col3:
                                    st.metric(
                                        "Translation",
                                        f"{evaluation.get('translation_score', 0)}/5",
                                    )
                                with eval_col4:
                                    overall = evaluation.get("overall_score", 0)
                                    st.metric("Overall", f"{overall}/5")

                                # Show detailed evaluation with reasoning
                                with st.expander(
                                    "🤔 AI Assessment Details", expanded=False
                                ):
                                    reasoning = evaluation.get("llm_reasoning", "")
                                    if reasoning:
                                        # Parse reasoning into components
                                        parsed_reasoning = self._parse_ai_reasoning(
                                            reasoning
                                        )

                                        st.markdown("**Detailed AI Analysis:**")

                                        st.markdown("**📐 Structure Assessment:**")
                                        st.write(
                                            parsed_reasoning.get(
                                                "structure",
                                                "No structure reasoning available",
                                            )
                                        )

                                        st.markdown("**📝 Content Assessment:**")
                                        st.write(
                                            parsed_reasoning.get(
                                                "content",
                                                "No content reasoning available",
                                            )
                                        )

                                        st.markdown("**🗣️ Translation Assessment:**")
                                        st.write(
                                            parsed_reasoning.get(
                                                "translation",
                                                "No translation reasoning available",
                                            )
                                        )
                                    else:
                                        st.info(
                                            "No detailed reasoning available for this evaluation"
                                        )

                                    # Show evaluation metadata
                                    st.markdown("**📋 Evaluation Details:**")
                                    st.write(
                                        f"• **Model Used:** {evaluation.get('evaluation_model', 'Unknown')}"
                                    )
                                    st.write(
                                        f"• **Evaluated:** {evaluation.get('created_at', 'Unknown')}"
                                    )
                                    st.write(
                                        f"• **Product Type:** {evaluation.get('product_type', 'Unknown')}"
                                    )

                            else:
                                st.info(
                                    "🤖 No AI quality evaluation available for this product"
                                )

                        except (ImportError, Exception) as e:
                            st.info("AI evaluation system not available")

                        st.markdown("---")

                        # ============================================
                        # EXPORT OPTIONS (LAST)
                        # ============================================
                        # st.markdown("**📤 Export Options**")
                        # export_col1, export_col2 = st.columns(2)

                        # with export_col1:
                        #    self.export_buttons.render_json_download_button_compact(
                        #        result, config.id
                        #    )

                        # with export_col2:
                        #    self.export_buttons.render_dropbox_upload_button_compact(
                        #        result, config.id
                        #    )

                        # st.markdown("---")

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
                        st.markdown("**❌ Error Details**")
                        error_message = getattr(
                            config, "error_message", "No error details available"
                        )
                        st.code(error_message)

                        # Show data sources for context
                        self._render_data_sources(config)
                        st.markdown("---")

            else:
                # PHASE 3: Add creator info to pending products
                creator_info = self._format_creator_info(config)

                col1, col2 = st.columns([4, 1])
                with col1:
                    # PHASE 3: Include creator info
                    st.info(
                        f"Product {product_num}: ⏳ Processing... | {creator_info}",
                        icon="⏳",
                    )
                with col2:
                    # Show data sources button for pending products
                    if st.button(
                        "👁️", key=f"view_pending_{config.id}", help="View sources"
                    ):
                        toggle_key = f"pending_expanded_{config.id}"
                        st.session_state[toggle_key] = not st.session_state.get(
                            toggle_key, False
                        )

                # Show data sources ONLY when expanded
                if st.session_state.get(f"pending_expanded_{config.id}", False):
                    with st.container():
                        self._render_data_sources(config)
                        st.markdown("---")

    def render_config_list(self, configs):
        """Render list of configurations (for configuration management)"""
        if not configs:
            st.info(
                "No configurations found. Use the form above to add your first configuration."
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
                    source_summary = getattr(
                        config, "source_summary", lambda: "No sources"
                    )()
                    st.write(f"**Product {i+1}:** {source_summary}")

                with col2:
                    if st.button(
                        "👁️", key=f"view_config_{config.id}", help="View details"
                    ):
                        st.session_state[config_key] = not st.session_state[config_key]

                with col3:
                    if st.button("🗑️", key=f"remove_{config.id}", help="Remove"):
                        # Import the remove function when needed
                        from utils.product_config import remove_product_config

                        remove_product_config(config.id)
                        st.rerun()

                # Show details if toggled
                if st.session_state[config_key]:
                    st.write(f"**Product Type:** {config.product_type}")
                    st.write(
                        f"**Model:** {config.model_provider} / {config.model_name}"
                    )
                    st.write(f"**Status:** {config.status}")
                    self._render_data_sources(config)

                st.markdown("---")

    def _get_brand_from_result(self, result):
        """Extract brand name from result with fallback logic"""
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
        """Extract product name from result with fallback logic"""
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
            config: Product configuration object

        Returns:
            str: Formatted creator information
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

    def _format_price_display(self, result):
        """Format price for display"""
        price_fields = ["price", "Price", "cost", "Cost"]
        for field in price_fields:
            for catalog in ["catalogA", "catalogB"]:
                if catalog in result and isinstance(result[catalog], dict):
                    value = result[catalog].get(field)
                    if value and str(value).strip():
                        return str(value).strip()

            value = result.get(field)
            if value and str(value).strip():
                return str(value).strip()

        return "N/A"

    def _format_size_display(self, result):
        """Format size/volume for display"""
        size_fields = ["size", "Size", "volume", "Volume", "weight", "Weight"]
        for field in size_fields:
            for catalog in ["catalogA", "catalogB"]:
                if catalog in result and isinstance(result[catalog], dict):
                    value = result[catalog].get(field)
                    if value and str(value).strip():
                        return str(value).strip()

            value = result.get(field)
            if value and str(value).strip():
                return str(value).strip()

        return "N/A"

    def _render_product_overview(self, result):
        """Render a brief product overview"""
        brand = self._get_brand_from_result(result)
        product_name = self._get_product_name_from_result(result)
        price = self._format_price_display(result)

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{brand}**")
            st.write(product_name)
        with col2:
            st.write(f"**Price:** {price}")
            st.write(f"**Type:** {result.get('product_type', 'N/A')}")

    def render_disabled_reprocess_toggle(self, config_id):
        """Render a disabled reprocess toggle button"""
        st.button(
            "🔄",
            key=f"disabled_reprocess_{config_id}",
            disabled=True,
            label_visibility="collapsed",
        )

    def render_minimalist_bulk_export(self, completed_configs):
        """Render minimalist bulk export options - called from execute_tab.py"""
        if not completed_configs:
            return

        st.subheader("📤 Export All Results")

        col1, col2, col3 = st.columns(3)

        with col1:
            # All as JSON button (single file)
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
                help="Download all products in a single JSON file",
            )

        with col2:
            # Individual JSON files as ZIP
            self.export_buttons._render_individual_json_export_button(completed_configs)

        with col3:
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
