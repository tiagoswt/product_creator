"""
Tabs package for main UI sections
"""

from .configure_tab import render_configure_tab
from .execute_tab import render_execute_tab
from .reprocess_tab import render_reprocess_tab

__all__ = ["render_configure_tab", "render_execute_tab", "render_reprocess_tab"]
