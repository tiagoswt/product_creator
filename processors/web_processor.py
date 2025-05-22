import streamlit as st
import os
import sys
from langchain_community.document_loaders import WebBaseLoader

# Ensure imports work correctly regardless of where the script is run from
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def extract_website_data(website_url):
    """
    Extract text data from a website URL

    Args:
        website_url (str): URL of the website to extract data from

    Returns:
        str: Consolidated text from the website
    """
    if not website_url:
        return None

    try:
        loader = WebBaseLoader(website_url)
        docs = loader.load()

        website_text = f"--- WEBSITE DATA FROM {website_url} ---\n"
        for doc in docs:
            website_text += doc.page_content

        return website_text
    except Exception as e:
        st.error(f"Error loading website content: {e}")
        return None
