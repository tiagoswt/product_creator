"""
Draft Manager for Configuration Form
Auto-saves user configuration drafts and provides recovery mechanisms
"""

import streamlit as st
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class DraftManager:
    """Manages configuration drafts with auto-save and recovery"""

    DRAFT_EXPIRY_HOURS = 24  # Drafts older than this are auto-deleted

    def __init__(self):
        """Initialize draft manager and ensure session state is set up"""
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize draft-related session state variables"""
        if "configuration_drafts" not in st.session_state:
            st.session_state.configuration_drafts = []
        if "current_draft_id" not in st.session_state:
            st.session_state.current_draft_id = None
        if "last_auto_save" not in st.session_state:
            st.session_state.last_auto_save = None

    def auto_save_draft(self, form_data: Dict[str, Any]):
        """
        Auto-save current configuration draft

        Args:
            form_data: Dictionary containing current form state
                Expected keys: product_type, base_product, pdf_file_name, pdf_pages,
                              excel_file_name, excel_rows, excel_header_row, website_url
        """
        # Check if there's actual data to save
        if not self._has_meaningful_data(form_data):
            return

        # Get or create draft ID
        draft_id = st.session_state.current_draft_id
        if not draft_id:
            draft_id = str(uuid.uuid4())
            st.session_state.current_draft_id = draft_id

        # Create draft object
        draft = {
            "id": draft_id,
            "timestamp": datetime.now(),
            "form_data": form_data.copy(),
            "completed": False,
        }

        # Update or create draft
        existing_idx = self._find_draft_index(draft_id)
        if existing_idx is not None:
            # Update existing draft
            st.session_state.configuration_drafts[existing_idx] = draft
        else:
            # Create new draft
            st.session_state.configuration_drafts.append(draft)

        # Update last save timestamp
        st.session_state.last_auto_save = datetime.now()

        # Clean up old drafts
        self._cleanup_old_drafts()

    def _has_meaningful_data(self, form_data: Dict[str, Any]) -> bool:
        """Check if form data contains meaningful user input"""
        # Check if any data source is selected
        has_pdf = form_data.get("pdf_file_name") and form_data.get("pdf_pages")
        has_excel = form_data.get("excel_file_name") and form_data.get("excel_rows")
        has_website = (
            form_data.get("website_url") and form_data.get("website_url").strip()
        )

        return has_pdf or has_excel or has_website

    def _find_draft_index(self, draft_id: str) -> Optional[int]:
        """Find the index of a draft by ID"""
        for idx, draft in enumerate(st.session_state.configuration_drafts):
            if draft["id"] == draft_id:
                return idx
        return None

    def load_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a saved draft by ID

        Args:
            draft_id: UUID of the draft to load

        Returns:
            Form data dictionary or None if not found
        """
        draft_idx = self._find_draft_index(draft_id)
        if draft_idx is not None:
            draft = st.session_state.configuration_drafts[draft_idx]
            # Set this as current draft
            st.session_state.current_draft_id = draft_id
            return draft["form_data"]
        return None

    def mark_draft_completed(self, draft_id: str = None):
        """
        Mark a draft as completed (no longer needs recovery)

        Args:
            draft_id: UUID of the draft. If None, uses current draft ID
        """
        if draft_id is None:
            draft_id = st.session_state.current_draft_id

        if draft_id:
            draft_idx = self._find_draft_index(draft_id)
            if draft_idx is not None:
                st.session_state.configuration_drafts[draft_idx]["completed"] = True

            # Clear current draft ID
            st.session_state.current_draft_id = None

    def delete_draft(self, draft_id: str):
        """
        Delete a specific draft

        Args:
            draft_id: UUID of the draft to delete
        """
        st.session_state.configuration_drafts = [
            draft
            for draft in st.session_state.configuration_drafts
            if draft["id"] != draft_id
        ]

        # Clear current draft ID if it was deleted
        if st.session_state.current_draft_id == draft_id:
            st.session_state.current_draft_id = None

    def get_recoverable_drafts(self) -> List[Dict[str, Any]]:
        """
        Get all incomplete drafts that can be recovered

        Returns:
            List of draft dictionaries
        """
        return [
            draft
            for draft in st.session_state.configuration_drafts
            if not draft.get("completed", False)
        ]

    def _cleanup_old_drafts(self):
        """Remove drafts older than DRAFT_EXPIRY_HOURS"""
        cutoff_time = datetime.now() - timedelta(hours=self.DRAFT_EXPIRY_HOURS)

        st.session_state.configuration_drafts = [
            draft
            for draft in st.session_state.configuration_drafts
            if draft["timestamp"] > cutoff_time
        ]

    def render_draft_recovery_banner(self) -> Optional[str]:
        """
        Render draft recovery banner at top of form

        Returns:
            draft_id if user clicked to recover a draft, None otherwise
        """
        recoverable_drafts = self.get_recoverable_drafts()

        if not recoverable_drafts:
            return None

        # Show recovery banner
        st.info(
            f"📝 **{len(recoverable_drafts)} unsaved draft(s) found.** "
            "You can recover your previous work below."
        )

        # Show drafts in expander
        with st.expander("🔄 Recover Draft", expanded=False):
            for draft in recoverable_drafts:
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    # Show draft summary
                    form_data = draft["form_data"]
                    summary_parts = []

                    if form_data.get("product_type"):
                        summary_parts.append(f"Type: {form_data['product_type']}")

                    if form_data.get("pdf_file_name"):
                        summary_parts.append(
                            f"PDF: {len(form_data.get('pdf_pages', []))} pages"
                        )

                    if form_data.get("excel_file_name"):
                        summary_parts.append(
                            f"Excel: {len(form_data.get('excel_rows', []))} rows"
                        )

                    if form_data.get("website_url"):
                        url_count = len(
                            [
                                u.strip()
                                for u in form_data["website_url"].split(",")
                                if u.strip()
                            ]
                        )
                        summary_parts.append(f"URLs: {url_count}")

                    summary = " | ".join(summary_parts) if summary_parts else "Empty"
                    st.write(f"**{summary}**")

                with col2:
                    # Show timestamp
                    time_ago = self._format_time_ago(draft["timestamp"])
                    st.caption(f"Saved: {time_ago}")

                with col3:
                    # Recover button
                    if st.button(
                        "Recover", key=f"recover_draft_{draft['id']}", type="primary"
                    ):
                        return draft["id"]

                # Delete button
                if st.button(
                    "🗑️ Delete", key=f"delete_draft_{draft['id']}", help="Delete this draft"
                ):
                    self.delete_draft(draft["id"])
                    st.rerun()

                st.markdown("---")

        return None

    def _format_time_ago(self, timestamp: datetime) -> str:
        """Format timestamp as 'X minutes/hours ago'"""
        diff = datetime.now() - timestamp

        if diff.seconds < 60:
            return "Just now"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff.days == 0:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"

    def get_current_form_data_snapshot(self) -> Dict[str, Any]:
        """
        Get current form data from session state for auto-save

        Returns:
            Dictionary with current form state
        """
        return {
            "product_type": st.session_state.get("product_type_selector", "cosmetics"),
            "base_product": st.session_state.get("base_product_input", ""),
            "pdf_file_name": (
                st.session_state.current_pdf_file.name
                if st.session_state.get("current_pdf_file")
                else None
            ),
            "pdf_pages": list(st.session_state.get("pdf_selected_pages", set())),
            "excel_file_name": (
                st.session_state.current_excel_file.name
                if st.session_state.get("current_excel_file")
                else None
            ),
            "excel_rows": st.session_state.get("excel_rows_selected", []),
            "excel_header_row": st.session_state.get("excel_header_row", 0),
            "website_url": st.session_state.get(
                f"website_url_input_{st.session_state.get('form_counter', 0)}", ""
            ),
        }


def create_draft_manager() -> DraftManager:
    """
    Factory function to create or get existing DraftManager instance

    Returns:
        DraftManager instance
    """
    return DraftManager()
