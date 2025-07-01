"""
Configuration form component for product setup
"""

import streamlit as st
import time
from processors.pdf_processor import render_pdf_preview
from processors.excel_processor import process_excel_file
from utils.product_config import ProductConfig, add_product_config
import config

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
DEFAULT_TEMPERATURE = 0.4


class ConfigurationForm:
    """Handles the product configuration form"""

    def __init__(self):
        self._initialize_data_source_states()

    def _initialize_data_source_states(self):
        """Initialize data source states in session"""
        if "current_pdf_file" not in st.session_state:
            st.session_state.current_pdf_file = None
        if "current_excel_file" not in st.session_state:
            st.session_state.current_excel_file = None
        if "pdf_pages_selected" not in st.session_state:
            st.session_state.pdf_pages_selected = []
        if "excel_rows_selected" not in st.session_state:
            st.session_state.excel_rows_selected = []

    def render(self):
        """Render the complete configuration form"""
        # Product type selection OUTSIDE the form so it updates immediately
        product_type = st.selectbox(
            "Product Type",
            ["cosmetics", "fragrance", "subtype"],
            help="Choose the type of product to extract",
            key="product_type_selector",
        )

        # Base product field - show immediately when subtype is selected
        base_product = ""
        if product_type == "subtype":
            base_product = st.text_input(
                "Base Product",
                placeholder="e.g., lipbalm, serum, cream, cleanser",
                help="Enter the base product type for subtype classification (used in filename)",
                key="base_product_input",
            )

            if base_product:
                # Clean the base_product for filename use
                cleaned_base_product = (
                    base_product.strip().lower().replace(" ", "").replace("-", "")
                )
                if cleaned_base_product != base_product.strip():
                    st.caption(f"Will be saved as: {cleaned_base_product}")

        with st.form("new_product_config", clear_on_submit=False):
            st.markdown("---")
            st.write("### Data Sources")

            # Website source first (full width)
            website_url = self._render_website_section()

            # PDF source second (full width)
            selected_pdf_pages = self._render_pdf_section()

            # Excel source third (full width)
            selected_excel_rows = self._render_excel_section()

            # Submit button
            st.markdown("---")
            submitted = st.form_submit_button(
                "Add Product Configuration", type="primary"
            )

            if submitted:
                self._handle_form_submission(
                    selected_pdf_pages,
                    selected_excel_rows,
                    website_url,
                    product_type,
                    base_product,
                )

    def _render_pdf_section(self):
        """Render PDF upload and selection section"""
        st.write("**📄 PDF Source**")

        # PDF file uploader
        form_pdf_key = f"form_pdf_uploader_{int(time.time())}"
        pdf_file = st.file_uploader(
            "Upload PDF",
            type="pdf",
            key=form_pdf_key,
            help="Upload a PDF file containing product information",
        )

        # Store PDF file in session state
        if pdf_file:
            st.session_state.current_pdf_file = pdf_file
            st.success(f"PDF uploaded: {pdf_file.name}")

        selected_pdf_pages = []

        # PDF page selection
        if st.session_state.current_pdf_file:
            if st.form_submit_button("Preview PDF Pages", type="secondary"):
                with st.spinner("Rendering PDF preview..."):
                    pdf_preview = render_pdf_preview(st.session_state.current_pdf_file)
                    st.session_state.pdf_preview = pdf_preview
                    st.session_state.last_pdf_name = (
                        st.session_state.current_pdf_file.name
                    )
                    st.rerun()

            # Show page selection if preview is available
            if (
                "pdf_preview" in st.session_state
                and "last_pdf_name" in st.session_state
                and st.session_state.current_pdf_file
                and st.session_state.last_pdf_name
                == st.session_state.current_pdf_file.name
            ):
                selected_pdf_pages = self._render_pdf_page_selection()
            else:
                if st.session_state.current_pdf_file:
                    st.info("Click 'Preview PDF Pages' to select specific pages")

        return selected_pdf_pages

    def _render_pdf_page_selection(self):
        """Render PDF page selection interface"""
        total_pages = len(st.session_state.pdf_preview)
        st.write(f"Select pages from {total_pages} available:")

        # Page range selector
        page_selection_method = st.radio(
            "Page selection:",
            ["Select All", "Page Range", "Individual Pages"],
            key="pdf_page_method",
        )

        if page_selection_method == "Select All":
            selected_pdf_pages = list(range(total_pages))
            st.success(f"All {total_pages} pages selected")
        elif page_selection_method == "Page Range":
            col_start, col_end = st.columns(2)
            with col_start:
                start_page = st.number_input(
                    "Start page", min_value=1, max_value=total_pages, value=1
                )
            with col_end:
                end_page = st.number_input(
                    "End page",
                    min_value=start_page,
                    max_value=total_pages,
                    value=total_pages,
                )
            selected_pdf_pages = list(range(start_page - 1, end_page))
            st.info(
                f"Pages {start_page} to {end_page} selected ({len(selected_pdf_pages)} pages)"
            )
        else:  # Individual Pages
            selected_pages_input = st.text_input(
                "Enter page numbers (comma-separated, e.g., 1,3,5):",
                placeholder="1,2,3",
            )
            if selected_pages_input:
                try:
                    page_numbers = [
                        int(p.strip()) for p in selected_pages_input.split(",")
                    ]
                    selected_pdf_pages = [
                        p - 1 for p in page_numbers if 1 <= p <= total_pages
                    ]
                    st.success(
                        f"Selected {len(selected_pdf_pages)} pages: {', '.join(str(p+1) for p in selected_pdf_pages)}"
                    )
                except ValueError:
                    selected_pdf_pages = []
                    st.error(
                        "Invalid page numbers. Please use comma-separated numbers."
                    )
            else:
                selected_pdf_pages = []

        return selected_pdf_pages

    def _render_excel_section(self):
        """Render Excel/CSV upload and selection section"""
        st.write("**📊 Excel/CSV Source**")

        # Excel file uploader
        form_excel_key = f"form_excel_uploader_{int(time.time())}"
        excel_file = st.file_uploader(
            "Upload Excel/CSV",
            type=["xlsx", "xls", "csv"],
            key=form_excel_key,
            help="Upload an Excel or CSV file containing product information",
        )

        # Store Excel file in session state
        if excel_file:
            st.session_state.current_excel_file = excel_file
            st.success(f"File uploaded: {excel_file.name}")

        selected_excel_rows = []

        # Excel processing
        if st.session_state.current_excel_file:
            # Header row selection
            header_row = st.number_input(
                "Header row (0-based index):",
                min_value=0,
                max_value=50,
                value=0,
                help="Which row contains the column headers",
            )

            if st.form_submit_button("Preview Excel Data", type="secondary"):
                with st.spinner("Processing Excel file..."):
                    try:
                        st.session_state.current_excel_file.seek(0)
                        processed_df = process_excel_file(
                            st.session_state.current_excel_file, header=header_row
                        )
                        if processed_df is not None:
                            st.session_state.processed_excel_df = processed_df
                            st.session_state.excel_header_row = header_row
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error processing Excel: {str(e)}")

            # Show row selection if data is processed
            if (
                "processed_excel_df" in st.session_state
                and st.session_state.current_excel_file
            ):
                selected_excel_rows = self._render_excel_row_selection()
            else:
                if st.session_state.current_excel_file:
                    st.info("Click 'Preview Excel Data' to select specific rows")

        return selected_excel_rows

    def _render_excel_row_selection(self):
        """Render Excel row selection interface"""
        processed_df = st.session_state.processed_excel_df
        num_rows = len(processed_df)

        st.write(f"Select rows from {num_rows} available:")

        # Row selection method
        row_selection_method = st.radio(
            "Row selection:",
            ["Select All", "Row Range", "Individual Rows"],
            key="excel_row_method",
        )

        if row_selection_method == "Select All":
            selected_excel_rows = list(range(num_rows))
            st.success(f"All {num_rows} rows selected")
        elif row_selection_method == "Row Range":
            col_start, col_end = st.columns(2)
            with col_start:
                start_row = st.number_input(
                    "Start row", min_value=0, max_value=num_rows - 1, value=0
                )
            with col_end:
                end_row = st.number_input(
                    "End row",
                    min_value=start_row,
                    max_value=num_rows - 1,
                    value=min(4, num_rows - 1),
                )
            selected_excel_rows = list(range(start_row, end_row + 1))
            st.info(
                f"Rows {start_row} to {end_row} selected ({len(selected_excel_rows)} rows)"
            )
        else:  # Individual Rows
            selected_rows_input = st.text_input(
                "Enter row numbers (comma-separated, e.g., 0,2,4):", placeholder="0,1,2"
            )
            if selected_rows_input:
                try:
                    row_numbers = [
                        int(r.strip()) for r in selected_rows_input.split(",")
                    ]
                    selected_excel_rows = [r for r in row_numbers if 0 <= r < num_rows]
                    st.success(
                        f"Selected {len(selected_excel_rows)} rows: {', '.join(str(r) for r in selected_excel_rows)}"
                    )
                except ValueError:
                    selected_excel_rows = []
                    st.error("Invalid row numbers. Please use comma-separated numbers.")
            else:
                selected_excel_rows = []

        return selected_excel_rows

    def _render_website_section(self):
        """Render website URL input section"""
        st.write("**🌐 Website Source**")
        website_url = st.text_input(
            "Website URLs",
            placeholder="https://example.com/product-page, https://shop.example.com/item, another-site.com/product",
            help="Enter one or more website URLs containing product information. Separate multiple URLs with commas.",
        )

        # Show URL preview if user has entered something
        if website_url and website_url.strip():
            try:
                from processors.web_processor import get_url_preview

                preview = get_url_preview(website_url)
                st.caption(preview)
            except (ImportError, Exception):
                # Fallback if the new functions aren't available yet
                url_count = len(
                    [url.strip() for url in website_url.split(",") if url.strip()]
                )
                st.caption(f"📋 {url_count} URL(s) to process")

        return website_url

    def _handle_form_submission(
        self,
        selected_pdf_pages,
        selected_excel_rows,
        website_url,
        product_type,
        base_product,
    ):
        """Handle form submission and create product configuration"""
        # Validate that at least one data source is selected
        has_pdf = st.session_state.current_pdf_file and selected_pdf_pages
        has_excel = st.session_state.current_excel_file and selected_excel_rows
        has_website = website_url and website_url.strip()

        if not (has_pdf or has_excel or has_website):
            st.error(
                "❌ Please select at least one data source (PDF pages, Excel rows, or Website URL)."
            )
            return

        # Validate base_product for subtype
        if product_type == "subtype" and not base_product.strip():
            st.error("❌ Please enter a base product for subtype classification.")
            return

        # Use default model configuration (hidden from user)
        model_provider = config.DEFAULT_PROVIDER  # "groq"
        model_name = (
            config.DEFAULT_MODEL
        )  # "meta-llama/llama-4-maverick-17b-128e-instruct"
        temperature = config.DEFAULT_TEMPERATURE  # 0.4
        custom_instructions = ""  # No custom instructions

        # Clean base_product for filename use
        clean_base_product = ""
        if base_product:
            clean_base_product = (
                base_product.strip().lower().replace(" ", "").replace("-", "")
            )

        # Create the product configuration with default backend settings
        new_config = ProductConfig(
            product_type=product_type,
            base_product=clean_base_product,  # Add base_product
            pdf_file=st.session_state.current_pdf_file if has_pdf else None,
            pdf_pages=selected_pdf_pages if has_pdf else [],
            excel_file=st.session_state.current_excel_file if has_excel else None,
            excel_rows=selected_excel_rows if has_excel else [],
            website_url=website_url.strip() if has_website else None,
            model_provider=model_provider,
            model_name=model_name,
            temperature=temperature,
            custom_instructions=custom_instructions,
        )

        # Add to configurations
        add_product_config(new_config)

        # Show success message with summary
        sources_summary = []
        if has_pdf:
            sources_summary.append(f"📄 PDF: {len(selected_pdf_pages)} pages")
        if has_excel:
            sources_summary.append(f"📊 Excel: {len(selected_excel_rows)} rows")
        if has_website:
            url_count = len(
                [url.strip() for url in website_url.split(",") if url.strip()]
            )
            if url_count == 1:
                sources_summary.append(f"🌐 Website: {website_url.strip()}")
            else:
                sources_summary.append(f"🌐 Websites: {url_count} URLs")

        success_message = f"✅ Product configuration added successfully!\n\n**Data Sources:** {' | '.join(sources_summary)}"

        # Add base product info for subtype
        if product_type == "subtype" and clean_base_product:
            success_message += f"\n**Base Product:** {clean_base_product}"

        st.success(success_message)

        # Clear form data
        self._clear_form_data()

        # Rerun to refresh the UI
        st.rerun()

    def _clear_form_data(self):
        """Clear form data after successful submission"""
        st.session_state.current_pdf_file = None
        st.session_state.current_excel_file = None
        st.session_state.pdf_pages_selected = []
        st.session_state.excel_rows_selected = []
        if "pdf_preview" in st.session_state:
            del st.session_state["pdf_preview"]
        if "processed_excel_df" in st.session_state:
            del st.session_state["processed_excel_df"]
        # Don't clear product_type_selector and base_product_input
        # so user can easily add multiple products of the same type
