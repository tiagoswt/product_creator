"""
Complete Authentication System for Product Content Creator
Implements user registration, login, role-based access, and user management
"""

import streamlit as st
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import re


class UserManager:
    """Complete user management system with PostgreSQL backend"""

    def __init__(self):
        """Initialize the user manager with database connection"""
        self.connection = self._get_postgres_connection
        self._ensure_users_table_exists()
        self._ensure_default_admin_exists()

    @st.cache_resource
    def _get_postgres_connection(_self):
        """Get cached PostgreSQL connection for authentication"""
        try:
            # Use Streamlit secrets for PostgreSQL connection
            connection_params = {
                **st.secrets["postgres"],
                "sslmode": "require",
                "connect_timeout": 10,
                "application_name": "sweetcare_auth",
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
            st.error("❌ **PostgreSQL Connection Failed for Authentication**")
            st.error(f"Error: {str(e)}")
            st.stop()
        except Exception as e:
            st.error(f"❌ Unexpected authentication database error: {str(e)}")
            st.stop()

    def _run_auth_query(
        self, query: str, params: tuple = None, fetch_result: bool = True
    ):
        """Execute authentication queries"""
        conn = self._get_postgres_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)

                if query.strip().upper().startswith("SELECT"):
                    if fetch_result:
                        result = cur.fetchall()
                        return [dict(row) for row in result] if result else []
                    else:
                        return cur.fetchone()
                else:
                    conn.commit()
                    if fetch_result:
                        result = cur.fetchone()
                        return dict(result) if result else None
                    else:
                        return cur.rowcount
        except Exception as e:
            conn.rollback()
            raise e

    def _ensure_users_table_exists(self):
        """Create users table if it doesn't exist"""
        try:
            create_users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                products_created INTEGER DEFAULT 0,
                evaluations_completed INTEGER DEFAULT 0
            )
            """

            # Create sessions table for session management
            create_sessions_table = """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT true
            )
            """

            # Create activity log table
            create_activity_table = """
            CREATE TABLE IF NOT EXISTS user_activity (
                id SERIAL PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                activity_type VARCHAR(50) NOT NULL,
                activity_details TEXT,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

            self._run_auth_query(create_users_table, fetch_result=False)
            self._run_auth_query(create_sessions_table, fetch_result=False)
            self._run_auth_query(create_activity_table, fetch_result=False)

            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_activity_user_id ON user_activity(user_id)",
            ]

            for index_query in indexes:
                try:
                    self._run_auth_query(index_query, fetch_result=False)
                except:
                    pass  # Index might already exist

        except Exception as e:
            st.warning(f"Could not create authentication tables: {str(e)}")

    def _ensure_default_admin_exists(self):
        """Create default admin user if no users exist"""
        try:
            # Check if any users exist
            users_count = self._run_auth_query("SELECT COUNT(*) as count FROM users")

            if users_count and users_count[0]["count"] == 0:
                # Create default admin user
                default_password = os.getenv("MASTER_PASSWORD", "admin123")

                success, message = self.create_user(
                    username="admin",
                    email="admin@sweetcare.com",
                    name="System Administrator",
                    password=default_password,
                    role="admin",
                )

                if success:
                    print("✅ Default admin user created")
                else:
                    print(f"❌ Failed to create default admin: {message}")

        except Exception as e:
            print(f"Error creating default admin: {str(e)}")

    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash a password with salt"""
        if salt is None:
            salt = secrets.token_hex(32)

        # Combine password and salt
        password_salt = f"{password}{salt}"

        # Create hash
        password_hash = hashlib.sha256(password_salt.encode()).hexdigest()

        return password_hash, salt

    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify a password against stored hash"""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == stored_hash

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r"[0-9]", password):
            return False, "Password must contain at least one number"

        return True, "Password is strong"

    def create_user(
        self, username: str, email: str, name: str, password: str, role: str = "user"
    ) -> Tuple[bool, str]:
        """Create a new user"""
        try:
            # Validate inputs
            if not username or len(username) < 3:
                return False, "Username must be at least 3 characters long"

            if not self._validate_email(email):
                return False, "Invalid email format"

            if not name or len(name) < 2:
                return False, "Name must be at least 2 characters long"

            is_strong, password_message = self._validate_password_strength(password)
            if not is_strong:
                return False, password_message

            if role not in ["user", "admin"]:
                return False, "Role must be 'user' or 'admin'"

            # Check if username already exists
            existing_user = self._run_auth_query(
                "SELECT username FROM users WHERE username = %s", (username,)
            )
            if existing_user:
                return False, "Username already exists"

            # Check if email already exists
            existing_email = self._run_auth_query(
                "SELECT email FROM users WHERE email = %s", (email,)
            )
            if existing_email:
                return False, "Email already exists"

            # Hash password
            password_hash, salt = self._hash_password(password)

            # Create user
            query = """
            INSERT INTO users (username, email, name, password_hash, salt, role)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """

            result = self._run_auth_query(
                query,
                (username, email, name, password_hash, salt, role),
                fetch_result=True,
            )

            if result:
                self._log_activity(
                    result["id"],
                    "user_created",
                    f"User {username} created with role {role}",
                )
                return True, f"User {username} created successfully"
            else:
                return False, "Failed to create user"

        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    def authenticate_user(
        self, username: str, password: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """Authenticate a user"""
        try:
            # Get user from database
            user_data = self._run_auth_query(
                "SELECT * FROM users WHERE username = %s AND is_active = true",
                (username,),
            )

            if not user_data:
                return False, None, "Invalid username or password"

            user = user_data[0]

            # Verify password
            if not self._verify_password(password, user["password_hash"], user["salt"]):
                self._log_activity(
                    user["id"], "login_failed", f"Failed login attempt for {username}"
                )
                return False, None, "Invalid username or password"

            # Update last login
            self._run_auth_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user["id"],),
                fetch_result=False,
            )

            # Create session
            session_id = self._create_session(user["id"])

            # Log successful login
            self._log_activity(
                user["id"], "login_success", f"Successful login for {username}"
            )

            # Prepare user data for session
            user_session_data = {
                "id": str(user["id"]),
                "username": user["username"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "created_at": (
                    user["created_at"].isoformat() if user["created_at"] else None
                ),
                "last_login": (
                    user["last_login"].isoformat() if user["last_login"] else None
                ),
                "session_id": session_id,
                "products_created": user.get("products_created", 0),
                "evaluations_completed": user.get("evaluations_completed", 0),
            }

            return True, user_session_data, "Login successful"

        except Exception as e:
            return False, None, f"Authentication error: {str(e)}"

    def _create_session(self, user_id: str) -> str:
        """Create a new session for a user"""
        try:
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)  # Session expires in 7 days

            self._run_auth_query(
                "INSERT INTO user_sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s)",
                (session_id, user_id, expires_at),
                fetch_result=False,
            )

            return session_id

        except Exception as e:
            print(f"Error creating session: {str(e)}")
            return secrets.token_urlsafe(32)  # Fallback session ID

    def _validate_session(self, session_id: str) -> Optional[Dict]:
        """Validate a session and return user data"""
        try:
            session_data = self._run_auth_query(
                """
                SELECT s.*, u.* FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = %s 
                AND s.is_active = true 
                AND s.expires_at > CURRENT_TIMESTAMP
                AND u.is_active = true
            """,
                (session_id,),
            )

            if session_data:
                user = session_data[0]
                return {
                    "id": str(user["user_id"]),
                    "username": user["username"],
                    "email": user["email"],
                    "name": user["name"],
                    "role": user["role"],
                    "created_at": (
                        user["created_at"].isoformat() if user["created_at"] else None
                    ),
                    "last_login": (
                        user["last_login"].isoformat() if user["last_login"] else None
                    ),
                    "session_id": session_id,
                    "products_created": user.get("products_created", 0),
                    "evaluations_completed": user.get("evaluations_completed", 0),
                }

            return None

        except Exception as e:
            print(f"Error validating session: {str(e)}")
            return None

    def _log_activity(
        self, user_id: str, activity_type: str, activity_details: str = None
    ):
        """Log user activity"""
        try:
            self._run_auth_query(
                "INSERT INTO user_activity (user_id, activity_type, activity_details) VALUES (%s, %s, %s)",
                (user_id, activity_type, activity_details),
                fetch_result=False,
            )
        except Exception as e:
            print(f"Error logging activity: {str(e)}")

    def logout_user(self, session_id: str):
        """Logout a user by invalidating their session"""
        try:
            self._run_auth_query(
                "UPDATE user_sessions SET is_active = false WHERE session_id = %s",
                (session_id,),
                fetch_result=False,
            )
        except Exception as e:
            print(f"Error logging out user: {str(e)}")

    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user from session state"""
        if "authenticated_user" in st.session_state:
            user_data = st.session_state.authenticated_user

            # Validate session if session_id exists
            if "session_id" in user_data:
                validated_user = self._validate_session(user_data["session_id"])
                if validated_user:
                    return validated_user
                else:
                    # Session expired, clear it
                    del st.session_state.authenticated_user
                    return None

            return user_data

        return None

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.get_current_user() is not None

    def is_admin(self) -> bool:
        """Check if current user is admin"""
        user = self.get_current_user()
        return user and user.get("role") == "admin"

    def show_login_page(self):
        """Render the login page"""
        st.markdown("# 🔐 Login")
        st.markdown("Please login to access the Product Content Creator")

        # Login form
        with st.form("login_form"):
            st.markdown("### Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password"
            )

            col1, col2 = st.columns(2)
            with col1:
                login_button = st.form_submit_button(
                    "🔑 Login", use_container_width=True
                )
            with col2:
                register_button = st.form_submit_button(
                    "📝 Register", use_container_width=True
                )

            if login_button:
                if username and password:
                    success, user_data, message = self.authenticate_user(
                        username, password
                    )

                    if success:
                        st.session_state.authenticated_user = user_data
                        st.success(f"Welcome back, {user_data['name']}!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {message}")
                else:
                    st.error("Please enter both username and password")

            if register_button:
                st.session_state.show_registration = True
                st.rerun()

        # Registration form (if requested)
        if st.session_state.get("show_registration", False):
            self.show_registration_form()

    def show_registration_form(self):
        """Render the registration form"""
        st.markdown("---")
        st.markdown("### 📝 Register New User")

        with st.form("registration_form"):
            col1, col2 = st.columns(2)

            with col1:
                reg_username = st.text_input(
                    "Username*", placeholder="Choose a username"
                )
                reg_email = st.text_input("Email*", placeholder="Enter your email")

            with col2:
                reg_name = st.text_input(
                    "Full Name*", placeholder="Enter your full name"
                )
                reg_password = st.text_input(
                    "Password*", type="password", placeholder="Choose a secure password"
                )

            reg_confirm_password = st.text_input(
                "Confirm Password*",
                type="password",
                placeholder="Confirm your password",
            )

            st.caption("* Required fields")
            st.caption(
                "Password must be at least 8 characters with uppercase, lowercase, and numbers"
            )

            col1, col2 = st.columns(2)
            with col1:
                register_submit = st.form_submit_button(
                    "✅ Create Account", use_container_width=True
                )
            with col2:
                cancel_register = st.form_submit_button(
                    "❌ Cancel", use_container_width=True
                )

            if register_submit:
                if not all(
                    [
                        reg_username,
                        reg_email,
                        reg_name,
                        reg_password,
                        reg_confirm_password,
                    ]
                ):
                    st.error("Please fill in all required fields")
                elif reg_password != reg_confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = self.create_user(
                        username=reg_username,
                        email=reg_email,
                        name=reg_name,
                        password=reg_password,
                        role="user",
                    )

                    if success:
                        st.success(
                            f"Account created successfully! You can now login with username: {reg_username}"
                        )
                        st.session_state.show_registration = False
                        st.rerun()
                    else:
                        st.error(f"Registration failed: {message}")

            if cancel_register:
                st.session_state.show_registration = False
                st.rerun()

    def show_logout_button(self):
        """Render logout button in sidebar"""
        if st.button("🚪 Logout", use_container_width=True):
            user = self.get_current_user()
            if user and "session_id" in user:
                self.logout_user(user["session_id"])
                self._log_activity(user["id"], "logout", "User logged out")

            # Clear session state
            if "authenticated_user" in st.session_state:
                del st.session_state.authenticated_user

            st.success("Logged out successfully!")
            st.rerun()

    def get_user_statistics(self) -> Dict:
        """Get user statistics for admin panel"""
        try:
            stats = {}

            # Total users
            total_users = self._run_auth_query(
                "SELECT COUNT(*) as count FROM users WHERE is_active = true"
            )
            stats["total_users"] = total_users[0]["count"] if total_users else 0

            # Active users (logged in within last 30 days)
            active_users = self._run_auth_query(
                """
                SELECT COUNT(*) as count FROM users 
                WHERE is_active = true AND last_login > CURRENT_DATE - INTERVAL '30 days'
            """
            )
            stats["active_users"] = active_users[0]["count"] if active_users else 0

            # Total products created (if evaluations table exists with user tracking)
            try:
                total_products = self._run_auth_query(
                    "SELECT COUNT(*) as count FROM evaluations"
                )
                stats["total_products"] = (
                    total_products[0]["count"] if total_products else 0
                )
            except:
                stats["total_products"] = 0

            return stats

        except Exception as e:
            print(f"Error getting user statistics: {str(e)}")
            return {"total_users": 0, "active_users": 0, "total_products": 0}

    def render_user_management_page(self):
        """Render the user management page for admins"""
        st.markdown("# 👥 User Management")

        # Back button
        if st.button("← Back to Main App"):
            st.session_state.show_user_management = False
            st.rerun()

        # Get all users
        try:
            users = self._run_auth_query(
                """
                SELECT id, username, email, name, role, is_active, created_at, last_login,
                       products_created, evaluations_completed
                FROM users 
                ORDER BY created_at DESC
            """
            )

            if users:
                st.markdown(f"### Total Users: {len(users)}")

                # Display users table
                for user in users:
                    with st.expander(
                        f"👤 {user['name']} ({user['username']}) - {user['role'].title()}"
                    ):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Email:** {user['email']}")
                            st.write(f"**Role:** {user['role'].title()}")
                            st.write(
                                f"**Status:** {'Active' if user['is_active'] else 'Inactive'}"
                            )

                        with col2:
                            st.write(
                                f"**Created:** {user['created_at'].strftime('%Y-%m-%d') if user['created_at'] else 'Unknown'}"
                            )
                            st.write(
                                f"**Last Login:** {user['last_login'].strftime('%Y-%m-%d') if user['last_login'] else 'Never'}"
                            )
                            st.write(f"**Products:** {user.get('products_created', 0)}")

                        # Admin actions
                        if (
                            user["username"] != "admin"
                        ):  # Don't allow modifying the main admin
                            action_col1, action_col2 = st.columns(2)

                            with action_col1:
                                if user["is_active"]:
                                    if st.button(
                                        f"🚫 Deactivate", key=f"deactivate_{user['id']}"
                                    ):
                                        self._run_auth_query(
                                            "UPDATE users SET is_active = false WHERE id = %s",
                                            (user["id"],),
                                            fetch_result=False,
                                        )
                                        st.success(
                                            f"User {user['username']} deactivated"
                                        )
                                        st.rerun()
                                else:
                                    if st.button(
                                        f"✅ Activate", key=f"activate_{user['id']}"
                                    ):
                                        self._run_auth_query(
                                            "UPDATE users SET is_active = true WHERE id = %s",
                                            (user["id"],),
                                            fetch_result=False,
                                        )
                                        st.success(f"User {user['username']} activated")
                                        st.rerun()

                            with action_col2:
                                if user["role"] == "user":
                                    if st.button(
                                        f"👑 Make Admin", key=f"make_admin_{user['id']}"
                                    ):
                                        self._run_auth_query(
                                            "UPDATE users SET role = 'admin' WHERE id = %s",
                                            (user["id"],),
                                            fetch_result=False,
                                        )
                                        st.success(
                                            f"User {user['username']} is now an admin"
                                        )
                                        st.rerun()
                                else:
                                    if st.button(
                                        f"👤 Make User", key=f"make_user_{user['id']}"
                                    ):
                                        self._run_auth_query(
                                            "UPDATE users SET role = 'user' WHERE id = %s",
                                            (user["id"],),
                                            fetch_result=False,
                                        )
                                        st.success(
                                            f"User {user['username']} is now a regular user"
                                        )
                                        st.rerun()

            else:
                st.warning("No users found")

        except Exception as e:
            st.error(f"Error loading users: {str(e)}")


def require_auth(auth_manager: UserManager):
    """Decorator function to require authentication"""
    if not auth_manager.is_authenticated():
        auth_manager.show_login_page()
        st.stop()
