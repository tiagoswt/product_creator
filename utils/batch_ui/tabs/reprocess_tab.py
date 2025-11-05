"""
Reprocess Products Tab - Product reprocessing management
"""

import streamlit as st
from utils.product_config import get_product_configs
from ..handlers.reprocessor import ProductReprocessor
from ..components.export_buttons import ExportButtons

# Configuration constants
GROQ_MODELS = [
    "deepseek-r1-distill-llama-70b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.3-70b-versatile",
]

OPENAI_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
]

DEFAULT_GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
DEFAULT_OPENAI_MODEL = "gpt-4o"


def render_reprocess_tab():
    """Render the Reprocess Products tab"""
    st.subheader("🔄 Reprocess Products")
    st.markdown(
        """
    Reprocess extracted products with different models, parameters, or custom instructions.
    **Mark products for reprocessing** in the 'Execute Batch' tab, then configure reprocessing parameters here.
    """
    )

    # Initialize components
    reprocessor = ProductReprocessor()
    export_buttons = ExportButtons()

    # Get products marked for reprocessing
    all_configs = get_product_configs()
    completed_configs = [
        config for config in all_configs if config.has_successful_attempt()
    ]
    marked_configs = [
        config
        for config in completed_configs
        if st.session_state.get(f"mark_reprocess_{config.id}", False)
    ]

    if not completed_configs:
        st.warning("⚠️ No completed extractions available for reprocessing.")
        st.info("Complete some product extractions in the 'Execute Batch' tab first.")
        return

    # Show selection summary
    _render_selection_summary(completed_configs, marked_configs)

    if not marked_configs:
        _render_no_marked_products_info(completed_configs)
        return

    # Show marked products and reprocessing options
    st.markdown("---")
    st.subheader(f"📌 Products Marked for Reprocessing ({len(marked_configs)})")

    # Show each marked product with individual configuration
    for i, config in enumerate(marked_configs):
        _render_marked_product(config, i + 1, reprocessor, export_buttons)

    # Bulk reprocessing controls
    _render_bulk_reprocessing_controls(marked_configs, reprocessor)

    # Show reprocessing history
    _render_reprocessing_history(marked_configs)


def _render_selection_summary(completed_configs, marked_configs):
    """Render selection summary metrics"""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Completed", len(completed_configs))
    with col2:
        st.metric("Marked for Reprocessing", len(marked_configs), delta="📌")
    with col3:
        if st.button(
            "🔄 Refresh Selection", help="Refresh the list of marked products"
        ):
            st.rerun()


def _render_no_marked_products_info(completed_configs):
    """Render info when no products are marked for reprocessing"""
    st.info("📌 **No products marked for reprocessing**")
    st.markdown("**To mark products for reprocessing:**")
    st.markdown("1. Go to the **'Execute Batch'** tab")
    st.markdown("2. Expand the product details (👁️ button)")
    st.markdown(
        "3. Check **'Mark for reprocessing'** for products you want to reprocess"
    )
    st.markdown("4. Return to this tab to configure reprocessing")

    # Show available products for quick reference
    with st.expander("📋 Show All Completed Products"):
        for i, config in enumerate(completed_configs):
            latest_attempt = config.get_latest_attempt()
            result = latest_attempt.result
            # Import the extract function to use the same logic
            from evaluations.simple_db import extract_product_name_from_json
            product_name = extract_product_name_from_json(result)
            st.write(
                f"**{i+1}.** {product_name}"
            )
            st.caption(
                f"Model: {config.model_provider}/{config.model_name} | Sources: {config.source_summary()}"
            )


def _render_marked_product(config, index, reprocessor, export_buttons):
    """Render a single marked product for reprocessing"""
    latest_attempt = config.get_latest_attempt()
    result = latest_attempt.result

    with st.container():
        # Product header
        col1, col2 = st.columns([9, 1])

        with col1:
            # Import the extract function to use the same logic
            from evaluations.simple_db import extract_product_name_from_json
            product_name = extract_product_name_from_json(result)
            st.markdown(
                f"**{index}. {product_name}**"
            )
            st.caption(
                f"Current: {config.model_provider}/{config.model_name} | Sources: {config.source_summary()}"
            )

        with col2:
            # Remove from reprocessing list
            if st.button(
                "❌",
                key=f"remove_reprocess_{config.id}",
                help="Remove from reprocessing",
            ):
                st.session_state[f"mark_reprocess_{config.id}"] = False
                st.rerun()

        # Show JSON output
        st.write("**📄 Current JSON Output:**")
        st.json(result)

        # Individual reprocessing parameters for this product
        st.write("**⚙️ Configure Reprocessing Parameters:**")

        # Import the extract function to use the same logic
        from evaluations.simple_db import extract_product_name_from_json
        product_name = extract_product_name_from_json(result)
        with st.expander(
            f"🔧 Settings for {product_name}", expanded=False
        ):
            _render_reprocessing_settings(config, reprocessor, export_buttons)

        st.markdown("---")


