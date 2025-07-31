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

                    if row["notes"]:
                        st.markdown("**Human Notes:**")
                        st.text_area(
                            "Human Notes",
                            value=row["notes"],
                            height=80,
                            key=f"human_notes_{idx}",
                            disabled=True,
                            label_visibility="collapsed",
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
    """FIXED: Production model performance analysis with graceful handling of missing columns."""
    st.header("🏭 Production Model Performance")
    st.markdown(
        "**Analyze performance of LLMs that create product JSON (Llama, GPT-4, etc.)**"
    )

    if evaluations_df.empty:
        st.info("No evaluation data available.")
        return

    # FIXED: Check if production model columns exist in database
    try:
        # Try to query for production model columns
        production_columns_check = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'evaluations' 
        AND column_name IN ('production_model_provider', 'production_model_name', 'production_temperature')
        """

        existing_columns = run_analytics_query(production_columns_check)
        production_columns_exist = len(existing_columns) >= 3

    except Exception as e:
        production_columns_exist = False

    if not production_columns_exist:
        # FIXED: Show helpful message and alternative analysis
        st.warning("⚠️ **Production Model Tracking Not Yet Implemented**")

        st.info(
            """
        **What is Production Model Performance?**
        This feature tracks which LLM models (GPT-4, Llama, etc.) are used to *create* the product JSON, 
        separate from the evaluation models that *assess* the quality.
        
        **To enable this feature:**
        1. Database schema needs to be updated with production model columns
        2. Evaluation storage needs to capture model information from ProductConfig objects
        3. Re-run extractions to populate the new data
        """
        )

        # Show alternative analysis using available data
        st.subheader("📊 Available Analysis: Evaluator Model Performance")
        st.caption("Performance of models used to *evaluate* extraction quality")

        # Analysis using evaluation_model field (which does exist)
        if len(evaluations_df) > 0:
            model_stats = (
                evaluations_df.groupby("evaluation_model")
                .agg(
                    {
                        "overall_score": ["mean", "count", "std"],
                        "structure_score": "mean",
                        "accuracy_score": "mean",
                        "translation_score": "mean",
                        "created_at": ["min", "max"],
                    }
                )
                .round(3)
            )

            model_stats.columns = [
                "avg_quality",
                "evaluations",
                "quality_std",
                "avg_structure",
                "avg_content",
                "avg_translation",
                "first_used",
                "last_used",
            ]
            model_stats = model_stats.reset_index()
            model_stats["quality_std"] = model_stats["quality_std"].fillna(0)

            st.dataframe(model_stats, use_container_width=True)

            # Evaluator model comparison chart
            if len(model_stats) > 1:
                fig = px.bar(
                    model_stats,
                    x="evaluation_model",
                    y="avg_quality",
                    title="Average Quality by Evaluation Model",
                    labels={
                        "avg_quality": "Average Quality Score",
                        "evaluation_model": "Evaluation Model",
                    },
                    text="evaluations",
                )
                fig.update_layout(yaxis_range=[1, 5], xaxis_tickangle=-45)
                fig.update_traces(texttemplate="%{text} evals", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

            # Product type performance (available data)
            st.subheader("📋 Performance by Product Type")

            product_type_stats = (
                evaluations_df.groupby("product_type")
                .agg(
                    {
                        "overall_score": ["mean", "count"],
                        "structure_score": "mean",
                        "accuracy_score": "mean",
                        "translation_score": "mean",
                    }
                )
                .round(2)
                .reset_index()
            )

            product_type_stats.columns = [
                "product_type",
                "avg_quality",
                "count",
                "avg_structure",
                "avg_content",
                "avg_translation",
            ]

            fig = px.bar(
                product_type_stats,
                x="product_type",
                y="avg_quality",
                title="Average Quality by Product Type",
                labels={
                    "avg_quality": "Average Quality Score",
                    "product_type": "Product Type",
                },
                text="count",
            )
            fig.update_layout(yaxis_range=[1, 5])
            fig.update_traces(texttemplate="%{text} products", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        # Migration instructions
        st.subheader("🔧 Enable Production Model Tracking")

        with st.expander("📋 Implementation Guide"):
            st.markdown(
                """
            **Step 1: Update Database Schema**
            ```sql
            ALTER TABLE evaluations 
            ADD COLUMN production_model_provider VARCHAR(50) DEFAULT '',
            ADD COLUMN production_model_name VARCHAR(100) DEFAULT '',
            ADD COLUMN production_temperature DECIMAL(3,2) DEFAULT 0.0;
            ```
            
            **Step 2: Update Evaluation Storage**
            Modify `evaluation_core.py` to capture production model info from ProductConfig:
            - `evaluate_single_product()` should accept model_provider, model_name, temperature
            - `store_openevals_evaluation()` should store these values
            
            **Step 3: Update Batch Processing**
            Modify `batch_processor.py` to pass model info to evaluation functions
            
            **Step 4: Re-run Extractions**
            Process some new products to populate the production model data
            """
            )

        return

    # If production model columns exist, run full analysis
    st.success("✅ Production model columns found - running full analysis")

    production_data_query = """
    SELECT 
        id, product_config_id, overall_score, structure_score, 
        accuracy_score, translation_score, product_type, created_at,
        production_model_provider, production_model_name, 
        production_temperature, brand, product_name,
        CASE 
            WHEN production_model_provider = '' OR production_model_name = '' 
            THEN 'Legacy (No Model Info)'
            ELSE CONCAT(production_model_provider, '/', production_model_name)
        END as production_model_full,
        CASE 
            WHEN production_model_provider = '' THEN 'Unknown'
            ELSE production_model_provider 
        END as provider_clean
    FROM evaluations
    WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
    ORDER BY created_at DESC
    """

    try:
        production_data = run_analytics_query(production_data_query)
        production_df = pd.DataFrame(production_data)

        if production_df.empty:
            st.warning("No production model data available in the last 90 days.")
            return

        # Convert to proper data types
        production_df["created_at"] = pd.to_datetime(production_df["created_at"])
        for col in [
            "overall_score",
            "structure_score",
            "accuracy_score",
            "translation_score",
            "production_temperature",
        ]:
            production_df[col] = pd.to_numeric(production_df[col], errors="coerce")

        # Rest of production model analysis would go here
        st.info("Production model analysis would continue here with full data...")

    except Exception as e:
        st.error(f"Error in production model analysis: {str(e)}")
        return


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

                with col2:
                    if feedback_row["notes"]:
                        st.text_area(
                            "Human Notes",
                            value=feedback_row["notes"],
                            height=68,
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

    # Create tabs - ADD THE NEW USER ANALYTICS TAB
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "📊 Executive Dashboard",
            "🤖👥 Agreement Analysis",
            "⚙️ Model Performance",
            "📈 Quality Deep Dive",
            "🔍 Investigation Tools",
            "📤 Reports & Export",
            "👥 User Analytics",  # NEW TAB
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

    with tab7:  # NEW USER ANALYTICS TAB
        render_user_analytics_dashboard(evaluations_df, feedback_df)

    # Footer
    st.markdown("---")
    st.markdown(
        "**🔬 Enhanced Analytics Dashboard** | PHASE 5: Complete with User Analytics & Reporting"
    )


if __name__ == "__main__":
    main()
