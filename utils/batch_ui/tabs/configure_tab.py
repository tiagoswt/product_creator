"""
Configure Products Tab - Product configuration management
"""

import streamlit as st
from utils.product_config import get_product_configs
from ..components.configuration_form import ConfigurationForm
from ..components.results_display import ResultsDisplay


def render_configure_tab():
    """Render the Configure Products tab"""
    st.subheader("Add New Product Configuration")

    # Initialize components
    results_display = ResultsDisplay()
    configuration_form = ConfigurationForm()

    # Render the configuration form first
    configuration_form.render()

    # Add a separator
    st.markdown("---")

    # Display existing configurations after the form
    st.subheader("Product Configurations")

    # Get existing configurations
    configs = get_product_configs()

    # Display existing configurations
    results_display.render_config_list(configs)
