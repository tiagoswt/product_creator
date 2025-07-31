"""
Batch processing handler for product configurations - PHASE 3 USER TRACKING
ADDED: User context capture and attribution for product creation tracking
"""

import streamlit as st
import time
from models.model_factory import get_llm
from processors.pdf_processor import extract_pdf_data
from processors.excel_processor import extract_excel_data
from processors.web_processor import extract_website_data
from processors.text_processor import process_with_llm
from utils.product_config import get_product_configs, update_product_config
import config as app_config


class BatchProcessor:
    """Handles batch processing of product configurations with PHASE 3 user tracking"""

    def __init__(self):
        pass

    def _get_current_user_context(self) -> dict:
        """
        PHASE 3: Get current user context from session state.

        Returns:
            Dict with user_id, username, and user_name, or defaults if not found
        """
        if "current_user" in st.session_state:
            current_user = st.session_state["current_user"]
            return {
                "user_id": current_user.get("id"),
                "username": current_user.get("username", "unknown"),
                "user_name": current_user.get("name", "Unknown User"),
            }
        else:
            # Fallback for systems without authentication
            return {"user_id": None, "username": "system", "user_name": "System"}

    def _get_product_preview(self, config):
        """Get a brief preview name for the product being processed"""
        try:
            if config.pdf_file:
                return f"PDF: {config.pdf_file.name[:20]}..."
            elif config.excel_file:
                return f"Excel: {config.excel_file.name[:20]}..."
            elif config.website_url:
                url = config.website_url.split(",")[0].strip()
                if len(url) > 30:
                    url = url[:27] + "..."
                return f"Web: {url}"
            else:
                return f"{config.product_type.title()}"
        except:
            return f"{config.product_type.title()}"

    def process_all_configurations(self):
        """Process all product configurations with PHASE 3 user attribution"""
        configs = get_product_configs()

        if not configs:
            st.warning("No product configurations to process.")
            return

        # PHASE 3: Get current user context for attribution
        user_context = self._get_current_user_context()

        # Show user attribution info
        # if user_context["username"] != "system":
        #    st.info(
        #        f"🔄 Processing as user: **{user_context['user_name']}** ({user_context['username']})"
        #    )

        # Create single progress elements
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Simple start message
            total_configs = len(configs)
            status_text.info(f"🚀 Processing {total_configs} products...")

        # Process each configuration
        for i, config in enumerate(configs):
            current_num = i + 1

            # Skip already processed configurations silently
            if config.status in ["completed", "failed"] and not config.is_reprocessing:
                progress_bar.progress(current_num / total_configs)
                continue

            try:
                start_time = time.time()

                # Update configuration status
                config.status = "processing"
                update_product_config(config)

                # Phase 1: Data Extraction
                status_text.info(f"📄 Extracting data ({current_num}/{total_configs})")
                progress_bar.progress((current_num - 0.7) / total_configs)

                consolidated_text = self._create_consolidated_text(config)

                if consolidated_text:
                    # Phase 2: AI Processing
                    status_text.info(
                        f"🤖 AI processing ({current_num}/{total_configs})"
                    )
                    progress_bar.progress((current_num - 0.3) / total_configs)

                    # Get LLM model
                    llm = get_llm(
                        model_name=config.model_name,
                        temperature=config.temperature,
                        provider=config.model_provider,
                    )

                    if llm:
                        run_name = (
                            f"Batch:{config.id} - {config.product_type} extraction"
                        )

                        # Process the data
                        product_data = process_with_llm(
                            text=consolidated_text,
                            product_type=config.product_type,
                            llm=llm,
                            run_name=run_name,
                        )

                        processing_time = time.time() - start_time

                        if product_data:
                            # PHASE 3: Add user attribution to processing attempt
                            config.add_processing_attempt(
                                model_provider=config.model_provider,
                                model_name=config.model_name,
                                temperature=config.temperature,
                                custom_instructions=config.custom_instructions,
                                result=product_data,
                                status="completed",
                                processing_time=processing_time,
                                user_context=user_context,  # PHASE 3: Add user attribution
                            )
                        else:
                            config.add_processing_attempt(
                                model_provider=config.model_provider,
                                model_name=config.model_name,
                                temperature=config.temperature,
                                custom_instructions=config.custom_instructions,
                                status="failed",
                                processing_time=processing_time,
                                error_message="Failed to extract product data",
                                user_context=user_context,  # PHASE 3: Add user attribution
                            )
                    else:
                        config.add_processing_attempt(
                            model_provider=config.model_provider,
                            model_name=config.model_name,
                            temperature=config.temperature,
                            custom_instructions=config.custom_instructions,
                            status="failed",
                            error_message="Failed to initialize LLM",
                            user_context=user_context,  # PHASE 3: Add user attribution
                        )
                else:
                    config.add_processing_attempt(
                        model_provider=config.model_provider,
                        model_name=config.model_name,
                        temperature=config.temperature,
                        custom_instructions=config.custom_instructions,
                        status="failed",
                        error_message="No data extracted from sources",
                        user_context=user_context,  # PHASE 3: Add user attribution
                    )

            except Exception as e:
                config.add_processing_attempt(
                    model_provider=config.model_provider,
                    model_name=config.model_name,
                    temperature=config.temperature,
                    custom_instructions=config.custom_instructions,
                    status="failed",
                    error_message=str(e),
                    user_context=user_context,  # PHASE 3: Add user attribution
                )
                # Show error only for critical issues
                if "API" in str(e) or "connection" in str(e).lower():
                    st.error(f"❌ Processing error: {str(e)}")

            # Reset reprocessing flags
            config.is_reprocessing = False
            update_product_config(config)

            # Update progress bar
            progress_bar.progress(current_num / total_configs)

        # Phase 3: AI Evaluation (if enabled) with user attribution
        completed = sum(1 for cfg in configs if cfg.has_successful_attempt())

        if completed > 0:
            # Show evaluation phase
            status_text.info(f"🧠 AI evaluation ({completed} products)")
            progress_bar.progress(0.95)  # Almost complete

            # Evaluation section with PostgreSQL connection info
            try:
                from importlib import import_module

                eval_settings = import_module("config")
                evaluation_enabled = getattr(eval_settings, "EVALUATION_ENABLED", False)

                if evaluation_enabled:
                    try:
                        from evaluations.evaluation_core import evaluate_batch

                        # Silent database operation - no connection messages

                        completed_product_configs = [
                            product_config
                            for product_config in configs
                            if (
                                hasattr(product_config, "has_successful_attempt")
                                and product_config.has_successful_attempt()
                            )
                        ]

                        if completed_product_configs:
                            # PHASE 3: Pass user context to evaluation
                            evaluation_result = evaluate_batch(
                                completed_product_configs,
                                current_user=user_context,  # PHASE 3: User attribution
                            )
                            evaluated_count = evaluation_result.get("evaluated", 0)

                            if evaluated_count > 0:
                                # PHASE 3: Show user attribution in success message
                                if user_context["username"] != "system":
                                    status_text.success(
                                        f"✅ Quality evaluation completed: {evaluated_count} products (Created by: {user_context['username']})"
                                    )
                                else:
                                    status_text.success(
                                        f"✅ Quality evaluation completed: {evaluated_count} products"
                                    )
                            else:
                                st.warning("⚠️ Evaluation system unavailable")

                    except ImportError:
                        # Silently skip if evaluation system not available
                        pass
                    except Exception as eval_err:
                        st.error(f"❌ Evaluation failed: {str(eval_err)}")

            except Exception:
                # Silently skip if config import fails
                pass

        # Final completion status with user attribution
        progress_bar.progress(1.0)
        failed = sum(1 for cfg in configs if cfg.status == "failed")

        if failed > 0:
            if user_context["username"] != "system":
                status_text.warning(
                    f"🔄 Completed: {completed} successful, {failed} failed (User: {user_context['username']})"
                )
            else:
                status_text.warning(
                    f"🔄 Completed: {completed} successful, {failed} failed"
                )
        else:
            if user_context["username"] != "system":
                status_text.success(
                    f"🎉 All {completed} products processed successfully! (Created by: {user_context['username']})"
                )
            else:
                status_text.success(
                    f"🎉 All {completed} products processed successfully!"
                )

        # Brief pause to show final status
        time.sleep(1)

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

    def _extract_product_name(self, product_data):
        """Extract a readable product name from the result for status display"""
        try:
            # Try different field names based on product type
            name_fields = ["itemDescriptionEN", "product_name", "product_title_EN"]
            brand_fields = ["brand", "Brand"]

            brand = "Unknown"
            product_name = "Product"

            # Extract brand
            for field in brand_fields:
                if "catalogA" in product_data and product_data["catalogA"].get(field):
                    brand = product_data["catalogA"][field]
                    break
                elif "catalogB" in product_data and product_data["catalogB"].get(field):
                    brand = product_data["catalogB"][field]
                    break
                elif product_data.get(field):
                    brand = product_data[field]
                    break

            # Extract product name
            for field in name_fields:
                if "catalogB" in product_data and product_data["catalogB"].get(field):
                    product_name = product_data["catalogB"][field]
                    break
                elif "catalogA" in product_data and product_data["catalogA"].get(field):
                    product_name = product_data["catalogA"][field]
                    break
                elif product_data.get(field):
                    product_name = product_data[field]
                    break

            # Create display name
            if brand != "Unknown" and product_name != "Product":
                return f"{brand} - {product_name}"[:50]
            elif brand != "Unknown":
                return brand[:50]
            elif product_name != "Product":
                return product_name[:50]
            else:
                return "Product"

        except Exception:
            return "Product"

    def _create_consolidated_text(self, config):
        """Create consolidated text from all selected sources"""
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
                consolidated_text += f"## EXCEL SOURCE: {config.excel_file.name}\n\n"
                consolidated_text += excel_text + "\n\n"

        # Process Website if selected
        if config.website_url:
            website_text = extract_website_data(website_url=config.website_url)
            if website_text:
                consolidated_text += f"## WEBSITE SOURCE: {config.website_url}\n\n"
                consolidated_text += website_text

        # Add custom instructions if provided
        if hasattr(config, "custom_instructions") and config.custom_instructions:
            consolidated_text = f"## CUSTOM INSTRUCTIONS:\n{config.custom_instructions}\n\n## DATA:\n{consolidated_text}"

        return consolidated_text if consolidated_text.strip() else None
