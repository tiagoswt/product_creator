import streamlit as st
import os
from typing import Dict, List, Any, Optional
import json
import pandas as pd
import time  # Added for generating unique keys

from utils.product_config import (
    ProductConfig,
    get_product_configs,
    add_product_config,
    update_product_config,
    remove_product_config,
    clear_product_configs,
    migrate_product_configs,
)
from processors.pdf_processor import render_pdf_preview
from processors.excel_processor import process_excel_file, is_csv_file
from processors.web_processor import extract_website_data
from processors.text_processor import (
    process_consolidated_data,
    process_with_llm,
    load_prompt_from_file,
)
from models.model_factory import get_llm

# Define configuration constants directly in this file to avoid import issues
# These should match the values in config.py
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
DEFAULT_TEMPERATURE = 0.2


def render_batch_extraction_ui():
    """Render the UI for batch extraction of products"""

    # Migrate existing product configurations to ensure they have all required attributes
    migrate_product_configs()

    # Check if a reset was triggered - this is a signal from app.py
    reset_triggered = st.session_state.get("reset_triggered", False)

    # Handle form reset logic before rendering the form
    if (
        "clear_batch_form" in st.session_state and st.session_state.clear_batch_form
    ) or reset_triggered:
        # Reset all form-related session state variables
        # We'll create new keys with unique suffixes to avoid modifying widget states directly
        st.session_state["batch_pdf_uploader_reset"] = True
        st.session_state["batch_excel_uploader_reset"] = True
        st.session_state["batch_website_url_reset"] = True
        st.session_state["batch_custom_instructions_reset"] = True

        # Also clear PDF preview data
        if "pdf_preview" in st.session_state:
            del st.session_state["pdf_preview"]
        if "last_pdf_name" in st.session_state:
            del st.session_state["last_pdf_name"]
        if "pdf_pages_selected" in st.session_state:
            del st.session_state["pdf_pages_selected"]

        # Clear Excel related data
        if "raw_excel_df" in st.session_state:
            del st.session_state["raw_excel_df"]
        if "processed_excel_df" in st.session_state:
            del st.session_state["processed_excel_df"]
        if "excel_rows_selected" in st.session_state:
            del st.session_state["excel_rows_selected"]
        if "last_excel_name" in st.session_state:
            del st.session_state["last_excel_name"]
        if "header_row_last_used" in st.session_state:
            del st.session_state["header_row_last_used"]

        # Clear the flags
        st.session_state.clear_batch_form = False
        if reset_triggered:
            st.session_state.reset_triggered = False

    st.header("Batch Product Extraction")
    st.markdown(
        """
    This view allows you to create multiple product configurations and extract them all at once.
    For each product, you can assign specific data sources including PDF pages, Excel/CSV rows, and websites.
    You can also provide custom instructions to guide the LLM for each product.
    """
    )

    # Display existing configurations
    configs = get_product_configs()

    # Create tabs for configuration management and execution
    tab1, tab2 = st.tabs(["Configure Products", "Execute Batch"])

    with tab1:
        st.subheader("Product Configurations")

        if not configs:
            st.info(
                "No product configurations added yet. Use the form below to add your first configuration."
            )
        else:
            st.write(f"Total configurations: {len(configs)}")

            # Display each configuration in an expander
            for i, config in enumerate(configs):
                with st.expander(
                    f"Product {i+1}: {config.source_summary()}", expanded=False
                ):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.write(f"**Product Type:** {config.product_type}")
                        st.write(
                            f"**Model:** {config.model_provider} / {config.model_name}"
                        )
                        st.write(f"**Status:** {config.status}")
                        st.write(f"**Data Sources:**")
                        st.code(config.source_summary())

                        # Display custom instructions if they exist
                        if (
                            hasattr(config, "custom_instructions")
                            and config.custom_instructions
                        ):
                            st.write("**Custom Instructions:**")
                            st.code(config.custom_instructions)

                    with col2:
                        if st.button("Remove", key=f"remove_{config.id}"):
                            remove_product_config(config.id)
                            st.rerun()

        # Add a separator
        st.markdown("---")

        # Start the "Add New Product Configuration" section
        st.subheader("Add New Product Configuration")

        # PDF Source section - OUTSIDE the form but within the "Add New Product" section
        st.write("**PDF Source**")

        # Determine if we need to create a new key for the uploader to reset it
        pdf_uploader_key = "batch_pdf_uploader"
        if (
            "batch_pdf_uploader_reset" in st.session_state
            and st.session_state.batch_pdf_uploader_reset
        ):
            # Create a unique key by appending a timestamp
            import time

            pdf_uploader_key = f"batch_pdf_uploader_{int(time.time())}"
            st.session_state.batch_pdf_uploader_reset = False

        pdf_file = st.file_uploader("Upload PDF", type="pdf", key=pdf_uploader_key)

        # Initialize selected pages
        if "pdf_pages_selected" not in st.session_state:
            st.session_state.pdf_pages_selected = []

        if pdf_file:
            st.success(f"PDF uploaded: {pdf_file.name}")

            # Add a button to render the PDF pages (outside form, so this is OK)
            render_button = st.button("Render PDF Pages")

            if render_button or "pdf_preview" in st.session_state:
                # Show a loading message while rendering PDF
                with st.spinner("Rendering PDF preview..."):
                    # If we haven't rendered this PDF yet, or if it's a new PDF, render it
                    if (
                        "pdf_preview" not in st.session_state
                        or "last_pdf_name" not in st.session_state
                        or st.session_state.last_pdf_name != pdf_file.name
                    ):

                        # Store PDF in session state for preview and selection
                        pdf_preview = render_pdf_preview(pdf_file)
                        st.session_state.pdf_preview = pdf_preview
                        st.session_state.last_pdf_name = pdf_file.name
                        # Reset selected pages for new PDF
                        st.session_state.pdf_pages_selected = []
                    else:
                        # Use the existing preview
                        pdf_preview = st.session_state.pdf_preview

                    # Get total pages
                    total_pages = len(pdf_preview)

                    # Display a prominent notification that PDF is loaded
                    st.success(f"PDF rendered successfully: {total_pages} pages")

                    # Display a comprehensive preview of all PDF pages
                    st.write("**PDF Pages Preview:**")

                    # Use a select all option for convenience
                    select_all_pdf = st.checkbox(
                        "Select all pages", key="select_all_pdf_pages"
                    )

                    if select_all_pdf:
                        st.session_state.pdf_pages_selected = list(range(total_pages))
                        st.success(f"All {total_pages} pages selected")
                    else:
                        # Let's use a grid layout for the checkboxes next to thumbnails
                        # Divide into pages with 3 thumbnails per row
                        for page_idx in range(0, total_pages, 3):
                            # Create a row with 3 columns
                            cols = st.columns(3)

                            # Fill the row with up to 3 thumbnails
                            for i in range(3):
                                if page_idx + i < total_pages:
                                    with cols[i]:
                                        page_num, img_bytes = pdf_preview[page_idx + i]

                                        # Display the thumbnail
                                        st.image(
                                            img_bytes,
                                            caption=f"Page {page_num+1}",
                                            use_column_width=True,
                                        )

                                        # Add checkbox below the thumbnail
                                        # Check if this page is already selected
                                        page_selected = (
                                            page_num
                                            in st.session_state.pdf_pages_selected
                                        )

                                        if st.checkbox(
                                            f"Select Page {page_num+1}",
                                            value=page_selected,
                                            key=f"batch_pdf_page_{page_num}",
                                        ):
                                            if (
                                                page_num
                                                not in st.session_state.pdf_pages_selected
                                            ):
                                                st.session_state.pdf_pages_selected.append(
                                                    page_num
                                                )
                                        else:
                                            if (
                                                page_num
                                                in st.session_state.pdf_pages_selected
                                            ):
                                                st.session_state.pdf_pages_selected.remove(
                                                    page_num
                                                )

                    if st.session_state.pdf_pages_selected:
                        st.success(
                            f"Selected {len(st.session_state.pdf_pages_selected)} pages: {', '.join(str(p+1) for p in st.session_state.pdf_pages_selected)}"
                        )
                    else:
                        st.warning(
                            "No pages selected - please select at least one page"
                        )
            else:
                st.info("Click 'Render PDF Pages' to view and select pages")
        else:
            st.info("Please upload a PDF file to continue")

        # EXCEL/CSV SOURCE - Also outside the form
        st.write("**Excel/CSV Source**")

        # Determine if we need to create a new key for the uploader to reset it
        excel_uploader_key = "batch_excel_uploader"
        if (
            "batch_excel_uploader_reset" in st.session_state
            and st.session_state.batch_excel_uploader_reset
        ):
            # Create a unique key by appending a timestamp
            import time

            excel_uploader_key = f"batch_excel_uploader_{int(time.time())}"
            st.session_state.batch_excel_uploader_reset = False

            # Also clear any excel related data
            if "raw_excel_df" in st.session_state:
                del st.session_state["raw_excel_df"]
            if "processed_excel_df" in st.session_state:
                del st.session_state["processed_excel_df"]
            if "excel_rows_selected" in st.session_state:
                del st.session_state["excel_rows_selected"]

        excel_file = st.file_uploader(
            "Upload Excel or CSV", type=["xlsx", "xls", "csv"], key=excel_uploader_key
        )

        # Initialize selected rows
        if "excel_rows_selected" not in st.session_state:
            st.session_state.excel_rows_selected = []

        if excel_file:
            file_type = "CSV" if is_csv_file(excel_file) else "Excel"
            st.success(f"{file_type} file uploaded: {excel_file.name}")

            try:
                # Process the Excel/CSV file for preview
                import pandas as pd

                # Only read the raw file if we haven't already or if it's a new file
                if (
                    "raw_excel_df" not in st.session_state
                    or "last_excel_name" not in st.session_state
                    or st.session_state.last_excel_name != excel_file.name
                ):

                    # Read raw data based on file type with robust parsing
                    if is_csv_file(excel_file):
                        # Robust CSV reading for preview
                        try:
                            raw_df = pd.read_csv(
                                excel_file,
                                header=None,
                                nrows=10,
                                sep=None,
                                engine="python",
                                encoding="utf-8",
                                on_bad_lines="skip",
                                skipinitialspace=True,
                                quoting=1,
                            )
                        except Exception as e:
                            st.warning(f"Initial CSV parsing failed: {str(e)}")
                            st.info("Trying alternative CSV parsing methods...")

                            # Try different separators
                            raw_df = None
                            for separator in [",", ";", "\t", "|"]:
                                try:
                                    excel_file.seek(0)  # Reset file pointer
                                    raw_df = pd.read_csv(
                                        excel_file,
                                        header=None,
                                        nrows=10,
                                        sep=separator,
                                        engine="python",
                                        encoding="utf-8",
                                        on_bad_lines="skip",
                                        skipinitialspace=True,
                                        quoting=1,
                                    )
                                    st.success(
                                        f"Successfully parsed CSV with '{separator}' separator"
                                    )
                                    break
                                except:
                                    continue

                            # If all separators fail, try with different encoding
                            if raw_df is None:
                                try:
                                    excel_file.seek(0)
                                    raw_df = pd.read_csv(
                                        excel_file,
                                        header=None,
                                        nrows=10,
                                        sep=None,
                                        engine="python",
                                        encoding="latin-1",
                                        on_bad_lines="skip",
                                        skipinitialspace=True,
                                    )
                                    st.success(
                                        "Successfully parsed CSV with latin-1 encoding"
                                    )
                                except Exception as final_e:
                                    st.error(f"Could not parse CSV file: {final_e}")
                                    st.info(
                                        "Please check that your CSV file is properly formatted with consistent delimiters."
                                    )
                                    return  # Exit early if we can't parse the file
                    else:
                        raw_df = pd.read_excel(excel_file, header=None, nrows=10)

                    # Convert all columns to strings
                    for col in raw_df.columns:
                        raw_df[col] = raw_df[col].astype(str)

                    # Store in session state
                    st.session_state.raw_excel_df = raw_df
                    st.session_state.last_excel_name = excel_file.name

                    # Reset rows when a new file is uploaded
                    st.session_state.excel_rows_selected = []
                else:
                    # Use cached data
                    raw_df = st.session_state.raw_excel_df

                # Show preview of raw data
                with st.expander(f"Raw {file_type} Preview", expanded=False):
                    st.dataframe(raw_df)

                # Header row selector with better UI
                st.write("**Select Header Row:**")
                header_row = st.number_input(
                    "Header row index (0-based)",
                    min_value=0,
                    max_value=max(0, len(raw_df) - 1) if not raw_df.empty else 0,
                    value=st.session_state.get("batch_excel_header_row", 0),
                    key="batch_excel_header_input",
                )

                # Store the header row in session state
                st.session_state.batch_excel_header_row = header_row

                # Process button to apply header and show processed data
                process_excel_button = st.button(
                    f"Process {file_type} with Selected Header"
                )

                # Check if we should process the Excel/CSV
                if process_excel_button or "processed_excel_df" in st.session_state:
                    # Process Excel/CSV with selected header row
                    if (
                        process_excel_button
                        or "header_row_last_used" not in st.session_state
                        or st.session_state.header_row_last_used != header_row
                    ):
                        # Only reprocess if the header row changed or button was clicked
                        with st.spinner(f"Processing {file_type} file..."):
                            # Reset the file to the beginning
                            excel_file.seek(0)

                            # Process with header
                            processed_df = process_excel_file(
                                excel_file, header=header_row
                            )

                            if processed_df is not None:
                                # Fix dataframe by converting all column values to strings
                                for col in processed_df.columns:
                                    processed_df[col] = processed_df[col].astype(str)

                                # Store in session state
                                st.session_state.processed_excel_df = processed_df
                                st.session_state.header_row_last_used = header_row
                    else:
                        # Use cached processed data
                        processed_df = st.session_state.processed_excel_df

                    # If we have processed data, show it and allow row selection
                    if "processed_excel_df" in st.session_state:
                        processed_df = st.session_state.processed_excel_df

                        # Show processed data
                        st.subheader(f"Processed {file_type} Data")
                        st.dataframe(processed_df)

                        # Row selection
                        st.write(f"**Select {file_type} Rows:**")

                        # Get the number of rows
                        num_rows = len(processed_df)

                        # Create a select all checkbox
                        select_all = st.checkbox(
                            "Select all rows", key="batch_excel_select_all"
                        )

                        if select_all:
                            # Select all rows
                            st.session_state.excel_rows_selected = list(range(num_rows))
                            st.success(f"Selected all {num_rows} rows")
                        else:
                            # Show multiselect with row preview
                            row_options = []
                            for i in range(num_rows):
                                # Get the first non-null value as preview
                                preview_values = []
                                for col in processed_df.columns[
                                    :3
                                ]:  # Use first 3 columns
                                    val = processed_df.iloc[
                                        i, processed_df.columns.get_loc(col)
                                    ]
                                    if (
                                        val
                                        and str(val).strip()
                                        and str(val).lower() != "nan"
                                    ):
                                        preview_values.append(str(val))
                                        if len(preview_values) >= 2:
                                            break

                                preview = " | ".join(preview_values)
                                if len(preview) > 40:
                                    preview = preview[:37] + "..."

                                row_options.append(f"Row {i}: {preview}")

                            # Check if we have existing selections
                            default_selections = []
                            for idx in st.session_state.excel_rows_selected:
                                if idx < len(row_options):
                                    default_selections.append(row_options[idx])

                            # Show multiselect
                            selected_row_options = st.multiselect(
                                "Choose rows to extract",
                                options=row_options,
                                default=default_selections,
                                key=f"batch_excel_rows_select_{excel_file.name}_{header_row}",
                            )

                            # Convert selected options back to indices
                            excel_rows = [
                                int(row.split(":")[0].replace("Row ", ""))
                                for row in selected_row_options
                            ]

                            # Store in session state
                            st.session_state.excel_rows_selected = excel_rows

                            if excel_rows:
                                st.success(
                                    f"Selected {len(excel_rows)} rows: {', '.join(str(r) for r in excel_rows)}"
                                )
                            else:
                                st.warning("No rows selected")
                else:
                    st.info(
                        f"Click 'Process {file_type} with Selected Header' to view and select rows"
                    )
            except Exception as e:
                st.error(f"Error processing {file_type} file: {str(e)}")
                st.info(
                    f"Please check that your {file_type} file is properly formatted and try again."
                )

        # Now show the form for the rest of the product configuration details
        st.subheader("Other Configuration Details")

        # Set up model selector outside the form but make it less prominent
        provider_selection = st.selectbox(
            "Select Provider for Model Configuration",
            ["groq", "openai"],
            key="provider_selection_outside_form",
            label_visibility="collapsed",  # Hide the label
        )

        # Update the model options based on provider selection
        if provider_selection == "groq":
            model_options = GROQ_MODELS
            default_model = DEFAULT_GROQ_MODEL
        else:  # openai
            model_options = OPENAI_MODELS
            default_model = DEFAULT_OPENAI_MODEL

        # Store the selected provider and model options in session state
        st.session_state.current_provider = provider_selection
        st.session_state.current_model_options = model_options
        st.session_state.current_default_model = default_model

        with st.form("new_product_config"):
            # Product type selection
            product_type = st.selectbox(
                "Product Type", ["cosmetics", "fragrance", "subtype"]
            )

            # Website input - inside form
            st.write("**Website Source**")

            # Determine if we need to create a new key for the text input to reset it
            website_key = "batch_website_url"
            if (
                "batch_website_url_reset" in st.session_state
                and st.session_state.batch_website_url_reset
            ):
                # Create a unique key by appending a timestamp
                website_key = f"batch_website_url_{int(time.time())}"
                st.session_state.batch_website_url_reset = False

            # Use an empty default value to ensure it resets properly
            website_url = st.text_input("Website URL", value="", key=website_key)

            # Add custom instructions text area
            st.write("**Custom Instructions to LLM**")

            # Determine if we need to create a new key for the text area to reset it
            custom_instructions_key = "batch_custom_instructions"
            if (
                "batch_custom_instructions_reset" in st.session_state
                and st.session_state.batch_custom_instructions_reset
            ):
                # Create a unique key by appending a timestamp
                custom_instructions_key = (
                    f"batch_custom_instructions_{int(time.time())}"
                )
                st.session_state.batch_custom_instructions_reset = False

            # Use an empty default value to ensure it resets properly
            custom_instructions = st.text_area(
                "Enter custom instructions for the LLM",
                value="",
                help="These instructions will be added to the prompt sent to the LLM when processing this product.",
                height=150,
                key=custom_instructions_key,
            )

            # Model selection
            st.write("**Model Configuration**")

            # Create columns for model configuration
            col1, col2, col3 = st.columns(3)

            with col1:
                # Display provider dropdown (visual only, value comes from outside form)
                provider_visual = st.selectbox(
                    "Provider",
                    ["groq", "openai"],
                    index=0 if provider_selection == "groq" else 1,
                    key="provider_visual_in_form",
                    disabled=True,  # Make it read-only
                )

            with col2:
                # Use the model options based on provider selection from outside the form
                model_name = st.selectbox(
                    "Model",
                    st.session_state.current_model_options,
                    index=(
                        st.session_state.current_model_options.index(
                            st.session_state.current_default_model
                        )
                        if st.session_state.current_default_model
                        in st.session_state.current_model_options
                        else 0
                    ),
                )

            with col3:
                temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=DEFAULT_TEMPERATURE,
                    step=0.1,
                    key="batch_temperature",
                )

            # Submit button
            submitted = st.form_submit_button("Add to Batch")

            if submitted:
                # Use the PDF pages selected outside the form
                pdf_pages = (
                    st.session_state.pdf_pages_selected
                    if "pdf_pages_selected" in st.session_state
                    else []
                )

                # Use the Excel rows selected outside the form
                excel_rows = (
                    st.session_state.excel_rows_selected
                    if "excel_rows_selected" in st.session_state
                    else []
                )

                # Get the provider from outside the form
                model_provider = st.session_state.current_provider

                # Create a new product configuration
                new_config = ProductConfig(
                    product_type=product_type,
                    pdf_file=pdf_file,
                    pdf_pages=pdf_pages,
                    excel_file=excel_file,
                    excel_rows=excel_rows,
                    website_url=website_url,
                    model_provider=model_provider,
                    model_name=model_name,
                    temperature=temperature,
                    custom_instructions=custom_instructions,  # Add custom instructions
                )

                if new_config.has_data_source():
                    add_product_config(new_config)
                    st.success("Product configuration added to batch!")

                    # Set a flag to indicate we need to clear form data
                    if "clear_batch_form" not in st.session_state:
                        st.session_state.clear_batch_form = True

                    # Rerun to update the UI
                    st.rerun()
                else:
                    st.error(
                        "Please select at least one data source (PDF, Excel/CSV, or Website)."
                    )

    with tab2:
        st.subheader("Execute Batch Extraction")

        if not configs:
            st.warning(
                "No product configurations available. Please add at least one configuration in the Configure Products tab."
            )
        else:
            st.write(f"Ready to extract {len(configs)} product configurations.")

            col1, col2 = st.columns([1, 3])

            with col1:
                if st.button("Start Batch Extraction", use_container_width=True):
                    process_batch_extraction()

            with col2:
                if st.button("Clear All Configurations", use_container_width=True):
                    clear_product_configs()
                    st.rerun()

        # Display extraction results
        if "product_configs" in st.session_state and any(
            config.status == "completed" for config in st.session_state.product_configs
        ):
            st.markdown("---")
            st.subheader("Extraction Results")

            # Count configurations by status
            total = len(st.session_state.product_configs)
            completed = sum(
                1
                for config in st.session_state.product_configs
                if config.status == "completed"
            )
            failed = sum(
                1
                for config in st.session_state.product_configs
                if config.status == "failed"
            )
            pending = total - completed - failed

            st.write(
                f"**Status Summary:** {completed} completed, {failed} failed, {pending} pending"
            )

            # Display each completed configuration's result
            for i, config in enumerate(st.session_state.product_configs):
                if config.status == "completed" and config.result is not None:
                    with st.expander(
                        f"Product {i+1}: {config.source_summary()}", expanded=False
                    ):
                        st.json(config.result)

            # Export options
            st.markdown("---")
            st.subheader("Export Results")

            col1, col2 = st.columns(2)

            with col1:
                export_format = st.selectbox("Export Format", ["JSON", "CSV"])

            with col2:
                if st.button("Export Completed Products"):
                    # Collect all completed products
                    completed_products = [
                        config.result
                        for config in st.session_state.product_configs
                        if config.status == "completed" and config.result is not None
                    ]

                    if not completed_products:
                        st.warning("No completed products to export.")
                    else:
                        if export_format == "JSON":
                            json_str = json.dumps(completed_products, indent=2)
                            st.download_button(
                                label="Download JSON",
                                data=json_str,
                                file_name="batch_extracted_products.json",
                                mime="application/json",
                            )
                        else:  # CSV
                            import pandas as pd

                            # Flatten JSON to make it suitable for CSV
                            flattened_products = []
                            for product in completed_products:
                                flat_product = {}
                                for key, value in product.items():
                                    if isinstance(value, list):
                                        flat_product[key] = ", ".join(
                                            str(item) for item in value
                                        )
                                    else:
                                        flat_product[key] = value
                                flattened_products.append(flat_product)

                            df = pd.DataFrame(flattened_products)
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name="batch_extracted_products.csv",
                                mime="text/csv",
                            )


