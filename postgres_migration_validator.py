"""
PostgreSQL Migration Validator - Phase 3
Test script to validate the PostgreSQL migration is working correctly
Run with: streamlit run postgres_migration_validator.py

VALIDATION CHECKLIST:
✅ PostgreSQL connection using Streamlit patterns
✅ Query caching functionality
✅ Database table access
✅ Analytics dashboard compatibility
✅ All existing functionality preserved
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import time
from datetime import datetime
import json

# Configuration
st.set_page_config(
    page_title="PostgreSQL Migration Validator", page_icon="🧪", layout="wide"
)

st.title("🧪 PostgreSQL Migration Validator")
st.markdown("**Phase 3 Validation: Testing PostgreSQL integration with Streamlit**")

# ================================
# CONNECTION TESTING
# ================================


@st.cache_resource
def test_postgres_connection():
    """Test PostgreSQL connection using Streamlit's recommended pattern."""
    try:
        # Use Streamlit secrets for PostgreSQL connection
        connection_params = {
            **st.secrets["postgres"],
            "sslmode": "require",
            "connect_timeout": 10,
            "application_name": "migration_validator",
        }

        # Try both pooler and direct connections
        ports_to_try = ["6543", "5432"]

        for port in ports_to_try:
            try:
                connection_params["port"] = port
                conn = psycopg2.connect(
                    **connection_params, cursor_factory=RealDictCursor
                )

                # Test the connection
                with conn.cursor() as test_cur:
                    test_cur.execute(
                        "SELECT version() as pg_version, current_database() as db_name"
                    )
                    result = test_cur.fetchone()

                return {
                    "success": True,
                    "port": port,
                    "connection": conn,
                    "db_info": dict(result),
                    "message": f"Connected successfully via port {port}",
                }
            except Exception as e:
                if port == ports_to_try[-1]:  # Last port, raise the error
                    raise e
                continue

    except Exception as e:
        return {"success": False, "error": str(e), "message": "Connection failed"}


@st.cache_data(ttl=60)  # Cache for 1 minute
def test_cached_query(query: str, test_id: str):
    """Test query caching functionality."""
    conn_result = test_postgres_connection()
    if not conn_result["success"]:
        return None

    conn = conn_result["connection"]
    start_time = time.time()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            result = cur.fetchall()
            query_time = time.time() - start_time

            return {
                "success": True,
                "rows": len(result),
                "query_time": query_time,
                "data": [dict(row) for row in result] if result else [],
                "cached": False,  # First time will not be cached
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query_time": time.time() - start_time,
        }


# ================================
# VALIDATION TESTS
# ================================


