import streamlit as st
import os
import json
import pandas as pd

# Load environment variables first - BEFORE other imports
from dotenv import load_dotenv

load_dotenv()  # This loads your .env file

from models.model_factory import get_llm
from utils.state_manager import initialize_state, reset_application
from utils.langsmith_utils import initialize_langsmith
from utils.dropbox_utils import get_dropbox_client, test_dropbox_connection
import config

# Update the import path to use the fixed version, with a direct import
# to ensure it's found correctly
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.batch_ui import render_batch_extraction_ui

# Check if Dropbox is available
try:
    import dropbox

    DROPBOX_AVAILABLE = True
    dropbox_token = os.getenv(config.ENV_DROPBOX_ACCESS_TOKEN)
    DROPBOX_CONFIGURED = bool(dropbox_token)
except ImportError:
    DROPBOX_AVAILABLE = False
    DROPBOX_CONFIGURED = False


def main():
    st.set_page_config(
        page_title="Sweetcare Product Content Creator",
        page_icon="💚",  # Changed to green heart to match Sweetcare branding
        layout="wide",
        initial_sidebar_state="collapsed",  # Changed from "expanded" to "collapsed"
    )

    # Custom header with Sweetcare logo
    col1, col2 = st.columns([1, 10])

    with col1:
        # Display Sweetcare logo
        try:
            st.image("sweetlogo.jpg", width=60)
        except:
            # Fallback to heart emoji if logo file not found
            st.markdown("💚", unsafe_allow_html=True)

    with col2:
        st.markdown("# Sweetcare Product Content Creator")

    # Initialize app state
    initialize_state()

    # Initialize LangSmith if possible and store status in session state
    if "langsmith_enabled" not in st.session_state:
        st.session_state.langsmith_enabled = initialize_langsmith()

    # Sidebar layout
    with st.sidebar:
        st.header("Configuration")

        # Show LangSmith status
        if st.session_state.langsmith_enabled:
            st.success("✅ LangSmith tracing enabled")

        # Show Dropbox status with enhanced information
        st.markdown("---")
        st.markdown("### Cloud Storage Integration")

        if DROPBOX_AVAILABLE:
            if DROPBOX_CONFIGURED:
                st.success("✅ Dropbox configured")
                st.caption("Access token loaded from environment")

                # Test connection button
                if st.button("🔗 Test Connection", key="sidebar_test_dropbox"):
                    with st.spinner("Testing Dropbox connection..."):
                        success = test_dropbox_connection()
                        if not success:
                            st.error("Connection failed. Check your access token.")
            else:
                st.warning("⚠️ Dropbox available but not configured")
                st.caption("Add DROPBOX_ACCESS_TOKEN to your .env file")

                # Show how to configure
                with st.expander("📖 How to configure Dropbox"):
                    st.markdown(
                        """
                    **Step 1:** Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
                    
                    **Step 2:** Create a new app with these settings:
                    - Choose "Scoped access"
                    - Choose "Full Dropbox" access
                    - Give your app a name
                    
                    **Step 3:** Generate an access token:
                    - Go to your app's settings
                    - Scroll to "OAuth 2" section
                    - Click "Generate access token"
                    
                    **Step 4:** Add to your .env file:
                    ```
                    DROPBOX_ACCESS_TOKEN=your_token_here
                    ```
                    """
                    )
        else:
            st.info("💡 Install 'dropbox' package for cloud upload")
            st.caption("Run: pip install dropbox>=12.0.0")

            with st.expander("📦 Installation Guide"):
                st.code("pip install dropbox>=12.0.0")
                st.markdown("After installation, restart the application.")

        # Removed the Product Type selection from sidebar

        st.markdown("---")
        st.markdown("### Data Sources")
        st.info("Select one or more data sources to extract product information.")

        st.markdown("---")
        st.markdown("### Application Management")

        # Reset application button
        if st.button(
            "🔄 Reset Application",
            help="Clear all cache and session data to start fresh",
            use_container_width=True,
        ):
            reset_application()
            # Set a flag to indicate that a reset was triggered
            st.session_state.reset_triggered = True
            st.rerun()

        # Clear products button
        if st.button(
            "🗑️ Clear Products",
            help="Remove all extracted products",
            use_container_width=True,
        ):
            if "product_configs" in st.session_state:
                st.session_state.product_configs = []
            if "products" in st.session_state:
                st.session_state.products = []
            st.success("All products cleared!")
            st.rerun()

        # Environment info
        st.markdown("---")
        st.markdown("### Environment Info")

        # Check API keys
        groq_key = os.getenv(config.ENV_GROQ_API_KEY) or st.session_state.get(
            config.STATE_GROQ_API_KEY
        )
        openai_key = os.getenv(config.ENV_OPENAI_API_KEY) or st.session_state.get(
            config.STATE_OPENAI_API_KEY
        )

        # API Keys status
        col1, col2 = st.columns(2)

        with col1:
            if groq_key:
                st.success("✅ Groq")
            else:
                st.error("❌ Groq")

        with col2:
            if openai_key:
                st.success("✅ OpenAI")
            else:
                st.error("❌ OpenAI")

        # Show model information
        st.caption(f"Default OpenAI: {config.DEFAULT_OPENAI_MODEL}")
        st.caption(f"HScode Model: {config.HSCODE_MODEL}")

    # Initialize LLM with default parameters (GPT-4o)
    llm = get_llm(provider="openai")
    if not llm:
        st.error(
            "❌ Unable to initialize the language model. Please check your API key."
        )

        # Show API key input if not configured
        if not openai_key:
            st.warning("**Missing OpenAI API Key**")
            st.info(
                """
            To use this application, you need to configure your OpenAI API key:
            
            **Option 1 (Recommended):** Add to your `.env` file:
            ```
            OPENAI_API_KEY=your_openai_api_key_here
            ```
            
            **Option 2:** The app will prompt you to enter it manually.
            """
            )

        st.stop()

    # Simplified main content area - removed welcome text and metrics
    # Always render batch processing UI directly
    render_batch_extraction_ui()


if __name__ == "__main__":
    main()
