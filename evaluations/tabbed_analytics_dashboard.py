"""
PostgreSQL Analytics Dashboard - PHASE 3 MIGRATION COMPLETE
Comprehensive Tabbed Analytics Dashboard with PostgreSQL Backend
Run with: streamlit run tabbed_analytics_dashboard.py

MIGRATION CHANGES:
- Replaced SQLite with PostgreSQL connection using Streamlit patterns
- Updated all queries for PostgreSQL compatibility
- Added Streamlit caching for optimal performance
- Maintained all existing functionality

Implements 6-tab structure:
1. Executive Dashboard - High-level overview
2. Agreement Analysis - AI vs Human comparison
3. Model Performance - Technical comparison
4. Quality Deep Dive - 3-metric analysis
5. Investigation Tools - Search and filter
6. Reports & Export - Data export and reporting
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import json
import io
from datetime import datetime, timedelta

# FIXED: Add the missing import for get_db
from simple_db import get_db, run_cached_query

# Configuration
st.set_page_config(
    page_title="Quality Analytics Dashboard", page_icon="🔬", layout="wide"
)

# ================================
# POSTGRESQL CONNECTION (PHASE 3)
# ================================


@st.cache_resource
def get_postgres_connection():
    """Get cached PostgreSQL connection with no success messages."""
    try:
        connection_params = {
            **st.secrets["postgres"],
            "sslmode": "require",
            "connect_timeout": 10,
            "application_name": "enhanced_analytics_dashboard",
        }

        original_port = connection_params.get("port", "5432")
        if original_port == "5432":
            connection_params["port"] = "6543"
            try:
                conn = psycopg2.connect(
                    **connection_params, cursor_factory=RealDictCursor
                )
                with conn.cursor() as test_cur:
                    test_cur.execute("SELECT 1 as test")
                    test_cur.fetchone()
                return conn
            except (psycopg2.OperationalError, psycopg2.Error):
                pass

        connection_params["port"] = "5432"
        conn = psycopg2.connect(**connection_params, cursor_factory=RealDictCursor)
        with conn.cursor() as test_cur:
            test_cur.execute("SELECT 1 as test")
            test_cur.fetchone()
        return conn

    except psycopg2.OperationalError as e:
        st.error("❌ **PostgreSQL Connection Failed**")
        st.error(f"Error: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected database error: {str(e)}")
        st.stop()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def run_analytics_query(query: str, params: tuple = None):
    """Execute SELECT queries with caching for better performance."""
    conn = get_postgres_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            result = cur.fetchall()
            return [dict(row) for row in result] if result else []
    except Exception as e:
        st.error(f"Analytics query failed: {str(e)}")
        raise


def load_enhanced_evaluation_data():
    """
    Load evaluation data with brand, product name, input text, and JSON output.
    """
    try:
        # Load evaluations with all new fields
        evaluations_query = """
            SELECT 
                id, product_config_id, structure_score, accuracy_score, 
                translation_score, overall_score, evaluation_model,
                product_type, created_at, llm_reasoning,
                brand, product_name, input_text, extracted_json,
                CASE 
                    WHEN evaluation_model LIKE 'openevals%%' THEN 'OpenEvals'
                    WHEN evaluation_model LIKE 'fallback%%' THEN 'Fallback'
                    ELSE 'Legacy'
                END as evaluator_type
            FROM evaluations
            ORDER BY created_at DESC
        """

        evaluations_data = run_analytics_query(evaluations_query)
        evaluations_df = pd.DataFrame(evaluations_data)

        # Load human feedback with enhanced join
        feedback_query = """
            SELECT
                hf.evaluation_id, hf.human_rating, hf.notes,
                hf.created_at as feedback_date,
                hf.created_by_username as feedback_username, hf.created_by_name as feedback_user_name,
                hf.user_id as feedback_user_id,
                e.overall_score as llm_score, e.product_type, e.evaluation_model,
                e.brand, e.product_name
            FROM human_feedback hf
            JOIN evaluations e ON hf.evaluation_id = e.id
            ORDER BY hf.created_at DESC
        """

        feedback_data = run_analytics_query(feedback_query)
        feedback_df = pd.DataFrame(feedback_data)

        # Convert datetime columns and ensure proper data types if data exists
        if not evaluations_df.empty:
            evaluations_df["created_at"] = pd.to_datetime(evaluations_df["created_at"])
            # Ensure numeric columns are proper numeric types for plotly compatibility
            numeric_columns = [
                "structure_score",
                "accuracy_score",
                "translation_score",
                "overall_score",
            ]
            for col in numeric_columns:
                evaluations_df[col] = pd.to_numeric(
                    evaluations_df[col], errors="coerce"
                )

        if not feedback_df.empty:
            feedback_df["feedback_date"] = pd.to_datetime(feedback_df["feedback_date"])
            feedback_df["human_rating"] = pd.to_numeric(
                feedback_df["human_rating"], errors="coerce"
            )
            feedback_df["llm_score"] = pd.to_numeric(
                feedback_df["llm_score"], errors="coerce"
            )

        return evaluations_df, feedback_df

    except Exception as e:
        st.error(f"Error loading enhanced data from PostgreSQL: {str(e)}")
        return None, None


def parse_ai_reasoning_for_analytics(llm_reasoning: str) -> dict:
    """
    Parse concatenated AI reasoning into separate metric components for analytics display.

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

    # Try to parse fallback format or single reasoning
    elif any(
        keyword in llm_reasoning.lower()
        for keyword in ["structure", "content", "translation"]
    ):
        # Try to find individual metric reasoning within a longer text
        lines = llm_reasoning.split("\n")
        current_metric = None
        current_reasoning = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts a new metric section
            if line.lower().startswith("structure"):
                if current_metric and current_reasoning:
                    parsed_reasoning[current_metric] = " ".join(current_reasoning)
                current_metric = "structure"
                current_reasoning = (
                    [line.split(":", 1)[-1].strip()] if ":" in line else [line]
                )
            elif line.lower().startswith("content") or line.lower().startswith(
                "accuracy"
            ):
                if current_metric and current_reasoning:
                    parsed_reasoning[current_metric] = " ".join(current_reasoning)
                current_metric = "content"
                current_reasoning = (
                    [line.split(":", 1)[-1].strip()] if ":" in line else [line]
                )
            elif line.lower().startswith("translation") or line.lower().startswith(
                "completeness"
            ):
                if current_metric and current_reasoning:
                    parsed_reasoning[current_metric] = " ".join(current_reasoning)
                current_metric = "translation"
                current_reasoning = (
                    [line.split(":", 1)[-1].strip()] if ":" in line else [line]
                )
            else:
                # Continue current reasoning
                if current_metric:
                    current_reasoning.append(line)

        # Don't forget the last metric
        if current_metric and current_reasoning:
            parsed_reasoning[current_metric] = " ".join(current_reasoning)

    else:
        # Single reasoning block - use for all metrics
        parsed_reasoning = {
            "structure": llm_reasoning,
            "content": llm_reasoning,
            "translation": llm_reasoning,
        }

    return parsed_reasoning


def render_enhanced_ai_reasoning_analytics(llm_reasoning: str, unique_key: str):
    """
    Render AI reasoning in 3 separate columns for analytics dashboard.

    Args:
        llm_reasoning (str): The concatenated AI reasoning
        unique_key (str): Unique key for Streamlit components
    """
    st.markdown("**🤖 AI Assessment Reasoning**")

    # Parse the reasoning into components
    parsed_reasoning = parse_ai_reasoning_for_analytics(llm_reasoning)

    # Display in 3 columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🏗️ Structure**")
        st.caption("*JSON format and schema compliance*")
        st.text_area(
            "Structure",
            value=parsed_reasoning["structure"],
            height=100,
            key=f"analytics_structure_{unique_key}",
            disabled=True,
            label_visibility="collapsed",
        )

    with col2:
        st.markdown("**📝 Content**")
        st.caption("*Accuracy vs input, hallucination detection*")
        st.text_area(
            "Content",
            value=parsed_reasoning["content"],
            height=100,
            key=f"analytics_content_{unique_key}",
            disabled=True,
            label_visibility="collapsed",
        )

    with col3:
        st.markdown("**🌍 Translation**")
        st.caption("*Portuguese translation quality*")
        st.text_area(
            "Translation",
            value=parsed_reasoning["translation"],
            height=100,
            key=f"analytics_translation_{unique_key}",
            disabled=True,
            label_visibility="collapsed",
        )


# ================================
# TAB 1: EXECUTIVE DASHBOARD
# ================================


