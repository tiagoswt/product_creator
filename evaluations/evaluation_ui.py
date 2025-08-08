"""
Simple UI components for displaying evaluation results.
ENHANCED: Added 3-column AI reasoning display for better readability.
"""

import streamlit as st
from typing import Dict, Optional
from .evaluation_core import get_evaluation_for_config, store_human_feedback


def parse_evaluation_reasoning(llm_reasoning: str) -> dict:
    """
    Parse concatenated AI reasoning into separate metric components for evaluation UI.

    Args:
        llm_reasoning (str): Concatenated reasoning from all metrics

    Returns:
        dict: Separated reasoning for each metric
    """
    if not llm_reasoning or llm_reasoning.strip() == "":
        return {
            "structure": "No reasoning available",
            "content": "No reasoning available",
            "translation": "No reasoning available",
        }

    # Initialize with defaults
    parsed_reasoning = {
        "structure": "No specific reasoning provided",
        "content": "No specific reasoning provided",
        "translation": "No specific reasoning provided",
    }

    # Try to parse OpenEvals format: "metric_name: reasoning | metric_name: reasoning"
    if " | " in llm_reasoning:
        parts = llm_reasoning.split(" | ")
        for part in parts:
            if ":" in part:
                metric_part, reasoning_part = part.split(":", 1)
                metric_part = metric_part.strip().lower()
                reasoning_part = reasoning_part.strip()

                # Map different metric naming conventions
                if "structure" in metric_part:
                    parsed_reasoning["structure"] = reasoning_part
                elif "content" in metric_part or "accuracy" in metric_part:
                    parsed_reasoning["content"] = reasoning_part
                elif "translation" in metric_part or "completeness" in metric_part:
                    parsed_reasoning["translation"] = reasoning_part

    # Single reasoning fallback
    else:
        # Use the full reasoning for all metrics if we can't parse it
        parsed_reasoning = {
            "structure": llm_reasoning,
            "content": llm_reasoning,
            "translation": llm_reasoning,
        }

    return parsed_reasoning


def render_enhanced_reasoning_display(llm_reasoning: str, unique_key: str):
    """
    Render AI reasoning in 3 separate columns for evaluation UI.

    Args:
        llm_reasoning (str): The concatenated AI reasoning
        unique_key (str): Unique key for Streamlit components
    """
    st.markdown("**🤔 AI Assessment Reasoning**")

    # Parse the reasoning into components
    parsed_reasoning = parse_evaluation_reasoning(llm_reasoning)

    # Display in 3 columns with evaluation-specific styling
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🏗️ Structure Assessment**")
        st.caption("*JSON structure and schema compliance*")
        with st.container():
            st.text_area(
                "Structure Reasoning",
                value=parsed_reasoning["structure"],
                height=100,
                key=f"eval_structure_{unique_key}",
                disabled=True,
                label_visibility="collapsed",
            )

    with col2:
        st.markdown("**📝 Content Assessment**")
        st.caption("*Accuracy vs input, hallucination detection*")
        with st.container():
            st.text_area(
                "Content Reasoning",
                value=parsed_reasoning["content"],
                height=100,
                key=f"eval_content_{unique_key}",
                disabled=True,
                label_visibility="collapsed",
            )

    with col3:
        st.markdown("**🌍 Translation Assessment**")
        st.caption("*Portuguese translation quality*")
        with st.container():
            st.text_area(
                "Translation Reasoning",
                value=parsed_reasoning["translation"],
                height=100,
                key=f"eval_translation_{unique_key}",
                disabled=True,
                label_visibility="collapsed",
            )


def render_quality_badge(evaluation: Dict) -> str:
    """Render a quality score badge based on overall score."""
    if not evaluation:
        return "⚪ Not Evaluated"

    overall_score = evaluation.get("overall_score", 0)

    if overall_score >= 4.0:
        return f"🟢 Quality: {overall_score}/5"
    elif overall_score >= 3.0:
        return f"🟡 Quality: {overall_score}/5"
    else:
        return f"🔴 Quality: {overall_score}/5"


