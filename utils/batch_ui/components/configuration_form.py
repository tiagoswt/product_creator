"""
Configuration form component for product setup with automatic PDF preview
"""

import streamlit as st
import pandas as pd  # Added for Excel preview functionality
import time
from processors.pdf_processor import render_pdf_preview
from processors.excel_processor import process_excel_file
from utils.product_config import ProductConfig, add_product_config
import config


class ConfigurationForm:
    """Handles the product configuration form with automatic PDF preview"""

    def __init__(self):
        self._initialize_data_source_states()
        # Initialize form counter for dynamic keys
        if "form_counter" not in st.session_state:
            st.session_state.form_counter = 0

    def _initialize_data_source_states(self):
        """Initialize data source states in session"""
        # PDF states
        if "current_pdf_file" not in st.session_state:
            st.session_state.current_pdf_file = None
        if "pdf_selected_pages" not in st.session_state:
            st.session_state.pdf_selected_pages = set()
        if "last_pdf_processed" not in st.session_state:
            st.session_state.last_pdf_processed = None

        # Excel states (updated with new preview states)
        if "current_excel_file" not in st.session_state:
            st.session_state.current_excel_file = None
        if "excel_rows_selected" not in st.session_state:
            st.session_state.excel_rows_selected = []
        if "raw_excel_df" not in st.session_state:
            st.session_state.raw_excel_df = None
        if "processed_excel_df" not in st.session_state:
            st.session_state.processed_excel_df = None
        if "excel_header_row" not in st.session_state:
            st.session_state.excel_header_row = None

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

        st.markdown("---")
        st.write("### Data Sources")

        # Website source first (outside form for immediate feedback)
        website_url = self._render_website_section()

        # PDF source second (outside form for interactive selection)
        selected_pdf_pages = self._render_pdf_section_with_auto_preview()

        # Excel source third (outside form for immediate feedback)
        selected_excel_rows = self._render_excel_section()

        # Form only for final submission
        st.markdown("---")
        with st.form("new_product_config", clear_on_submit=False):
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

    def _render_pdf_section_with_auto_preview(self):
        """Render PDF upload section with automatic preview and clickable selection"""
        st.write("**📄 PDF Source**")

        # PDF file uploader (outside form)
        pdf_file = st.file_uploader(
            "Upload PDF",
            type="pdf",
            help="Upload a PDF file containing product information",
            key=f"main_pdf_uploader_{st.session_state.form_counter}",
        )

        selected_pdf_pages = []

        # Handle PDF file upload and auto-preview
        if pdf_file:
            # Check if this is a new PDF file
            is_new_pdf = (
                st.session_state.current_pdf_file is None
                or st.session_state.current_pdf_file.name != pdf_file.name
                or st.session_state.last_pdf_processed != pdf_file.name
            )

            if is_new_pdf:
                # Reset selection for new PDF
                st.session_state.pdf_selected_pages = set()
                st.session_state.current_pdf_file = pdf_file
                st.session_state.last_pdf_processed = pdf_file.name

                # Auto-generate preview for new PDF
                with st.spinner("📖 Loading PDF preview..."):
                    try:
                        pdf_preview = render_pdf_preview(pdf_file)
                        st.session_state.pdf_preview = pdf_preview
                        st.success(
                            f"✅ PDF loaded: {pdf_file.name} ({len(pdf_preview)} pages)"
                        )
                    except Exception as e:
                        st.error(f"❌ Error loading PDF: {str(e)}")
                        return []
            else:
                # Same PDF, keep existing selection
                st.session_state.current_pdf_file = pdf_file
                st.info(f"📄 PDF: {pdf_file.name}")

            # Show thumbnail grid if preview is available
            if "pdf_preview" in st.session_state and st.session_state.pdf_preview:
                selected_pdf_pages = self._render_pdf_thumbnail_grid()

        else:
            # No PDF uploaded
            if st.session_state.current_pdf_file:
                st.session_state.current_pdf_file = None
                st.session_state.pdf_selected_pages = set()
                if "pdf_preview" in st.session_state:
                    del st.session_state["pdf_preview"]

        return selected_pdf_pages

    def _render_pdf_thumbnail_grid(self):
        """Render PDF pages as clickable thumbnail grid"""
        pdf_preview = st.session_state.pdf_preview
        total_pages = len(pdf_preview)

        st.write(f"**Select pages from {total_pages} available:**")

        # Quick action buttons (outside form)
        self._render_pdf_quick_actions(total_pages)

        # Show current selection summary
        selected_count = len(st.session_state.pdf_selected_pages)
        if selected_count > 0:
            selected_list = sorted(st.session_state.pdf_selected_pages)
            selected_display = ", ".join(str(p + 1) for p in selected_list[:10])
            if len(selected_list) > 10:
                selected_display += f" ... (+{len(selected_list) - 10} more)"
            st.success(f"✅ Selected {selected_count} pages: {selected_display}")
        else:
            st.info("👆 Click page thumbnails below to select them")

        # Render thumbnail grid
        st.write("**Click on page thumbnails to select/deselect:**")

        # Create thumbnail grid (3 columns per row)
        cols_per_row = 3

        for row_start in range(0, total_pages, cols_per_row):
            cols = st.columns(cols_per_row)

            for col_idx in range(cols_per_row):
                page_idx = row_start + col_idx

                if page_idx < total_pages:
                    with cols[col_idx]:
                        self._render_pdf_page_thumbnail(page_idx, pdf_preview[page_idx])

        # Return selected pages as list
        return sorted(list(st.session_state.pdf_selected_pages))

    def _render_pdf_quick_actions(self, total_pages):
        """Render quick action buttons for PDF page selection"""
        st.write("**Quick Actions:**")
        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if st.button(
                "📋 Select All",
                key=f"pdf_select_all_{st.session_state.form_counter}",
                use_container_width=True,
            ):
                st.session_state.pdf_selected_pages = set(range(total_pages))
                st.rerun()

        with action_col2:
            if st.button(
                "🗑️ Clear All",
                key=f"pdf_clear_all_{st.session_state.form_counter}",
                use_container_width=True,
            ):
                st.session_state.pdf_selected_pages = set()
                st.rerun()

    def _render_pdf_page_thumbnail(self, page_idx, page_data):
        """Render a single PDF page thumbnail with selection button"""
        page_num = page_idx + 1
        is_selected = page_idx in st.session_state.pdf_selected_pages

        # Display the page image
        try:
            page_image_data = page_data[1]  # (page_number, image_bytes)
            st.image(
                page_image_data, caption=f"Page {page_num}", use_container_width=True
            )
        except Exception as e:
            st.error(f"Error loading page {page_num}")
            return

        # Selection button with visual feedback
        button_text = "✅ Selected" if is_selected else "📄 Select"
        button_type = "secondary" if is_selected else "primary"

        if st.button(
            button_text,
            key=f"pdf_page_select_{page_idx}_{st.session_state.form_counter}",
            type=button_type,
            use_container_width=True,
        ):
            # Toggle selection
            if is_selected:
                st.session_state.pdf_selected_pages.discard(page_idx)
            else:
                st.session_state.pdf_selected_pages.add(page_idx)
            st.rerun()

        # Visual indicator
        if is_selected:
            st.success("✅ Selected")
        else:
            st.caption("Click to select")

    def _render_excel_section(self):
        """Render Excel/CSV upload and selection section with preview before header selection"""
        st.write("**📊 Excel/CSV Source**")

        # Excel file uploader (outside form)
        excel_file = st.file_uploader(
            "Upload Excel/CSV",
            type=["xlsx", "xls", "csv"],
            help="Upload an Excel or CSV file containing product information",
            key=f"main_excel_uploader_{st.session_state.form_counter}",
        )

        selected_excel_rows = []

        # Handle Excel file upload
        if excel_file:
            # Check if this is a new file
            is_new_file = (
                st.session_state.current_excel_file is None
                or st.session_state.current_excel_file.name != excel_file.name
            )

            if is_new_file:
                # Reset states for new file
                st.session_state.current_excel_file = excel_file
                if "raw_excel_df" in st.session_state:
                    del st.session_state["raw_excel_df"]
                if "processed_excel_df" in st.session_state:
                    del st.session_state["processed_excel_df"]
                if "excel_header_row" in st.session_state:
                    del st.session_state["excel_header_row"]

                # Auto-load raw preview for new file
                with st.spinner("📊 Loading file preview..."):
                    try:
                        # Load raw data without headers for preview
                        excel_file.seek(0)
                        raw_df = process_excel_file(
                            excel_file, header=None, nrows=20
                        )  # Load first 20 rows
                        if raw_df is not None:
                            st.session_state.raw_excel_df = raw_df
                            st.success(f"✅ File loaded: {excel_file.name}")
                        else:
                            st.error(
                                "❌ Error loading file. Please check the file format."
                            )
                            return []
                    except Exception as e:
                        st.error(f"❌ Error loading file: {str(e)}")
                        return []
            else:
                st.session_state.current_excel_file = excel_file
                st.info(f"📊 File: {excel_file.name}")

            # Show raw preview if available
            if (
                "raw_excel_df" in st.session_state
                and st.session_state.raw_excel_df is not None
            ):
                # Show raw data preview
                st.write("**📋 File Preview (first 20 rows):**")

                # Display the raw data with row numbers
                preview_df = st.session_state.raw_excel_df.copy()
                preview_df.index.name = "Row"

                # Show the dataframe with row indices
                st.dataframe(preview_df, use_container_width=True, height=300)

                # Header row selection based on preview
                total_rows = len(preview_df)
                st.write("**🏷️ Select Header Row:**")

                header_row = st.selectbox(
                    "Which row contains the column headers?",
                    options=list(range(total_rows)),
                    index=0,
                    format_func=lambda x: f"Row {x} - {self._format_row_preview(preview_df.iloc[x])}",
                    help="Select the row that contains your column headers",
                    key=f"excel_header_row_selector_{st.session_state.form_counter}",
                )

                # Show selected header row highlight
                if header_row is not None:
                    st.write(f"**Selected header row {header_row}:**")
                    header_preview = preview_df.iloc[header_row : header_row + 1]
                    st.dataframe(
                        header_preview, use_container_width=True, hide_index=False
                    )

                # Process data with selected header row
                if st.button(
                    "✅ Apply Header Row",
                    type="primary",
                    key=f"apply_header_row_{st.session_state.form_counter}",
                ):
                    with st.spinner("Processing Excel file with selected headers..."):
                        try:
                            st.session_state.current_excel_file.seek(0)
                            processed_df = process_excel_file(
                                st.session_state.current_excel_file, header=header_row
                            )
                            if processed_df is not None and not processed_df.empty:
                                st.session_state.processed_excel_df = processed_df
                                st.session_state.excel_header_row = header_row
                                st.success(
                                    f"✅ Data processed with row {header_row} as headers"
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "❌ Error processing file with selected headers. The result is empty."
                                )
                                # Clear the processed data
                                if "processed_excel_df" in st.session_state:
                                    del st.session_state["processed_excel_df"]
                        except Exception as e:
                            st.error(f"❌ Error processing Excel: {str(e)}")
                            # Clear the processed data on error
                            if "processed_excel_df" in st.session_state:
                                del st.session_state["processed_excel_df"]

                # Show row selection if data is processed with headers
                if (
                    "processed_excel_df" in st.session_state
                    and st.session_state.processed_excel_df is not None
                    and not st.session_state.processed_excel_df.empty
                    and st.session_state.current_excel_file
                    and st.session_state.get("excel_header_row") == header_row
                ):
                    st.markdown("---")
                    st.write("**📋 Processed Data with Headers:**")

                    try:
                        # Show processed data preview with additional safety checks
                        processed_preview = st.session_state.processed_excel_df.head(10)
                        st.dataframe(processed_preview, use_container_width=True)

                        selected_excel_rows = self._render_excel_row_selection()
                    except Exception as e:
                        st.error(f"❌ Error displaying processed data: {str(e)}")
                        # Clear the problematic processed data
                        if "processed_excel_df" in st.session_state:
                            del st.session_state["processed_excel_df"]
                        selected_excel_rows = []

            else:
                if st.session_state.current_excel_file:
                    st.error("Unable to preview file. Please try uploading again.")

        else:
            # No Excel uploaded - clear all related session state
            if st.session_state.current_excel_file:
                st.session_state.current_excel_file = None
                if "raw_excel_df" in st.session_state:
                    del st.session_state["raw_excel_df"]
                if "processed_excel_df" in st.session_state:
                    del st.session_state["processed_excel_df"]
                if "excel_header_row" in st.session_state:
                    del st.session_state["excel_header_row"]

        return selected_excel_rows

    def _render_excel_row_selection(self):
        """Render Excel row selection interface with additional safety checks"""
        # Add safety check for processed_excel_df
        if (
            "processed_excel_df" not in st.session_state
            or st.session_state.processed_excel_df is None
            or st.session_state.processed_excel_df.empty
        ):
            st.error("❌ No processed Excel data available. Please reprocess the file.")
            return []

        processed_df = st.session_state.processed_excel_df
        num_rows = len(processed_df)

        if num_rows == 0:
            st.warning("⚠️ No data rows available after header processing.")
            return []

        st.write(f"Select rows from {num_rows} available:")

        # Row selection method
        row_selection_method = st.radio(
            "Row selection:",
            ["Select All", "Row Range", "Individual Rows"],
            key=f"excel_row_method_{st.session_state.form_counter}",
        )

        try:
            if row_selection_method == "Select All":
                selected_excel_rows = list(range(num_rows))
                st.success(f"All {num_rows} rows selected")
            elif row_selection_method == "Row Range":
                col_start, col_end = st.columns(2)
                with col_start:
                    start_row = st.number_input(
                        "Start row",
                        min_value=0,
                        max_value=num_rows - 1,
                        value=0,
                        key=f"excel_start_row_{st.session_state.form_counter}",
                    )
                with col_end:
                    end_row = st.number_input(
                        "End row",
                        min_value=start_row,
                        max_value=num_rows - 1,
                        value=min(4, num_rows - 1),
                        key=f"excel_end_row_{st.session_state.form_counter}",
                    )
                selected_excel_rows = list(range(start_row, end_row + 1))
                st.info(
                    f"Rows {start_row} to {end_row} selected ({len(selected_excel_rows)} rows)"
                )
            else:  # Individual Rows
                selected_rows_input = st.text_input(
                    "Enter row numbers (comma-separated, e.g., 0,2,4):",
                    placeholder="0,1,2",
                    key=f"excel_individual_rows_{st.session_state.form_counter}",
                )
                if selected_rows_input:
                    try:
                        row_numbers = [
                            int(r.strip()) for r in selected_rows_input.split(",")
                        ]
                        selected_excel_rows = [
                            r for r in row_numbers if 0 <= r < num_rows
                        ]
                        if len(selected_excel_rows) != len(row_numbers):
                            invalid_rows = [
                                r for r in row_numbers if r < 0 or r >= num_rows
                            ]
                            st.warning(f"⚠️ Invalid row numbers ignored: {invalid_rows}")
                        st.success(
                            f"Selected {len(selected_excel_rows)} rows: {', '.join(str(r) for r in selected_excel_rows)}"
                        )
                    except ValueError:
                        selected_excel_rows = []
                        st.error(
                            "Invalid row numbers. Please use comma-separated numbers."
                        )
                else:
                    selected_excel_rows = []
        except Exception as e:
            st.error(f"❌ Error in row selection: {str(e)}")
            selected_excel_rows = []

        return selected_excel_rows

    def _format_row_preview(self, row):
        """Format a row for preview in the header selection dropdown"""
        try:
            # Show first 3 non-null values from the row
            non_null_values = [
                str(val) for val in row.values if pd.notna(val) and str(val).strip()
            ]
            if non_null_values:
                preview_text = " | ".join(non_null_values[:3])
                if len(preview_text) > 50:
                    preview_text = preview_text[:47] + "..."
                return preview_text
            else:
                return "Empty row"
        except Exception as e:
            return f"Error reading row: {str(e)}"

    def _render_website_section(self):
        """Render website URL input section"""
        st.write("**🌐 Website Source**")
        website_url = st.text_input(
            "Website URLs",
            placeholder="https://example.com/product-page, https://shop.example.com/item, another-site.com/product",
            help="Enter one or more website URLs containing product information. Separate multiple URLs with commas.",
            key=f"website_url_input_{st.session_state.form_counter}",
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
        model_provider = config.DEFAULT_PROVIDER  # Now respects config setting

        # Select the correct model based on provider
        if model_provider == "groq":
            model_name = config.DEFAULT_GROQ_MODEL
        else:  # openai
            model_name = config.DEFAULT_OPENAI_MODEL

        temperature = config.DEFAULT_TEMPERATURE
        custom_instructions = ""  # No custom instructions

        # Clean base_product for filename use
        clean_base_product = ""
        if base_product:
            clean_base_product = (
                base_product.strip().lower().replace(" ", "").replace("-", "")
            )

        # Get the header row that was used for this configuration
        excel_header_row = st.session_state.get("excel_header_row", 0) if has_excel else 0

        # Create the product configuration with default backend settings
        new_config = ProductConfig(
            product_type=product_type,
            base_product=clean_base_product,  # Add base_product
            pdf_file=st.session_state.current_pdf_file if has_pdf else None,
            pdf_pages=selected_pdf_pages if has_pdf else [],
            excel_file=st.session_state.current_excel_file if has_excel else None,
            excel_rows=selected_excel_rows if has_excel else [],
            excel_header_row=excel_header_row,  # Store header row per configuration
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
        # Increment form counter to reset all widgets with new keys
        st.session_state.form_counter += 1

        # Clear internal file tracking
        st.session_state.current_pdf_file = None
        st.session_state.current_excel_file = None
        st.session_state.pdf_selected_pages = set()
        st.session_state.excel_rows_selected = []

        # Clear PDF-related session state
        if "pdf_preview" in st.session_state:
            del st.session_state["pdf_preview"]
        if "last_pdf_processed" in st.session_state:
            del st.session_state["last_pdf_processed"]

        # Clear Excel-related session state (including new raw preview data)
        if "raw_excel_df" in st.session_state:
            del st.session_state["raw_excel_df"]
        if "processed_excel_df" in st.session_state:
            del st.session_state["processed_excel_df"]
        if "excel_header_row" in st.session_state:
            del st.session_state["excel_header_row"]
        if "excel_header_row_selector" in st.session_state:
            del st.session_state["excel_header_row_selector"]

        # Don't clear product_type_selector and base_product_input
        # so user can easily add multiple products of the same type