def process_batch_extraction():
    """Process all product configurations in the batch"""
    configs = get_product_configs()

    if not configs:
        st.warning("No product configurations to process.")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Process each configuration
    for i, config in enumerate(configs):
        # Skip already processed configurations
        if config.status in ["completed", "failed"]:
            continue

        # Update status
        config.status = "processing"
        update_product_config(config)

        # Update progress display
        progress_percentage = i / len(configs)
        progress_bar.progress(progress_percentage)
        status_text.text(
            f"Processing {i+1} of {len(configs)}: {config.source_summary()}"
        )

        try:
            # Create consolidated text from all selected sources
            consolidated_text = ""

            # Process PDF if selected
            if config.pdf_file is not None and config.pdf_pages:
                from processors.pdf_processor import extract_pdf_data

                pdf_text = extract_pdf_data(
                    pdf_file=config.pdf_file, pdf_pages=config.pdf_pages
                )
                if pdf_text:
                    consolidated_text += f"## PDF SOURCE: {config.pdf_file.name}\n\n"
                    consolidated_text += pdf_text + "\n\n"

            # Process Excel/CSV if selected
            if config.excel_file is not None and config.excel_rows:
                from processors.excel_processor import extract_excel_data

                # Use the stored header row from session state for this extraction
                excel_header_row = st.session_state.get("batch_excel_header_row", 0)

                excel_text = extract_excel_data(
                    excel_file=config.excel_file,
                    excel_rows=config.excel_rows,
                    header_row=excel_header_row,
                )
                if excel_text:
                    file_type = "CSV" if is_csv_file(config.excel_file) else "EXCEL"
                    consolidated_text += (
                        f"## {file_type} SOURCE: {config.excel_file.name}\n\n"
                    )
                    consolidated_text += excel_text + "\n\n"

            # Process Website if selected
            if config.website_url:
                from processors.web_processor import extract_website_data

                website_text = extract_website_data(website_url=config.website_url)
                if website_text:
                    consolidated_text += f"## WEBSITE SOURCE: {config.website_url}\n\n"
                    consolidated_text += website_text

            # Add custom instructions to the consolidated text if provided
            if hasattr(config, "custom_instructions") and config.custom_instructions:
                consolidated_text = f"## CUSTOM INSTRUCTIONS:\n{config.custom_instructions}\n\n## DATA:\n{consolidated_text}"

            if consolidated_text:
                # Get LLM model
                llm = get_llm(
                    model_name=config.model_name,
                    temperature=config.temperature,
                    provider=config.model_provider,
                )

                if llm:
                    # Log some details for debugging
                    status_text.text(
                        f"Processing {i+1} of {len(configs)}: Running LLM extraction..."
                    )

                    # Create a run name that includes configuration details for tracing
                    run_name = f"Batch:{config.id} - {config.product_type} extraction"

                    # Process the data
                    product_data = process_with_llm(
                        text=consolidated_text,
                        product_type=config.product_type,
                        llm=llm,
                        run_name=run_name,
                    )

                    if product_data:
                        # Update configuration with result
                        config.result = product_data
                        config.status = "completed"
                        status_text.text(f"Processed {i+1} of {len(configs)}: Success!")
                    else:
                        config.status = "failed"
                        status_text.text(
                            f"Processed {i+1} of {len(configs)}: Failed to extract product data."
                        )
                else:
                    config.status = "failed"
                    status_text.text(
                        f"Processed {i+1} of {len(configs)}: Failed to initialize LLM."
                    )
            else:
                config.status = "failed"
                status_text.text(
                    f"Processed {i+1} of {len(configs)}: No data extracted from sources."
                )

        except Exception as e:
            st.error(f"Error processing configuration: {str(e)}")
            config.status = "failed"
            status_text.text(f"Processed {i+1} of {len(configs)}: Error: {str(e)}")

        # Update the configuration in session state
        update_product_config(config)

        # Update progress bar
        progress_bar.progress((i + 1) / len(configs))

    # Final progress update
    progress_bar.progress(1.0)
    status_text.text(f"Processed {len(configs)} configurations.")

    # Display completion message
    completed = sum(1 for config in configs if config.status == "completed")
    failed = sum(1 for config in configs if config.status == "failed")

    if failed > 0:
        st.warning(
            f"Batch processing completed: {completed} successful, {failed} failed"
        )
    else:
        st.success(
            f"Batch processing completed: All {completed} configurations processed successfully!"
        )