def render_evaluation_details(config_id: str) -> None:
    """Render detailed evaluation information with enhanced reasoning display."""
    try:
        evaluation = get_evaluation_for_config(config_id)

        if not evaluation:
            st.info("🤖 No quality evaluation available for this product")
            return

        st.markdown("### 🧠 LLM Quality Assessment")

        # Show scores in columns
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Structure", f"{evaluation.get('structure_score', 0)}/5")

        with col2:
            st.metric("Accuracy", f"{evaluation.get('accuracy_score', 0)}/5")

        with col3:
            st.metric("Completeness", f"{evaluation.get('translation_score', 0)}/5")

        with col4:
            overall = evaluation.get("overall_score", 0)
            st.metric("Overall", f"{overall}/5", delta=_get_score_delta(overall))

        # ENHANCED: Show LLM reasoning in 3 columns if available
        reasoning = evaluation.get("llm_reasoning", "")
        if reasoning:
            with st.expander("🤔 AI Assessment Details", expanded=False):
                render_enhanced_reasoning_display(reasoning, f"detail_{config_id}")

        # Show evaluation metadata
        with st.expander("📋 Evaluation Details"):
            st.write(f"**Model Used:** {evaluation.get('evaluation_model', 'Unknown')}")
            st.write(f"**Evaluated:** {evaluation.get('created_at', 'Unknown')}")
            st.write(f"**Product Type:** {evaluation.get('product_type', 'Unknown')}")

        # Human feedback section
        _render_human_feedback_section(evaluation)

    except Exception as e:
        st.error(f"Error displaying evaluation details: {str(e)}")


def _get_score_delta(overall_score: float) -> Optional[str]:
    """Get delta indicator for overall score metric."""
    if overall_score >= 4.0:
        return "Excellent"
    elif overall_score >= 3.0:
        return "Good"
    elif overall_score >= 2.0:
        return "Fair"
    else:
        return "Poor"


def _render_human_feedback_section(evaluation: Dict):
    """Render human feedback collection interface."""
    st.markdown("---")
    st.markdown("### 👥 Human Feedback")

    evaluation_id = evaluation.get("id")
    if not evaluation_id:
        return

    # Check if feedback already exists
    feedback_key = f"feedback_given_{evaluation_id}"
    if st.session_state.get(feedback_key, False):
        st.success("✅ Thank you for your feedback!")
        return

    # Simple feedback form
    st.markdown("**How would you rate this extraction quality?**")

    human_rating = st.select_slider(
        "Your Rating",
        options=[1, 2, 3, 4, 5],
        value=3,
        format_func=lambda x: f"{x}/5 - {_get_rating_label(x)}",
        key=f"human_rating_{evaluation_id}",
    )

    feedback_notes = st.text_area(
        "Optional Notes",
        placeholder="Any specific observations about the extraction quality...",
        max_chars=100000,
        key=f"feedback_notes_{evaluation_id}",
    )

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button(f"Submit Feedback", key=f"submit_feedback_{evaluation_id}"):
            if store_human_feedback(evaluation_id, human_rating, feedback_notes):
                st.session_state[feedback_key] = True
                st.success(
                    "✅ Feedback saved! Thank you for helping improve our system."
                )
                st.rerun()
            else:
                st.error("❌ Failed to save feedback. Please try again.")

    with col2:
        st.caption("Your feedback helps improve our AI extraction quality")


def _get_rating_label(rating: int) -> str:
    """Get human-readable label for rating."""
    labels = {1: "Poor", 2: "Fair", 3: "Good", 4: "Very Good", 5: "Excellent"}
    return labels.get(rating, "Unknown")


def render_batch_quality_summary():
    """Render a summary of quality metrics for the current batch."""
    try:
        from .simple_db import get_db

        db = get_db()
        stats = db.get_evaluation_stats()

        if stats["total_evaluations"] == 0:
            return

        st.markdown("### 📊 Batch Quality Summary")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Evaluated", stats["total_evaluations"])

        with col2:
            st.metric("Average Score", f"{stats['average_score']}/5.0")

        with col3:
            st.metric(
                "High Quality",
                stats["high_quality_count"],
                help="Products scoring 4.0 or above",
            )

        with col4:
            st.metric(
                "Low Quality",
                stats["low_quality_count"],
                help="Products scoring below 3.0",
            )

        # Quality distribution bar
        if stats["total_evaluations"] > 0:
            high_pct = (stats["high_quality_count"] / stats["total_evaluations"]) * 100
            low_pct = (stats["low_quality_count"] / stats["total_evaluations"]) * 100
            med_pct = 100 - high_pct - low_pct

            st.markdown("**Quality Distribution:**")
            quality_data = {
                "High (4.0+)": high_pct,
                "Medium (3.0-3.9)": med_pct,
                "Low (<3.0)": low_pct,
            }

            st.bar_chart(quality_data)

    except Exception as e:
        st.warning(f"Could not display quality summary: {str(e)}")
