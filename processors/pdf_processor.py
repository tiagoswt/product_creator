import os
import tempfile
import streamlit as st
import fitz  # PyMuPDF
from langchain_community.document_loaders import PyPDFLoader
import config


def render_pdf_preview(pdf_file):
    """
    Render a preview of PDF pages

    Args:
        pdf_file: A PDF file object from Streamlit file uploader

    Returns:
        list: List of tuples containing (page_number, image_bytes) for each page
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(pdf_file.getvalue())
        tmp_path = tmp_file.name

    doc = fitz.open(tmp_path)
    pages = []

    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(
            matrix=fitz.Matrix(config.PDF_PREVIEW_SCALE, config.PDF_PREVIEW_SCALE)
        )
        img_bytes = pix.tobytes("png")
        pages.append((i, img_bytes))

    doc.close()
    os.unlink(tmp_path)  # Clean up the temp file

    return pages


def extract_pdf_data(pdf_file, pdf_pages):
    """
    Extract text data from PDF

    Args:
        pdf_file: A PDF file object from Streamlit file uploader
        pdf_pages (list): List of page numbers to extract

    Returns:
        str: Consolidated text from the PDF pages
    """
    if not pdf_file or not pdf_pages:
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(pdf_file.getvalue())
        tmp_path = tmp_file.name

    loader = PyPDFLoader(tmp_path)
    pages = loader.load()

    # Filter by selected pages
    selected_pages = [page for page in pages if page.metadata["page"] in pdf_pages]

    # Extract text from selected pages
    consolidated_text = []
    for page in selected_pages:
        consolidated_text.append(
            f"--- PDF PAGE {page.metadata['page'] + 1} CONTENT ---\n{page.page_content}"
        )

    os.unlink(tmp_path)  # Clean up the temp file

    # Return the consolidated text
    if consolidated_text:
        return "\n\n".join(consolidated_text)
    else:
        return None
