"""
Execute Batch Tab - Batch execution and results display
"""

import streamlit as st
from utils.product_config import get_product_configs, clear_product_configs
from ..handlers.batch_processor import BatchProcessor
from ..components.results_display import ResultsDisplay


def render_execute_tab():
    """Render the Execute Batch tab with minimalist side-by-side layout"""
    st.subheader("Execute Batch Extraction")

    # Get configurations
    configs = get_product_configs()

    # Initialize components
    batch_processor = BatchProcessor()
    results_display = ResultsDisplay()

    if not configs:
        st.warning(
            "No product configurations available. Please add at least one configuration in the Configure Products tab."
        )
        return

    # Create side-by-side layout
    col1, col2 = st.columns([1, 1])

    # Left column: Execution controls
    with col1:
        st.markdown("### 🚀 Batch Processing")

        # Show compact summary of configurations
        st.write(f"**Ready to process:** {len(configs)} product configurations")

        # Show brief overview
        with st.expander("📋 Configuration Overview", expanded=False):
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
                    sources.append(f"Web({url_count})")

                source_text = "+".join(sources) if sources else "No sources"
                st.caption(f"{i+1}. {config.product_type.title()} - {source_text}")

        # Action buttons
        if st.button(
            "🚀 Start Batch Extraction",
            type="primary",
            use_container_width=True,
        ):
            batch_processor.process_all_configurations()

        if st.button("🗑️ Clear All Configurations", use_container_width=True):
            clear_product_configs()
            st.success("All configurations cleared!")
            st.rerun()

    # Right column: Metrics only
    with col2:
        st.markdown("### 📊 Extraction Metrics")

        # Get all configs for metrics display
        all_configs = st.session_state.get("product_configs", [])

        if all_configs:
            # Show compact metrics
            total = len(all_configs)
            completed = sum(
                1 for config in all_configs if config.has_successful_attempt()
            )
            failed = sum(1 for config in all_configs if config.status == "failed")
            pending = total - completed - failed

            # Compact metrics display
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("✅ Done", completed)
            with metric_col2:
                st.metric("❌ Failed", failed)
            with metric_col3:
                st.metric("⏳ Pending", pending)

            # Show failed products list if any
            if failed > 0:
                st.markdown("**❌ Failed Products:**")
                failed_configs = [
                    config for config in all_configs if config.status == "failed"
                ]
                for config in failed_configs:
                    # Find the product number (index + 1) in the original list
                    product_num = all_configs.index(config) + 1
                    preview_name = results_display._get_failed_product_preview(config)
                    st.caption(f"Product {product_num}: ❌ {preview_name}")
        else:
            st.info("No extractions yet.")

    # Products Created section - Full width below the columns
    st.markdown("---")
    st.markdown("### 📦 Products Created")

    all_configs = st.session_state.get("product_configs", [])
    if all_configs:
        # Show the actual products list in full width
        results_display.render_minimalist_results(all_configs)
    else:
        st.info("No products created yet. Start batch extraction to see products here.")

    # Bulk export section (only if there are completed products)
    completed_configs = [
        config
        for config in st.session_state.get("product_configs", [])
        if config.has_successful_attempt()
    ]

    if completed_configs:
        st.markdown("---")
        results_display.render_minimalist_bulk_export(completed_configs)
