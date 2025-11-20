"""
Configuration form component for product setup with automatic PDF preview
ENHANCED: Draft auto-save, smart header detection, multi-select, unified preview
"""

import streamlit as st
import pandas as pd  # Added for Excel preview functionality
import time
from processors.pdf_processor import render_pdf_preview
from processors.excel_processor import process_excel_file
from utils.product_config import ProductConfig, add_product_config
from utils.draft_manager import create_draft_manager
import config


class ConfigurationForm:
    """Handles the product configuration form with automatic PDF preview"""

    def __init__(self):
        self._initialize_data_source_states()
        # Initialize form counter for dynamic keys
        if "form_counter" not in st.session_state:
            st.session_state.form_counter = 0
        # Initialize draft manager
        self.draft_manager = create_draft_manager()

    def _initialize_data_source_states(self):
        """Initialize data source states in session"""
        # PDF states
        if "current_pdf_file" not in st.session_state:
            st.session_state.current_pdf_file = None
        if "pdf_selected_pages" not in st.session_state:
            st.session_state.pdf_selected_pages = set()
        if "last_pdf_processed" not in st.session_state:
            st.session_state.last_pdf_processed = None

        # Excel states
        if "current_excel_file" not in st.session_state:
            st.session_state.current_excel_file = None
        if "excel_rows_selected" not in st.session_state:
            st.session_state.excel_rows_selected = []
        if "processed_excel_df" not in st.session_state:
            st.session_state.processed_excel_df = None
        if "excel_header_row" not in st.session_state:
            st.session_state.excel_header_row = None

    def render(self):
        """Render the complete configuration form"""

        # IMPROVEMENT #1: Draft Recovery Banner
        recovered_draft_id = self.draft_manager.render_draft_recovery_banner()
        if recovered_draft_id:
            # User clicked to recover a draft
            draft_data = self.draft_manager.load_draft(recovered_draft_id)
            if draft_data:
                self._restore_draft_data(draft_data)
                st.success("✅ Draft recovered successfully!")
                st.rerun()

        # Product type selection OUTSIDE the form so it updates immediately
        product_type = st.selectbox(
            "Product Type",
            ["cosmetics", "fragrance", "subtype", "supplement", "tech"],
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

        # Auto-save draft after selections
        self._trigger_auto_save()

        # IMPROVEMENT #4: Unified Data Preview
        self._render_unified_preview(website_url, selected_pdf_pages, selected_excel_rows)

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
                if "processed_excel_df" in st.session_state:
                    del st.session_state["processed_excel_df"]
                if "excel_header_row" in st.session_state:
                    del st.session_state["excel_header_row"]

                # Auto-load file with first row as header
                with st.spinner("📊 Loading file..."):
                    try:
                        # Load data with first row (row 0) as header
                        excel_file.seek(0)
                        processed_df = process_excel_file(
                            excel_file, header=0
                        )  # Use first row as header
                        if processed_df is not None and not processed_df.empty:
                            st.session_state.processed_excel_df = processed_df
                            st.session_state.excel_header_row = 0  # Automatically set to row 0
                            st.success(f"✅ File loaded: {excel_file.name} ({len(processed_df)} rows)")
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

            # Show processed data with headers if available
            if (
                "processed_excel_df" in st.session_state
                and st.session_state.processed_excel_df is not None
                and not st.session_state.processed_excel_df.empty
                and st.session_state.current_excel_file
            ):
                st.markdown("---")
                st.write("**📋 Processed Data with Headers:**")

                try:
                    # Show processed data preview with additional safety checks
                    processed_preview = st.session_state.processed_excel_df.head(10)
                    st.dataframe(processed_preview, use_container_width=True)

                    # NEW FEATURE: Batch Mode Toggle
                    st.markdown("---")
                    st.write("**📦 Import Mode:**")

                    batch_mode = st.checkbox(
                        "Batch Mode: Each row = 1 product",
                        value=False,
                        help="Automatically create one product configuration per row (Excel only)",
                        key=f"excel_batch_mode_{st.session_state.form_counter}"
                    )

                    if batch_mode:
                        # Count non-empty rows
                        processed_df = st.session_state.processed_excel_df
                        non_empty_df = processed_df.dropna(how='all')
                        total_rows = len(processed_df)
                        valid_rows = len(non_empty_df)
                        empty_rows = total_rows - valid_rows

                        # Show batch mode info
                        if empty_rows > 0:
                            st.info(f"✨ **Batch Mode Active:** Creating {valid_rows} product configs ({empty_rows} empty rows will be skipped)")
                        else:
                            st.info(f"✨ **Batch Mode Active:** Creating {valid_rows} product configurations")

                        # Warning for large files
                        if valid_rows > 100:
                            st.warning(f"⚠️ Creating {valid_rows} configurations may take several minutes to process.")

                        if valid_rows > 500:
                            st.error(f"❌ Maximum 500 products per batch. Your file has {valid_rows} valid rows. Please split the file.")

                        # Show preview of first 3 rows
                        st.write("**Preview (first 3 rows as examples):**")
                        st.dataframe(non_empty_df.head(3), use_container_width=True)
                        if valid_rows > 3:
                            st.caption(f"... and {valid_rows - 3} more rows")

                        # Store valid rows count for later use
                        st.session_state[f"batch_valid_rows_{st.session_state.form_counter}"] = valid_rows

                        # NEW FEATURE: URL Column Selection for Batch Mode (Always Visible)
                        st.markdown("---")

                        processed_df = st.session_state.processed_excel_df
                        column_options = list(processed_df.columns)

                        # Try to auto-detect URL column (columns with keywords)
                        url_keywords = ["url", "link", "website", "web", "site", "href"]
                        url_column_candidates = [
                            col for col in column_options
                            if any(keyword in str(col).lower() for keyword in url_keywords)
                        ]

                        # Add "None" option at the beginning
                        dropdown_options = ["None (Excel only)"] + column_options

                        # Set default index
                        default_index = 0  # Default to "None"
                        if url_column_candidates:
                            # Auto-select first detected URL column
                            default_index = dropdown_options.index(url_column_candidates[0])
                            st.info(f"💡 Auto-detected URL column: **{url_column_candidates[0]}** (change to 'None' if not needed)")

                        url_column_selection = st.selectbox(
                            "Website URLs:",
                            options=dropdown_options,
                            index=default_index,
                            help="Choose a column with URLs to scrape website content for each product, or select 'None' to use Excel data only",
                            key=f"url_column_select_{st.session_state.form_counter}"
                        )

                        # Only process if not "None"
                        if url_column_selection != "None (Excel only)":
                            url_column = url_column_selection

                            # Show preview of URLs from first 5 rows
                            preview_urls = processed_df[url_column].head(5)
                            urls_valid = 0
                            urls_empty = 0

                            for idx, url in enumerate(preview_urls):
                                if pd.notna(url) and str(url).strip():
                                    url_str = str(url).strip()
                                    if url_str.startswith(('http://', 'https://')):
                                        st.caption(f"✅ Row {idx}: {url_str}")
                                        urls_valid += 1
                                    else:
                                        st.caption(f"⚠️ Row {idx}: {url_str} (missing http/https)")
                                        urls_valid += 1
                                else:
                                    st.caption(f"❌ Row {idx}: Empty or invalid")
                                    urls_empty += 1

                            # Count total URLs in entire dataset
                            all_urls = processed_df[url_column].dropna()
                            total_urls_found = len([url for url in all_urls if str(url).strip()])
                            total_urls_missing = valid_rows - total_urls_found

                            if total_urls_missing > 0:
                                st.warning(f"⚠️ {total_urls_missing} out of {valid_rows} rows have missing URLs. These will use Excel data only.")

                            # Store URL column for later use
                            st.session_state[f"batch_url_column_{st.session_state.form_counter}"] = url_column
                        else:
                            # Clear the URL column selection if "None" is selected
                            url_column_key = f"batch_url_column_{st.session_state.form_counter}"
                            if url_column_key in st.session_state:
                                del st.session_state[url_column_key]

                        # Skip row selection in batch mode
                        selected_excel_rows = []
                    else:
                        # Normal mode: show row selection
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
                if "processed_excel_df" in st.session_state:
                    del st.session_state["processed_excel_df"]
                if "excel_header_row" in st.session_state:
                    del st.session_state["excel_header_row"]

        return selected_excel_rows

    def _render_excel_row_selection(self):
        """IMPROVEMENT #3: Excel row selection with multi-select widget"""
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

        # Initialize selected rows in session state if not present
        if "excel_rows_selected" not in st.session_state:
            st.session_state.excel_rows_selected = []

        st.write(f"**📋 Select Rows to Process** ({num_rows} available)")

        # Quick action buttons row
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)

        with action_col1:
            if st.button(
                "☑️ Select All",
                key=f"excel_select_all_{st.session_state.form_counter}",
                use_container_width=True,
            ):
                st.session_state.excel_rows_selected = list(range(num_rows))
                st.rerun()

        with action_col2:
            if st.button(
                "⬜ Clear All",
                key=f"excel_clear_all_{st.session_state.form_counter}",
                use_container_width=True,
            ):
                st.session_state.excel_rows_selected = []
                st.rerun()

        with action_col3:
            if st.button(
                "🔄 Invert",
                key=f"excel_invert_{st.session_state.form_counter}",
                use_container_width=True,
                help="Invert selection",
            ):
                all_rows = set(range(num_rows))
                current_selection = set(st.session_state.excel_rows_selected)
                st.session_state.excel_rows_selected = list(all_rows - current_selection)
                st.rerun()

        with action_col4:
            selected_count = len(st.session_state.excel_rows_selected)
            st.metric("Selected", selected_count, delta=None)

        # Multi-select widget
        try:
            # Get first column name for preview
            first_col = processed_df.columns[0] if len(processed_df.columns) > 0 else None

            selected_rows = st.multiselect(
                "Select rows (click to add/remove):",
                options=list(range(num_rows)),
                default=st.session_state.excel_rows_selected,
                format_func=lambda x: (
                    f"Row {x}: {str(processed_df.iloc[x][first_col])[:50]}"
                    if first_col
                    else f"Row {x}"
                ),
                key=f"excel_row_multiselect_{st.session_state.form_counter}",
                help="Use dropdown or quick action buttons above to select rows",
            )

            # Update session state
            st.session_state.excel_rows_selected = selected_rows

            # Show live preview of selected rows
            if selected_rows:
                st.write(f"**Preview of selected rows** (showing first 5 of {len(selected_rows)}):")
                preview_rows = selected_rows[:5]
                preview_df = processed_df.iloc[preview_rows]
                st.dataframe(preview_df, use_container_width=True, height=200)

                if len(selected_rows) > 5:
                    st.caption(f"... and {len(selected_rows) - 5} more rows")
            else:
                st.info("👆 Use the dropdown or quick action buttons to select rows")

            return selected_rows

        except Exception as e:
            st.error(f"❌ Error in row selection: {str(e)}")
            return []

    def _render_website_section(self):
        """Render website URL input section with optional batch mode"""
        st.write("**🌐 Website Source**")

        # Add batch mode toggle
        website_batch_mode = st.checkbox(
            "Batch Mode: Each URL = 1 product",
            value=False,
            help="Create one product configuration per URL (separate extractions). Paste one URL per line.",
            key=f"website_batch_mode_{st.session_state.form_counter}"
        )

        website_url = None

        if website_batch_mode:
            # Batch mode: Text area with one URL per line
            website_urls_text = st.text_area(
                "Website URLs (one per line)",
                placeholder="https://example.com/product1\nhttps://example.com/product2\nhttps://example.com/product3",
                height=150,
                help="Enter one website URL per line. Each URL will be processed as a separate product.",
                key=f"website_urls_batch_{st.session_state.form_counter}"
            )

            # Parse and validate URLs
            if website_urls_text and website_urls_text.strip():
                from processors.web_processor import validate_urls

                # Split by newlines and filter empty lines
                raw_urls = [line.strip() for line in website_urls_text.split('\n') if line.strip()]

                # Validate URLs
                valid_urls, invalid_urls = [], []
                for url in raw_urls:
                    try:
                        is_valid, cleaned_urls, error_msg = validate_urls(url)
                        if is_valid and cleaned_urls:
                            valid_urls.extend(cleaned_urls)  # Extend with URL list only
                        else:
                            invalid_urls.append(url)
                    except Exception:
                        invalid_urls.append(url)

                # Store valid URLs count in session state
                st.session_state[f"batch_website_count_{st.session_state.form_counter}"] = len(valid_urls)
                st.session_state[f"batch_website_urls_{st.session_state.form_counter}"] = valid_urls

                # Show preview
                if valid_urls:
                    from config import MAX_WEBSITE_BATCH_SIZE

                    if len(valid_urls) > MAX_WEBSITE_BATCH_SIZE:
                        st.error(f"❌ Maximum {MAX_WEBSITE_BATCH_SIZE} URLs per batch. You have {len(valid_urls)} URLs. Please reduce the number.")
                    else:
                        st.info(f"✨ **Batch Mode Active:** Creating {len(valid_urls)} product configurations")

                        # Show preview of first 3 URLs
                        st.write("**Preview (first 3 URLs):**")
                        for i, url in enumerate(valid_urls[:3], 1):
                            st.caption(f"{i}. {url}")

                        if len(valid_urls) > 3:
                            st.caption(f"... and {len(valid_urls) - 3} more URLs")

                # Show invalid URLs warning
                if invalid_urls:
                    st.warning(f"⚠️ {len(invalid_urls)} invalid URLs will be skipped")
                    with st.expander("Show invalid URLs"):
                        for url in invalid_urls:
                            st.caption(f"❌ {url}")

            # Return None for batch mode (handled separately in submission)
            return None

        else:
            # Normal mode: Comma-separated URLs (existing behavior)
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
        """Handle form submission with batch mode support"""

        # Check if batch mode is active
        batch_mode_key = f"excel_batch_mode_{st.session_state.form_counter}"
        is_batch_mode = st.session_state.get(batch_mode_key, False)

        # Check if website batch mode is active
        website_batch_mode_key = f"website_batch_mode_{st.session_state.form_counter}"
        is_website_batch_mode = st.session_state.get(website_batch_mode_key, False)

        if is_website_batch_mode:
            # ========== WEBSITE BATCH MODE HANDLING ==========

            # Get valid URLs count
            valid_urls_count = st.session_state.get(f"batch_website_count_{st.session_state.form_counter}", 0)

            if valid_urls_count == 0:
                st.error("❌ No valid URLs to process. Please enter at least one valid URL.")
                return

            # Validate: no PDF or Excel sources in website batch mode
            has_pdf = st.session_state.current_pdf_file and selected_pdf_pages
            has_excel = st.session_state.current_excel_file and selected_excel_rows

            if has_pdf:
                st.error("❌ Website batch mode does not support PDF sources. Please remove PDF or disable batch mode.")
                return

            if has_excel:
                st.error("❌ Website batch mode does not support Excel sources. Please remove Excel or disable batch mode.")
                return

            # Validate base_product for subtype
            if product_type == "subtype" and not base_product.strip():
                st.error("❌ Please enter a base product for subtype classification.")
                return

            # Execute website batch mode
            self._create_website_batch_configurations(
                product_type=product_type,
                base_product=base_product
            )
            return  # Early return after batch processing

        if is_batch_mode:
            # ========== BATCH MODE HANDLING ==========

            # Validate: max 500 rows
            valid_rows_key = f"batch_valid_rows_{st.session_state.form_counter}"
            valid_rows = st.session_state.get(valid_rows_key, 0)

            if valid_rows > 500:
                st.error("❌ Cannot create more than 500 products in batch mode. Please split your file.")
                return

            if valid_rows == 0:
                st.error("❌ No valid rows to process. Please check your Excel file.")
                return

            # Validate: no PDF sources (websites are allowed via URL column)
            has_pdf = st.session_state.current_pdf_file and selected_pdf_pages

            if has_pdf:
                st.error("❌ Batch mode does not support PDF sources. Please remove PDF or disable batch mode.")
                return

            # Note: Website sources are now supported via URL column selection
            # Manual website_url input is still not compatible with batch mode
            has_manual_website = website_url and website_url.strip()
            if has_manual_website:
                st.warning("⚠️ Manual website URL will be ignored in batch mode. Use the URL column feature instead.")
                website_url = ""  # Clear it to avoid confusion

            # Validate base_product for subtype
            if product_type == "subtype" and not base_product.strip():
                st.error("❌ Please enter a base product for subtype classification.")
                return

            # Execute batch mode
            self._create_batch_configurations(
                product_type=product_type,
                base_product=base_product
            )
            return  # Early return after batch processing

        # ========== NORMAL MODE HANDLING ==========

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

        # Clear Excel-related session state
        if "processed_excel_df" in st.session_state:
            del st.session_state["processed_excel_df"]
        if "excel_header_row" in st.session_state:
            del st.session_state["excel_header_row"]

        # Don't clear product_type_selector and base_product_input
        # so user can easily add multiple products of the same type

        # Mark draft as completed
        self.draft_manager.mark_draft_completed()

    # ========== IMPROVEMENT #4: Unified Preview ==========

    def _render_unified_preview(
        self, website_url: str, selected_pdf_pages: list, selected_excel_rows: list
    ):
        """
        Show unified preview with batch mode support

        Args:
            website_url: Website URL string
            selected_pdf_pages: List of selected PDF page indices
            selected_excel_rows: List of selected Excel row indices
        """
        # Check if batch mode is active
        batch_mode_key = f"excel_batch_mode_{st.session_state.form_counter}"
        is_batch_mode = st.session_state.get(batch_mode_key, False)

        # Check if any sources selected
        has_pdf = st.session_state.current_pdf_file and selected_pdf_pages
        has_website = website_url and website_url.strip()

        # In batch mode, has_excel check is different
        if is_batch_mode:
            has_excel = (
                st.session_state.current_excel_file
                and st.session_state.processed_excel_df is not None
            )
        else:
            has_excel = st.session_state.current_excel_file and selected_excel_rows

        if not (has_pdf or has_excel or has_website):
            return  # Nothing to preview

        st.markdown("---")
        st.subheader("📋 Configuration Summary")

        # Summary metrics row
        col1, col2, col3 = st.columns(3)

        with col1:
            if has_pdf:
                st.metric(
                    label="PDF Source",
                    value=f"{len(selected_pdf_pages)} pages",
                    delta=st.session_state.current_pdf_file.name,
                )
            else:
                st.metric(label="PDF Source", value="None", delta="Not selected")

        with col2:
            if has_excel:
                if is_batch_mode:
                    # Show batch mode count
                    valid_rows_key = f"batch_valid_rows_{st.session_state.form_counter}"
                    valid_rows = st.session_state.get(valid_rows_key, 0)
                    st.metric(
                        label="Excel Source (Batch)",
                        value=f"{valid_rows} products",
                        delta=st.session_state.current_excel_file.name,
                    )
                else:
                    # Normal mode
                    st.metric(
                        label="Excel Source",
                        value=f"{len(selected_excel_rows)} rows",
                        delta=st.session_state.current_excel_file.name,
                    )
            else:
                st.metric(label="Excel Source", value="None", delta="Not selected")

        with col3:
            if has_website:
                url_count = len(
                    [u.strip() for u in website_url.split(",") if u.strip()]
                )
                st.metric(
                    label="Website Source", value=f"{url_count} URL(s)", delta="Web scraping"
                )
            else:
                st.metric(label="Website Source", value="None", delta="Not selected")

        # Show batch mode alert
        if is_batch_mode and has_excel:
            valid_rows_key = f"batch_valid_rows_{st.session_state.form_counter}"
            valid_rows = st.session_state.get(valid_rows_key, 0)

            # Check if URL column is enabled
            url_column_key = f"batch_url_column_{st.session_state.form_counter}"
            url_column = st.session_state.get(url_column_key, None)

            info_text = f"""
📦 **Batch Mode Active**
- Each row will create 1 separate product configuration
- Total configurations to create: **{valid_rows}**
- Empty rows will be automatically skipped
"""
            if url_column:
                info_text += f"- Website URLs will be scraped from column: **{url_column}**\n"

            st.info(info_text)

            # Show warning if mixing with PDF (websites via column are now allowed)
            if has_pdf:
                st.error("❌ **Batch mode does not support PDF sources.** Please remove PDF or disable batch mode.")

        # Tabbed preview (only if multiple sources)
        tab_labels = []
        if has_pdf:
            tab_labels.append("📄 PDF Preview")
        if has_excel:
            tab_labels.append("📊 Excel Preview")
        if has_website:
            tab_labels.append("🌐 Website Preview")

        if len(tab_labels) > 1:
            tabs = st.tabs(tab_labels)
            tab_idx = 0

            if has_pdf:
                with tabs[tab_idx]:
                    page_nums = [p + 1 for p in selected_pdf_pages[:10]]
                    st.write(f"**Selected pages:** {', '.join(str(p) for p in page_nums)}")
                    if len(selected_pdf_pages) > 10:
                        st.caption(f"... and {len(selected_pdf_pages)-10} more pages")
                    st.caption(f"📄 File: {st.session_state.current_pdf_file.name}")
                tab_idx += 1

            if has_excel:
                with tabs[tab_idx]:
                    processed_df = st.session_state.processed_excel_df
                    preview_df = processed_df.iloc[selected_excel_rows[:5]]
                    st.dataframe(preview_df, use_container_width=True)
                    if len(selected_excel_rows) > 5:
                        st.caption(f"... and {len(selected_excel_rows)-5} more rows")
                    st.caption(f"📊 File: {st.session_state.current_excel_file.name}")
                tab_idx += 1

            if has_website:
                with tabs[tab_idx]:
                    urls = [u.strip() for u in website_url.split(",") if u.strip()]
                    for i, url in enumerate(urls[:5], 1):
                        st.write(f"{i}. {url}")
                    if len(urls) > 5:
                        st.caption(f"... and {len(urls)-5} more URLs")

    # ========== IMPROVEMENT #1: Draft Management ==========

    def _trigger_auto_save(self):
        """Trigger auto-save of current form state"""
        form_data = self.draft_manager.get_current_form_data_snapshot()
        self.draft_manager.auto_save_draft(form_data)

    def _restore_draft_data(self, draft_data: dict):
        """
        Restore form state from draft data

        Args:
            draft_data: Dictionary containing saved form state
        """
        # Note: This is a simplified restore - full implementation would need to
        # reconstruct file objects which is complex in Streamlit.
        # For now, we just show a message with what was saved.

        st.info(
            f"""
            **Draft contains:**
            - Product Type: {draft_data.get('product_type', 'N/A')}
            - PDF: {draft_data.get('pdf_file_name', 'None')} ({len(draft_data.get('pdf_pages', []))} pages)
            - Excel: {draft_data.get('excel_file_name', 'None')} ({len(draft_data.get('excel_rows', []))} rows)
            - Website: {draft_data.get('website_url', 'None')}

            Please re-upload files to continue with this configuration.
            """
        )

    # ========== NEW FEATURE: Batch Mode ==========

    def _create_batch_configurations(self, product_type: str, base_product: str):
        """
        Create multiple ProductConfig objects, one per row in Excel (Batch Mode)

        Args:
            product_type: Product type (cosmetics/fragrance/subtype)
            base_product: Base product name (for subtype only)
        """

        if not st.session_state.current_excel_file or st.session_state.processed_excel_df is None:
            st.error("❌ No Excel file processed.")
            return

        processed_df = st.session_state.processed_excel_df

        # Filter out empty rows (all NaN)
        non_empty_df = processed_df.dropna(how='all')
        total_rows = len(processed_df)
        valid_rows = len(non_empty_df)
        empty_rows_skipped = total_rows - valid_rows

        # Get model configuration (hidden from user)
        model_provider = config.DEFAULT_PROVIDER
        if model_provider == "groq":
            model_name = config.DEFAULT_GROQ_MODEL
        else:
            model_name = config.DEFAULT_OPENAI_MODEL
        temperature = config.DEFAULT_TEMPERATURE

        # Clean base product for subtype
        clean_base_product = ""
        if base_product:
            clean_base_product = base_product.strip().lower().replace(" ", "").replace("-", "")

        # Get header row used
        excel_header_row = st.session_state.get("excel_header_row", 0)

        # Check if URL column is enabled for batch mode
        url_column_key = f"batch_url_column_{st.session_state.form_counter}"
        url_column = st.session_state.get(url_column_key, None)

        # Create configurations with progress indicator
        with st.spinner(f"Creating {valid_rows} product configurations..."):
            configs_created = 0
            urls_found = 0
            urls_missing = 0
            urls_invalid = 0

            # Use original indices from processed_df for row numbers
            for original_idx in non_empty_df.index:
                try:
                    # Extract website URL from the row if column is specified
                    website_url = None
                    if url_column and url_column in processed_df.columns:
                        url_value = processed_df.loc[original_idx, url_column]
                        if pd.notna(url_value) and str(url_value).strip():
                            website_url = str(url_value).strip()
                            # Add http:// if missing
                            if not website_url.startswith(('http://', 'https://')):
                                website_url = 'https://' + website_url
                            urls_found += 1
                        else:
                            urls_missing += 1

                    # Create config for single row
                    new_config = ProductConfig(
                        product_type=product_type,
                        base_product=clean_base_product,
                        pdf_file=None,
                        pdf_pages=[],
                        excel_file=st.session_state.current_excel_file,
                        excel_rows=[original_idx],  # Single row
                        excel_header_row=excel_header_row,
                        website_url=website_url,  # Now includes URL from column!
                        model_provider=model_provider,
                        model_name=model_name,
                        temperature=temperature,
                        custom_instructions="",
                    )

                    # Add to configurations
                    add_product_config(new_config)
                    configs_created += 1

                except Exception as e:
                    st.warning(f"⚠️ Failed to create config for row {original_idx}: {str(e)}")
                    continue

        # Success message
        if empty_rows_skipped > 0:
            success_msg = f"✅ Created {configs_created} product configurations in batch mode! ({empty_rows_skipped} empty rows skipped)"
        else:
            success_msg = f"✅ Created {configs_created} product configurations in batch mode!"

        # Add details
        success_msg += f"\n\n**Source:** {st.session_state.current_excel_file.name}"
        success_msg += f"\n**Product Type:** {product_type}"
        if product_type == "subtype" and clean_base_product:
            success_msg += f"\n**Base Product:** {clean_base_product}"

        # Add URL statistics if URL column was used
        if url_column:
            success_msg += f"\n\n**🔗 Website URLs:**"
            success_msg += f"\n  • Column: {url_column}"
            success_msg += f"\n  • Found: {urls_found}"
            if urls_missing > 0:
                success_msg += f"\n  • Missing: {urls_missing} (will use Excel data only)"

        st.success(success_msg)

        # Clear form data
        self._clear_form_data()

        # Rerun to refresh the UI
        st.rerun()

    def _create_website_batch_configurations(self, product_type: str, base_product: str):
        """
        Create multiple ProductConfig objects, one per URL (Website Batch Mode)

        Args:
            product_type: Product type (cosmetics/fragrance/subtype/supplement/tech)
            base_product: Base product name (for subtype only)
        """
        from config import MAX_WEBSITE_BATCH_SIZE

        # Get valid URLs from session state
        valid_urls = st.session_state.get(f"batch_website_urls_{st.session_state.form_counter}", [])

        if not valid_urls:
            st.error("❌ No valid URLs found.")
            return

        # Check maximum limit
        if len(valid_urls) > MAX_WEBSITE_BATCH_SIZE:
            st.error(f"❌ Maximum {MAX_WEBSITE_BATCH_SIZE} URLs per batch. You have {len(valid_urls)} URLs.")
            return

        # Get model configuration (hidden from user)
        model_provider = config.DEFAULT_PROVIDER
        if model_provider == "groq":
            model_name = config.DEFAULT_GROQ_MODEL
        else:
            model_name = config.DEFAULT_OPENAI_MODEL
        temperature = config.DEFAULT_TEMPERATURE

        # Clean base product for subtype
        clean_base_product = ""
        if base_product:
            clean_base_product = base_product.strip().lower().replace(" ", "").replace("-", "")

        # Create configurations with progress indicator
        with st.spinner(f"Creating {len(valid_urls)} product configurations..."):
            configs_created = 0

            for url in valid_urls:
                try:
                    # Create ProductConfig for this URL
                    new_config = ProductConfig(
                        product_type=product_type,
                        base_product=clean_base_product,
                        pdf_file=None,
                        pdf_pages=[],
                        excel_file=None,
                        excel_rows=[],
                        excel_header_row=0,
                        website_url=url,  # Single URL per config
                        model_provider=model_provider,
                        model_name=model_name,
                        temperature=temperature,
                        custom_instructions="",
                    )

                    # Add to product configurations
                    add_product_config(new_config)
                    configs_created += 1

                except Exception as e:
                    st.error(f"Error creating configuration for URL {url}: {e}")
                    continue

        # Show success message
        if configs_created > 0:
            st.success(
                f"✅ Successfully created {configs_created} product configuration(s) from website URLs!"
            )

            # Show summary
            st.info(
                f"""
                **Batch Processing Summary:**
                - Total URLs: {len(valid_urls)}
                - Configurations created: {configs_created}
                - Product type: {product_type}
                - Model: {model_name}
                - Temperature: {temperature}

                **Next Step:** Go to the "Execute Batch" tab to process these configurations.
                """
            )

        # Clear form data
        self._clear_form_data()

        # Rerun to refresh the UI
        st.rerun()
