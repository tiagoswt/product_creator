"""
Enhanced PostgreSQL database for evaluation system - PHASE 3 USER TRACKING
ADDED: Complete user attribution for product creation tracking
"""

import streamlit as st

try:
    import psycopg2
except ImportError:
    import psycopg2.extensions as psycopg2

from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


def _sanitize_for_postgres(data: Any) -> Any:
    """
    Remove NUL characters (0x00) from data to prevent PostgreSQL errors.
    PostgreSQL TEXT/VARCHAR columns cannot store NUL characters.

    Args:
        data: Any data type (str, dict, list, etc.)

    Returns:
        Sanitized data with NUL characters removed from all strings
    """
    if data is None:
        return None

    if isinstance(data, str):
        # Remove NUL characters from strings
        return data.replace('\x00', '')

    if isinstance(data, dict):
        # Recursively sanitize dictionary values
        return {key: _sanitize_for_postgres(value) for key, value in data.items()}

    if isinstance(data, list):
        # Recursively sanitize list items
        return [_sanitize_for_postgres(item) for item in data]

    # Return other types unchanged (int, float, bool, etc.)
    return data


def extract_brand_from_json(extracted_json: Dict) -> str:
    """Extract brand from extracted JSON, handling different product structures."""
    try:
        # Try different field names and structures
        brand_fields = ["brand", "Brand", "BRAND"]

        for field in brand_fields:
            # Handle nested catalogA or catalogB structure
            for catalog in ["catalogA", "catalogB"]:
                if catalog in extracted_json and isinstance(
                    extracted_json[catalog], dict
                ):
                    value = extracted_json[catalog].get(field)
                    if (
                        value
                        and str(value).strip()
                        and str(value).lower() not in ["", "null", "none", "unknown"]
                    ):
                        return str(value).strip()

            # Handle flat structure (fragrance)
            value = extracted_json.get(field)
            if (
                value
                and str(value).strip()
                and str(value).lower() not in ["", "null", "none", "unknown"]
            ):
                return str(value).strip()

        return "Unknown Brand"
    except Exception as e:
        print(f"Error extracting brand: {str(e)}")
        return "Unknown Brand"


def extract_product_name_from_json(extracted_json: Dict) -> str:
    """Extract product name from extracted JSON, handling different product structures."""
    try:
        # Try different field names in order of preference - UrlEN first, then existing fields
        name_fields = [
            "UrlEN",  # Primary preference - SEO URL slug
            "ItemDescriptionEN",  # For cosmetics and subtype (updated case)
            "itemDescriptionEN",  # For cosmetics and subtype (legacy case)
            "product_name",  # For fragrance
            "product_title_EN",  # Alternative from catalogA
            "ItemDescriptionPT",  # Portuguese fallback (updated case)
            "itemDescriptionPT",  # Portuguese fallback (legacy case)
            "product_title_PT",  # Portuguese fallback
        ]

        for field in name_fields:
            # Handle nested catalogB structure
            if "catalogB" in extracted_json and isinstance(
                extracted_json["catalogB"], dict
            ):
                value = extracted_json["catalogB"].get(field)
                if (
                    value
                    and str(value).strip()
                    and str(value).lower() not in ["", "null", "none", "unknown"]
                ):
                    return str(value).strip()

            # Handle nested catalogA structure
            if "catalogA" in extracted_json and isinstance(
                extracted_json["catalogA"], dict
            ):
                value = extracted_json["catalogA"].get(field)
                if (
                    value
                    and str(value).strip()
                    and str(value).lower() not in ["", "null", "none", "unknown"]
                ):
                    return str(value).strip()

            # Handle flat structure (fragrance)
            value = extracted_json.get(field)
            if (
                value
                and str(value).strip()
                and str(value).lower() not in ["", "null", "none", "unknown"]
            ):
                return str(value).strip()

        return "Unknown Product"
    except Exception as e:
        print(f"Error extracting product name: {str(e)}")
        return "Unknown Product"


# Streamlit-optimized connection pattern
@st.cache_resource
def get_postgres_connection():
    """Get cached PostgreSQL connection with no success messages."""
    try:
        # Use Streamlit secrets for PostgreSQL connection
        connection_params = {
            **st.secrets["postgres"],
            "sslmode": "require",  # Required for Supabase
            "connect_timeout": 10,  # 10 second timeout
            "application_name": "analytics_dashboard",  # Help identify connections
        }

        # Try connection pool port first (6543), then direct port (5432)
        original_port = connection_params.get("port", "5432")

        # First try: Use pooler port 6543 (recommended for Supabase)
        if original_port == "5432":
            connection_params["port"] = "6543"
            try:
                conn = psycopg2.connect(
                    **connection_params, cursor_factory=RealDictCursor
                )
                # Test the connection
                with conn.cursor() as test_cur:
                    test_cur.execute("SELECT 1 as test")
                    test_cur.fetchone()
                return conn
            except (psycopg2.OperationalError, psycopg2.Error):
                pass  # Try direct connection

        # Second try: Use direct connection port 5432
        connection_params["port"] = "5432"
        conn = psycopg2.connect(**connection_params, cursor_factory=RealDictCursor)

        # Test the connection
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
def run_cached_query(query: str, params: tuple = None):
    """Execute SELECT queries with caching for better performance."""
    conn = get_postgres_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            result = cur.fetchall()
            return list(result) if result else []
    except Exception as e:
        # Only show errors if explicitly called from analytics dashboard
        if "analytics" in str(st.session_state.get("current_page", "")):
            st.error(f"Query failed: {str(e)}")
        run_cached_query.clear()
        raise


