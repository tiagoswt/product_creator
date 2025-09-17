import streamlit as st
import os
import sys
from langchain_community.document_loaders import WebBaseLoader
from urllib.parse import urlparse

# Ensure imports work correctly regardless of where the script is run from
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def validate_urls(website_urls):
    """
    Validate and clean up URLs

    Args:
        website_urls (str): Single URL or multiple URLs separated by commas

    Returns:
        tuple: (is_valid: bool, cleaned_urls: list, error_message: str)
    """
    if not website_urls:
        return False, [], "No URLs provided"

    url_list = [url.strip() for url in website_urls.split(",") if url.strip()]

    if not url_list:
        return False, [], "No valid URLs found"

    cleaned_urls = []
    invalid_urls = []

    for url in url_list:
        cleaned_url = clean_url(url)
        if is_valid_url(cleaned_url):
            cleaned_urls.append(cleaned_url)
        else:
            invalid_urls.append(url)

    if invalid_urls:
        error_msg = f"Invalid URLs found: {', '.join(invalid_urls)}"
        if cleaned_urls:
            return (
                True,
                cleaned_urls,
                f"Some URLs are invalid: {', '.join(invalid_urls)}",
            )
        else:
            return False, [], error_msg

    return True, cleaned_urls, ""


def clean_url(url):
    """Clean and normalize a URL"""
    url = url.strip()

    # Add https if no protocol is specified
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def is_valid_url(url):
    """Basic URL validation"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and "." in result.netloc
    except:
        return False


def get_url_preview(website_urls):
    """
    Get a preview of what URLs will be processed

    Args:
        website_urls (str): Single URL or multiple URLs separated by commas

    Returns:
        str: Formatted preview string
    """
    is_valid, cleaned_urls, error_msg = validate_urls(website_urls)

    if not is_valid:
        return f"❌ {error_msg}"

    if len(cleaned_urls) == 1:
        return f"✅ 1 URL ready: {cleaned_urls[0]}"
    else:
        preview = f"✅ {len(cleaned_urls)} URLs ready:\n"
        for i, url in enumerate(cleaned_urls[:3], 1):  # Show first 3 URLs
            preview += f"  {i}. {url}\n"

        if len(cleaned_urls) > 3:
            preview += f"  ... and {len(cleaned_urls) - 3} more"

        if error_msg:
            preview += f"\n⚠️ {error_msg}"

        return preview


def extract_website_data(website_url):
    """
    Extract text data from a website URL or multiple URLs

    Args:
        website_url (str): URL(s) of the website(s) to extract data from

    Returns:
        str: Consolidated text from the website(s)
    """
    if not website_url:
        return None

    # Handle multiple URLs separated by commas
    is_valid, cleaned_urls, error_msg = validate_urls(website_url)

    if not is_valid:
        st.error(f"Invalid URLs: {error_msg}")
        return None

    consolidated_website_text = ""

    for url in cleaned_urls:
        try:
            loader = WebBaseLoader(url)
            docs = loader.load()

            website_text = f"--- WEBSITE DATA FROM {url} ---\n"
            for doc in docs:
                website_text += doc.page_content + "\n"

            consolidated_website_text += website_text + "\n\n"

        except Exception as e:
            st.warning(f"Error loading website content from {url}: {e}")
            continue

    return consolidated_website_text if consolidated_website_text.strip() else None