def render_executive_dashboard(evaluations_df, feedback_df):
    """Executive-level overview with key metrics and alerts."""
    st.header("📊 Executive Dashboard")
    st.markdown("**High-level quality metrics and key insights**")

    if evaluations_df.empty:
        st.warning("No evaluation data available.")
        return

    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_evals = len(evaluations_df)
        st.metric("Total Evaluations", total_evals)

    with col2:
        avg_quality = evaluations_df["overall_score"].mean()
        quality_trend = (
            "↗️" if avg_quality >= 4.0 else "➡️" if avg_quality >= 3.0 else "↘️"
        )
        st.metric("Avg Quality", f"{avg_quality:.2f}/5", delta=quality_trend)

    with col3:
        high_quality = len(evaluations_df[evaluations_df["overall_score"] >= 4.0])
        high_quality_pct = (high_quality / total_evals) * 100 if total_evals > 0 else 0
        st.metric(
            "High Quality", f"{high_quality_pct:.1f}%", delta=f"{high_quality} products"
        )

    with col4:
        human_feedback_count = len(feedback_df)
        feedback_coverage = (
            (human_feedback_count / total_evals) * 100 if total_evals > 0 else 0
        )
        st.metric(
            "Human Coverage",
            f"{feedback_coverage:.1f}%",
            delta=f"{human_feedback_count} reviews",
        )

    with col5:
        if not feedback_df.empty:
            # Calculate AI-Human agreement
            merged = feedback_df.merge(
                evaluations_df[["id", "overall_score"]],
                left_on="evaluation_id",
                right_on="id",
                how="inner",
            )
            if not merged.empty:
                agreement = len(
                    merged[abs(merged["overall_score"] - merged["human_rating"]) <= 1.0]
                )
                agreement_pct = (agreement / len(merged)) * 100
                agreement_status = (
                    "✅"
                    if agreement_pct >= 80
                    else "⚠️" if agreement_pct >= 60 else "❌"
                )
                st.metric(
                    "AI-Human Agreement",
                    f"{agreement_pct:.1f}%",
                    delta=agreement_status,
                )
            else:
                st.metric("AI-Human Agreement", "N/A")
        else:
            st.metric("AI-Human Agreement", "N/A")

    # Quality Trends
    st.subheader("📈 Quality Trends")

    col1, col2 = st.columns(2)

    with col1:
        # Daily quality trend (PostgreSQL-compatible date aggregation)
        daily_quality = (
            evaluations_df.groupby(evaluations_df["created_at"].dt.date)
            .agg({"overall_score": "mean", "id": "count"})
            .tail(30)
        )  # Last 30 days

        fig = px.line(
            x=daily_quality.index,
            y=daily_quality["overall_score"],
            title="Daily Average Quality (Last 30 Days)",
            labels={"x": "Date", "y": "Average Quality Score"},
        )
        fig.update_layout(yaxis_range=[1, 5])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Quality distribution
        quality_bins = pd.cut(
            evaluations_df["overall_score"],
            bins=[0, 2, 3, 4, 5],
            labels=["Poor (1-2)", "Fair (2-3)", "Good (3-4)", "Excellent (4-5)"],
        )
        quality_counts = quality_bins.value_counts()

        fig = px.pie(
            values=quality_counts.values,
            names=quality_counts.index,
            title="Quality Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Alerts and Action Items
    st.subheader("🚨 Alerts & Action Items")

    alerts = []

    # Low quality alert
    low_quality_count = len(evaluations_df[evaluations_df["overall_score"] < 3.0])
    if low_quality_count > 0:
        alerts.append(
            {
                "type": "warning",
                "title": f"{low_quality_count} Low Quality Products",
                "message": f"{(low_quality_count/total_evals)*100:.1f}% of products scored below 3.0",
                "action": "Review extraction prompts and model configuration",
            }
        )

    # Agreement issues
    if not feedback_df.empty:
        merged = feedback_df.merge(
            evaluations_df[["id", "overall_score"]],
            left_on="evaluation_id",
            right_on="id",
            how="inner",
        )
        if not merged.empty:
            large_discrepancies = len(
                merged[abs(merged["overall_score"] - merged["human_rating"]) > 1.5]
            )
            if large_discrepancies > 0:
                alerts.append(
                    {
                        "type": "error",
                        "title": f"{large_discrepancies} Large AI-Human Discrepancies",
                        "message": "Significant disagreement between AI and human assessments",
                        "action": "Review discrepancy cases in Agreement Analysis tab",
                    }
                )

    # Model performance issues
    model_performance = evaluations_df.groupby("evaluator_type")["overall_score"].mean()
    if len(model_performance) > 1:
        worst_model = model_performance.idxmin()
        best_model = model_performance.idxmax()
        performance_gap = model_performance[best_model] - model_performance[worst_model]
        if performance_gap > 0.5:
            alerts.append(
                {
                    "type": "info",
                    "title": f"Model Performance Gap: {performance_gap:.1f} points",
                    "message": f"{best_model} ({model_performance[best_model]:.1f}) vs {worst_model} ({model_performance[worst_model]:.1f})",
                    "action": "Consider switching to better performing model",
                }
            )

    # Display alerts
    if alerts:
        for alert in alerts:
            if alert["type"] == "error":
                st.error(f"🚨 **{alert['title']}**: {alert['message']}")
            elif alert["type"] == "warning":
                st.warning(f"⚠️ **{alert['title']}**: {alert['message']}")
            else:
                st.info(f"💡 **{alert['title']}**: {alert['message']}")
            st.caption(f"**Action**: {alert['action']}")
    else:
        st.success("✅ **All systems healthy** - No critical issues detected")


# ================================
# TAB 2: AGREEMENT ANALYSIS
# ================================


def render_enhanced_agreement_analysis(evaluations_df, feedback_df):
    """ENHANCED: AI vs Human agreement analysis with brand, product name, input text, and JSON output."""
    st.header("🤖 vs 👥 Agreement Analysis")
    st.markdown("**Compare AI evaluations with human feedback**")

    if feedback_df.empty:
        st.info(
            "No human feedback available yet. Complete some human evaluations to see AI-Human comparisons!"
        )
        return

    # Merge AI and human data - load from database with full information
    merged_query = """
    SELECT 
        e.id, e.product_config_id, e.overall_score, e.structure_score, 
        e.accuracy_score, e.translation_score, e.product_type, 
        e.evaluation_model, e.llm_reasoning, e.brand, e.product_name,
        e.input_text, e.extracted_json, e.created_at,
        h.human_rating, h.notes, h.created_at as feedback_date
    FROM evaluations e
    JOIN human_feedback h ON e.id = h.evaluation_id
    ORDER BY e.created_at DESC
    """

    merged_data = run_cached_query(merged_query)
    merged_df = pd.DataFrame(merged_data)

    if merged_df.empty:
        st.warning("No matched AI-Human evaluation pairs found.")
        return

    # Parse JSON data
    for idx, row in merged_df.iterrows():
        if row.get("extracted_json"):
            try:
                merged_df.at[idx, "extracted_json"] = json.loads(row["extracted_json"])
            except:
                merged_df.at[idx, "extracted_json"] = {}

    merged_df["score_diff"] = abs(
        merged_df["overall_score"] - merged_df["human_rating"]
    )

    # Agreement Statistics
    st.subheader("📊 Agreement Statistics")

    col1, col2, col3, col4 = st.columns(4)

    total_comparisons = len(merged_df)
    excellent_agreement = len(merged_df[merged_df["score_diff"] <= 0.5])
    good_agreement = len(merged_df[merged_df["score_diff"] <= 1.0])
    poor_agreement = len(merged_df[merged_df["score_diff"] > 1.5])

    with col1:
        st.metric("Total Comparisons", total_comparisons)
    with col2:
        st.metric(
            "Excellent (±0.5)",
            f"{excellent_agreement} ({excellent_agreement/total_comparisons*100:.1f}%)",
        )
    with col3:
        st.metric(
            "Good (±1.0)",
            f"{good_agreement} ({good_agreement/total_comparisons*100:.1f}%)",
        )
    with col4:
        st.metric(
            "Poor (>1.5)",
            f"{poor_agreement} ({poor_agreement/total_comparisons*100:.1f}%)",
        )

    # ENHANCED: Large Discrepancies Analysis with full product information
    st.subheader("🔍 Large Discrepancies (>1.5 points) - ENHANCED VIEW")

    large_discrepancies = merged_df[merged_df["score_diff"] > 1.5].sort_values(
        "score_diff", ascending=False
    )

    if not large_discrepancies.empty:
        st.warning(f"Found {len(large_discrepancies)} cases requiring review")

        for idx, row in large_discrepancies.iterrows():
            # ENHANCED: Show brand and product name in the expander title
            expander_title = f"🔍 {row['brand']} - {row['product_name']} | AI={row['overall_score']:.1f}, Human={row['human_rating']}, Diff={row['score_diff']:.1f}"

            with st.expander(expander_title):
                # ENHANCED: Add product identification section
                st.markdown("### 🏷️ Product Information")
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Brand:** {row['brand']}")
                    st.write(f"**Product:** {row['product_name']}")
                    st.write(f"**Type:** {row['product_type']}")

                with col2:
                    st.write(f"**Evaluation ID:** {row['id']}")
                    st.write(f"**Config ID:** {row['product_config_id']}")
                    st.write(
                        f"**Date:** {row['created_at'].strftime('%Y-%m-%d %H:%M')}"
                    )

                # Scores comparison
                st.markdown("### 📊 Score Comparison")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**🤖 AI Assessment**")
                    st.write(f"Overall: {row['overall_score']:.1f}/5")
                    st.write(f"Structure: {row['structure_score']}/5")
                    st.write(f"Content: {row['accuracy_score']}/5")
                    st.write(f"Translation: {row['translation_score']}/5")
                    st.write(f"Model: {row['evaluation_model']}")

                with col2:
                    st.markdown("**👥 Human Assessment**")
                    st.write(f"Rating: {row['human_rating']}/5")
                    st.write(
                        f"Feedback Date: {row['feedback_date'].strftime('%Y-%m-%d')}"
                    )

                    # Show feedback provider name
                    feedback_user = (
                        row.get("feedback_user_name")
                        or row.get("feedback_username")
                        or "Unknown User"
                    )
                    if feedback_user and feedback_user != "System":
                        st.write(f"Feedback by: {feedback_user}")

                    if row["notes"]:
                        st.markdown("**Human Notes:**")
                        st.text_area(
                            "Human Notes",
                            value=row["notes"],
                            height=200,
                            key=f"human_notes_{idx}",
                            disabled=True,
                            label_visibility="collapsed",
                            max_chars=10000000,
                        )
                    else:
                        st.info("No human notes provided")

                # ENHANCED: Input Text Display
                st.markdown("### 📝 Input Text")
                if row.get("input_text"):
                    input_text = row["input_text"]
                    if len(input_text) > 1000:
                        st.text_area(
                            "Full Input Text",
                            value=input_text,
                            height=200,
                            key=f"input_text_{idx}",
                            disabled=True,
                            label_visibility="collapsed",
                        )
                    else:
                        st.text(input_text)
                else:
                    st.info("No input text available")

                # ENHANCED: JSON Output Display
                st.markdown("### 📋 Extracted JSON Output")
                if row.get("extracted_json") and isinstance(
                    row["extracted_json"], dict
                ):
                    st.json(row["extracted_json"])
                else:
                    st.info("No JSON output available")

                # AI Reasoning
                st.markdown("### 🤖 AI Reasoning")
                if row["llm_reasoning"]:
                    # Parse and display reasoning in 3 columns if it contains separators
                    if " | " in row["llm_reasoning"]:
                        reasoning_parts = row["llm_reasoning"].split(" | ")
                        col1, col2, col3 = st.columns(3)

                        for i, part in enumerate(reasoning_parts[:3]):
                            with [col1, col2, col3][i]:
                                if ":" in part:
                                    metric, reasoning = part.split(":", 1)
                                    st.markdown(f"**{metric.strip()}**")
                                    st.caption(reasoning.strip())
                                else:
                                    st.text(part)
                    else:
                        st.text_area(
                            "AI Reasoning",
                            value=row["llm_reasoning"],
                            height=100,
                            key=f"ai_reasoning_{idx}",
                            disabled=True,
                            label_visibility="collapsed",
                        )
                else:
                    st.info("No AI reasoning available")

    else:
        st.success("✅ No large discrepancies found - excellent AI-Human agreement!")


# ================================
# TAB 3: MODEL PERFORMANCE
# ================================


def render_production_model_performance(evaluations_df, feedback_df):
    """
    UPDATED: Production model performance analysis with radar chart.
    ADD the radar chart call to your existing function.
    """
    st.header("🏭 Production Model Performance")
    st.markdown(
        "**Analyze performance of LLMs that create product JSON (OpenAI vs Groq, different models, etc.)**"
    )

    if evaluations_df.empty:
        st.info("No evaluation data available.")
        return

    # Detect which production model tracking approach is available
    production_data = _load_production_model_performance_data()

    if production_data is None or production_data.empty:
        _render_production_model_setup_instructions()
        return

    # Success - we have production model data
    st.success(
        f"✅ Production model data available for {len(production_data)} evaluations"
    )

    # Display key metrics at the top
    _render_production_model_overview(production_data)

    # Create two columns for main analysis
    col1, col2 = st.columns(2)

    with col1:
        _render_provider_performance_comparison(production_data)
        _render_model_performance_table(production_data)

    with col2:
        _render_temperature_impact_analysis(production_data)
        _render_product_type_specialization(production_data)

    # ADD THIS LINE: Radar chart in full width
    st.markdown("---")
    _render_model_metrics_radar_chart(production_data)  # <-- ADD THIS LINE

    # Full width advanced analysis
    st.markdown("---")
    _render_advanced_model_analytics(production_data)

    # Insights and recommendations
    st.markdown("---")
    _render_model_performance_insights(production_data)


def _load_production_model_performance_data():
    """
    Load production model performance data using the appropriate method.
    FIXED: Better error handling to detect column existence properly.
    """
    try:
        # First, check if production_model_id column exists in evaluations table
        column_check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'evaluations' 
        AND column_name = 'production_model_id'
        """

        column_exists = False
        try:
            column_result = run_analytics_query(column_check_query)
            column_exists = len(column_result) > 0
        except Exception:
            column_exists = False

        if column_exists:
            # Try the direct column approach
            direct_query = """
            SELECT 
                e.id, e.overall_score, e.structure_score, e.accuracy_score, 
                e.translation_score, e.product_type, e.created_at, e.brand, e.product_name,
                pm.provider as production_model_provider,
                pm.model_name as production_model_name, 
                pm.temperature as production_temperature,
                CONCAT(pm.provider, '/', pm.model_name) as model_full_name
            FROM evaluations e
            JOIN production_models pm ON e.production_model_id = pm.id
            WHERE e.created_at >= CURRENT_DATE - INTERVAL '90 days'
            AND e.overall_score IS NOT NULL
            ORDER BY e.created_at DESC
            """

            try:
                direct_data = run_analytics_query(direct_query)
                if direct_data and len(direct_data) > 0:
                    df = pd.DataFrame(direct_data)
                    df["data_source"] = "direct_column"
                    return df
            except Exception as e:
                st.warning(f"Direct column approach failed: {str(e)}")

        # Use the separate tracking table approach
        # First check if tracking table exists and has data
        tracking_check_query = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_name = 'evaluation_production_models'
        """

        tracking_table_exists = False
        try:
            tracking_check = run_analytics_query(tracking_check_query)
            tracking_table_exists = (
                tracking_check[0]["count"] > 0 if tracking_check else False
            )
        except Exception:
            tracking_table_exists = False

        if tracking_table_exists:
            tracking_query = """
            SELECT 
                e.id, e.overall_score, e.structure_score, e.accuracy_score, 
                e.translation_score, e.product_type, e.created_at, e.brand, e.product_name,
                pm.provider as production_model_provider,
                pm.model_name as production_model_name, 
                pm.temperature as production_temperature,
                CONCAT(pm.provider, '/', pm.model_name) as model_full_name
            FROM evaluations e
            JOIN evaluation_production_models epm ON e.id = epm.evaluation_id
            JOIN production_models pm ON epm.production_model_id = pm.id
            WHERE e.created_at >= CURRENT_DATE - INTERVAL '90 days'
            AND e.overall_score IS NOT NULL
            ORDER BY e.created_at DESC
            """

            try:
                tracking_data = run_analytics_query(tracking_query)
                if tracking_data and len(tracking_data) > 0:
                    df = pd.DataFrame(tracking_data)
                    df["data_source"] = "tracking_table"
                    return df
            except Exception as e:
                st.warning(f"Tracking table approach failed: {str(e)}")

        # If we get here, no production model data is available yet
        return None

    except Exception as e:
        st.error(f"Error loading production model data: {str(e)}")
        return None


def _render_production_model_setup_instructions():
    """Show setup instructions when production model data is not available."""
    st.warning("⚠️ **Production Model Tracking Ready - Waiting for Data**")

    with st.expander("📋 System Status & Next Steps"):
        st.markdown(
            """
        **Production Model Performance** tracks which LLM models (GPT-4, Llama, etc.) are used to 
        *create* the product JSON, separate from the evaluation models that *assess* the quality.
        
        **Current System Status:**
        """
        )

        # Check what's available
        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**Production Models Table**")
            try:
                pm_check = run_analytics_query(
                    "SELECT COUNT(*) as count FROM production_models"
                )
                pm_count = pm_check[0]["count"] if pm_check else 0
                if pm_count > 0:
                    st.success(f"✅ {pm_count} model configs")
                else:
                    st.error("❌ Table missing")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

        with col2:
            st.write("**Evaluations Column**")
            try:
                col_check = run_analytics_query(
                    """
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'evaluations' AND column_name = 'production_model_id'
                """
                )
                if col_check:
                    st.success("✅ Direct column")
                else:
                    st.info("ℹ️ Using tracking table")
            except Exception as e:
                st.info("ℹ️ Using tracking table")

        with col3:
            st.write("**Data Available**")
            try:
                # Check for any production model data
                data_check_queries = [
                    # Try direct approach
                    """
                    SELECT COUNT(*) as count FROM evaluations e 
                    JOIN production_models pm ON e.production_model_id = pm.id 
                    WHERE e.created_at >= CURRENT_DATE - INTERVAL '30 days'
                    """,
                    # Try tracking table approach
                    """
                    SELECT COUNT(*) as count FROM evaluations e
                    JOIN evaluation_production_models epm ON e.id = epm.evaluation_id
                    JOIN production_models pm ON epm.production_model_id = pm.id
                    WHERE e.created_at >= CURRENT_DATE - INTERVAL '30 days'
                    """,
                ]

                data_count = 0
                for query in data_check_queries:
                    try:
                        result = run_analytics_query(query)
                        if result and result[0]["count"] > 0:
                            data_count = result[0]["count"]
                            break
                    except:
                        continue

                if data_count > 0:
                    st.success(f"✅ {data_count} evaluations")
                else:
                    st.warning("⚠️ No data yet")

            except Exception as e:
                st.warning("⚠️ No data yet")

        st.markdown("---")
        st.markdown(
            """
        **✅ System is Ready!** 
        
        Your production model tracking system is properly configured. To see analytics:
        
        1. **Process some products** - Go to your main product extraction interface
        2. **Use different models** - Try both OpenAI and Groq models if available  
        3. **Return here** - Analytics will appear automatically with your data
        
        **Next Steps:**
        - 🔄 **Process 2-3 products** to populate initial data
        - 📊 **Analytics will appear** showing model performance comparisons
        - 💡 **Get insights** on which models work best for your use cases
        
        The system will automatically track which models were used to create each product JSON!
        """
        )


def safe_run_analytics_query(query, params=None, default_return=None):
    """
    Safe wrapper for analytics queries that handles errors gracefully.
    Add this function to help with error handling.
    """
    try:
        result = run_analytics_query(query, params)
        return result if result else (default_return or [])
    except Exception as e:
        # Don't show error for expected failures (like column not existing)
        if "does not exist" not in str(e).lower():
            st.warning(f"Query issue: {str(e)}")
        return default_return or []


def _render_production_model_overview(data):
    """Render key overview metrics for production models."""
    st.subheader("📊 Production Model Overview")

    # Calculate key metrics
    total_evaluations = len(data)
    unique_models = data["model_full_name"].nunique()
    avg_quality = data["overall_score"].mean()
    unique_providers = data["production_model_provider"].nunique()

    # Date range
    date_range = f"{data['created_at'].min().strftime('%Y-%m-%d')} to {data['created_at'].max().strftime('%Y-%m-%d')}"

    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Evaluations", f"{total_evaluations:,}")

    with col2:
        st.metric("Unique Models", unique_models)

    with col3:
        st.metric("Average Quality", f"{avg_quality:.2f}")

    with col4:
        st.metric("Providers", unique_providers)

    with col5:
        st.metric("Date Range", date_range.split(" to ")[1])  # Show end date

    # Data source indicator
    data_source = (
        data["data_source"].iloc[0] if "data_source" in data.columns else "unknown"
    )
    if data_source == "direct_column":
        st.caption("📊 Data source: Direct column (optimal performance)")
    elif data_source == "tracking_table":
        st.caption("📊 Data source: Tracking table (fallback approach)")


def _render_provider_performance_comparison(data):
    """Compare performance between different providers (OpenAI, Groq, etc.)."""
    st.subheader("🏢 Provider Performance Comparison")

    # Calculate provider statistics
    provider_stats = (
        data.groupby("production_model_provider")
        .agg(
            {
                "overall_score": ["mean", "std", "count"],
                "structure_score": "mean",
                "accuracy_score": "mean",
                "translation_score": "mean",
            }
        )
        .round(3)
    )

    provider_stats.columns = [
        "avg_quality",
        "std_quality",
        "evaluations",
        "avg_structure",
        "avg_accuracy",
        "avg_translation",
    ]
    provider_stats = provider_stats.reset_index()

    if len(provider_stats) > 1:
        # Create comparison chart
        fig = px.bar(
            provider_stats,
            x="production_model_provider",
            y="avg_quality",
            title="Average Quality Score by Provider",
            text="evaluations",
            color="avg_quality",
            color_continuous_scale="RdYlGn",
        )
        fig.update_traces(texttemplate="%{text} evals", textposition="outside")
        fig.update_layout(
            yaxis_range=[1, 5],
            xaxis_title="Provider",
            yaxis_title="Average Quality Score",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Show detailed statistics table
        st.dataframe(
            provider_stats.style.format(
                {
                    "avg_quality": "{:.2f}",
                    "std_quality": "{:.2f}",
                    "avg_structure": "{:.2f}",
                    "avg_accuracy": "{:.2f}",
                    "avg_translation": "{:.2f}",
                }
            ),
            use_container_width=True,
        )
    else:
        st.info("Need multiple providers for comparison analysis.")


def _render_model_performance_table(data):
    """Enhanced individual model performance table with clear metric averages (no matplotlib dependency)."""
    st.subheader("🎯 Individual Model Performance")

    # Calculate comprehensive model statistics
    model_stats = (
        data.groupby(
            [
                "production_model_provider",
                "production_model_name",
                "production_temperature",
            ]
        )
        .agg(
            {
                "overall_score": ["mean", "std", "count", "min", "max"],
                "structure_score": ["mean", "std"],
                "accuracy_score": ["mean", "std"],
                "translation_score": ["mean", "std"],
            }
        )
        .round(2)
    )

    # Flatten column names
    model_stats.columns = [
        "overall_avg",
        "overall_std",
        "evaluations",
        "overall_min",
        "overall_max",
        "structure_avg",
        "structure_std",
        "accuracy_avg",
        "accuracy_std",
        "translation_avg",
        "translation_std",
    ]
    model_stats = model_stats.reset_index()

    # Sort by overall average quality descending
    model_stats = model_stats.sort_values("overall_avg", ascending=False)

    # Add performance indicator
    model_stats["performance_status"] = model_stats["overall_avg"].apply(
        lambda x: (
            "🥇 Excellent"
            if x >= 4.5
            else (
                "🥈 Good"
                if x >= 4.0
                else "🥉 Fair" if x >= 3.5 else "⚠️ Needs Attention"
            )
        )
    )

    # Create model identifier for cleaner display
    model_stats["model_display"] = (
        model_stats["production_model_provider"]
        + "/"
        + model_stats["production_model_name"]
    )

    # Add color indicators for performance (using emojis instead of background colors)
    def get_performance_color(score):
        if score >= 4.5:
            return f"🟢 {score:.2f}"
        elif score >= 4.0:
            return f"🟡 {score:.2f}"
        elif score >= 3.5:
            return f"🟠 {score:.2f}"
        else:
            return f"🔴 {score:.2f}"

    model_stats["overall_display"] = model_stats["overall_avg"].apply(
        get_performance_color
    )
    model_stats["structure_display"] = model_stats["structure_avg"].apply(
        get_performance_color
    )
    model_stats["accuracy_display"] = model_stats["accuracy_avg"].apply(
        get_performance_color
    )
    model_stats["translation_display"] = model_stats["translation_avg"].apply(
        get_performance_color
    )

    # Display options
    display_option = st.radio(
        "Display Format:", ["📊 Summary View", "📋 Detailed View"], horizontal=True
    )

    if display_option == "📊 Summary View":
        # Summary view with key metrics
        summary_display = model_stats[
            [
                "model_display",
                "production_temperature",
                "evaluations",
                "overall_display",
                "structure_display",
                "accuracy_display",
                "translation_display",
                "performance_status",
            ]
        ].copy()

        st.dataframe(
            summary_display,
            use_container_width=True,
            column_config={
                "model_display": st.column_config.TextColumn("Model", width="medium"),
                "production_temperature": st.column_config.NumberColumn(
                    "Temp", format="%.1f"
                ),
                "evaluations": st.column_config.NumberColumn("Count", format="%d"),
                "overall_display": st.column_config.TextColumn(
                    "Overall Avg", width="small"
                ),
                "structure_display": st.column_config.TextColumn(
                    "Structure Avg", width="small"
                ),
                "accuracy_display": st.column_config.TextColumn(
                    "Accuracy Avg", width="small"
                ),
                "translation_display": st.column_config.TextColumn(
                    "Translation Avg", width="small"
                ),
                "performance_status": st.column_config.TextColumn(
                    "Status", width="medium"
                ),
            },
        )

    else:
        # Detailed view with statistics (using raw numbers)
        detailed_display = model_stats[
            [
                "model_display",
                "production_temperature",
                "evaluations",
                "overall_avg",
                "overall_std",
                "overall_min",
                "overall_max",
                "structure_avg",
                "structure_std",
                "accuracy_avg",
                "accuracy_std",
                "translation_avg",
                "translation_std",
                "performance_status",
            ]
        ].copy()

        st.dataframe(
            detailed_display.style.format(
                {
                    "overall_avg": "{:.2f}",
                    "overall_std": "{:.2f}",
                    "overall_min": "{:.2f}",
                    "overall_max": "{:.2f}",
                    "structure_avg": "{:.2f}",
                    "structure_std": "{:.2f}",
                    "accuracy_avg": "{:.2f}",
                    "accuracy_std": "{:.2f}",
                    "translation_avg": "{:.2f}",
                    "translation_std": "{:.2f}",
                    "production_temperature": "{:.1f}",
                }
            ),
            use_container_width=True,
            column_config={
                "model_display": st.column_config.TextColumn("Model", width="medium"),
                "production_temperature": st.column_config.NumberColumn(
                    "Temp", format="%.1f"
                ),
                "evaluations": st.column_config.NumberColumn("Count", format="%d"),
                "overall_avg": st.column_config.NumberColumn(
                    "Overall Avg", format="%.2f"
                ),
                "overall_std": st.column_config.NumberColumn(
                    "Overall Std", format="%.2f"
                ),
                "overall_min": st.column_config.NumberColumn(
                    "Overall Min", format="%.2f"
                ),
                "overall_max": st.column_config.NumberColumn(
                    "Overall Max", format="%.2f"
                ),
                "structure_avg": st.column_config.NumberColumn(
                    "Structure Avg", format="%.2f"
                ),
                "structure_std": st.column_config.NumberColumn(
                    "Structure Std", format="%.2f"
                ),
                "accuracy_avg": st.column_config.NumberColumn(
                    "Accuracy Avg", format="%.2f"
                ),
                "accuracy_std": st.column_config.NumberColumn(
                    "Accuracy Std", format="%.2f"
                ),
                "translation_avg": st.column_config.NumberColumn(
                    "Translation Avg", format="%.2f"
                ),
                "translation_std": st.column_config.NumberColumn(
                    "Translation Std", format="%.2f"
                ),
                "performance_status": st.column_config.TextColumn(
                    "Status", width="medium"
                ),
            },
        )

    # Show top performers summary
    st.markdown("---")
    st.write("**🏆 Top Performers by Metric:**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        best_overall = model_stats.loc[model_stats["overall_avg"].idxmax()]
        st.metric(
            "🎯 Best Overall",
            f"{best_overall['overall_avg']:.2f}",
            delta=f"{best_overall['model_display']} (T:{best_overall['production_temperature']})",
        )

    with col2:
        best_structure = model_stats.loc[model_stats["structure_avg"].idxmax()]
        st.metric(
            "🏗️ Best Structure",
            f"{best_structure['structure_avg']:.2f}",
            delta=f"{best_structure['model_display']} (T:{best_structure['production_temperature']})",
        )

    with col3:
        best_accuracy = model_stats.loc[model_stats["accuracy_avg"].idxmax()]
        st.metric(
            "🎯 Best Accuracy",
            f"{best_accuracy['accuracy_avg']:.2f}",
            delta=f"{best_accuracy['model_display']} (T:{best_accuracy['production_temperature']})",
        )

    with col4:
        best_translation = model_stats.loc[model_stats["translation_avg"].idxmax()]
        st.metric(
            "🌐 Best Translation",
            f"{best_translation['translation_avg']:.2f}",
            delta=f"{best_translation['model_display']} (T:{best_translation['production_temperature']})",
        )

    # Performance insights
    st.markdown("---")
    st.write("**📊 Performance Insights:**")

    # Calculate some insights
    total_models = len(model_stats)
    excellent_models = len(model_stats[model_stats["overall_avg"] >= 4.5])
    good_models = len(
        model_stats[
            (model_stats["overall_avg"] >= 4.0) & (model_stats["overall_avg"] < 4.5)
        ]
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"**{excellent_models}/{total_models}** models are Excellent (≥4.5)")

    with col2:
        st.info(f"**{good_models}/{total_models}** models are Good (4.0-4.4)")

    with col3:
        avg_performance = model_stats["overall_avg"].mean()
        st.info(f"**Average performance**: {avg_performance:.2f}")

    # Add metric explanations
    with st.expander("📖 Metric Explanations"):
        st.markdown(
            """
        **Understanding the Metrics:**
        
        - **Overall Score**: Combined quality rating (1-5 scale)
        - **Structure Score**: JSON format and schema compliance (1-5 scale)  
        - **Accuracy Score**: Content accuracy vs input, no hallucinations (1-5 scale)
        - **Translation Score**: Portuguese translation quality (1-5 scale)
        - **Temperature**: Model randomness setting (0.0 = deterministic, 1.0 = creative)
        - **Count**: Number of evaluations for statistical reliability
        - **Std**: Standard deviation (lower = more consistent performance)
        
        **Performance Indicators:**
        - 🟢 **Excellent**: 4.5+ average score
        - 🟡 **Good**: 4.0-4.4 average score  
        - 🟠 **Fair**: 3.5-3.9 average score
        - 🔴 **Needs Attention**: <3.5 average score
        
        **Color Legend:**
        - 🥇 Excellent / 🥈 Good / 🥉 Fair / ⚠️ Needs Attention
        """
        )


def _render_model_metrics_chart(data):
    """
    Optional: Add this function to show a radar chart of model performance.
    You can call this from your main render function if you want visual comparison.
    """
    st.subheader("📊 Model Performance Radar Chart")

    # Calculate model averages for radar chart
    model_averages = (
        data.groupby(
            [
                "production_model_provider",
                "production_model_name",
                "production_temperature",
            ]
        )
        .agg(
            {
                "overall_score": "mean",
                "structure_score": "mean",
                "accuracy_score": "mean",
                "translation_score": "mean",
            }
        )
        .round(2)
        .reset_index()
    )

    # Create model identifier
    model_averages["model_id"] = (
        model_averages["production_model_provider"]
        + "/"
        + model_averages["production_model_name"]
        + " (T:"
        + model_averages["production_temperature"].astype(str)
        + ")"
    )

    # Select top 5 models for radar chart (to avoid clutter)
    top_models = model_averages.nlargest(5, "overall_score")

    # Create radar chart
    fig = go.Figure()

    for _, model in top_models.iterrows():
        fig.add_trace(
            go.Scatterpolar(
                r=[
                    model["structure_score"],
                    model["accuracy_score"],
                    model["translation_score"],
                    model["overall_score"],
                ],
                theta=["Structure", "Accuracy", "Translation", "Overall"],
                fill="toself",
                name=model["model_id"],
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
        showlegend=True,
        title="Top 5 Models - Performance Radar Chart",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_temperature_impact_analysis(data):
    """Analyze the impact of temperature settings on quality."""
    st.subheader("🌡️ Temperature Impact Analysis")

    # Group by temperature and calculate stats
    temp_stats = (
        data.groupby("production_temperature")
        .agg(
            {
                "overall_score": ["mean", "count"],
                "structure_score": "mean",
                "accuracy_score": "mean",
                "translation_score": "mean",
            }
        )
        .round(3)
    )

    temp_stats.columns = [
        "avg_quality",
        "evaluations",
        "avg_structure",
        "avg_accuracy",
        "avg_translation",
    ]
    temp_stats = temp_stats.reset_index()

    if len(temp_stats) > 1:
        # Create line chart
        fig = px.line(
            temp_stats,
            x="production_temperature",
            y="avg_quality",
            title="Quality vs Temperature Settings",
            markers=True,
            text="evaluations",
        )
        fig.update_traces(texttemplate="%{text} evals", textposition="top center")
        fig.update_layout(
            xaxis_title="Temperature",
            yaxis_title="Average Quality Score",
            yaxis_range=[1, 5],
        )
        st.plotly_chart(fig, use_container_width=True)

        # Find optimal temperature
        optimal_temp = temp_stats.loc[
            temp_stats["avg_quality"].idxmax(), "production_temperature"
        ]
        optimal_quality = temp_stats.loc[
            temp_stats["avg_quality"].idxmax(), "avg_quality"
        ]

        st.info(
            f"🎯 **Optimal Temperature**: {optimal_temp} (Quality: {optimal_quality:.2f})"
        )
    else:
        st.info("Need multiple temperature settings for analysis.")


def _render_product_type_specialization(data):
    """Analyze which models work best for different product types."""
    st.subheader("📦 Product Type Specialization")

    # Create pivot table
    specialization = data.pivot_table(
        values="overall_score",
        index="model_full_name",
        columns="product_type",
        aggfunc="mean",
    ).round(2)

    if not specialization.empty:
        # Create heatmap
        fig = px.imshow(
            specialization.values,
            x=specialization.columns,
            y=specialization.index,
            title="Model Performance by Product Type",
            color_continuous_scale="RdYlGn",
            aspect="auto",
        )
        fig.update_layout(xaxis_title="Product Type", yaxis_title="Model")
        st.plotly_chart(fig, use_container_width=True)

        # Show best model for each product type
        st.write("**🏆 Best Model by Product Type:**")
        for product_type in specialization.columns:
            if not specialization[product_type].isna().all():
                best_model = specialization[product_type].idxmax()
                best_score = specialization[product_type].max()
                st.write(f"- **{product_type}**: {best_model} ({best_score:.2f})")


def _render_advanced_model_analytics(data):
    """Advanced analytics including distributions and correlations."""
    st.subheader("📈 Advanced Model Analytics")

    tab1, tab2 = st.tabs(["Quality Distributions", "Performance Trends"])

    with tab1:
        # Box plot of quality distributions by model
        fig = px.box(
            data,
            x="model_full_name",
            y="overall_score",
            title="Quality Score Distributions by Model",
        )
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Performance over time
        data["date"] = pd.to_datetime(data["created_at"]).dt.date

        daily_performance = (
            data.groupby(["date", "production_model_provider"])["overall_score"]
            .mean()
            .reset_index()
        )

        fig = px.line(
            daily_performance,
            x="date",
            y="overall_score",
            color="production_model_provider",
            title="Quality Trends Over Time by Provider",
        )
        fig.update_layout(yaxis_range=[1, 5])
        st.plotly_chart(fig, use_container_width=True)


def _render_model_performance_insights(data):
    """Generate automated insights and recommendations."""
    st.subheader("🧠 Performance Insights & Recommendations")

    insights = []

    # Provider comparison insight
    provider_performance = data.groupby("production_model_provider")[
        "overall_score"
    ].mean()
    if len(provider_performance) > 1:
        best_provider = provider_performance.idxmax()
        best_score = provider_performance.max()
        worst_provider = provider_performance.idxmin()
        worst_score = provider_performance.min()

        if best_score - worst_score > 0.2:
            insights.append(
                {
                    "type": "success",
                    "title": f"{best_provider} outperforms {worst_provider}",
                    "message": f"{best_provider} achieves {best_score:.2f} vs {worst_provider} at {worst_score:.2f}",
                    "recommendation": f"Consider prioritizing {best_provider} models for higher quality results",
                }
            )

    # Temperature optimization insight
    temp_performance = data.groupby("production_temperature")["overall_score"].mean()
    if len(temp_performance) > 1:
        optimal_temp = temp_performance.idxmax()
        optimal_score = temp_performance.max()

        insights.append(
            {
                "type": "info",
                "title": f"Optimal temperature identified",
                "message": f"Temperature {optimal_temp} produces best results ({optimal_score:.2f} quality)",
                "recommendation": f"Configure new models to use temperature {optimal_temp} for optimal performance",
            }
        )

    # Volume vs quality insight
    model_stats = (
        data.groupby("model_full_name")
        .agg({"overall_score": "mean", "id": "count"})
        .rename(columns={"id": "usage_count"})
    )

    high_usage = model_stats[
        model_stats["usage_count"] > model_stats["usage_count"].quantile(0.7)
    ]
    if not high_usage.empty:
        best_high_usage = high_usage["overall_score"].idxmax()
        best_score = high_usage.loc[best_high_usage, "overall_score"]
        usage_count = high_usage.loc[best_high_usage, "usage_count"]

        insights.append(
            {
                "type": "info",
                "title": "High-usage model performance",
                "message": f"{best_high_usage} shows both high usage ({usage_count} evaluations) and quality ({best_score:.2f})",
                "recommendation": "This model provides a good balance of reliability and performance",
            }
        )

    # Display insights
    if insights:
        for insight in insights:
            if insight["type"] == "success":
                st.success(f"✅ **{insight['title']}**: {insight['message']}")
            elif insight["type"] == "warning":
                st.warning(f"⚠️ **{insight['title']}**: {insight['message']}")
            else:
                st.info(f"💡 **{insight['title']}**: {insight['message']}")

            st.caption(f"**Recommendation**: {insight['recommendation']}")
    else:
        st.info(
            "Process more products with different models to see personalized insights!"
        )


# ================================
# TAB 4: QUALITY DEEP DIVE
# ================================


def render_quality_deep_dive(evaluations_df, feedback_df):
    """Deep dive into 3-metric analysis."""
    st.header("📈 Quality Deep Dive")
    st.markdown("**Detailed analysis of Structure, Content, and Translation metrics**")

    if evaluations_df.empty:
        st.info("No evaluation data available.")
        return

    # 3-Metric Overview
    st.subheader("🎯 3-Metric Performance Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        avg_structure = evaluations_df["structure_score"].mean()
        st.metric(
            "Structure",
            f"{avg_structure:.2f}/5",
            help="JSON structure and schema compliance",
        )

    with col2:
        avg_content = evaluations_df["accuracy_score"].mean()
        st.metric(
            "Content",
            f"{avg_content:.2f}/5",
            help="Accuracy vs input, hallucination detection",
        )

    with col3:
        avg_translation = evaluations_df["translation_score"].mean()
        st.metric(
            "Translation",
            f"{avg_translation:.2f}/5",
            help="Portuguese translation quality",
        )

    # Metric Distributions
    st.subheader("📊 Score Distributions")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Ensure proper data types for plotly
        structure_data = pd.to_numeric(
            evaluations_df["structure_score"], errors="coerce"
        ).dropna()
        fig = px.histogram(
            x=structure_data,
            title="Structure Score Distribution",
            nbins=5,
            range_x=[0.5, 5.5],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        accuracy_data = pd.to_numeric(
            evaluations_df["accuracy_score"], errors="coerce"
        ).dropna()
        fig = px.histogram(
            x=accuracy_data,
            title="Content Score Distribution",
            nbins=5,
            range_x=[0.5, 5.5],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        completeness_data = pd.to_numeric(
            evaluations_df["translation_score"], errors="coerce"
        ).dropna()
        fig = px.histogram(
            x=completeness_data,
            title="Translation Score Distribution",
            nbins=5,
            range_x=[0.5, 5.5],
        )
        st.plotly_chart(fig, use_container_width=True)

    # Correlation Analysis
    st.subheader("🔗 Metric Correlation Analysis")

    # Ensure proper numeric data types for correlation
    correlation_df = evaluations_df[
        ["structure_score", "accuracy_score", "translation_score", "overall_score"]
    ].copy()

    # Convert to numeric and handle any non-numeric values
    for col in correlation_df.columns:
        correlation_df[col] = pd.to_numeric(correlation_df[col], errors="coerce")

    correlation_data = correlation_df.corr()

    fig = px.imshow(
        correlation_data,
        text_auto=True,
        aspect="auto",
        title="Metric Correlation Matrix",
        color_continuous_scale="RdBu",
        range_color=[-1, 1],
    )

    fig.update_layout(
        xaxis=dict(
            tickvals=list(range(4)),
            ticktext=["Structure", "Content", "Translation", "Overall"],
        ),
        yaxis=dict(
            tickvals=list(range(4)),
            ticktext=["Structure", "Content", "Translation", "Overall"],
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Performance by Product Type
    st.subheader("📋 Metric Performance by Product Type")

    product_metrics = (
        evaluations_df.groupby("product_type")
        .agg(
            {
                "structure_score": "mean",
                "accuracy_score": "mean",
                "translation_score": "mean",
                "overall_score": "mean",
            }
        )
        .round(2)
        .reset_index()
    )

    # Melt for easier plotting and ensure proper data types
    melted_metrics = product_metrics.melt(
        id_vars=["product_type"],
        value_vars=["structure_score", "accuracy_score", "translation_score"],
        var_name="metric",
        value_name="score",
    )
    melted_metrics["metric"] = melted_metrics["metric"].map(
        {
            "structure_score": "Structure",
            "accuracy_score": "Content",
            "translation_score": "Translation",
        }
    )
    # Ensure score is numeric for plotly
    melted_metrics["score"] = pd.to_numeric(melted_metrics["score"], errors="coerce")

    fig = px.bar(
        melted_metrics,
        x="product_type",
        y="score",
        color="metric",
        title="Average Metric Scores by Product Type",
        labels={"score": "Average Score (1-5)", "product_type": "Product Type"},
        barmode="group",
    )
    fig.update_layout(yaxis_range=[1, 5])
    st.plotly_chart(fig, use_container_width=True)

    # Quality Issues Analysis
    st.subheader("🚨 Quality Issues Analysis")

    # Find products with scores below 3 in each metric
    structure_issues = evaluations_df[evaluations_df["structure_score"] < 3]
    content_issues = evaluations_df[evaluations_df["accuracy_score"] < 3]
    translation_issues = evaluations_df[evaluations_df["translation_score"] < 3]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Structure Issues",
            len(structure_issues),
            delta=f"{len(structure_issues)/len(evaluations_df)*100:.1f}% of products",
        )

    with col2:
        st.metric(
            "Content Issues",
            len(content_issues),
            delta=f"{len(content_issues)/len(evaluations_df)*100:.1f}% of products",
        )

    with col3:
        st.metric(
            "Translation Issues",
            len(translation_issues),
            delta=f"{len(translation_issues)/len(evaluations_df)*100:.1f}% of products",
        )


# ================================
# TAB 5: INVESTIGATION TOOLS
# ================================


def render_enhanced_investigation_tools(evaluations_df, feedback_df):
    """ENHANCED: Investigation tools with brand, product name, input text, and JSON output."""
    st.header("🔍 Investigation Tools - ENHANCED VIEW")
    st.markdown(
        "**Search, filter, and analyze individual evaluations with complete product data**"
    )

    # Load all evaluation data with complete information
    full_data_query = """
    SELECT 
        e.id, e.product_config_id, e.overall_score, e.structure_score,
        e.accuracy_score, e.translation_score, e.product_type,
        e.evaluation_model, e.llm_reasoning, e.brand, e.product_name,
        e.input_text, e.extracted_json, e.created_at,
        CASE 
            WHEN e.evaluation_model LIKE 'openevals%' THEN 'OpenEvals'
            WHEN e.evaluation_model LIKE 'fallback%' THEN 'Fallback'
            ELSE 'Legacy'
        END as evaluator_type
    FROM evaluations e
    ORDER BY e.created_at DESC
    """

    full_data = run_cached_query(full_data_query)
    full_evaluations_df = pd.DataFrame(full_data)

    if full_evaluations_df.empty:
        st.info("No evaluation data available.")
        return

    # Parse JSON data
    for idx, row in full_evaluations_df.iterrows():
        if row.get("extracted_json"):
            try:
                full_evaluations_df.at[idx, "extracted_json"] = json.loads(
                    row["extracted_json"]
                )
            except:
                full_evaluations_df.at[idx, "extracted_json"] = {}

    # ENHANCED: Search and Filter Controls
    st.subheader("🔧 Enhanced Search & Filter Controls")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search_term = st.text_input(
            "🔍 Search", placeholder="Brand, product name, or reasoning..."
        )

    with col2:
        product_types = ["All"] + list(full_evaluations_df["product_type"].unique())
        selected_type = st.selectbox("Product Type", product_types)

    with col3:
        score_range = st.slider("Overall Score Range", 1.0, 5.0, (1.0, 5.0), 0.1)

    with col4:
        evaluator_types = ["All"] + list(full_evaluations_df["evaluator_type"].unique())
        selected_evaluator = st.selectbox("Evaluator Type", evaluator_types)

    # Additional search row
    col1, col2 = st.columns(2)

    with col1:
        brand_search = st.text_input(
            "🏷️ Brand Search", placeholder="Search by brand name..."
        )

    with col2:
        product_search = st.text_input(
            "📦 Product Search", placeholder="Search by product name..."
        )

    # Apply filters
    filtered_df = full_evaluations_df.copy()

    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["product_type"] == selected_type]

    if selected_evaluator != "All":
        filtered_df = filtered_df[filtered_df["evaluator_type"] == selected_evaluator]

    filtered_df = filtered_df[
        (filtered_df["overall_score"] >= score_range[0])
        & (filtered_df["overall_score"] <= score_range[1])
    ]

    # ENHANCED: Multi-field search
    if search_term:
        search_mask = (
            filtered_df["llm_reasoning"].str.contains(search_term, case=False, na=False)
            | filtered_df["brand"].str.contains(search_term, case=False, na=False)
            | filtered_df["product_name"].str.contains(
                search_term, case=False, na=False
            )
        )
        filtered_df = filtered_df[search_mask]

    if brand_search:
        filtered_df = filtered_df[
            filtered_df["brand"].str.contains(brand_search, case=False, na=False)
        ]

    if product_search:
        filtered_df = filtered_df[
            filtered_df["product_name"].str.contains(
                product_search, case=False, na=False
            )
        ]

    st.write(f"**Results:** {len(filtered_df)} evaluations match your criteria")

    # ENHANCED: Results Display with complete information
    st.subheader("📋 Detailed Results with Complete Product Information")

    if filtered_df.empty:
        st.info("No evaluations match your search criteria.")
        return

    # Paginated results
    results_per_page = st.selectbox("Results per page", [5, 10, 20, 50], index=1)
    total_pages = (len(filtered_df) - 1) // results_per_page + 1

    if total_pages > 1:
        page = st.selectbox("Page", range(1, total_pages + 1))
        start_idx = (page - 1) * results_per_page
        end_idx = start_idx + results_per_page
        page_df = filtered_df.iloc[start_idx:end_idx]
    else:
        page_df = filtered_df

    # ENHANCED: Display individual results with complete product information
    for idx, row in page_df.iterrows():
        # ENHANCED: Expander title includes brand and product name
        expander_title = f"🔍 {row['brand']} - {row['product_name']} | Score: {row['overall_score']:.1f}/5 | {row['product_type']} | {row['created_at'].strftime('%Y-%m-%d')}"

        with st.expander(expander_title):
            # ENHANCED: Product Information Section
            st.markdown("### 🏷️ Product Information")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Brand:** {row['brand']}")
                st.write(f"**Product:** {row['product_name']}")
                st.write(f"**Type:** {row['product_type']}")

            with col2:
                st.write(f"**Evaluation ID:** {row['id']}")
                st.write(f"**Config ID:** {row['product_config_id']}")
                st.write(f"**Evaluator:** {row['evaluator_type']}")

            with col3:
                st.write(f"**Date:** {row['created_at'].strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Model:** {row['evaluation_model']}")

            # Scores section
            st.markdown("### 📊 AI Evaluation Scores")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Overall", f"{row['overall_score']:.1f}/5")
            with col2:
                st.metric("Structure", f"{row['structure_score']}/5")
            with col3:
                st.metric("Content", f"{row['accuracy_score']}/5")
            with col4:
                st.metric("Translation", f"{row['translation_score']}/5")

            # ENHANCED: Input Text Section
            st.markdown("### 📝 Input Text")
            if row.get("input_text"):
                input_text = row["input_text"]
                if len(input_text) > 500:
                    with st.expander("📄 View Full Input Text"):
                        st.text_area(
                            "Complete Input Text",
                            value=input_text,
                            height=300,
                            key=f"investigation_input_{row['id']}",
                            disabled=True,
                            label_visibility="collapsed",
                        )
                else:
                    st.text(input_text)
            else:
                st.info("No input text available")

            # ENHANCED: JSON Output Section
            st.markdown("### 📋 Extracted JSON Output")
            if row.get("extracted_json") and isinstance(row["extracted_json"], dict):
                with st.expander("🔍 View JSON Output"):
                    st.json(row["extracted_json"])
            else:
                st.info("No JSON output available")

            # AI Reasoning Section
            st.markdown("### 🤖 AI Assessment Reasoning")
            if row["llm_reasoning"]:
                # Enhanced reasoning display with 3-column parsing
                if " | " in row["llm_reasoning"]:
                    reasoning_parts = row["llm_reasoning"].split(" | ")

                    if len(reasoning_parts) >= 3:
                        col1, col2, col3 = st.columns(3)
                        titles = ["🏗️ Structure", "📝 Content", "🌍 Translation"]

                        for i, (part, title) in enumerate(
                            zip(reasoning_parts[:3], titles)
                        ):
                            with [col1, col2, col3][i]:
                                st.markdown(f"**{title}**")
                                if ":" in part:
                                    _, reasoning = part.split(":", 1)
                                    st.text_area(
                                        title,
                                        value=reasoning.strip(),
                                        height=100,
                                        key=f"reasoning_{row['id']}_{i}",
                                        disabled=True,
                                        label_visibility="collapsed",
                                    )
                                else:
                                    st.text(part)
                    else:
                        st.text_area(
                            "AI Reasoning",
                            value=row["llm_reasoning"],
                            height=120,
                            key=f"reasoning_full_{row['id']}",
                            disabled=True,
                            label_visibility="collapsed",
                        )
                else:
                    st.text_area(
                        "AI Reasoning",
                        value=row["llm_reasoning"],
                        height=120,
                        key=f"reasoning_{row['id']}",
                        disabled=True,
                        label_visibility="collapsed",
                    )
            else:
                st.info("No AI reasoning available")

            # Human Feedback Section (if available)
            human_feedback = feedback_df[feedback_df["evaluation_id"] == row["id"]]
            if not human_feedback.empty:
                feedback_row = human_feedback.iloc[0]
                st.markdown("### 👥 Human Feedback")
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Rating:** {feedback_row['human_rating']}/5")
                    score_diff = abs(
                        row["overall_score"] - feedback_row["human_rating"]
                    )
                    st.write(f"**Agreement:** ±{score_diff:.1f}")

                    # Show feedback provider name
                    feedback_user = (
                        feedback_row.get("feedback_user_name")
                        or feedback_row.get("feedback_username")
                        or "Unknown User"
                    )
                    if feedback_user and feedback_user != "System":
                        st.write(f"**Feedback by:** {feedback_user}")

                with col2:
                    if feedback_row["notes"]:
                        st.text_area(
                            "Human Notes",
                            value=feedback_row["notes"],
                            height=120,
                            key=f"human_feedback_{row['id']}",
                            disabled=True,
                            label_visibility="collapsed",
                        )


# ================================
# TAB 6: REPORTS & EXPORT
# ================================


def render_reports_export(evaluations_df, feedback_df):
    """Data export and reporting tools."""
    st.header("📤 Reports & Export")
    st.markdown("**Generate reports and export data for external analysis**")

    if evaluations_df.empty:
        st.info("No evaluation data available for export.")
        return

    # Quick Stats Summary
    st.subheader("📊 Export Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Evaluations", len(evaluations_df))
    with col2:
        st.metric("Human Feedback", len(feedback_df))
    with col3:
        st.metric("Product Types", len(evaluations_df["product_type"].unique()))
    with col4:
        st.metric("Evaluator Types", len(evaluations_df["evaluator_type"].unique()))

    # Export Options
    st.subheader("📥 Data Export Options")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Structured Data Exports**")

        # CSV Export
        if st.button("📄 Export Evaluations CSV", use_container_width=True):
            csv_data = evaluations_df.to_csv(index=False)
            st.download_button(
                "Download Evaluations CSV",
                csv_data,
                f"evaluations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
            )

        # Human Feedback CSV
        if not feedback_df.empty and st.button(
            "👥 Export Human Feedback CSV", use_container_width=True
        ):
            csv_data = feedback_df.to_csv(index=False)
            st.download_button(
                "Download Human Feedback CSV",
                csv_data,
                f"human_feedback_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
            )

        # JSON Export
        if st.button("📋 Export All Data JSON", use_container_width=True):
            export_data = {
                "evaluations": evaluations_df.to_dict("records"),
                "human_feedback": feedback_df.to_dict("records"),
                "export_date": datetime.now().isoformat(),
                "summary": {
                    "total_evaluations": len(evaluations_df),
                    "avg_quality": float(evaluations_df["overall_score"].mean()),
                    "human_feedback_count": len(feedback_df),
                },
            }
            json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
            st.download_button(
                "Download Complete Dataset JSON",
                json_data,
                f"quality_analytics_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                "application/json",
            )

    with col2:
        st.markdown("**📈 Analytics Reports**")

        # Executive Summary Report
        if st.button("📊 Generate Executive Summary", use_container_width=True):
            # Calculate summary statistics
            total_evals = len(evaluations_df)
            avg_quality = evaluations_df["overall_score"].mean()
            high_quality = len(evaluations_df[evaluations_df["overall_score"] >= 4.0])

            # Agreement stats
            agreement_stats = "No human feedback available"
            if not feedback_df.empty:
                merged = feedback_df.merge(
                    evaluations_df[["id", "overall_score"]],
                    left_on="evaluation_id",
                    right_on="id",
                    how="inner",
                )
                if not merged.empty:
                    agreement = len(
                        merged[
                            abs(merged["overall_score"] - merged["human_rating"]) <= 1.0
                        ]
                    )
                    agreement_pct = (agreement / len(merged)) * 100
                    agreement_stats = f"{agreement_pct:.1f}% agreement (±1.0 points)"

            # Model performance
            model_performance = (
                evaluations_df.groupby("evaluator_type")["overall_score"]
                .mean()
                .to_dict()
            )

            report_text = f"""# Quality Analytics Executive Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Database: PostgreSQL (Migrated from SQLite)

## Key Metrics
- **Total Evaluations**: {total_evals}
- **Average Quality**: {avg_quality:.2f}/5.0
- **High Quality Products**: {high_quality} ({(high_quality/total_evals)*100:.1f}%)
- **AI-Human Agreement**: {agreement_stats}

## Model Performance
"""
            for model, score in model_performance.items():
                report_text += f"- **{model}**: {score:.2f}/5.0\n"

            report_text += f"""
## Quality Distribution
- **Excellent (4.0+)**: {len(evaluations_df[evaluations_df['overall_score'] >= 4.0])} products
- **Good (3.0-3.9)**: {len(evaluations_df[(evaluations_df['overall_score'] >= 3.0) & (evaluations_df['overall_score'] < 4.0)])} products
- **Needs Improvement (<3.0)**: {len(evaluations_df[evaluations_df['overall_score'] < 3.0])} products

## Migration Benefits
- **Improved Reliability**: PostgreSQL provides better data persistence
- **Enhanced Performance**: Query caching and connection pooling
- **Scalability**: Ready for production workloads
- **Backup & Recovery**: Built-in data protection

## Recommendations
"""

            # Add recommendations based on data
            if avg_quality < 3.5:
                report_text += (
                    "- ⚠️ Overall quality below target - review extraction prompts\n"
                )
            if not feedback_df.empty:
                merged = feedback_df.merge(
                    evaluations_df[["id", "overall_score"]],
                    left_on="evaluation_id",
                    right_on="id",
                    how="inner",
                )
                if not merged.empty:
                    large_discrepancies = len(
                        merged[
                            abs(merged["overall_score"] - merged["human_rating"]) > 1.5
                        ]
                    )
                    if large_discrepancies > 0:
                        report_text += f"- 🔍 Review {large_discrepancies} cases with large AI-Human discrepancies\n"

            if len(model_performance) > 1:
                best_model = max(
                    model_performance.keys(), key=lambda k: model_performance[k]
                )
                report_text += (
                    f"- 💡 Consider using {best_model} model for better performance\n"
                )

            st.download_button(
                "Download Executive Summary",
                report_text,
                f"executive_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                "text/markdown",
            )

        # Quality Analysis Report
        if st.button("🔬 Generate Detailed Analysis", use_container_width=True):
            # Create detailed analysis
            analysis_data = {
                "database_info": {
                    "type": "PostgreSQL",
                    "migration_date": datetime.now().isoformat(),
                    "connection_method": "Streamlit cached connection",
                },
                "summary": {
                    "total_evaluations": len(evaluations_df),
                    "date_range": {
                        "start": evaluations_df["created_at"].min().isoformat(),
                        "end": evaluations_df["created_at"].max().isoformat(),
                    },
                    "product_types": evaluations_df["product_type"]
                    .value_counts()
                    .to_dict(),
                    "evaluator_types": evaluations_df["evaluator_type"]
                    .value_counts()
                    .to_dict(),
                },
                "quality_metrics": {
                    "overall_score": {
                        "mean": float(evaluations_df["overall_score"].mean()),
                        "std": float(evaluations_df["overall_score"].std()),
                        "min": float(evaluations_df["overall_score"].min()),
                        "max": float(evaluations_df["overall_score"].max()),
                    },
                    "structure_score": {
                        "mean": float(evaluations_df["structure_score"].mean()),
                        "distribution": evaluations_df["structure_score"]
                        .value_counts()
                        .to_dict(),
                    },
                    "content_score": {
                        "mean": float(evaluations_df["accuracy_score"].mean()),
                        "distribution": evaluations_df["accuracy_score"]
                        .value_counts()
                        .to_dict(),
                    },
                    "translation_score": {
                        "mean": float(evaluations_df["translation_score"].mean()),
                        "distribution": evaluations_df["translation_score"]
                        .value_counts()
                        .to_dict(),
                    },
                },
            }

            # Add human feedback analysis if available
            if not feedback_df.empty:
                merged = feedback_df.merge(
                    evaluations_df[["id", "overall_score"]],
                    left_on="evaluation_id",
                    right_on="id",
                    how="inner",
                )
                if not merged.empty:
                    merged["score_diff"] = abs(
                        merged["overall_score"] - merged["human_rating"]
                    )
                    analysis_data["human_feedback"] = {
                        "total_feedback": len(merged),
                        "avg_human_rating": float(merged["human_rating"].mean()),
                        "avg_ai_score": float(merged["overall_score"].mean()),
                        "agreement_stats": {
                            "excellent_agreement": len(
                                merged[merged["score_diff"] <= 0.5]
                            ),
                            "good_agreement": len(merged[merged["score_diff"] <= 1.0]),
                            "poor_agreement": len(merged[merged["score_diff"] > 1.5]),
                        },
                    }

            json_data = json.dumps(analysis_data, indent=2, ensure_ascii=False)
            st.download_button(
                "Download Detailed Analysis JSON",
                json_data,
                f"detailed_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                "application/json",
            )

    # Recent Activity Log
    st.subheader("📅 Recent Activity")

    recent_evaluations = evaluations_df.head(10)
    activity_data = []

    for _, row in recent_evaluations.iterrows():
        activity_data.append(
            {
                "Date": row["created_at"].strftime("%Y-%m-%d %H:%M"),
                "Product Type": row["product_type"],
                "Model": row["evaluator_type"],
                "Quality": f"{row['overall_score']:.1f}/5",
                "ID": row["id"],
            }
        )

    st.dataframe(pd.DataFrame(activity_data), use_container_width=True)


# ================================
# TAB 7: USER ANALYTICS (NEW)
# ================================


def render_user_analytics_dashboard(evaluations_df, feedback_df):
    """PHASE 5: Comprehensive User Analytics Dashboard"""
    st.header("👥 User Analytics Dashboard")
    st.markdown("**Track user productivity, activity, and performance metrics**")

    if evaluations_df.empty:
        st.warning("No evaluation data available for user analytics.")
        return

    # Check if user tracking columns exist
    user_columns = ["created_by_username", "created_by_name", "user_id"]
    missing_columns = [col for col in user_columns if col not in evaluations_df.columns]

    if missing_columns:
        st.error(f"❌ User tracking not available. Missing columns: {missing_columns}")
        st.info(
            "📋 To enable user analytics, ensure the database schema includes user attribution fields."
        )
        return

    # Filter out system/unknown users for cleaner analytics
    user_df = evaluations_df[
        (evaluations_df["created_by_username"].notna())
        & (evaluations_df["created_by_username"] != "")
        & (evaluations_df["created_by_username"] != "system")
        & (evaluations_df["created_by_username"] != "unknown")
    ].copy()

    if user_df.empty:
        st.warning(
            "No user-attributed products found. All products appear to be created by system/unknown users."
        )
        st.info(
            "💡 **Tip**: User attribution is captured when users create products while logged in."
        )
        return

    # ================================
    # 1. USER OVERVIEW METRICS
    # ================================
    st.subheader("📊 User Overview")

    # Calculate key metrics
    total_users = user_df["created_by_username"].nunique()
    total_products = len(user_df)
    avg_products_per_user = total_products / total_users if total_users > 0 else 0

    # Active users (created products in last 30 days)
    recent_date = user_df["created_at"].max() - timedelta(days=30)
    active_users = user_df[user_df["created_at"] > recent_date][
        "created_by_username"
    ].nunique()

    # Quality metrics
    avg_quality = user_df["overall_score"].mean()
    high_quality_products = len(user_df[user_df["overall_score"] >= 4.0])

    # Display key metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Users", total_users)

    with col2:
        st.metric("Total Products", total_products)

    with col3:
        st.metric("Avg Products/User", f"{avg_products_per_user:.1f}")

    with col4:
        st.metric(
            "Active Users (30d)",
            active_users,
            delta=f"{(active_users/total_users)*100:.0f}%" if total_users > 0 else "0%",
        )

    with col5:
        st.metric(
            "Avg Quality",
            f"{avg_quality:.2f}/5",
            delta=f"{(high_quality_products/total_products)*100:.0f}% high quality",
        )

    # ================================
    # 2. USER PRODUCTIVITY ANALYSIS
    # ================================
    st.subheader("🚀 User Productivity Analysis")

    # User productivity summary
    user_productivity = (
        user_df.groupby(["created_by_username", "created_by_name"])
        .agg(
            {
                "id": "count",  # Total products
                "overall_score": ["mean", "std"],
                "created_at": ["min", "max"],
                "structure_score": "mean",
                "accuracy_score": "mean",
                "translation_score": "mean",
            }
        )
        .round(2)
    )

    # Flatten column names
    user_productivity.columns = [
        "total_products",
        "avg_quality",
        "quality_std",
        "first_product",
        "latest_product",
        "avg_structure",
        "avg_accuracy",
        "avg_translation",
    ]
    user_productivity = user_productivity.reset_index()
    user_productivity["quality_std"] = user_productivity["quality_std"].fillna(0)

    # Calculate additional metrics
    user_productivity["days_active"] = (
        user_productivity["latest_product"] - user_productivity["first_product"]
    ).dt.days + 1
    user_productivity["products_per_day"] = (
        user_productivity["total_products"] / user_productivity["days_active"]
    ).round(3)

    # High performers (top quality + high volume)
    user_productivity["performance_score"] = (
        user_productivity["avg_quality"] * 0.6
        + (
            user_productivity["total_products"]
            / user_productivity["total_products"].max()
        )
        * 2
        * 0.4
    ).round(2)

    col1, col2 = st.columns(2)

    with col1:
        # Top producers chart
        top_producers = user_productivity.nlargest(10, "total_products")
        fig = px.bar(
            top_producers,
            x="created_by_name",
            y="total_products",
            title="Top 10 Product Creators",
            labels={"total_products": "Products Created", "created_by_name": "User"},
            text="total_products",
        )
        fig.update_layout(xaxis_tickangle=-45)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Quality vs Quantity scatter
        fig = px.scatter(
            user_productivity,
            x="total_products",
            y="avg_quality",
            size="performance_score",
            hover_name="created_by_name",
            title="Quality vs Quantity Analysis",
            labels={
                "total_products": "Products Created",
                "avg_quality": "Average Quality Score",
                "performance_score": "Performance Score",
            },
        )
        fig.add_hline(
            y=4.0,
            line_dash="dash",
            line_color="green",
            annotation_text="High Quality Threshold",
        )
        fig.update_layout(yaxis_range=[1, 5])
        st.plotly_chart(fig, use_container_width=True)

    # ================================
    # 3. USER PERFORMANCE LEADERBOARD
    # ================================
    st.subheader("🏆 User Performance Leaderboard")

    # Create tabs for different leaderboard views
    leaderboard_tab1, leaderboard_tab2, leaderboard_tab3, leaderboard_tab4 = st.tabs(
        [
            "🥇 Overall Performance",
            "📊 Total Products",
            "⭐ Quality Leaders",
            "⚡ Recent Activity",
        ]
    )

    with leaderboard_tab1:
        # Overall performance ranking
        top_performers = user_productivity.nlargest(10, "performance_score")

        st.markdown("**🏆 Top Performers (Quality + Volume)**")
        for i, (_, user) in enumerate(top_performers.iterrows(), 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
            with col1:
                st.write(medal)
            with col2:
                st.write(
                    f"**{user['created_by_name']}** ({user['created_by_username']})"
                )
            with col3:
                st.write(f"Score: {user['performance_score']:.2f}")
            with col4:
                st.write(
                    f"{user['total_products']} products @ {user['avg_quality']:.1f}/5"
                )

    with leaderboard_tab2:
        # Volume leaders
        top_volume = user_productivity.nlargest(10, "total_products")

        st.markdown("**📊 Most Productive Users**")
        for i, (_, user) in enumerate(top_volume.iterrows(), 1):
            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
            with col1:
                st.write(f"{i}.")
            with col2:
                st.write(
                    f"**{user['created_by_name']}** ({user['created_by_username']})"
                )
            with col3:
                st.write(f"{user['total_products']} products")
            with col4:
                st.write(f"{user['products_per_day']:.2f} per day")

    with leaderboard_tab3:
        # Quality leaders (minimum 3 products)
        quality_leaders = user_productivity[
            user_productivity["total_products"] >= 3
        ].nlargest(10, "avg_quality")

        st.markdown("**⭐ Highest Quality (min. 3 products)**")
        for i, (_, user) in enumerate(quality_leaders.iterrows(), 1):
            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
            with col1:
                st.write(f"{i}.")
            with col2:
                st.write(
                    f"**{user['created_by_name']}** ({user['created_by_username']})"
                )
            with col3:
                st.write(f"{user['avg_quality']:.2f}/5 avg")
            with col4:
                quality_consistency = "🎯" if user["quality_std"] < 0.5 else "📊"
                st.write(f"{user['total_products']} products {quality_consistency}")

    with leaderboard_tab4:
        # Recent activity (last 30 days)
        recent_activity = (
            user_df[user_df["created_at"] > recent_date]
            .groupby(["created_by_username", "created_by_name"])
            .agg({"id": "count", "overall_score": "mean", "created_at": "max"})
            .round(2)
        )
        recent_activity.columns = [
            "recent_products",
            "recent_avg_quality",
            "last_activity",
        ]
        recent_activity = recent_activity.reset_index().sort_values(
            "recent_products", ascending=False
        )

        st.markdown("**⚡ Most Active (Last 30 Days)**")
        if not recent_activity.empty:
            for i, (_, user) in enumerate(recent_activity.head(10).iterrows(), 1):
                col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
                with col1:
                    st.write(f"{i}.")
                with col2:
                    st.write(
                        f"**{user['created_by_name']}** ({user['created_by_username']})"
                    )
                with col3:
                    st.write(f"{user['recent_products']} products")
                with col4:
                    last_activity_naive = (
                        user["last_activity"].replace(tzinfo=None)
                        if user["last_activity"].tzinfo
                        else user["last_activity"]
                    )
                    days_ago = (datetime.now() - last_activity_naive).days
                    st.write(f"{days_ago} days ago")
        else:
            st.info("No activity in the last 30 days")

    # ================================
    # 4. USER ACTIVITY TIMELINE
    # ================================
    st.subheader("📅 User Activity Timeline")

    # Daily activity heatmap
    user_df["date"] = user_df["created_at"].dt.date
    daily_activity = (
        user_df.groupby(["date", "created_by_username"])
        .size()
        .reset_index(name="products")
    )

    # Create pivot for heatmap
    activity_pivot = daily_activity.pivot(
        index="date", columns="created_by_username", values="products"
    ).fillna(0)

    if len(activity_pivot) > 0:
        # Show last 60 days for readability
        recent_activity_pivot = activity_pivot.tail(60)

        fig = px.imshow(
            recent_activity_pivot.T,
            title="User Activity Heatmap (Last 60 Days)",
            labels={"x": "Date", "y": "User", "color": "Products Created"},
            aspect="auto",
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Weekly activity trend
    user_df["week"] = user_df["created_at"].dt.to_period("W")
    weekly_activity = (
        user_df.groupby("week")
        .agg({"id": "count", "created_by_username": "nunique", "overall_score": "mean"})
        .reset_index()
    )
    weekly_activity.columns = ["week", "total_products", "active_users", "avg_quality"]
    weekly_activity["week_str"] = weekly_activity["week"].astype(str)

    col1, col2 = st.columns(2)

    with col1:
        # Weekly products trend
        fig = px.bar(
            weekly_activity.tail(12),  # Last 12 weeks
            x="week_str",
            y="total_products",
            title="Weekly Product Creation Trend",
            labels={"total_products": "Products Created", "week_str": "Week"},
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Weekly active users
        fig = px.line(
            weekly_activity.tail(12),
            x="week_str",
            y="active_users",
            title="Weekly Active Users",
            labels={"active_users": "Active Users", "week_str": "Week"},
            markers=True,
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # ================================
    # 5. DETAILED USER PROFILES
    # ================================
    st.subheader("👤 Detailed User Profiles")

    # User selection
    selected_user = st.selectbox(
        "Select User for Detailed Analysis",
        options=user_productivity["created_by_username"].tolist(),
        format_func=lambda x: f"{user_productivity[user_productivity['created_by_username']==x]['created_by_name'].iloc[0]} ({x})",
    )

    if selected_user:
        user_data = user_productivity[
            user_productivity["created_by_username"] == selected_user
        ].iloc[0]
        user_products = user_df[user_df["created_by_username"] == selected_user]

        # User profile header
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Products", user_data["total_products"])
        with col2:
            st.metric("Average Quality", f"{user_data['avg_quality']:.2f}/5")
        with col3:
            st.metric("Quality Consistency", f"±{user_data['quality_std']:.2f}")
        with col4:
            st.metric("Productivity", f"{user_data['products_per_day']:.2f}/day")

        # User's quality trend over time
        user_products_sorted = user_products.sort_values("created_at")

        col1, col2 = st.columns(2)

        with col1:
            # Quality over time
            fig = px.line(
                user_products_sorted,
                x="created_at",
                y="overall_score",
                title=f"{user_data['created_by_name']}'s Quality Trend",
                labels={"overall_score": "Quality Score", "created_at": "Date"},
                markers=True,
            )
            fig.add_hline(
                y=4.0,
                line_dash="dash",
                line_color="green",
                annotation_text="High Quality",
            )
            fig.update_layout(yaxis_range=[1, 5])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Product type distribution
            type_distribution = user_products["product_type"].value_counts()
            fig = px.pie(
                values=type_distribution.values,
                names=type_distribution.index,
                title=f"{user_data['created_by_name']}'s Product Types",
            )
            st.plotly_chart(fig, use_container_width=True)

        # User's detailed metrics table
        with st.expander(f"📊 {user_data['created_by_name']}'s Detailed Metrics"):
            detailed_metrics = (
                user_products.groupby("product_type")
                .agg(
                    {
                        "id": "count",
                        "overall_score": ["mean", "min", "max"],
                        "structure_score": "mean",
                        "accuracy_score": "mean",
                        "translation_score": "mean",
                    }
                )
                .round(2)
            )

            # Flatten column names
            detailed_metrics.columns = [
                "products",
                "avg_quality",
                "min_quality",
                "max_quality",
                "avg_structure",
                "avg_accuracy",
                "avg_translation",
            ]
            detailed_metrics = detailed_metrics.reset_index()

            st.dataframe(detailed_metrics, use_container_width=True)

    # ================================
    # 6. USER COMPARISON ANALYSIS
    # ================================
    st.subheader("⚖️ User Comparison Analysis")

    # Multi-user selector for comparison
    comparison_users = st.multiselect(
        "Select Users to Compare (max 5)",
        options=user_productivity["created_by_username"].tolist(),
        format_func=lambda x: f"{user_productivity[user_productivity['created_by_username']==x]['created_by_name'].iloc[0]} ({x})",
        max_selections=5,
    )

    if len(comparison_users) >= 2:
        comparison_data = user_productivity[
            user_productivity["created_by_username"].isin(comparison_users)
        ]

        # Comparison radar chart
        categories = [
            "Total Products (scaled)",
            "Avg Quality",
            "Avg Structure",
            "Avg Accuracy",
            "Avg Translation",
        ]

        fig = go.Figure()

        for _, user in comparison_data.iterrows():
            # Scale total products to 1-5 range for radar chart
            scaled_products = min(
                5,
                (user["total_products"] / comparison_data["total_products"].max()) * 5,
            )

            values = [
                scaled_products,
                user["avg_quality"],
                user["avg_structure"],
                user["avg_accuracy"],
                user["avg_translation"],
            ]

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill="toself",
                    name=user["created_by_name"],
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True,
            title="User Performance Comparison",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Comparison table
        comparison_table = comparison_data[
            [
                "created_by_name",
                "total_products",
                "avg_quality",
                "products_per_day",
                "performance_score",
            ]
        ].copy()
        comparison_table.columns = [
            "User",
            "Products",
            "Avg Quality",
            "Productivity",
            "Performance Score",
        ]
        comparison_table = comparison_table.sort_values(
            "Performance Score", ascending=False
        )

        st.dataframe(comparison_table, use_container_width=True, hide_index=True)


# ================================
# TAB 7: USER ANALYTICS (NEW)
# ================================


def _render_model_metrics_radar_chart(data):
    """
    Clean radar chart showing model performance across all metrics.
    """
    st.subheader("📊 Model Performance Radar Chart")

    # Calculate model averages for radar chart
    model_averages = (
        data.groupby(
            [
                "production_model_provider",
                "production_model_name",
                "production_temperature",
            ]
        )
        .agg(
            {
                "overall_score": "mean",
                "structure_score": "mean",
                "accuracy_score": "mean",
                "translation_score": "mean",
            }
        )
        .round(2)
        .reset_index()
    )

    # Create model identifier
    model_averages["model_id"] = (
        model_averages["production_model_provider"]
        + "/"
        + model_averages["production_model_name"]
        + " (T:"
        + model_averages["production_temperature"].astype(str)
        + ")"
    )

    # Sort by overall score for better selection
    model_averages = model_averages.sort_values("overall_score", ascending=False)

    if len(model_averages) == 0:
        st.warning("No model data available for radar chart.")
        return

    # Let user select which models to compare
    col1, col2 = st.columns([2, 1])

    with col1:
        # Multi-select for models to compare
        selected_models = st.multiselect(
            "Select models to compare (max 6 for readability):",
            options=model_averages["model_id"].tolist(),
            default=model_averages["model_id"]
            .head(min(3, len(model_averages)))
            .tolist(),
            help="Choose which models you want to compare in the radar chart",
        )

    with col2:
        # Chart style options
        chart_style = st.selectbox(
            "Chart Style:",
            ["Filled Areas", "Lines Only", "Points Only"],
            help="Choose how to display the radar chart",
        )

    if not selected_models:
        st.warning("Please select at least one model to display.")
        return

    if len(selected_models) > 6:
        st.warning("Too many models selected. Showing first 6 for readability.")
        selected_models = selected_models[:6]

    # Filter data for selected models
    selected_data = model_averages[
        model_averages["model_id"].isin(selected_models)
    ].copy()

    if len(selected_data) == 0:
        st.error("No data found for selected models.")
        return

    # Create radar chart
    fig = go.Figure()

    # Define colors for different models
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]

    for i, (_, model) in enumerate(selected_data.iterrows()):
        color = colors[i % len(colors)]

        # Determine fill and line settings based on style
        if chart_style == "Filled Areas":
            fill = "toself"
            line_width = 2
            opacity = 0.6
        elif chart_style == "Lines Only":
            fill = "none"
            line_width = 3
            opacity = 1.0
        else:  # Points Only
            fill = "none"
            line_width = 1
            opacity = 1.0

        fig.add_trace(
            go.Scatterpolar(
                r=[
                    model["structure_score"],
                    model["accuracy_score"],
                    model["translation_score"],
                    model["overall_score"],
                    model["structure_score"],  # Close the shape
                ],
                theta=["Structure", "Accuracy", "Translation", "Overall", "Structure"],
                fill=fill,
                name=model["model_id"],
                line=dict(color=color, width=line_width),
                fillcolor=color,
                opacity=opacity,
                mode="lines+markers" if chart_style == "Points Only" else "lines",
                marker=dict(size=8 if chart_style == "Points Only" else 6),
            )
        )

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[1, 5],
                tickmode="linear",
                tick0=1,
                dtick=1,
                gridcolor="lightgray",
                gridwidth=1,
            ),
            angularaxis=dict(
                tickfont=dict(size=12), rotation=90, direction="clockwise"
            ),
        ),
        showlegend=True,
        title={
            "text": f"Model Performance Comparison - {chart_style}",
            "x": 0.5,
            "font": {"size": 16},
        },
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=600,
        margin=dict(t=80, b=100, l=80, r=80),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show performance summary for selected models
    st.markdown("---")
    st.write("**📈 Performance Summary for Selected Models:**")

    # Create summary table
    summary_table = selected_data[
        [
            "model_id",
            "overall_score",
            "structure_score",
            "accuracy_score",
            "translation_score",
        ]
    ].copy()
    summary_table = summary_table.sort_values("overall_score", ascending=False)

    # Add rankings
    summary_table["overall_rank"] = (
        summary_table["overall_score"].rank(ascending=False, method="min").astype(int)
    )
    summary_table["structure_rank"] = (
        summary_table["structure_score"].rank(ascending=False, method="min").astype(int)
    )
    summary_table["accuracy_rank"] = (
        summary_table["accuracy_score"].rank(ascending=False, method="min").astype(int)
    )
    summary_table["translation_rank"] = (
        summary_table["translation_score"]
        .rank(ascending=False, method="min")
        .astype(int)
    )

    # Format for display
    display_summary = summary_table.copy()
    display_summary["Overall"] = display_summary.apply(
        lambda x: f"#{x['overall_rank']} ({x['overall_score']:.2f})", axis=1
    )
    display_summary["Structure"] = display_summary.apply(
        lambda x: f"#{x['structure_rank']} ({x['structure_score']:.2f})", axis=1
    )
    display_summary["Accuracy"] = display_summary.apply(
        lambda x: f"#{x['accuracy_rank']} ({x['accuracy_score']:.2f})", axis=1
    )
    display_summary["Translation"] = display_summary.apply(
        lambda x: f"#{x['translation_rank']} ({x['translation_score']:.2f})", axis=1
    )

    st.dataframe(
        display_summary[
            ["model_id", "Overall", "Structure", "Accuracy", "Translation"]
        ],
        use_container_width=True,
        column_config={
            "model_id": st.column_config.TextColumn("Model", width="large"),
            "Overall": st.column_config.TextColumn(
                "Overall (Rank & Score)", width="medium"
            ),
            "Structure": st.column_config.TextColumn(
                "Structure (Rank & Score)", width="medium"
            ),
            "Accuracy": st.column_config.TextColumn(
                "Accuracy (Rank & Score)", width="medium"
            ),
            "Translation": st.column_config.TextColumn(
                "Translation (Rank & Score)", width="medium"
            ),
        },
    )

    # Performance insights
    if len(selected_data) > 1:
        st.markdown("---")
        st.write("**🔍 Key Insights:**")

        # Best overall performer
        best_overall = selected_data.loc[selected_data["overall_score"].idxmax()]
        st.success(
            f"🏆 **Best Overall**: {best_overall['model_id']} with {best_overall['overall_score']:.2f}"
        )

        # Most consistent performer (lowest std dev across metrics)
        selected_data["consistency"] = selected_data[
            ["structure_score", "accuracy_score", "translation_score", "overall_score"]
        ].std(axis=1)
        most_consistent = selected_data.loc[selected_data["consistency"].idxmin()]
        st.info(
            f"📊 **Most Consistent**: {most_consistent['model_id']} (std dev: {most_consistent['consistency']:.2f})"
        )

        # Specialist recommendations
        best_structure = selected_data.loc[selected_data["structure_score"].idxmax()]
        best_accuracy = selected_data.loc[selected_data["accuracy_score"].idxmax()]
        best_translation = selected_data.loc[
            selected_data["translation_score"].idxmax()
        ]

        col1, col2, col3 = st.columns(3)
        with col1:
            if best_structure["model_id"] != best_overall["model_id"]:
                st.info(
                    f"🏗️ **Best Structure**: {best_structure['model_id']} ({best_structure['structure_score']:.2f})"
                )

        with col2:
            if best_accuracy["model_id"] != best_overall["model_id"]:
                st.info(
                    f"🎯 **Best Accuracy**: {best_accuracy['model_id']} ({best_accuracy['accuracy_score']:.2f})"
                )

        with col3:
            if best_translation["model_id"] != best_overall["model_id"]:
                st.info(
                    f"🌐 **Best Translation**: {best_translation['model_id']} ({best_translation['translation_score']:.2f})"
                )

    # Usage recommendations
    st.markdown("---")
    st.write("**💡 Usage Recommendations:**")

    if len(selected_data) >= 2:
        # Find the best and worst performers
        best_model = selected_data.loc[selected_data["overall_score"].idxmax()]
        worst_model = selected_data.loc[selected_data["overall_score"].idxmin()]

        performance_gap = best_model["overall_score"] - worst_model["overall_score"]

        if performance_gap > 0.5:
            st.warning(
                f"⚠️ **Significant Performance Gap**: {performance_gap:.2f} points between best and worst models"
            )
            st.info(
                f"💡 **Recommendation**: Prioritize {best_model['model_id']} for better quality results"
            )

        # Temperature insights
        unique_temps = selected_data["production_temperature"].unique()
        if len(unique_temps) > 1:
            temp_performance = selected_data.groupby("production_temperature")[
                "overall_score"
            ].mean()
            best_temp = temp_performance.idxmax()
            st.info(
                f"🌡️ **Optimal Temperature**: {best_temp} shows best average performance"
            )
    else:
        st.info("💡 Select multiple models to see comparative recommendations")


def render_user_analytics_dashboard(evaluations_df, feedback_df):
    """PHASE 5: Comprehensive User Analytics Dashboard"""
    st.header("👥 User Analytics Dashboard")
    st.markdown("**Track user productivity, activity, and performance metrics**")

    if evaluations_df.empty:
        st.warning("No evaluation data available for user analytics.")
        return

    # Check if user tracking columns exist
    user_columns = ["created_by_username", "created_by_name", "user_id"]
    missing_columns = [col for col in user_columns if col not in evaluations_df.columns]

    if missing_columns:
        st.error(f"❌ User tracking not available. Missing columns: {missing_columns}")
        st.info(
            "📋 To enable user analytics, ensure the database schema includes user attribution fields."
        )
        return

    # Filter out system/unknown users for cleaner analytics
    user_df = evaluations_df[
        (evaluations_df["created_by_username"].notna())
        & (evaluations_df["created_by_username"] != "")
        & (evaluations_df["created_by_username"] != "system")
        & (evaluations_df["created_by_username"] != "unknown")
    ].copy()

    if user_df.empty:
        st.warning(
            "No user-attributed products found. All products appear to be created by system/unknown users."
        )
        st.info(
            "💡 **Tip**: User attribution is captured when users create products while logged in."
        )
        return

    # ================================
    # 1. USER OVERVIEW METRICS
    # ================================
    st.subheader("📊 User Overview")

    # Calculate key metrics with safe operations
    total_users = user_df["created_by_username"].nunique()
    total_products = len(user_df)
    avg_products_per_user = total_products / max(
        total_users, 1
    )  # Avoid division by zero

    # Active users (created products in last 30 days)
    recent_date = user_df["created_at"].max() - timedelta(days=30)
    active_users = user_df[user_df["created_at"] > recent_date][
        "created_by_username"
    ].nunique()

    # Quality metrics with safe calculations
    avg_quality = user_df["overall_score"].mean() if not user_df.empty else 0
    high_quality_products = len(user_df[user_df["overall_score"] >= 4.0])
    activity_percentage = (
        active_users / max(total_users, 1)
    ) * 100  # Avoid division by zero
    quality_percentage = (
        high_quality_products / max(total_products, 1)
    ) * 100  # Avoid division by zero

    # Display key metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Users", total_users)

    with col2:
        st.metric("Total Products", total_products)

    with col3:
        st.metric("Avg Products/User", f"{avg_products_per_user:.1f}")

    with col4:
        st.metric(
            "Active Users (30d)", active_users, delta=f"{activity_percentage:.0f}%"
        )

    with col5:
        st.metric(
            "Avg Quality",
            f"{avg_quality:.2f}/5",
            delta=f"{quality_percentage:.0f}% high quality",
        )

    # ================================
    # 2. USER PRODUCTIVITY ANALYSIS
    # ================================
    st.subheader("🚀 User Productivity Analysis")

    # User productivity summary with proper data type handling
    user_productivity = user_df.groupby(["created_by_username", "created_by_name"]).agg(
        {
            "id": "count",  # Total products
            "overall_score": ["mean", "std"],
            "created_at": ["min", "max"],
            "structure_score": "mean",
            "accuracy_score": "mean",
            "translation_score": "mean",
        }
    )

    # Flatten column names
    user_productivity.columns = [
        "total_products",
        "avg_quality",
        "quality_std",
        "first_product",
        "latest_product",
        "avg_structure",
        "avg_accuracy",
        "avg_translation",
    ]
    user_productivity = user_productivity.reset_index()

    # Convert to proper numeric types and handle NaN values
    numeric_columns = [
        "total_products",
        "avg_quality",
        "quality_std",
        "avg_structure",
        "avg_accuracy",
        "avg_translation",
    ]
    for col in numeric_columns:
        user_productivity[col] = pd.to_numeric(
            user_productivity[col], errors="coerce"
        ).fillna(0)

    # Round numeric values
    user_productivity[numeric_columns] = user_productivity[numeric_columns].round(2)

    # Calculate additional metrics with proper data type handling
    user_productivity["days_active"] = (
        user_productivity["latest_product"] - user_productivity["first_product"]
    ).dt.days + 1

    # Ensure numeric columns and handle division by zero
    user_productivity["total_products"] = pd.to_numeric(
        user_productivity["total_products"], errors="coerce"
    )
    user_productivity["avg_quality"] = pd.to_numeric(
        user_productivity["avg_quality"], errors="coerce"
    )
    user_productivity["days_active"] = pd.to_numeric(
        user_productivity["days_active"], errors="coerce"
    )

    # Calculate products per day with safe division
    user_productivity["products_per_day"] = (
        (
            user_productivity["total_products"]
            / user_productivity["days_active"].replace(0, 1)
        )
        .fillna(0)
        .round(3)
    )

    # High performers (top quality + high volume) with safe calculations
    max_products = user_productivity["total_products"].max()
    if max_products > 0:
        volume_score = (user_productivity["total_products"] / max_products) * 2
    else:
        volume_score = 0

    user_productivity["performance_score"] = (
        (
            user_productivity["avg_quality"].fillna(0) * 0.6
            + pd.to_numeric(volume_score, errors="coerce").fillna(0) * 0.4
        )
        .fillna(0)
        .round(2)
    )

    col1, col2 = st.columns(2)

    with col1:
        # Top producers chart
        top_producers = user_productivity.nlargest(10, "total_products")
        fig = px.bar(
            top_producers,
            x="created_by_name",
            y="total_products",
            title="Top 10 Product Creators",
            labels={"total_products": "Products Created", "created_by_name": "User"},
            text="total_products",
        )
        fig.update_layout(xaxis_tickangle=-45)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Quality vs Quantity scatter
        fig = px.scatter(
            user_productivity,
            x="total_products",
            y="avg_quality",
            size="performance_score",
            hover_name="created_by_name",
            title="Quality vs Quantity Analysis",
            labels={
                "total_products": "Products Created",
                "avg_quality": "Average Quality Score",
                "performance_score": "Performance Score",
            },
        )
        fig.add_hline(
            y=4.0,
            line_dash="dash",
            line_color="green",
            annotation_text="High Quality Threshold",
        )
        fig.update_layout(yaxis_range=[1, 5])
        st.plotly_chart(fig, use_container_width=True)

    # ================================
    # 3. USER PERFORMANCE LEADERBOARD
    # ================================
    st.subheader("🏆 User Performance Leaderboard")

    # Create tabs for different leaderboard views
    leaderboard_tab1, leaderboard_tab2, leaderboard_tab3, leaderboard_tab4 = st.tabs(
        [
            "🥇 Overall Performance",
            "📊 Total Products",
            "⭐ Quality Leaders",
            "⚡ Recent Activity",
        ]
    )

    with leaderboard_tab1:
        # Overall performance ranking
        top_performers = user_productivity.nlargest(10, "performance_score")

        st.markdown("**🏆 Top Performers (Quality + Volume)**")
        for i, (_, user) in enumerate(top_performers.iterrows(), 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
            with col1:
                st.write(medal)
            with col2:
                st.write(
                    f"**{user['created_by_name']}** ({user['created_by_username']})"
                )
            with col3:
                st.write(f"Score: {user['performance_score']:.2f}")
            with col4:
                st.write(
                    f"{user['total_products']} products @ {user['avg_quality']:.1f}/5"
                )

    with leaderboard_tab2:
        # Volume leaders
        top_volume = user_productivity.nlargest(10, "total_products")

        st.markdown("**📊 Most Productive Users**")
        for i, (_, user) in enumerate(top_volume.iterrows(), 1):
            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
            with col1:
                st.write(f"{i}.")
            with col2:
                st.write(
                    f"**{user['created_by_name']}** ({user['created_by_username']})"
                )
            with col3:
                st.write(f"{user['total_products']} products")
            with col4:
                st.write(f"{user['products_per_day']:.2f} per day")

    with leaderboard_tab3:
        # Quality leaders (minimum 3 products)
        quality_leaders = user_productivity[
            user_productivity["total_products"] >= 3
        ].nlargest(10, "avg_quality")

        st.markdown("**⭐ Highest Quality (min. 3 products)**")
        for i, (_, user) in enumerate(quality_leaders.iterrows(), 1):
            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
            with col1:
                st.write(f"{i}.")
            with col2:
                st.write(
                    f"**{user['created_by_name']}** ({user['created_by_username']})"
                )
            with col3:
                st.write(f"{user['avg_quality']:.2f}/5 avg")
            with col4:
                quality_consistency = "🎯" if user["quality_std"] < 0.5 else "📊"
                st.write(f"{user['total_products']} products {quality_consistency}")

    with leaderboard_tab4:
        # Recent activity (last 30 days) with proper data handling
        recent_activity = (
            user_df[user_df["created_at"] > recent_date]
            .groupby(["created_by_username", "created_by_name"])
            .agg({"id": "count", "overall_score": "mean", "created_at": "max"})
            .reset_index()
        )
        recent_activity.columns = [
            "created_by_username",
            "created_by_name",
            "recent_products",
            "recent_avg_quality",
            "last_activity",
        ]

        # Convert to proper numeric types
        recent_activity["recent_products"] = pd.to_numeric(
            recent_activity["recent_products"], errors="coerce"
        ).fillna(0)
        recent_activity["recent_avg_quality"] = (
            pd.to_numeric(recent_activity["recent_avg_quality"], errors="coerce")
            .fillna(0)
            .round(2)
        )
        recent_activity = recent_activity.sort_values(
            "recent_products", ascending=False
        )

        st.markdown("**⚡ Most Active (Last 30 Days)**")
        if not recent_activity.empty:
            for i, (_, user) in enumerate(recent_activity.head(10).iterrows(), 1):
                col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
                with col1:
                    st.write(f"{i}.")
                with col2:
                    st.write(
                        f"**{user['created_by_name']}** ({user['created_by_username']})"
                    )
                with col3:
                    st.write(f"{int(user['recent_products'])} products")
                with col4:
                    days_ago = (
                        datetime.now() - user["last_activity"].replace(tzinfo=None)
                    ).days
                    st.write(f"{days_ago} days ago")
        else:
            st.info("No activity in the last 30 days")

    # ================================
    # 4. USER ACTIVITY TIMELINE
    # ================================
    st.subheader("📅 User Activity Timeline")

    # Daily activity heatmap
    user_df["date"] = user_df["created_at"].dt.date
    daily_activity = (
        user_df.groupby(["date", "created_by_username"])
        .size()
        .reset_index(name="products")
    )

    # Create pivot for heatmap
    activity_pivot = daily_activity.pivot(
        index="date", columns="created_by_username", values="products"
    ).fillna(0)

    if len(activity_pivot) > 0:
        # Show last 60 days for readability
        recent_activity_pivot = activity_pivot.tail(60)

        fig = px.imshow(
            recent_activity_pivot.T,
            title="User Activity Heatmap (Last 60 Days)",
            labels={"x": "Date", "y": "User", "color": "Products Created"},
            aspect="auto",
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Weekly activity trend with proper data handling
    user_df["week"] = user_df["created_at"].dt.to_period("W")
    weekly_activity = (
        user_df.groupby("week")
        .agg({"id": "count", "created_by_username": "nunique", "overall_score": "mean"})
        .reset_index()
    )
    weekly_activity.columns = ["week", "total_products", "active_users", "avg_quality"]

    # Convert to proper numeric types
    weekly_activity["total_products"] = pd.to_numeric(
        weekly_activity["total_products"], errors="coerce"
    ).fillna(0)
    weekly_activity["active_users"] = pd.to_numeric(
        weekly_activity["active_users"], errors="coerce"
    ).fillna(0)
    weekly_activity["avg_quality"] = pd.to_numeric(
        weekly_activity["avg_quality"], errors="coerce"
    ).fillna(0)
    weekly_activity["week_str"] = weekly_activity["week"].astype(str)

    col1, col2 = st.columns(2)

    with col1:
        # Weekly products trend
        fig = px.bar(
            weekly_activity.tail(12),  # Last 12 weeks
            x="week_str",
            y="total_products",
            title="Weekly Product Creation Trend",
            labels={"total_products": "Products Created", "week_str": "Week"},
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Weekly active users
        fig = px.line(
            weekly_activity.tail(12),
            x="week_str",
            y="active_users",
            title="Weekly Active Users",
            labels={"active_users": "Active Users", "week_str": "Week"},
            markers=True,
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # ================================
    # 5. DETAILED USER PROFILES
    # ================================
    st.subheader("👤 Detailed User Profiles")

    # User selection
    selected_user = st.selectbox(
        "Select User for Detailed Analysis",
        options=user_productivity["created_by_username"].tolist(),
        format_func=lambda x: f"{user_productivity[user_productivity['created_by_username']==x]['created_by_name'].iloc[0]} ({x})",
    )

    if selected_user:
        user_data = user_productivity[
            user_productivity["created_by_username"] == selected_user
        ].iloc[0]
        user_products = user_df[user_df["created_by_username"] == selected_user]

        # User profile header
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Products", user_data["total_products"])
        with col2:
            st.metric("Average Quality", f"{user_data['avg_quality']:.2f}/5")
        with col3:
            st.metric("Quality Consistency", f"±{user_data['quality_std']:.2f}")
        with col4:
            st.metric("Productivity", f"{user_data['products_per_day']:.2f}/day")

        # User's quality trend over time
        user_products_sorted = user_products.sort_values("created_at")

        col1, col2 = st.columns(2)

        with col1:
            # Quality over time
            fig = px.line(
                user_products_sorted,
                x="created_at",
                y="overall_score",
                title=f"{user_data['created_by_name']}'s Quality Trend",
                labels={"overall_score": "Quality Score", "created_at": "Date"},
                markers=True,
            )
            fig.add_hline(
                y=4.0,
                line_dash="dash",
                line_color="green",
                annotation_text="High Quality",
            )
            fig.update_layout(yaxis_range=[1, 5])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Product type distribution
            type_distribution = user_products["product_type"].value_counts()
            fig = px.pie(
                values=type_distribution.values,
                names=type_distribution.index,
                title=f"{user_data['created_by_name']}'s Product Types",
            )
            st.plotly_chart(fig, use_container_width=True)

        # User's detailed metrics table
        with st.expander(f"📊 {user_data['created_by_name']}'s Detailed Metrics"):
            detailed_metrics = user_products.groupby("product_type").agg(
                {
                    "id": "count",
                    "overall_score": ["mean", "min", "max"],
                    "structure_score": "mean",
                    "accuracy_score": "mean",
                    "translation_score": "mean",
                }
            )

            # Flatten column names
            detailed_metrics.columns = [
                "products",
                "avg_quality",
                "min_quality",
                "max_quality",
                "avg_structure",
                "avg_accuracy",
                "avg_translation",
            ]
            detailed_metrics = detailed_metrics.reset_index()

            # Convert to proper numeric types and round
            numeric_cols = [
                "products",
                "avg_quality",
                "min_quality",
                "max_quality",
                "avg_structure",
                "avg_accuracy",
                "avg_translation",
            ]
            for col in numeric_cols:
                if col in detailed_metrics.columns:
                    detailed_metrics[col] = pd.to_numeric(
                        detailed_metrics[col], errors="coerce"
                    ).fillna(0)
                    if col != "products":  # Don't round the count
                        detailed_metrics[col] = detailed_metrics[col].round(2)

            st.dataframe(detailed_metrics, use_container_width=True)

    # ================================
    # 6. USER COMPARISON ANALYSIS
    # ================================
    st.subheader("⚖️ User Comparison Analysis")

    # Multi-user selector for comparison
    comparison_users = st.multiselect(
        "Select Users to Compare (max 5)",
        options=user_productivity["created_by_username"].tolist(),
        format_func=lambda x: f"{user_productivity[user_productivity['created_by_username']==x]['created_by_name'].iloc[0]} ({x})",
        max_selections=5,
    )

    if len(comparison_users) >= 2:
        comparison_data = user_productivity[
            user_productivity["created_by_username"].isin(comparison_users)
        ]

        # Comparison radar chart
        categories = [
            "Total Products (scaled)",
            "Avg Quality",
            "Avg Structure",
            "Avg Accuracy",
            "Avg Translation",
        ]

        fig = go.Figure()

        for _, user in comparison_data.iterrows():
            # Scale total products to 1-5 range for radar chart
            scaled_products = min(
                5,
                (user["total_products"] / comparison_data["total_products"].max()) * 5,
            )

            values = [
                scaled_products,
                user["avg_quality"],
                user["avg_structure"],
                user["avg_accuracy"],
                user["avg_translation"],
            ]

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill="toself",
                    name=user["created_by_name"],
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True,
            title="User Performance Comparison",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Comparison table
        comparison_table = comparison_data[
            [
                "created_by_name",
                "total_products",
                "avg_quality",
                "products_per_day",
                "performance_score",
            ]
        ].copy()
        comparison_table.columns = [
            "User",
            "Products",
            "Avg Quality",
            "Productivity",
            "Performance Score",
        ]
        comparison_table = comparison_table.sort_values(
            "Performance Score", ascending=False
        )

        st.dataframe(comparison_table, use_container_width=True, hide_index=True)

    # ================================
    # 7. USER INSIGHTS & RECOMMENDATIONS
    # ================================
    st.subheader("💡 User Insights & Recommendations")

    insights = []

    # Identify power users
    power_users = user_productivity[
        user_productivity["performance_score"]
        >= user_productivity["performance_score"].quantile(0.8)
    ]
    if not power_users.empty:
        insights.append(
            {
                "type": "success",
                "title": f"🌟 Top Performers ({len(power_users)} users)",
                "message": f"Users with exceptional performance: {', '.join(power_users['created_by_name'].tolist())}",
                "action": "Consider recognizing these users or having them mentor others",
            }
        )

    # Identify inactive users
    inactive_users = total_users - active_users
    if inactive_users > 0:
        insights.append(
            {
                "type": "warning",
                "title": f"😴 Inactive Users ({inactive_users} users)",
                "message": f"{inactive_users} users haven't created products in the last 30 days",
                "action": "Consider reaching out to re-engage inactive users",
            }
        )

    # Quality consistency insights
    inconsistent_users = user_productivity[user_productivity["quality_std"] > 1.0]
    if not inconsistent_users.empty:
        insights.append(
            {
                "type": "info",
                "title": f"📊 Quality Consistency Opportunity ({len(inconsistent_users)} users)",
                "message": f"Some users show high quality variation: {', '.join(inconsistent_users['created_by_name'].tolist())}",
                "action": "Provide additional training or quality guidelines",
            }
        )

    # Display insights
    if insights:
        for insight in insights:
            if insight["type"] == "success":
                st.success(f"**{insight['title']}**: {insight['message']}")
            elif insight["type"] == "warning":
                st.warning(f"**{insight['title']}**: {insight['message']}")
            else:
                st.info(f"**{insight['title']}**: {insight['message']}")
            st.caption(f"**Recommendation**: {insight['action']}")
    else:
        st.success(
            "✅ **All systems healthy** - No specific user insights at this time"
        )

    # ================================
    # 8. USER EXPORT FUNCTIONALITY
    # ================================
    st.subheader("📤 User Analytics Export")

    col1, col2 = st.columns(2)

    with col1:
        # Export user productivity summary
        if st.button("📊 Export User Productivity Summary", use_container_width=True):
            csv_data = user_productivity.to_csv(index=False)
            st.download_button(
                "Download User Productivity CSV",
                csv_data,
                f"user_productivity_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
            )

    with col2:
        # Export detailed user activity
        if st.button("📋 Export Detailed User Activity", use_container_width=True):
            export_data = user_df[
                [
                    "created_by_username",
                    "created_by_name",
                    "product_type",
                    "overall_score",
                    "created_at",
                ]
            ].copy()
            csv_data = export_data.to_csv(index=False)
            st.download_button(
                "Download User Activity CSV",
                csv_data,
                f"user_activity_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
            )


# ================================
# TAB 8: PRODUCTS WITH FEEDBACK
# ================================


def render_products_with_feedback_dashboard(evaluations_df, feedback_df):
    """Display all products with human feedback using the same detailed format as Agreement Analysis."""
    st.header("📝 Products with Human Feedback")
    st.markdown("**Comprehensive view of all products that received human feedback**")

    if feedback_df.empty:
        st.info(
            "No human feedback available yet. Complete some human evaluations to see product details!"
        )
        return

    # Load all products with human feedback (same query as Agreement Analysis)
    merged_query = """
    SELECT
        e.id, e.product_config_id, e.overall_score, e.structure_score,
        e.accuracy_score, e.translation_score, e.product_type,
        e.evaluation_model, e.llm_reasoning, e.brand, e.product_name,
        e.input_text, e.extracted_json, e.created_at,
        h.human_rating, h.notes, h.created_at as feedback_date,
        h.created_by_username as feedback_username, h.created_by_name as feedback_user_name,
        h.user_id as feedback_user_id
    FROM evaluations e
    JOIN human_feedback h ON e.id = h.evaluation_id
    ORDER BY e.created_at DESC
    """

    merged_data = run_cached_query(merged_query)
    merged_df = pd.DataFrame(merged_data)

    if merged_df.empty:
        st.warning("No products with human feedback found.")
        return

    # Parse JSON data
    for idx, row in merged_df.iterrows():
        if row.get("extracted_json"):
            try:
                merged_df.at[idx, "extracted_json"] = json.loads(row["extracted_json"])
            except:
                merged_df.at[idx, "extracted_json"] = {}

    merged_df["score_diff"] = abs(
        merged_df["overall_score"] - merged_df["human_rating"]
    )

    # Summary Statistics
    st.subheader("📊 Summary Statistics")

    col1, col2, col3, col4 = st.columns(4)

    total_products = len(merged_df)
    avg_human_rating = merged_df["human_rating"].mean()
    avg_ai_score = merged_df["overall_score"].mean()
    avg_agreement = merged_df["score_diff"].mean()

    with col1:
        st.metric("Total Products", total_products)
    with col2:
        st.metric("Avg Human Rating", f"{avg_human_rating:.1f}/5")
    with col3:
        st.metric("Avg AI Score", f"{avg_ai_score:.1f}/5")
    with col4:
        st.metric("Avg Agreement Gap", f"±{avg_agreement:.1f}")

    # Filters
    st.subheader("🔍 Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        brands = ["All"] + sorted(merged_df["brand"].unique().tolist())
        selected_brand = st.selectbox("Filter by Brand", brands)

    with col2:
        product_types = ["All"] + sorted(merged_df["product_type"].unique().tolist())
        selected_type = st.selectbox("Filter by Product Type", product_types)

    with col3:
        rating_range = st.slider("Human Rating Range", 1, 5, (1, 5))

    # Apply filters
    filtered_df = merged_df.copy()

    if selected_brand != "All":
        filtered_df = filtered_df[filtered_df["brand"] == selected_brand]

    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["product_type"] == selected_type]

    filtered_df = filtered_df[
        (filtered_df["human_rating"] >= rating_range[0])
        & (filtered_df["human_rating"] <= rating_range[1])
        & (filtered_df["notes"].notna())
        & (filtered_df["notes"].str.strip() != "")
    ]

    if filtered_df.empty:
        st.warning("No products match the selected filters.")
        return

    # Display all products with detailed information
    st.subheader(f"🔍 Product Details ({len(filtered_df)} products)")
    st.markdown(
        "Each product shows the same comprehensive information as the Agreement Analysis tab"
    )

    for idx, row in filtered_df.iterrows():
        # Create expander title with key product info
        agreement_status = (
            "🟢 Good"
            if row["score_diff"] <= 1.0
            else "🟡 Fair" if row["score_diff"] <= 1.5 else "🔴 Poor"
        )
        expander_title = f"{agreement_status} | {row['brand']} - {row['product_name']} | AI={row['overall_score']:.1f}, Human={row['human_rating']}, Diff={row['score_diff']:.1f}"

        with st.expander(expander_title):
            # Product Information Section
            st.markdown("### 🏷️ Product Information")
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Brand:** {row['brand']}")
                st.write(f"**Product:** {row['product_name']}")
                st.write(f"**Type:** {row['product_type']}")

            with col2:
                st.write(f"**Evaluation ID:** {row['id']}")
                st.write(f"**Config ID:** {row['product_config_id']}")
                st.write(f"**Date:** {row['created_at'].strftime('%Y-%m-%d %H:%M')}")

            # Score Comparison Section
            st.markdown("### 📊 Score Comparison")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**🤖 AI Assessment**")
                st.write(f"Overall: {row['overall_score']:.1f}/5")
                st.write(f"Structure: {row['structure_score']}/5")
                st.write(f"Content: {row['accuracy_score']}/5")
                st.write(f"Translation: {row['translation_score']}/5")
                st.write(f"Model: {row['evaluation_model']}")

            with col2:
                st.markdown("**👥 Human Assessment**")
                st.write(f"Rating: {row['human_rating']}/5")
                st.write(f"Feedback Date: {row['feedback_date'].strftime('%Y-%m-%d')}")

                # Show feedback provider name
                feedback_user = (
                    row.get("feedback_user_name")
                    or row.get("feedback_username")
                    or "Unknown User"
                )
                if feedback_user and feedback_user != "System":
                    st.write(f"Feedback by: {feedback_user}")

                if row["notes"]:
                    st.markdown("**Human Notes:**")
                    st.text_area(
                        "Human Notes",
                        value=row["notes"],
                        height=120,
                        key=f"human_notes_feedback_{idx}",
                        disabled=True,
                        label_visibility="collapsed",
                    )
                else:
                    st.info("No human notes provided")

            # Input Text Section
            st.markdown("### 📝 Input Text")
            if row.get("input_text"):
                input_text = row["input_text"]
                if len(input_text) > 1000:
                    st.text_area(
                        "Full Input Text",
                        value=input_text,
                        height=200,
                        key=f"input_text_feedback_{idx}",
                        disabled=True,
                        label_visibility="collapsed",
                    )
                else:
                    st.text(input_text)
            else:
                st.info("No input text available")

            # JSON Output Section
            st.markdown("### 📋 Extracted JSON Output")
            if row.get("extracted_json") and isinstance(row["extracted_json"], dict):
                st.json(row["extracted_json"])
            else:
                st.info("No JSON output available")

            # AI Reasoning Section
            st.markdown("### 🤖 AI Reasoning")
            if row["llm_reasoning"]:
                # Parse and display reasoning in 3 columns if it contains separators
                if " | " in row["llm_reasoning"]:
                    reasoning_parts = row["llm_reasoning"].split(" | ")
                    col1, col2, col3 = st.columns(3)

                    for i, part in enumerate(reasoning_parts[:3]):
                        with [col1, col2, col3][i]:
                            if ":" in part:
                                metric, reasoning = part.split(":", 1)
                                st.markdown(f"**{metric.strip()}**")
                                st.caption(reasoning.strip())
                            else:
                                st.text(part)
                else:
                    st.text_area(
                        "AI Reasoning",
                        value=row["llm_reasoning"],
                        height=100,
                        key=f"ai_reasoning_feedback_{idx}",
                        disabled=True,
                        label_visibility="collapsed",
                    )
            else:
                st.info("No AI reasoning available")


# ================================
# UPDATE MAIN FUNCTION
# ================================


def main():
    """Enhanced main application with User Analytics tab"""
    st.title("🔬 Enhanced Quality Analytics Dashboard")

    # Load data using the fixed database
    try:
        db = get_db()

        # Load evaluations with complete data INCLUDING USER ATTRIBUTION
        evaluations_data = run_analytics_query(
            """
            SELECT 
                id, product_config_id, structure_score, accuracy_score, 
                translation_score, overall_score, evaluation_model,
                product_type, created_at, llm_reasoning, brand, product_name,
                input_text, extracted_json,
                user_id, created_by_username, created_by_name,
                CASE 
                    WHEN evaluation_model LIKE 'openevals%%' THEN 'OpenEvals'
                    WHEN evaluation_model LIKE 'fallback%%' THEN 'Fallback'
                    ELSE 'Legacy'
                END as evaluator_type
            FROM evaluations
            ORDER BY created_at DESC
        """
        )

        evaluations_df = pd.DataFrame(evaluations_data)

        # Load human feedback
        feedback_data = run_analytics_query(
            """
            SELECT 
                hf.evaluation_id, hf.human_rating, hf.notes,
                hf.created_at as feedback_date,
                e.overall_score as llm_score, e.product_type, e.evaluation_model
            FROM human_feedback hf
            JOIN evaluations e ON hf.evaluation_id = e.id
            ORDER BY hf.created_at DESC
        """
        )

        feedback_df = pd.DataFrame(feedback_data)

        # Convert datetime columns
        if not evaluations_df.empty:
            evaluations_df["created_at"] = pd.to_datetime(evaluations_df["created_at"])

        if not feedback_df.empty:
            feedback_df["feedback_date"] = pd.to_datetime(feedback_df["feedback_date"])

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return

    if evaluations_df.empty:
        st.warning(
            "No evaluation data found. Run some product extractions to see analytics."
        )
        return

    st.success(
        f"✅ Loaded {len(evaluations_df)} evaluations with complete product information"
    )

    # Create tabs - UPDATED WITH PRODUCTS WITH FEEDBACK TAB
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "📊 Executive Dashboard",
            "🤖👥 Agreement Analysis",
            "⚙️ Model Performance",
            "📈 Quality Deep Dive",
            "🔍 Investigation Tools",
            "📤 Reports & Export",
            "👥 User Analytics",
            "📝 Products with Feedback",  # NEW TAB
        ]
    )

    with tab1:
        render_executive_dashboard(evaluations_df, feedback_df)

    with tab2:
        render_enhanced_agreement_analysis(evaluations_df, feedback_df)

    with tab3:
        render_production_model_performance(evaluations_df, feedback_df)

    with tab4:
        render_quality_deep_dive(evaluations_df, feedback_df)

    with tab5:
        render_enhanced_investigation_tools(evaluations_df, feedback_df)

    with tab6:
        render_reports_export(evaluations_df, feedback_df)

    with tab7:  # USER ANALYTICS TAB
        render_user_analytics_dashboard(evaluations_df, feedback_df)

    with tab8:  # NEW PRODUCTS WITH FEEDBACK TAB
        render_products_with_feedback_dashboard(evaluations_df, feedback_df)

    # Footer
    st.markdown("---")
    st.markdown(
        "**🔬 Enhanced Analytics Dashboard** | PHASE 6: Complete with Products with Feedback View"
    )


if __name__ == "__main__":
    main()