def run_write_query(query: str, params: tuple = None, fetch_result: bool = False):
    """Execute INSERT/UPDATE/DELETE queries without caching."""
    conn = get_postgres_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            conn.commit()

            if fetch_result:
                result = cur.fetchone()
                return result if result else None
            else:
                return cur.rowcount
    except Exception as e:
        conn.rollback()
        # Only show errors for critical operations
        if "human_feedback" not in query.lower():  # Don't show for optional operations
            st.error(f"Database write failed: {str(e)}")
        run_cached_query.clear()
        raise


class EvaluationDB:
    """Enhanced PostgreSQL database with PHASE 3 USER TRACKING for product attribution."""

    def __init__(self, db_path: str = None):
        # db_path parameter kept for backward compatibility but ignored
        self.connection = get_postgres_connection
        self._ensure_tables_exist()
        self._migrate_schema_if_needed()

    def _ensure_tables_exist(self):
        """Ensure database tables exist with user tracking."""
        try:
            # Create evaluations table with user tracking
            create_evaluations_table = """
            CREATE TABLE IF NOT EXISTS evaluations (
                id SERIAL PRIMARY KEY,
                product_config_id VARCHAR(255) NOT NULL,
                input_text TEXT DEFAULT '',
                extracted_json JSONB DEFAULT '{}',
                structure_score INTEGER DEFAULT 3,
                accuracy_score INTEGER DEFAULT 3,
                translation_score INTEGER DEFAULT 3,
                overall_score DECIMAL(3,2) DEFAULT 3.00,
                llm_reasoning TEXT DEFAULT '',
                evaluation_model VARCHAR(255) DEFAULT '',
                product_type VARCHAR(100) DEFAULT '',
                brand VARCHAR(255) DEFAULT 'Unknown Brand',
                product_name VARCHAR(500) DEFAULT 'Unknown Product',
                user_id UUID REFERENCES users(id),
                created_by_username VARCHAR(50) DEFAULT '',
                created_by_name VARCHAR(100) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

            # Create human_feedback table if it doesn't exist
            create_feedback_table = """
            CREATE TABLE IF NOT EXISTS human_feedback (
                id SERIAL PRIMARY KEY,
                evaluation_id INTEGER REFERENCES evaluations(id) ON DELETE CASCADE,
                human_rating INTEGER NOT NULL CHECK (human_rating BETWEEN 1 AND 5),
                notes TEXT DEFAULT '',
                user_id UUID REFERENCES users(id),
                created_by_username VARCHAR(50) DEFAULT '',
                created_by_name VARCHAR(100) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

            run_write_query(create_evaluations_table)
            run_write_query(create_feedback_table)

            # Create indexes for better performance
            create_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_evaluations_config_id ON evaluations(product_config_id)",
                "CREATE INDEX IF NOT EXISTS idx_evaluations_product_type ON evaluations(product_type)",
                "CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_evaluations_brand ON evaluations(brand)",
                "CREATE INDEX IF NOT EXISTS idx_evaluations_user_id ON evaluations(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_evaluations_created_by ON evaluations(created_by_username)",
                "CREATE INDEX IF NOT EXISTS idx_human_feedback_eval_id ON human_feedback(evaluation_id)",
            ]

            for index_query in create_indexes:
                try:
                    run_write_query(index_query)
                except:
                    pass  # Index might already exist

        except Exception as e:
            st.warning(f"Could not create database tables: {str(e)}")

    def _migrate_schema_if_needed(self):
        """Add user tracking columns if they don't exist."""
        try:
            # Check if new columns exist in evaluations table
            evaluations_columns_query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'evaluations'
            AND column_name IN ('brand', 'product_name', 'input_text', 'extracted_json', 'user_id', 'created_by_username', 'created_by_name')
            """

            # Check if user tracking columns exist in human_feedback table
            feedback_columns_query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'human_feedback'
            AND column_name IN ('user_id', 'created_by_username', 'created_by_name')
            """

            existing_evaluations_columns = run_cached_query(evaluations_columns_query)
            existing_evaluations_column_names = [row["column_name"] for row in existing_evaluations_columns]

            existing_feedback_columns = run_cached_query(feedback_columns_query)
            existing_feedback_column_names = [row["column_name"] for row in existing_feedback_columns]

            # Add missing columns
            migrations = []

            # Evaluations table migrations
            if "brand" not in existing_evaluations_column_names:
                migrations.append(
                    "ALTER TABLE evaluations ADD COLUMN brand VARCHAR(255) DEFAULT 'Unknown Brand'"
                )

            if "product_name" not in existing_evaluations_column_names:
                migrations.append(
                    "ALTER TABLE evaluations ADD COLUMN product_name VARCHAR(500) DEFAULT 'Unknown Product'"
                )

            if "input_text" not in existing_evaluations_column_names:
                migrations.append(
                    "ALTER TABLE evaluations ADD COLUMN input_text TEXT DEFAULT ''"
                )

            if "extracted_json" not in existing_evaluations_column_names:
                migrations.append(
                    "ALTER TABLE evaluations ADD COLUMN extracted_json JSONB DEFAULT '{}'"
                )

            # PHASE 3: Add user tracking columns to evaluations
            if "user_id" not in existing_evaluations_column_names:
                migrations.append(
                    "ALTER TABLE evaluations ADD COLUMN user_id UUID REFERENCES users(id)"
                )

            if "created_by_username" not in existing_evaluations_column_names:
                migrations.append(
                    "ALTER TABLE evaluations ADD COLUMN created_by_username VARCHAR(50) DEFAULT ''"
                )

            if "created_by_name" not in existing_evaluations_column_names:
                migrations.append(
                    "ALTER TABLE evaluations ADD COLUMN created_by_name VARCHAR(100) DEFAULT ''"
                )

            # Add user tracking columns to human_feedback table
            if "user_id" not in existing_feedback_column_names:
                migrations.append(
                    "ALTER TABLE human_feedback ADD COLUMN user_id UUID REFERENCES users(id)"
                )

            if "created_by_username" not in existing_feedback_column_names:
                migrations.append(
                    "ALTER TABLE human_feedback ADD COLUMN created_by_username VARCHAR(50) DEFAULT ''"
                )

            if "created_by_name" not in existing_feedback_column_names:
                migrations.append(
                    "ALTER TABLE human_feedback ADD COLUMN created_by_name VARCHAR(100) DEFAULT ''"
                )

            for migration in migrations:
                run_write_query(migration)
                column_name = migration.split("ADD COLUMN")[1].split()[0]
                st.info(f"✅ Database schema updated: {column_name}")

            # Clear cache after schema changes
            run_cached_query.clear()

        except Exception as e:
            # Silent migration failure
            pass

    def store_evaluation(
        self,
        product_config_id: str,
        input_text: str,
        extracted_json: Dict,
        scores: Dict[str, float],
        llm_reasoning: str,
        evaluation_model: str,
        product_type: str,
        user_id: str = None,
        username: str = None,
        user_name: str = None,
    ) -> int:
        """
        PHASE 3: Store evaluation with user attribution.

        Args:
            user_id: UUID of the user who created this product
            username: Username of the creator
            user_name: Full name of the creator
        """

        # FIXED: Ensure we have valid input text
        if not input_text or not input_text.strip():
            input_text = f"Product extraction for {product_type}"

        # FIXED: Ensure we have valid JSON
        if not extracted_json:
            extracted_json = {"error": "No extracted data available"}

        # Extract brand and product name from JSON
        brand = extract_brand_from_json(extracted_json)
        product_name = extract_product_name_from_json(extracted_json)

        # PHASE 3: Get user context from session state if not provided
        if not user_id and "current_user" in st.session_state:
            current_user = st.session_state["current_user"]
            user_id = current_user.get("id")
            username = current_user.get("username", "unknown")
            user_name = current_user.get("name", "Unknown User")

        # Default values for user attribution
        user_id = user_id or None
        username = username or "system"
        user_name = user_name or "System"

        # Debug info
        print(
            f"STORING EVALUATION: brand='{brand}', product_name='{product_name}', creator='{username}'"
        )
        print(f"Input text length: {len(input_text)}")
        print(f"JSON keys: {list(extracted_json.keys())}")

        # Sanitize data to remove NUL characters before database insert
        input_text = _sanitize_for_postgres(input_text)
        extracted_json = _sanitize_for_postgres(extracted_json)
        llm_reasoning = _sanitize_for_postgres(llm_reasoning or "No reasoning provided")
        brand = _sanitize_for_postgres(brand)
        product_name = _sanitize_for_postgres(product_name)
        username = _sanitize_for_postgres(username)
        user_name = _sanitize_for_postgres(user_name)

        query = """
        INSERT INTO evaluations (
            product_config_id, input_text, extracted_json,
            structure_score, accuracy_score, translation_score, overall_score,
            llm_reasoning, evaluation_model, product_type, brand, product_name,
            user_id, created_by_username, created_by_name
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            product_config_id,
            input_text,  # FIXED: Store complete input text (sanitized)
            json.dumps(
                extracted_json, ensure_ascii=False
            ),  # FIXED: Store complete JSON (sanitized)
            scores.get("structure_score", 3),
            scores.get("accuracy_score", 3),
            scores.get("translation_score", 3),
            scores.get("overall_score", 3.0),
            llm_reasoning,
            evaluation_model or "Unknown model",
            product_type,
            brand,
            product_name,
            user_id,  # PHASE 3: User attribution
            username,  # PHASE 3: User attribution
            user_name,  # PHASE 3: User attribution
        )

        result = run_write_query(query, params, fetch_result=True)
        run_cached_query.clear()

        if result:
            st.info(
                f"✅ Stored evaluation for: {brand} - {product_name} (Created by: {username})"
            )

        return result["id"] if result else None

    def store_openevals_evaluation(
        self,
        product_config_id: str,
        openevals_results: Dict,
        product_type: str,
        input_text: str = "",
        extracted_json: Dict = None,
        user_id: str = None,
        username: str = None,
        user_name: str = None,
    ) -> int:
        """
        PHASE 3: Store OpenEvals results with user attribution.

        Args:
            user_id: UUID of the user who created this product
            username: Username of the creator
            user_name: Full name of the creator
        """

        # FIXED: Validate and ensure we have proper input data
        if not input_text or not input_text.strip():
            input_text = f"OpenEvals evaluation for {product_type} product"

        if not extracted_json:
            extracted_json = {"error": "No extracted JSON available"}

        # Extract scores from OpenEvals results
        structure_score = openevals_results.get("structure_correctness", {}).get(
            "score", 3
        )
        content_score = openevals_results.get("content_correctness", {}).get("score", 3)
        translation_score = openevals_results.get("translation_correctness", {}).get(
            "score", 3
        )
        overall_score = openevals_results.get("overall_score", 3.0)

        # Validate scores are in 1-5 range
        structure_score = max(1, min(5, int(structure_score)))
        content_score = max(1, min(5, int(content_score)))
        translation_score = max(1, min(5, int(translation_score)))
        overall_score = max(1.0, min(5.0, float(overall_score)))

        # FIXED: Extract brand and product name from JSON
        brand = extract_brand_from_json(extracted_json)
        product_name = extract_product_name_from_json(extracted_json)

        # PHASE 3: Get user context from session state if not provided
        if not user_id and "current_user" in st.session_state:
            current_user = st.session_state["current_user"]
            user_id = current_user.get("id")
            username = current_user.get("username", "unknown")
            user_name = current_user.get("name", "Unknown User")

        # Default values for user attribution
        user_id = user_id or None
        username = username or "system"
        user_name = user_name or "System"

        # Debug info
        print(
            f"STORING OPENEVALS: brand='{brand}', product_name='{product_name}', creator='{username}'"
        )
        print(f"Input text length: {len(input_text)}")
        print(f"JSON keys: {list(extracted_json.keys())}")

        # Create reasoning from all metrics
        reasoning_parts = []
        for metric_name, metric_data in openevals_results.items():
            if isinstance(metric_data, dict) and "reasoning" in metric_data:
                reasoning_parts.append(f"{metric_name}: {metric_data['reasoning']}")

        llm_reasoning = (
            " | ".join(reasoning_parts)
            if reasoning_parts
            else "OpenEvals 3-metric evaluation completed"
        )

        # Add evaluation metadata
        eval_time = openevals_results.get("evaluation_time", 0)
        evaluation_model = f"openevals/gpt-4o-mini (Time: {eval_time:.2f}s)"

        # Sanitize data to remove NUL characters before database insert
        input_text = _sanitize_for_postgres(input_text)
        extracted_json = _sanitize_for_postgres(extracted_json)
        llm_reasoning = _sanitize_for_postgres(llm_reasoning)
        brand = _sanitize_for_postgres(brand)
        product_name = _sanitize_for_postgres(product_name)
        username = _sanitize_for_postgres(username)
        user_name = _sanitize_for_postgres(user_name)

        query = """
        INSERT INTO evaluations (
            product_config_id, input_text, extracted_json,
            structure_score, accuracy_score, translation_score, overall_score,
            llm_reasoning, evaluation_model, product_type, brand, product_name,
            user_id, created_by_username, created_by_name
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            product_config_id,
            input_text,  # FIXED: Store actual input text (sanitized)
            json.dumps(extracted_json, ensure_ascii=False),  # FIXED: Store actual JSON (sanitized)
            structure_score,
            content_score,
            translation_score,
            overall_score,
            llm_reasoning,
            evaluation_model,
            product_type,
            brand,
            product_name,
            user_id,  # PHASE 3: User attribution
            username,  # PHASE 3: User attribution
            user_name,  # PHASE 3: User attribution
        )

        result = run_write_query(query, params, fetch_result=True)
        run_cached_query.clear()

        if result:
            st.info(
                f"✅ Stored OpenEvals evaluation for: {brand} - {product_name} (Created by: {username})"
            )

        return result["id"] if result else None

    def get_evaluations_by_user(
        self, user_id: str = None, username: str = None
    ) -> List[Dict]:
        """
        PHASE 3: Get evaluations created by a specific user.

        Args:
            user_id: User UUID to filter by
            username: Username to filter by (alternative to user_id)
        """
        if user_id:
            query = (
                "SELECT * FROM evaluations WHERE user_id = %s ORDER BY created_at DESC"
            )
            params = (user_id,)
        elif username:
            query = "SELECT * FROM evaluations WHERE created_by_username = %s ORDER BY created_at DESC"
            params = (username,)
        else:
            return []

        results = run_cached_query(query, params)

        # Parse JSON fields back to dicts
        for result in results:
            if result.get("extracted_json"):
                try:
                    result["extracted_json"] = json.loads(result["extracted_json"])
                except:
                    result["extracted_json"] = {}

        return results

    def get_user_statistics_detailed(self, user_id: str = None) -> Dict:
        """
        PHASE 3: Get detailed statistics for a user or all users.
        """
        try:
            if user_id:
                # Statistics for specific user
                stats_query = """
                SELECT 
                    COUNT(*) as total_evaluations,
                    AVG(overall_score) as avg_score,
                    COUNT(CASE WHEN overall_score >= 4.0 THEN 1 END) as high_quality,
                    COUNT(CASE WHEN overall_score < 3.0 THEN 1 END) as low_quality,
                    MIN(created_at) as first_evaluation,
                    MAX(created_at) as latest_evaluation,
                    COUNT(DISTINCT product_type) as product_types_count
                FROM evaluations 
                WHERE user_id = %s
                """
                stats_result = run_cached_query(stats_query, (user_id,))
            else:
                # Statistics for all users
                stats_query = """
                SELECT 
                    created_by_username,
                    created_by_name,
                    COUNT(*) as total_evaluations,
                    AVG(overall_score) as avg_score,
                    COUNT(CASE WHEN overall_score >= 4.0 THEN 1 END) as high_quality,
                    COUNT(CASE WHEN overall_score < 3.0 THEN 1 END) as low_quality,
                    MIN(created_at) as first_evaluation,
                    MAX(created_at) as latest_evaluation
                FROM evaluations 
                WHERE created_by_username IS NOT NULL AND created_by_username != ''
                GROUP BY created_by_username, created_by_name
                ORDER BY total_evaluations DESC
                """
                stats_result = run_cached_query(stats_query)

            return stats_result

        except Exception as e:
            print(f"Error getting user statistics: {str(e)}")
            return []

    def get_creators_list(self) -> List[Dict]:
        """
        PHASE 3: Get list of all product creators.
        """
        try:
            query = """
            SELECT DISTINCT 
                created_by_username as username,
                created_by_name as name,
                COUNT(*) as product_count
            FROM evaluations 
            WHERE created_by_username IS NOT NULL AND created_by_username != ''
            GROUP BY created_by_username, created_by_name
            ORDER BY product_count DESC
            """

            results = run_cached_query(query)
            return results

        except Exception as e:
            print(f"Error getting creators list: {str(e)}")
            return []

    # Keep all existing methods unchanged for backward compatibility
    def get_evaluation(self, evaluation_id: int) -> Optional[Dict]:
        """Get a specific evaluation by ID with all data."""
        query = "SELECT * FROM evaluations WHERE id = %s"
        results = run_cached_query(query, (evaluation_id,))

        if results:
            result = results[0]
            # Parse JSON field back to dict
            if result.get("extracted_json"):
                try:
                    result["extracted_json"] = json.loads(result["extracted_json"])
                except:
                    result["extracted_json"] = {}
            return result
        return None

    def get_evaluations_for_config(self, product_config_id: str) -> List[Dict]:
        """Get all evaluations for a specific product configuration with all data."""
        query = """
        SELECT * FROM evaluations 
        WHERE product_config_id = %s
        ORDER BY created_at DESC
        """
        results = run_cached_query(query, (product_config_id,))

        # Parse JSON fields back to dicts
        for result in results:
            if result.get("extracted_json"):
                try:
                    result["extracted_json"] = json.loads(result["extracted_json"])
                except:
                    result["extracted_json"] = {}

        return results

    def store_human_feedback(
        self, evaluation_id: int, human_rating: int, notes: str = "",
        user_id: str = None, username: str = None, user_name: str = None
    ) -> int:
        """Store human feedback for an evaluation with user attribution."""

        # Get user context from session state if not provided
        if not user_id and "current_user" in st.session_state:
            current_user = st.session_state["current_user"]
            user_id = current_user.get("id")
            username = current_user.get("username", "unknown")
            user_name = current_user.get("name", "Unknown User")

        # Default values for user attribution
        user_id = user_id or None
        username = username or "system"
        user_name = user_name or "System"

        query = """
        INSERT INTO human_feedback (evaluation_id, human_rating, notes, user_id, created_by_username, created_by_name)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        result = run_write_query(
            query, (evaluation_id, human_rating, notes, user_id, username, user_name), fetch_result=True
        )

        run_cached_query.clear()
        return result["id"] if result else None

    def get_recent_evaluations(self, limit: int = 50) -> List[Dict]:
        """Get recent evaluations with human feedback and full data."""
        query = """
        SELECT 
            e.*,
            h.human_rating,
            h.notes as feedback_notes
        FROM evaluations e
        LEFT JOIN human_feedback h ON e.id = h.evaluation_id
        ORDER BY e.created_at DESC
        LIMIT %s
        """
        results = run_cached_query(query, (limit,))

        # Parse JSON fields back to dicts
        for result in results:
            if result.get("extracted_json"):
                try:
                    result["extracted_json"] = json.loads(result["extracted_json"])
                except:
                    result["extracted_json"] = {}

        return results

    def get_evaluation_stats(self) -> Dict:
        """Get basic statistics about evaluations."""
        stats_query = """
        SELECT 
            COUNT(*) as total_evaluations,
            AVG(overall_score) as avg_score,
            COUNT(CASE WHEN overall_score >= 4.0 THEN 1 END) as high_quality,
            COUNT(CASE WHEN overall_score < 3.0 THEN 1 END) as low_quality
        FROM evaluations
        """

        feedback_query = "SELECT COUNT(*) as feedback_count FROM human_feedback"

        stats_result = run_cached_query(stats_query)
        feedback_result = run_cached_query(feedback_query)

        stats_row = stats_result[0] if stats_result else {}
        feedback_row = feedback_result[0] if feedback_result else {}

        return {
            "total_evaluations": stats_row.get("total_evaluations", 0) or 0,
            "average_score": (
                round(float(stats_row.get("avg_score", 0.0)), 2)
                if stats_row.get("avg_score")
                else 0.0
            ),
            "high_quality_count": stats_row.get("high_quality", 0) or 0,
            "low_quality_count": stats_row.get("low_quality", 0) or 0,
            "feedback_count": feedback_row.get("feedback_count", 0) or 0,
        }

    def get_evaluations_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get evaluations within a specific date range with all data."""
        query = """
        SELECT * FROM evaluations 
        WHERE created_at BETWEEN %s AND %s
        ORDER BY created_at DESC
        """
        results = run_cached_query(query, (start_date, end_date))

        # Parse JSON fields back to dicts
        for result in results:
            if result.get("extracted_json"):
                try:
                    result["extracted_json"] = json.loads(result["extracted_json"])
                except:
                    result["extracted_json"] = {}

        return results

    def cleanup_old_evaluations(self, days_to_keep: int = 90) -> int:
        """Clean up evaluations older than specified days. Returns count of deleted rows."""
        query = """
        DELETE FROM evaluations 
        WHERE created_at < CURRENT_DATE - INTERVAL %s
        """
        return run_write_query(query, (f"{days_to_keep} days",))

    def get_database_info(self) -> Dict:
        """Get database size and performance information with user tracking info."""
        # Get table sizes
        table_query = """
        SELECT 
            'evaluations' as table_name,
            COUNT(*) as row_count
        FROM evaluations
        UNION ALL
        SELECT 
            'human_feedback' as table_name,
            COUNT(*) as row_count
        FROM human_feedback
        UNION ALL
        SELECT 
            'users' as table_name,
            COUNT(*) as row_count
        FROM users
        """

        table_results = run_cached_query(table_query)
        table_info = {row["table_name"]: row["row_count"] for row in table_results}

        # Get date range
        date_query = """
        SELECT 
            MIN(created_at) as earliest_evaluation,
            MAX(created_at) as latest_evaluation
        FROM evaluations
        """
        date_results = run_cached_query(date_query)
        date_info = date_results[0] if date_results else {}

        # PHASE 3: Get user attribution stats
        user_stats_query = """
        SELECT 
            COUNT(DISTINCT created_by_username) as unique_creators,
            COUNT(CASE WHEN created_by_username IS NOT NULL AND created_by_username != '' THEN 1 END) as attributed_evaluations,
            COUNT(*) as total_evaluations
        FROM evaluations
        """
        user_stats_results = run_cached_query(user_stats_query)
        user_stats = user_stats_results[0] if user_stats_results else {}

        return {
            "database_type": "PostgreSQL (Supabase) + PHASE 3 User Tracking",
            "connection_method": "Streamlit cached connection",
            "table_sizes": table_info,
            "date_range": {
                "earliest": date_info.get("earliest_evaluation"),
                "latest": date_info.get("latest_evaluation"),
            },
            "total_records": table_info.get("evaluations", 0)
            + table_info.get("human_feedback", 0)
            + table_info.get("users", 0),
            "user_attribution": {
                "unique_creators": user_stats.get("unique_creators", 0),
                "attributed_evaluations": user_stats.get("attributed_evaluations", 0),
                "total_evaluations": user_stats.get("total_evaluations", 0),
                "attribution_rate": (
                    (
                        user_stats.get("attributed_evaluations", 0)
                        / user_stats.get("total_evaluations", 1)
                    )
                    * 100
                    if user_stats.get("total_evaluations", 0) > 0
                    else 0
                ),
            },
        }

    # Check if production_model_id column exists
    def _production_model_column_exists(self) -> bool:
        """Check if production_model_id column exists in evaluations table."""
        try:
            columns_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'evaluations' 
            AND column_name = 'production_model_id'
            """
            existing_columns = run_cached_query(columns_query)
            return len(existing_columns) > 0
        except Exception:
            return False

    # Get or create production model (works with your existing table)
    def get_or_create_production_model(
        self, provider: str, model_name: str, temperature: float
    ) -> int:
        """
        Get or create a production model configuration.
        Returns the production_model_id.
        """
        try:
            # First, try to find existing model
            query = """
            SELECT id FROM production_models 
            WHERE provider = %s AND model_name = %s AND temperature = %s
            """

            result = run_cached_query(query, (provider, model_name, temperature))

            if result:
                return result[0]["id"]

            # If not found, create new one
            insert_query = """
            INSERT INTO production_models (provider, model_name, temperature)
            VALUES (%s, %s, %s)
            ON CONFLICT (provider, model_name, temperature) DO UPDATE SET
                provider = EXCLUDED.provider
            RETURNING id
            """

            insert_result = run_write_query(
                insert_query, (provider, model_name, temperature), fetch_result=True
            )

            if insert_result:
                run_cached_query.clear()  # Clear cache after insert
                return insert_result["id"]

            return None

        except Exception as e:
            st.error(f"Error getting/creating production model: {str(e)}")
            return None

    def _ensure_production_model_tracking_table(self):
        """Create temporary tracking table for production models until column is added."""
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS evaluation_production_models (
                id SERIAL PRIMARY KEY,
                evaluation_id INTEGER,
                production_model_id INTEGER REFERENCES production_models(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(evaluation_id)
            )
            """
            run_write_query(create_table_query)

            # Add index
            index_query = """
            CREATE INDEX IF NOT EXISTS idx_eval_prod_models_eval_id 
            ON evaluation_production_models(evaluation_id)
            """
            run_write_query(index_query)

        except Exception as e:
            st.warning(f"Could not create production model tracking table: {str(e)}")

    # METHOD 4: REPLACE your existing store_openevals_evaluation method with this:
    def store_openevals_evaluation(
        self,
        product_config_id: str,
        openevals_results: Dict,
        product_type: str,
        input_text: str = "",
        extracted_json: Dict = None,
        user_id: str = None,
        username: str = None,
        user_name: str = None,
        production_model_provider: str = None,
        production_model_name: str = None,
        production_temperature: float = None,
    ) -> int:
        """Store OpenEvals results with flexible production model tracking."""

        # FIXED: Validate and ensure we have proper input data
        if not input_text or not input_text.strip():
            input_text = f"OpenEvals evaluation for {product_type} product"

        if not extracted_json:
            extracted_json = {"error": "No extracted JSON available"}

        # Extract scores from OpenEvals results
        structure_score = openevals_results.get("structure_correctness", {}).get(
            "score", 3
        )
        content_score = openevals_results.get("content_correctness", {}).get("score", 3)
        translation_score = openevals_results.get("translation_correctness", {}).get(
            "score", 3
        )
        overall_score = openevals_results.get("overall_score", 3.0)

        # Validate scores are in 1-5 range
        structure_score = max(1, min(5, int(structure_score)))
        content_score = max(1, min(5, int(content_score)))
        translation_score = max(1, min(5, int(translation_score)))
        overall_score = max(1.0, min(5.0, float(overall_score)))

        # Extract brand and product name from JSON
        brand = extract_brand_from_json(extracted_json)
        product_name = extract_product_name_from_json(extracted_json)

        # Get user context from session state if not provided
        if not user_id and "current_user" in st.session_state:
            current_user = st.session_state["current_user"]
            user_id = current_user.get("id")
            username = current_user.get("username", "unknown")
            user_name = current_user.get("name", "Unknown User")

        # Default values for user attribution
        user_id = user_id or None
        username = username or "system"
        user_name = user_name or "System"

        # Get production model info
        import config

        final_provider = production_model_provider or config.DEFAULT_PROVIDER
        final_model = production_model_name or config.DEFAULT_MODEL
        final_temp = (
            production_temperature
            if production_temperature is not None
            else config.DEFAULT_TEMPERATURE
        )

        # Create reasoning from all metrics
        reasoning_parts = []
        for metric_name, metric_data in openevals_results.items():
            if isinstance(metric_data, dict) and "reasoning" in metric_data:
                reasoning_parts.append(f"{metric_name}: {metric_data['reasoning']}")

        llm_reasoning = (
            " | ".join(reasoning_parts)
            if reasoning_parts
            else "OpenEvals 3-metric evaluation completed"
        )

        # Add evaluation metadata
        eval_time = openevals_results.get("evaluation_time", 0)
        evaluation_model = f"openevals/gpt-4o-mini (Time: {eval_time:.2f}s)"

        # Check if production_model_id column exists in evaluations table
        has_production_column = self._production_model_column_exists()

        if has_production_column:
            # IDEAL: Use production_model_id column directly
            production_model_id = self.get_or_create_production_model(
                final_provider, final_model, final_temp
            )

            query = """
            INSERT INTO evaluations (
                product_config_id, input_text, extracted_json,
                structure_score, accuracy_score, translation_score, overall_score,
                llm_reasoning, evaluation_model, product_type, brand, product_name,
                user_id, created_by_username, created_by_name, production_model_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """

            params = (
                product_config_id,
                input_text,
                json.dumps(extracted_json, ensure_ascii=False),
                structure_score,
                content_score,
                translation_score,
                overall_score,
                llm_reasoning,
                evaluation_model,
                product_type,
                brand,
                product_name,
                user_id,
                username,
                user_name,
                production_model_id,
            )

            success_msg = f"✅ Stored OpenEvals evaluation for: {brand} - {product_name} (Created by: {username}, Model: {final_provider}/{final_model})"

        else:
            # FALLBACK: Store evaluation normally, track production model separately
            query = """
            INSERT INTO evaluations (
                product_config_id, input_text, extracted_json,
                structure_score, accuracy_score, translation_score, overall_score,
                llm_reasoning, evaluation_model, product_type, brand, product_name,
                user_id, created_by_username, created_by_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """

            params = (
                product_config_id,
                input_text,
                json.dumps(extracted_json, ensure_ascii=False),
                structure_score,
                content_score,
                translation_score,
                overall_score,
                llm_reasoning,
                evaluation_model,
                product_type,
                brand,
                product_name,
                user_id,
                username,
                user_name,
            )

            success_msg = f"✅ Stored OpenEvals evaluation for: {brand} - {product_name} (Created by: {username}, Model: {final_provider}/{final_model}) [Separate tracking]"

        # Store the evaluation
        result = run_write_query(query, params, fetch_result=True)
        run_cached_query.clear()

        if result and not has_production_column:
            # Store production model info in separate tracking table
            evaluation_id = result["id"]

            # Ensure tracking table exists
            self._ensure_production_model_tracking_table()

            # Get or create production model
            production_model_id = self.get_or_create_production_model(
                final_provider, final_model, final_temp
            )

            if production_model_id:
                # Store the relationship in tracking table
                tracking_query = """
                INSERT INTO evaluation_production_models (evaluation_id, production_model_id)
                VALUES (%s, %s)
                ON CONFLICT (evaluation_id) DO UPDATE SET
                    production_model_id = EXCLUDED.production_model_id
                """

                try:
                    run_write_query(
                        tracking_query, (evaluation_id, production_model_id)
                    )
                except Exception as e:
                    st.warning(f"Could not store production model tracking: {str(e)}")

        if result:
            st.info(success_msg)

        return result["id"] if result else None

    # METHOD 5: REPLACE your existing store_evaluation method with this:
    def store_evaluation(
        self,
        product_config_id: str,
        input_text: str,
        extracted_json: Dict,
        scores: Dict[str, float],
        llm_reasoning: str,
        evaluation_model: str,
        product_type: str,
        user_id: str = None,
        username: str = None,
        user_name: str = None,
        production_model_provider: str = None,
        production_model_name: str = None,
        production_temperature: float = None,
    ) -> int:
        """Store evaluation with flexible production model tracking."""

        # Extract brand and product name from JSON
        brand = extract_brand_from_json(extracted_json)
        product_name = extract_product_name_from_json(extracted_json)

        # Get user context from session state if not provided
        if not user_id and "current_user" in st.session_state:
            current_user = st.session_state["current_user"]
            user_id = current_user.get("id")
            username = current_user.get("username", "unknown")
            user_name = current_user.get("name", "Unknown User")

        # Default values for user attribution
        user_id = user_id or None
        username = username or "system"
        user_name = user_name or "System"

        # Get production model info
        import config

        final_provider = production_model_provider or config.DEFAULT_PROVIDER
        final_model = production_model_name or config.DEFAULT_MODEL
        final_temp = (
            production_temperature
            if production_temperature is not None
            else config.DEFAULT_TEMPERATURE
        )

        # Sanitize data to remove NUL characters before database insert
        input_text = _sanitize_for_postgres(input_text)
        extracted_json = _sanitize_for_postgres(extracted_json)
        llm_reasoning = _sanitize_for_postgres(llm_reasoning or "No reasoning provided")
        brand = _sanitize_for_postgres(brand)
        product_name = _sanitize_for_postgres(product_name)
        username = _sanitize_for_postgres(username)
        user_name = _sanitize_for_postgres(user_name)

        # Check if production_model_id column exists
        has_production_column = self._production_model_column_exists()

        if has_production_column:
            # IDEAL: Use production_model_id column directly
            production_model_id = self.get_or_create_production_model(
                final_provider, final_model, final_temp
            )

            query = """
            INSERT INTO evaluations (
                product_config_id, input_text, extracted_json,
                structure_score, accuracy_score, translation_score, overall_score,
                llm_reasoning, evaluation_model, product_type, brand, product_name,
                user_id, created_by_username, created_by_name, production_model_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """

            params = (
                product_config_id,
                input_text[:100000],  # (sanitized)
                json.dumps(extracted_json, ensure_ascii=False),  # (sanitized)
                scores.get("structure_score", 3),
                scores.get("accuracy_score", 3),
                scores.get("translation_score", 3),
                scores.get("overall_score", 3.0),
                llm_reasoning,
                evaluation_model or "Unknown model",
                product_type,
                brand,
                product_name,
                user_id,
                username,
                user_name,
                production_model_id,
            )

            success_msg = f"✅ Stored evaluation for: {brand} - {product_name} (Created by: {username}, Model: {final_provider}/{final_model})"

        else:
            # FALLBACK: Store evaluation normally, track production model separately
            query = """
            INSERT INTO evaluations (
                product_config_id, input_text, extracted_json,
                structure_score, accuracy_score, translation_score, overall_score,
                llm_reasoning, evaluation_model, product_type, brand, product_name,
                user_id, created_by_username, created_by_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """

            params = (
                product_config_id,
                input_text[:100000],  # (sanitized)
                json.dumps(extracted_json, ensure_ascii=False),  # (sanitized)
                scores.get("structure_score", 3),
                scores.get("accuracy_score", 3),
                scores.get("translation_score", 3),
                scores.get("overall_score", 3.0),
                llm_reasoning,
                evaluation_model or "Unknown model",
                product_type,
                brand,
                product_name,
                user_id,
                username,
                user_name,
            )

            success_msg = f"✅ Stored evaluation for: {brand} - {product_name} (Created by: {username}, Model: {final_provider}/{final_model}) [Separate tracking]"

        # Store the evaluation
        result = run_write_query(query, params, fetch_result=True)
        run_cached_query.clear()

        if result and not has_production_column:
            # Store production model info in separate tracking table
            evaluation_id = result["id"]

            # Ensure tracking table exists
            self._ensure_production_model_tracking_table()

            # Get or create production model
            production_model_id = self.get_or_create_production_model(
                final_provider, final_model, final_temp
            )

            if production_model_id:
                # Store the relationship
                tracking_query = """
                INSERT INTO evaluation_production_models (evaluation_id, production_model_id)
                VALUES (%s, %s)
                ON CONFLICT (evaluation_id) DO UPDATE SET
                    production_model_id = EXCLUDED.production_model_id
                """

                try:
                    run_write_query(
                        tracking_query, (evaluation_id, production_model_id)
                    )
                except Exception as e:
                    st.warning(f"Could not store production model tracking: {str(e)}")

        if result:
            st.info(success_msg)

        return result["id"] if result else None

    # METHOD 6: ADD this method for analytics (handles both approaches)
    def get_evaluations_with_production_models(self, limit: int = 50) -> List[Dict]:
        """Get evaluations with production model info, handling both column and separate table approaches."""

        has_production_column = self._production_model_column_exists()

        if has_production_column:
            # Use direct JOIN with production_model_id column
            query = """
            SELECT 
                e.*,
                pm.provider as production_model_provider,
                pm.model_name as production_model_name,
                pm.temperature as production_temperature,
                h.human_rating,
                h.notes as feedback_notes
            FROM evaluations e
            LEFT JOIN production_models pm ON e.production_model_id = pm.id
            LEFT JOIN human_feedback h ON e.id = h.evaluation_id
            ORDER BY e.created_at DESC
            LIMIT %s
            """
            params = (limit,)

        else:
            # Use separate tracking table approach
            query = """
            SELECT 
                e.*,
                pm.provider as production_model_provider,
                pm.model_name as production_model_name,
                pm.temperature as production_temperature,
                h.human_rating,
                h.notes as feedback_notes
            FROM evaluations e
            LEFT JOIN evaluation_production_models epm ON e.id = epm.evaluation_id
            LEFT JOIN production_models pm ON epm.production_model_id = pm.id
            LEFT JOIN human_feedback h ON e.id = h.evaluation_id
            ORDER BY e.created_at DESC
            LIMIT %s
            """
            params = (limit,)

        results = run_cached_query(query, params)

        # Parse JSON fields back to dicts
        for result in results:
            if result.get("extracted_json"):
                try:
                    result["extracted_json"] = json.loads(result["extracted_json"])
                except:
                    result["extracted_json"] = {}

        return results


# Global database instance with Streamlit caching
@st.cache_resource
def get_db() -> EvaluationDB:
    """Get or create the global database instance with Streamlit caching."""
    return EvaluationDB()
