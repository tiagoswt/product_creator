"""
Batch processing handler for product configurations
"""

import streamlit as st
import time
from models.model_factory import get_llm
from processors.pdf_processor import extract_pdf_data
from processors.excel_processor import extract_excel_data
from processors.web_processor import extract_website_data
from processors.text_processor import process_with_llm
from utils.product_config import get_product_configs, update_product_config


class BatchProcessor:
    """Handles batch processing of product configurations"""

    def __init__(self):
        pass

    def _get_product_preview(self, config):
        """Get a preview name for the product being processed"""
        try:
            # Try to extract a preview from the sources
            if config.pdf_file:
                return f"PDF: {config.pdf_file.name[:30]}"
            elif config.excel_file:
                return f"Excel: {config.excel_file.name[:30]}"
            elif config.website_url:
                url = config.website_url.split(",")[0].strip()
                if len(url) > 40:
                    url = url[:37] + "..."
                return f"Web: {url}"
            else:
                return f"{config.product_type.title()} Product"
        except:
            return f"{config.product_type.title()} Product"

    def process_all_configurations(self):
        """Process all product configurations in the batch"""
        configs = get_product_configs()

        if not configs:
            st.warning("No product configurations to process.")
            return

        # Create single progress elements that will be updated
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Initial status
            total_configs = len(configs)
            status_text.info(
                f"🚀 Starting batch processing of {total_configs} products..."
            )

        # Process each configuration
        for i, config in enumerate(configs):
            current_num = i + 1

            # Skip already processed configurations (unless they're marked for reprocessing)
            if config.status in ["completed", "failed"] and not config.is_reprocessing:
                # Update progress for skipped items
                progress_bar.progress(current_num / total_configs)
                status_text.info(
                    f"⏭️ Skipping {current_num}/{total_configs}: Already processed"
                )
                time.sleep(0.1)  # Brief pause so user can see the skip
                continue

            # Get product preview for status
            product_preview = self._get_product_preview(config)

            # Update status to show current product
            status_text.info(
                f"🔄 Processing {current_num}/{total_configs}: {product_preview}"
            )

            # Update configuration status
            config.status = "processing"
            update_product_config(config)

            # Update progress bar
            progress_bar.progress((current_num - 0.5) / total_configs)

            try:
                start_time = time.time()

                # Update status for data extraction phase
                status_text.info(
                    f"📄 Extracting data {current_num}/{total_configs}: {product_preview}"
                )

                # Create consolidated text from all selected sources
                consolidated_text = self._create_consolidated_text(config)

                if consolidated_text:
                    # Update status for AI processing phase
                    status_text.info(
                        f"🤖 AI Processing {current_num}/{total_configs}: {product_preview}"
                    )

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
                            # Add successful processing attempt
                            config.add_processing_attempt(
                                model_provider=config.model_provider,
                                model_name=config.model_name,
                                temperature=config.temperature,
                                custom_instructions=config.custom_instructions,
                                result=product_data,
                                status="completed",
                                processing_time=processing_time,
                            )

                            # Show success status briefly
                            product_name = self._extract_product_name(product_data)
                            status_text.success(
                                f"✅ Completed {current_num}/{total_configs}: {product_name}"
                            )
                            time.sleep(0.5)  # Brief pause to show success
                        else:
                            config.add_processing_attempt(
                                model_provider=config.model_provider,
                                model_name=config.model_name,
                                temperature=config.temperature,
                                custom_instructions=config.custom_instructions,
                                status="failed",
                                processing_time=processing_time,
                                error_message="Failed to extract product data",
                            )
                            status_text.error(
                                f"❌ Failed {current_num}/{total_configs}: {product_preview}"
                            )
                            time.sleep(0.5)  # Brief pause to show error
                    else:
                        config.add_processing_attempt(
                            model_provider=config.model_provider,
                            model_name=config.model_name,
                            temperature=config.temperature,
                            custom_instructions=config.custom_instructions,
                            status="failed",
                            error_message="Failed to initialize LLM",
                        )
                        status_text.error(
                            f"❌ LLM Error {current_num}/{total_configs}: {product_preview}"
                        )
                        time.sleep(0.5)
                else:
                    config.add_processing_attempt(
                        model_provider=config.model_provider,
                        model_name=config.model_name,
                        temperature=config.temperature,
                        custom_instructions=config.custom_instructions,
                        status="failed",
                        error_message="No data extracted from sources",
                    )
                    status_text.error(
                        f"❌ No Data {current_num}/{total_configs}: {product_preview}"
                    )
                    time.sleep(0.5)

            except Exception as e:
                config.add_processing_attempt(
                    model_provider=config.model_provider,
                    model_name=config.model_name,
                    temperature=config.temperature,
                    custom_instructions=config.custom_instructions,
                    status="failed",
                    error_message=str(e),
                )
                # REMOVED: Don't show error details during processing - just simple status
                status_text.error(
                    f"❌ Failed {current_num}/{total_configs}: {product_preview}"
                )
                time.sleep(0.5)

            # Reset reprocessing flags
            config.is_reprocessing = False
            update_product_config(config)

            # Update progress bar to full for this item
            progress_bar.progress(current_num / total_configs)

        # Final completion status
        progress_bar.progress(1.0)

        # Show final summary
        completed = sum(1 for config in configs if config.has_successful_attempt())
        failed = sum(1 for config in configs if config.status == "failed")
        skipped = total_configs - completed - failed

        if failed > 0:
            status_text.warning(
                f"🔄 Batch completed: {completed} successful, {failed} failed, {skipped} skipped"
            )
        else:
            status_text.success(
                f"🎉 Batch completed: All {completed} products processed successfully!"
            )

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
                return f"{brand} - {product_name}"[:60]
            elif brand != "Unknown":
                return brand[:60]
            elif product_name != "Product":
                return product_name[:60]
            else:
                return "Extracted Product"

        except Exception:
            return "Extracted Product"

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
