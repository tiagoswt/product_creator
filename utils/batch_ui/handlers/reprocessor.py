"""
Reprocessing handler for product configurations
"""

import streamlit as st
import time
from models.model_factory import get_llm
from processors.pdf_processor import extract_pdf_data
from processors.excel_processor import extract_excel_data
from processors.web_processor import extract_website_data
from processors.text_processor import process_with_llm, process_hscode_with_deepseek
from utils.product_config import update_product_config


class ProductReprocessor:
    """Handles reprocessing of product configurations"""

    def __init__(self):
        pass

    def reprocess_individual(
        self, config, provider, model, temperature, custom_instructions, reprocess_type
    ):
        """Start reprocessing for a single product with individual settings"""

        latest_attempt = config.get_latest_attempt()
        product_name = (
            latest_attempt.result.get("product_name", "Unknown")
            if latest_attempt.result
            else "Unknown"
        )

        st.markdown("---")
        st.subheader(f"🔄 Reprocessing: {product_name}")

        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            start_time = time.time()

            status_text.text(f"Reprocessing {product_name}...")
            progress_bar.progress(0.2)

            # Update configuration parameters
            config.update_current_parameters(
                model_provider=provider,
                model_name=model,
                temperature=temperature,
                custom_instructions=custom_instructions,
            )

            # Mark as reprocessing
            config.is_reprocessing = True
            config.reprocess_type = reprocess_type
            config.status = "processing"
            update_product_config(config)

            progress_bar.progress(0.4)

            # Perform reprocessing
            if reprocess_type == "hscode_only":
                status_text.text(f"Reprocessing HScode for {product_name}...")
                # Only reprocess HScode
                if latest_attempt and latest_attempt.result:
                    result = self._reprocess_hscode_only(latest_attempt.result, config)
                else:
                    result = None
            else:
                status_text.text(f"Full reprocessing for {product_name}...")
                # Full reprocessing
                result = self._perform_full_reprocessing(config)

            progress_bar.progress(0.8)
            processing_time = time.time() - start_time

            if result:
                # Add successful processing attempt
                config.add_processing_attempt(
                    model_provider=provider,
                    model_name=model,
                    temperature=temperature,
                    custom_instructions=custom_instructions,
                    result=result,
                    status="completed",
                    processing_time=processing_time,
                )
                progress_bar.progress(1.0)
                status_text.text(f"✅ Completed: {product_name}")
                st.success(f"🎉 Successfully reprocessed: {product_name}")

                # Show the new result
                st.write("**📄 New JSON Result:**")
                st.json(result)

                return result
            else:
                # Add failed processing attempt
                config.add_processing_attempt(
                    model_provider=provider,
                    model_name=model,
                    temperature=temperature,
                    custom_instructions=custom_instructions,
                    status="failed",
                    processing_time=processing_time,
                    error_message="Failed to extract product data during reprocessing",
                )
                progress_bar.progress(1.0)
                status_text.text(f"❌ Failed: {product_name}")
                st.error(f"❌ Failed to reprocess: {product_name}")
                return None

            # Reset reprocessing flags
            config.is_reprocessing = False
            update_product_config(config)

        except Exception as e:
            st.error(f"Error reprocessing {product_name}: {str(e)}")
            # Add failed processing attempt
            config.add_processing_attempt(
                model_provider=provider,
                model_name=model,
                temperature=temperature,
                custom_instructions=custom_instructions,
                status="failed",
                error_message=str(e),
            )
            config.is_reprocessing = False
            update_product_config(config)
            progress_bar.progress(1.0)
            status_text.text(f"❌ Error: {product_name}")
            return None

    def reprocess_bulk_with_individual_settings(self, marked_configs):
        """Start bulk reprocessing using individual settings for each product"""

        if not marked_configs:
            st.warning("No products selected for reprocessing.")
            return

        st.markdown("---")
        st.subheader(f"🔄 Bulk Reprocessing {len(marked_configs)} Products")

        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        successful_count = 0
        failed_count = 0

        for i, config in enumerate(marked_configs):
            # Get individual settings for this product from session state
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
            reprocess_type = st.session_state.get(f"reprocess_type_{config.id}", "full")

            # Update progress
            progress_percentage = i / len(marked_configs)
            progress_bar.progress(progress_percentage)

            latest_attempt = config.get_latest_attempt()
            product_name = (
                latest_attempt.result.get("product_name", "Unknown")
                if latest_attempt.result
                else "Unknown"
            )
            status_text.text(
                f"Reprocessing {i+1}/{len(marked_configs)}: {product_name}"
            )

            try:
                start_time = time.time()

                # Update configuration parameters
                config.update_current_parameters(
                    model_provider=provider,
                    model_name=model,
                    temperature=temperature,
                    custom_instructions=instructions,
                )

                # Mark as reprocessing
                config.is_reprocessing = True
                config.reprocess_type = reprocess_type
                config.status = "processing"
                update_product_config(config)

                # Perform reprocessing
                if reprocess_type == "hscode_only":
                    # Only reprocess HScode
                    if latest_attempt and latest_attempt.result:
                        result = self._reprocess_hscode_only(
                            latest_attempt.result, config
                        )
                    else:
                        result = None
                else:
                    # Full reprocessing
                    result = self._perform_full_reprocessing(config)

                processing_time = time.time() - start_time

                if result:
                    # Add successful processing attempt
                    config.add_processing_attempt(
                        model_provider=provider,
                        model_name=model,
                        temperature=temperature,
                        custom_instructions=instructions,
                        result=result,
                        status="completed",
                        processing_time=processing_time,
                    )
                    successful_count += 1
                    status_text.text(
                        f"✅ Completed {i+1}/{len(marked_configs)}: {product_name}"
                    )
                else:
                    # Add failed processing attempt
                    config.add_processing_attempt(
                        model_provider=provider,
                        model_name=model,
                        temperature=temperature,
                        custom_instructions=instructions,
                        status="failed",
                        processing_time=processing_time,
                        error_message="Failed to extract product data during reprocessing",
                    )
                    failed_count += 1
                    status_text.text(
                        f"❌ Failed {i+1}/{len(marked_configs)}: {product_name}"
                    )

                # Reset reprocessing flags
                config.is_reprocessing = False
                update_product_config(config)

            except Exception as e:
                st.error(f"Error reprocessing {product_name}: {str(e)}")
                # Add failed processing attempt
                config.add_processing_attempt(
                    model_provider=provider,
                    model_name=model,
                    temperature=temperature,
                    custom_instructions=instructions,
                    status="failed",
                    error_message=str(e),
                )
                config.is_reprocessing = False
                update_product_config(config)
                failed_count += 1

            # Update progress
            progress_bar.progress((i + 1) / len(marked_configs))

        # Final progress update
        progress_bar.progress(1.0)
        status_text.empty()

        # Show completion summary
        if failed_count > 0:
            st.warning(
                f"🔄 Bulk reprocessing completed: {successful_count} successful, {failed_count} failed"
            )
        else:
            st.success(
                f"🎉 Bulk reprocessing completed: All {successful_count} products processed successfully!"
            )

        # Clear reprocessing selections
        for config in marked_configs:
            st.session_state[f"mark_reprocess_{config.id}"] = False

    def _reprocess_hscode_only(self, original_result, config):
        """Reprocess only the HScode using Deepseek"""
        try:
            # Create a copy of the original result
            updated_result = original_result.copy()

            # Reprocess HScode
            new_hscode = process_hscode_with_deepseek(updated_result)

            if new_hscode:
                updated_result["hscode"] = new_hscode
                return updated_result
            else:
                return None

        except Exception as e:
            st.error(f"Error reprocessing HScode: {str(e)}")
            return None

    def _perform_full_reprocessing(self, config):
        """Perform full reprocessing with current parameters"""
        try:
            # Create consolidated text from all selected sources (same as original processing)
            consolidated_text = ""

            # Process PDF if selected
            if config.pdf_file is not None and config.pdf_pages:
                pdf_text = extract_pdf_data(
                    pdf_file=config.pdf_file, pdf_pages=config.pdf_pages
                )
                if pdf_text:
                    consolidated_text += f"## PDF SOURCE: {config.pdf_file.name}\n\n"
                    consolidated_text += pdf_text + "\n\n"

            # Process Excel if selected
            if config.excel_file is not None and config.excel_rows:
                excel_header_row = st.session_state.get("excel_header_row", 0)
                excel_text = extract_excel_data(
                    excel_file=config.excel_file,
                    excel_rows=config.excel_rows,
                    header_row=excel_header_row,
                )
                if excel_text:
                    consolidated_text += (
                        f"## EXCEL SOURCE: {config.excel_file.name}\n\n"
                    )
                    consolidated_text += excel_text + "\n\n"

            # Process Website if selected
            if config.website_url:
                website_text = extract_website_data(website_url=config.website_url)
                if website_text:
                    consolidated_text += f"## WEBSITE SOURCE: {config.website_url}\n\n"
                    consolidated_text += website_text

            # Add custom instructions to the consolidated text if provided
            if config.custom_instructions:
                consolidated_text = f"## CUSTOM INSTRUCTIONS:\n{config.custom_instructions}\n\n## DATA:\n{consolidated_text}"

            if consolidated_text:
                # Get LLM model with current parameters
                llm = get_llm(
                    model_name=config.model_name,
                    temperature=config.temperature,
                    provider=config.model_provider,
                )

                if llm:
                    # Create a run name for tracing
                    run_name = (
                        f"Reprocess:{config.id} - {config.product_type} extraction"
                    )

                    # Process the data
                    product_data = process_with_llm(
                        text=consolidated_text,
                        product_type=config.product_type,
                        llm=llm,
                        run_name=run_name,
                    )

                    return product_data
                else:
                    st.error("Failed to initialize LLM for reprocessing")
                    return None
            else:
                st.error("No data extracted from sources for reprocessing")
                return None

        except Exception as e:
            st.error(f"Error during full reprocessing: {str(e)}")
            return None