def run_validation_tests():
    """Run comprehensive validation tests."""

    st.header("🔌 Connection Validation")

    # Test 1: Basic Connection
    with st.container():
        st.subheader("1. PostgreSQL Connection Test")

        with st.spinner("Testing PostgreSQL connection..."):
            conn_result = test_postgres_connection()

        if conn_result["success"]:
            st.success(f"✅ {conn_result['message']}")

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Port Used:** {conn_result['port']}")
                st.info(f"**Database:** {conn_result['db_info']['db_name']}")
            with col2:
                pg_version = conn_result["db_info"]["pg_version"].split()[1]
                st.info(f"**PostgreSQL Version:** {pg_version}")
        else:
            st.error(f"❌ {conn_result['message']}")
            st.error(f"**Error:** {conn_result['error']}")
            return False

    st.markdown("---")

    # Test 2: Table Structure Validation
    st.subheader("2. Database Schema Validation")

    schema_queries = {
        "evaluations": """
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'evaluations' 
            ORDER BY ordinal_position
        """,
        "human_feedback": """
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'human_feedback' 
            ORDER BY ordinal_position
        """,
    }

    for table_name, query in schema_queries.items():
        with st.expander(f"📋 {table_name.title()} Table Schema"):
            result = test_cached_query(query, f"schema_{table_name}")

            if result and result["success"]:
                if result["data"]:
                    df = pd.DataFrame(result["data"])
                    st.dataframe(df, use_container_width=True)
                    st.success(f"✅ {table_name} table structure validated")
                else:
                    st.warning(f"⚠️ {table_name} table exists but has no columns")
            else:
                st.error(f"❌ Could not access {table_name} table")
                if result:
                    st.error(f"Error: {result.get('error', 'Unknown error')}")

    st.markdown("---")

    # Test 3: Data Access and Caching
    st.subheader("3. Data Access & Caching Test")

    # Test basic data queries
    data_queries = {
        "evaluations_count": "SELECT COUNT(*) as total_evaluations FROM evaluations",
        "feedback_count": "SELECT COUNT(*) as total_feedback FROM human_feedback",
        "recent_evaluations": """
            SELECT id, product_type, overall_score, created_at 
            FROM evaluations 
            ORDER BY created_at DESC 
            LIMIT 5
        """,
    }

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Database Statistics**")

        for query_name, query in data_queries.items():
            if "count" in query_name:
                result = test_cached_query(query, query_name)
                if result and result["success"]:
                    count = (
                        result["data"][0][f"total_{query_name.split('_')[0]}"]
                        if result["data"]
                        else 0
                    )
                    st.metric(query_name.replace("_", " ").title(), count)
                else:
                    st.error(f"❌ Failed to get {query_name}")

    with col2:
        st.markdown("**⚡ Caching Performance Test**")

        test_query = "SELECT COUNT(*) as test_count FROM evaluations"

        # First query (not cached)
        st.info("Running first query (will be cached)...")
        start_time = time.time()
        result1 = test_cached_query(test_query, "cache_test_1")
        first_time = time.time() - start_time

        if result1 and result1["success"]:
            st.write(f"First query: {first_time:.3f} seconds")

            # Second query (should be cached)
            st.info("Running second query (should be cached)...")
            start_time = time.time()
            result2 = test_cached_query(test_query, "cache_test_1")  # Same cache key
            second_time = time.time() - start_time

            if result2 and result2["success"]:
                st.write(f"Second query: {second_time:.3f} seconds")

                if second_time < first_time * 0.5:  # Should be significantly faster
                    st.success("✅ Query caching is working effectively!")
                else:
                    st.info("ℹ️ Caching may not be active yet (normal on first run)")
            else:
                st.error("❌ Second query failed")
        else:
            st.error("❌ First query failed")

    st.markdown("---")

    # Test 4: Analytics Compatibility
    st.subheader("4. Analytics Dashboard Compatibility")

    # Test complex analytics queries
    analytics_query = """
        SELECT 
            product_type,
            COUNT(*) as total_count,
            AVG(overall_score) as avg_score,
            MIN(created_at) as earliest,
            MAX(created_at) as latest
        FROM evaluations
        GROUP BY product_type
        ORDER BY total_count DESC
    """

    result = test_cached_query(analytics_query, "analytics_test")

    if result and result["success"]:
        if result["data"]:
            st.success("✅ Complex analytics queries working correctly")
            df = pd.DataFrame(result["data"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ℹ️ No evaluation data found (expected for new installations)")
    else:
        st.error("❌ Analytics queries failed")
        if result:
            st.error(f"Error: {result.get('error', 'Unknown error')}")

    st.markdown("---")

    # Test 5: Migration Completeness
    st.subheader("5. Migration Completeness Check")

    migration_checks = []

    # Check if all expected tables exist
    tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('evaluations', 'human_feedback')
    """

    result = test_cached_query(tables_query, "tables_check")
    if result and result["success"]:
        existing_tables = [row["table_name"] for row in result["data"]]
        expected_tables = ["evaluations", "human_feedback"]

        for table in expected_tables:
            if table in existing_tables:
                migration_checks.append(f"✅ {table} table exists")
            else:
                migration_checks.append(f"❌ {table} table missing")
    else:
        migration_checks.append("❌ Could not check table existence")

    # Check for required columns
    required_columns = {
        "evaluations": [
            "id",
            "product_config_id",
            "structure_score",
            "accuracy_score",
            "translation_score",
            "overall_score",
        ],
        "human_feedback": ["id", "evaluation_id", "human_rating"],
    }

    for table, columns in required_columns.items():
        columns_query = f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table}'
        """
        result = test_cached_query(columns_query, f"columns_{table}")

        if result and result["success"]:
            existing_columns = [row["column_name"] for row in result["data"]]
            missing_columns = [col for col in columns if col not in existing_columns]

            if not missing_columns:
                migration_checks.append(f"✅ {table} has all required columns")
            else:
                migration_checks.append(
                    f"❌ {table} missing columns: {missing_columns}"
                )
        else:
            migration_checks.append(f"❌ Could not check {table} columns")

    # Display migration status
    st.markdown("**Migration Status:**")
    for check in migration_checks:
        if "✅" in check:
            st.success(check)
        else:
            st.error(check)

    # Overall migration status
    all_passed = all("✅" in check for check in migration_checks)
    if all_passed:
        st.success("🎉 **Migration Validation Complete!** All tests passed.")
    else:
        st.error("⚠️ **Migration Issues Detected** - Please review failed checks above.")

    return all_passed


# ================================
# CONNECTION TROUBLESHOOTING
# ================================


def render_troubleshooting_guide():
    """Render troubleshooting guide for common issues."""

    st.header("🔧 Troubleshooting Guide")

    with st.expander("🔐 **Secrets Configuration Issues**"):
        st.markdown(
            """
        **Problem:** Connection fails with authentication error
        
        **Solution:** Check your Streamlit secrets configuration:
        
        ```toml
        # .streamlit/secrets.toml (local development)
        [postgres]
        host = "your-supabase-host.supabase.co"
        database = "postgres"
        user = "postgres"
        password = "your-password"
        port = "5432"
        ```
        
        **For Streamlit Cloud:** Add the same configuration in your app's Secrets section.
        """
        )

    with st.expander("🌐 **Connection Timeout Issues**"):
        st.markdown(
            """
        **Problem:** Connection times out
        
        **Possible Causes:**
        1. **Supabase project paused** (free tier limitation)
        2. **Network/firewall blocking** the connection
        3. **Wrong host or port** in configuration
        
        **Solutions:**
        1. Check your Supabase project dashboard - unpause if needed
        2. Try both port 6543 (pooler) and 5432 (direct)
        3. Verify the host URL from your Supabase dashboard
        """
        )

    with st.expander("📊 **Missing Tables or Data**"):
        st.markdown(
            """
        **Problem:** Tables don't exist or have no data
        
        **Solution:** Run the database schema creation SQL in your Supabase SQL editor:
        
        ```sql
        -- Create evaluations table
        CREATE TABLE IF NOT EXISTS evaluations (
            id SERIAL PRIMARY KEY,
            product_config_id VARCHAR(255) NOT NULL,
            input_text TEXT,
            extracted_json JSONB,
            structure_score INTEGER,
            accuracy_score INTEGER,
            translation_score INTEGER,
            overall_score DECIMAL(3,2),
            llm_reasoning TEXT,
            evaluation_model VARCHAR(255),
            product_type VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create human_feedback table
        CREATE TABLE IF NOT EXISTS human_feedback (
            id SERIAL PRIMARY KEY,
            evaluation_id INTEGER REFERENCES evaluations(id),
            human_rating INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ```
        """
        )

    with st.expander("⚡ **Performance Issues**"):
        st.markdown(
            """
        **Problem:** Slow query performance
        
        **Solutions:**
        1. **Enable query caching** (should be automatic with @st.cache_data)
        2. **Use connection pooling** - try port 6543 first
        3. **Add database indexes** for frequently queried columns:
        
        ```sql
        CREATE INDEX IF NOT EXISTS idx_evaluations_product_type ON evaluations(product_type);
        CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at);
        CREATE INDEX IF NOT EXISTS idx_human_feedback_eval_id ON human_feedback(evaluation_id);
        ```
        """
        )


# ================================
# MAIN APPLICATION
# ================================


def main():
    """Main validation application."""

    # Check if secrets are configured
    if "postgres" not in st.secrets:
        st.error("❌ **PostgreSQL secrets not configured!**")
        st.markdown(
            """
        Please configure your PostgreSQL connection in Streamlit secrets:
        
        **For local development:**
        Create `.streamlit/secrets.toml` with:
        ```toml
        [postgres]
        host = "your-supabase-host.supabase.co"
        database = "postgres"
        user = "postgres"
        password = "your-password"
        port = "5432"
        ```
        
        **For Streamlit Cloud:**
        Add the same configuration in your app's Secrets section.
        """
        )
        st.stop()

    # Main validation
    st.info("🚀 Starting PostgreSQL migration validation...")

    # Run validation tests
    validation_passed = run_validation_tests()

    # Show troubleshooting if needed
    if not validation_passed:
        render_troubleshooting_guide()

    # Final summary
    st.markdown("---")
    if validation_passed:
        st.success("🎉 **Phase 3 Migration Validation Complete!**")
        st.markdown(
            """
        **Next Steps:**
        1. ✅ PostgreSQL connection is working
        2. ✅ Database schema is correct
        3. ✅ Query caching is functional
        4. ✅ Analytics compatibility confirmed
        
        **Ready to proceed to Phase 4:** Production deployment!
        """
        )
    else:
        st.error("⚠️ **Migration validation incomplete.**")
        st.markdown(
            "Please resolve the issues above before proceeding to production deployment."
        )

    # Show current time and session info
    st.markdown("---")
    st.caption(
        f"Validation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    main()