def _render_reprocessing_settings(config, reprocessor, export_buttons):
    """Render reprocessing settings for a single product"""
    param_col1, param_col2, param_col3 = st.columns(3)

    with param_col1:
        reprocess_provider = st.selectbox(
            "Model Provider",
            ["groq", "openai"],
            index=0 if config.model_provider == "groq" else 1,
            key=f"reprocess_provider_{config.id}",
        )

    with param_col2:
        if reprocess_provider == "groq":
            reprocess_model_options = GROQ_MODELS
            reprocess_default_model = DEFAULT_GROQ_MODEL
        else:
            reprocess_model_options = OPENAI_MODELS
            reprocess_default_model = DEFAULT_OPENAI_MODEL

        # Find current model index
        try:
            current_model_index = reprocess_model_options.index(config.model_name)
        except ValueError:
            current_model_index = (
                reprocess_model_options.index(reprocess_default_model)
                if reprocess_default_model in reprocess_model_options
                else 0
            )

        reprocess_model = st.selectbox(
            "Model",
            reprocess_model_options,
            index=current_model_index,
            key=f"reprocess_model_{config.id}",
        )

    with param_col3:
        reprocess_temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=config.temperature,
            step=0.1,
            key=f"reprocess_temperature_{config.id}",
        )

    # Custom instructions for this product
    custom_instructions = st.text_area(
        "Custom Instructions for this product",
        value=config.custom_instructions,
        placeholder="Enter specific instructions for reprocessing this product...",
        height=100,
        key=f"reprocess_instructions_{config.id}",
    )

    # Reprocessing type for this product
    reprocess_type = st.selectbox(
        "Reprocessing Type",
        ["full", "hscode_only"],
        format_func=lambda x: (
            "Full Reprocessing (LLM + HScode)"
            if x == "full"
            else "HScode Classification Only"
        ),
        key=f"reprocess_type_{config.id}",
    )

    # Individual reprocess button
    if st.button(
        f"🔄 Reprocess This Product",
        key=f"individual_reprocess_{config.id}",
        type="secondary",
        use_container_width=True,
    ):
        # Start individual reprocessing
        result = reprocessor.reprocess_individual(
            config,
            reprocess_provider,
            reprocess_model,
            reprocess_temperature,
            custom_instructions,
            reprocess_type,
        )

        if result:
            # Show export options for reprocessed result
            st.write("**📤 Export Reprocessed Result:**")
            export_buttons.render_single_product_buttons(
                result, config.id, is_reprocessed=True
            )


def _render_bulk_reprocessing_controls(marked_configs, reprocessor):
    """Render bulk reprocessing control buttons"""
    st.markdown("---")
    st.subheader("🚀 Bulk Operations")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            f"🔄 Reprocess All ({len(marked_configs)} products)",
            type="primary",
            use_container_width=True,
            help=f"Reprocess all {len(marked_configs)} products with their individual settings",
        ):
            reprocessor.reprocess_bulk_with_individual_settings(marked_configs)

    with col2:
        if st.button(
            "🧪 Test First Product",
            use_container_width=True,
            help="Test reprocessing on the first product only",
        ):
            if marked_configs:
                config = marked_configs[0]
                # Get individual settings for first product
                provider = st.session_state.get(
                    f"reprocess_provider_{config.id}", config.model_provider
                )
                model = st.session_state.get(
                    f"reprocess_model_{config.id}", config.model_name
                )
                temperature = st.session_state.get(
                    f"reprocess_temperature_{config.id}", config.temperature
                )
                instructions = st.session_state.get(
                    f"reprocess_instructions_{config.id}", config.custom_instructions
                )
                reprocess_type = st.session_state.get(
                    f"reprocess_type_{config.id}", "full"
                )

                reprocessor.reprocess_individual(
                    config, provider, model, temperature, instructions, reprocess_type
                )

    with col3:
        if st.button(
            "❌ Clear All Selections",
            use_container_width=True,
            help="Remove all products from reprocessing list",
        ):
            for config in marked_configs:
                st.session_state[f"mark_reprocess_{config.id}"] = False
            st.success("Cleared all reprocessing selections!")
            st.rerun()


def _render_reprocessing_history(marked_configs):
    """Render reprocessing history section"""
    if any(len(config.processing_attempts) > 1 for config in marked_configs):
        st.markdown("---")
        st.subheader("📈 Reprocessing History")

        multi_attempt_configs = [
            config for config in marked_configs if len(config.processing_attempts) > 1
        ]

        if multi_attempt_configs:
            st.write(
                f"**{len(multi_attempt_configs)} products have been reprocessed before:**"
            )

            for config in multi_attempt_configs:
                latest_attempt = config.get_latest_attempt()
                result = latest_attempt.result

                # Import the extract function to use the same logic
                from evaluations.simple_db import extract_product_name_from_json
                product_name = extract_product_name_from_json(result)
                with st.expander(
                    f"📊 {product_name} ({len(config.processing_attempts)} attempts)"
                ):
                    for j, attempt in enumerate(reversed(config.processing_attempts)):
                        attempt_num = len(config.processing_attempts) - j
                        status_icon = (
                            "✅"
                            if attempt.status == "completed"
                            else "❌" if attempt.status == "failed" else "⏳"
                        )

                        st.write(
                            f"**{status_icon} Attempt {attempt_num}** - {attempt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"- Provider: {attempt.model_provider}")
                            st.write(f"- Model: {attempt.model_name}")
                            st.write(f"- Temperature: {attempt.temperature}")
                            if attempt.processing_time:
                                st.write(
                                    f"- Processing Time: {attempt.processing_time:.2f}s"
                                )

                        with col2:
                            st.write(f"- Status: {attempt.status}")
                            if attempt.status == "failed" and attempt.error_message:
                                st.write(f"- Error: {attempt.error_message}")
                            elif attempt.status == "completed" and attempt.result:
                                key_info = []
                                if attempt.result.get("price"):
                                    key_info.append(
                                        f"Price: {attempt.result['price']} {attempt.result.get('currency', '')}"
                                    )
                                if attempt.result.get("hscode"):
                                    key_info.append(
                                        f"HScode: {attempt.result['hscode']}"
                                    )
                                if key_info:
                                    st.write(f"- Key Results: {' | '.join(key_info)}")

                        if (
                            j < len(config.processing_attempts) - 1
                        ):  # Don't show separator after last item
                            st.markdown("---")
