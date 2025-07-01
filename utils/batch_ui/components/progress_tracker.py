"""
Progress tracking component for batch operations
"""

import streamlit as st


class ProgressTracker:
    """Handles progress tracking and status display"""

    def __init__(self):
        self.progress_bar = None
        self.status_text = None

    def initialize(self):
        """Initialize progress tracking elements"""
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        return self.progress_bar, self.status_text

    def update(self, current, total, message=""):
        """Update progress and status"""
        if self.progress_bar and self.status_text:
            progress = current / total if total > 0 else 0
            self.progress_bar.progress(progress)
            if message:
                self.status_text.text(message)

    def complete(self, message="Complete!"):
        """Mark progress as complete"""
        if self.progress_bar and self.status_text:
            self.progress_bar.progress(1.0)
            self.status_text.text(message)

    def cleanup(self):
        """Clean up progress elements"""
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_text:
            self.status_text.empty()

    def render_metrics(self, total, completed, failed, pending):
        """Render progress metrics"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total", total)
        with col2:
            st.metric("Completed", completed, delta=None if completed == 0 else "✅")
        with col3:
            st.metric("Failed", failed, delta=None if failed == 0 else "❌")
        with col4:
            st.metric("Pending", pending, delta=None if pending == 0 else "⏳")

    def render_completion_summary(self, successful, failed, operation_name="operation"):
        """Render completion summary"""
        if failed > 0:
            st.warning(
                f"🔄 {operation_name.title()} completed: {successful} successful, {failed} failed"
            )
        else:
            st.success(
                f"🎉 {operation_name.title()} completed: All {successful} items processed successfully!"
            )

    def render_bulk_progress(self, current, total, item_name="item"):
        """Render progress for bulk operations"""
        progress_col1, progress_col2 = st.columns([3, 1])

        with progress_col1:
            progress_bar = st.progress(current / total if total > 0 else 0)

        with progress_col2:
            st.write(f"{current}/{total} {item_name}s")

        return progress_bar

    @staticmethod
    def render_processing_summary(configs):
        """Render summary of processing results"""
        if not configs:
            return

        # Count configurations by status
        total = len(configs)
        completed = sum(1 for config in configs if config.has_successful_attempt())
        failed = sum(1 for config in configs if config.status == "failed")
        pending = total - completed - failed

        # Show metrics
        ProgressTracker().render_metrics(total, completed, failed, pending)

        return total, completed, failed, pending
