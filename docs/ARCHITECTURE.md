# 🏗️ System Architecture Documentation

**SweetCare AI Product Content Creator**

---

## Table of Contents

- [Overview](#overview)
- [High-Level Architecture](#high-level-architecture)
- [System Layers](#system-layers)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Integration Architecture](#integration-architecture)
- [Security Architecture](#security-architecture)
- [Scalability Considerations](#scalability-considerations)
- [Design Patterns](#design-patterns)
- [Technology Stack](#technology-stack)

---

## Overview

The SweetCare AI Product Content Creator follows a **layered architecture** with clear separation of concerns:

- **Presentation Layer** (Streamlit UI)
- **Application Layer** (Business logic)
- **Service Layer** (LLM processing, data extraction)
- **Data Layer** (PostgreSQL, SQLite, File storage)
- **Integration Layer** (External APIs)

### Architecture Principles

1. **Modularity** - Each component has a single responsibility
2. **Extensibility** - Easy to add new product types and data sources
3. **Maintainability** - Clear code organization with comprehensive docstrings
4. **Scalability** - Stateless processing enables horizontal scaling
5. **Security** - Authentication, session management, activity logging

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                    (Streamlit Web Application)                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  Auth UI    │  │  Batch UI   │  │  Analytics Dashboard     │   │
│  │  Components │  │  Components │  │  (Metrics & Reports)     │   │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  app.py - Main Application Controller                       │  │
│  │  - Route requests to appropriate modules                     │  │
│  │  - Manage session state                                      │  │
│  │  - Coordinate workflow between components                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │ Auth        │  │ Processing  │  │ Evaluation  │  │ Export   │  │
│  │ Service     │  │ Service     │  │ Service     │  │ Service  │  │
│  │             │  │             │  │             │  │          │  │
│  │ - UserMgr   │  │ - LLM Proc  │  │ - 3-Metric  │  │ - CSV    │  │
│  │ - Sessions  │  │ - HSCode    │  │ - Scoring   │  │ - Excel  │  │
│  │ - RBAC      │  │ - Batch     │  │ - Analytics │  │ - Dropbox│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INTEGRATION LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  LLM        │  │  Storage    │  │  Monitoring              │   │
│  │  Providers  │  │  Providers  │  │  & Tracing               │   │
│  │             │  │             │  │                          │   │
│  │ - OpenAI    │  │ - Dropbox   │  │ - LangSmith              │   │
│  │ - Groq      │  │ - Local FS  │  │ - Logging                │   │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │  PostgreSQL     │  │  SQLite         │  │  File Storage    │   │
│  │  (Supabase)     │  │  (Evaluations)  │  │  (Results)       │   │
│  │                 │  │                 │  │                  │   │
│  │  - Users        │  │  - Metrics      │  │  - PDFs          │   │
│  │  - Sessions     │  │  - Scores       │  │  - Excel files   │   │
│  │  - Activity     │  │  - History      │  │  - Exports       │   │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## System Layers

### 1. Presentation Layer

**Technology:** Streamlit

**Components:**
- `app.py` - Main entry point
- `auth.py` - Authentication UI
- `utils/batch_ui/` - Batch processing interface
- `evaluations/tabbed_analytics_dashboard.py` - Analytics UI

**Responsibilities:**
- Render user interface components
- Handle user input and validation
- Display results and feedback
- Manage navigation and routing

**Key Features:**
- Form-based configuration
- Real-time progress tracking
- Interactive data tables
- Responsive design

---

### 2. Application Layer

**Main Controller:** `app.py`

**Responsibilities:**
- Initialize application state
- Route requests to appropriate services
- Manage user sessions
- Coordinate cross-cutting concerns (logging, error handling)

**Key Functions:**
```python
def main():
    # 1. Set page configuration
    st.set_page_config(...)

    # 2. Initialize authentication
    auth = UserManager()
    require_auth(auth)

    # 3. Initialize state
    initialize_state()

    # 4. Render main UI
    render_batch_extraction_ui()
```

---

### 3. Service Layer

#### 3.1 Authentication Service (`auth.py`)

**Class:** `UserManager`

**Responsibilities:**
- User registration and login
- Session management (7-day sessions)
- Password hashing and validation
- Role-based access control (RBAC)
- Activity logging

**Database Tables:**
- `users` - User accounts
- `user_sessions` - Active sessions
- `user_activity` - Audit log

**Key Methods:**
```python
def authenticate_user(username, password) -> Tuple[bool, Optional[Dict], str]
def create_user(username, email, name, password, role) -> Tuple[bool, str]
def _validate_session(session_id) -> Optional[Dict]
def logout_user(session_id)
```

---

#### 3.2 Processing Service

**Modules:**
- `processors/text_processor.py` - LLM processing
- `processors/pdf_processor.py` - PDF extraction
- `processors/excel_processor.py` - Excel/CSV parsing
- `processors/web_processor.py` - Website scraping

**Text Processor Workflow:**
```python
# 1. Load prompt template
prompt_content = load_prompt_from_file(prompt_file)

# 2. Process with LLM
product_data = process_with_llm(text, product_type, llm)

# 3. Classify HSCode
hscode = process_hscode_with_deepseek(product_data)

# 4. Place HSCode in correct location
product_data = place_hscode_in_correct_location(product_data, hscode)
```

**PDF Processor:**
- Uses PyMuPDF for text extraction
- Generates page thumbnails for preview
- Supports selective page processing

**Excel Processor:**
- Uses Pandas for parsing
- Configurable header row
- Row-level selection

**Web Processor:**
- Uses BeautifulSoup4 for HTML parsing
- Extracts text from common e-commerce structures
- Handles multiple URLs

---

#### 3.3 Model Factory (`models/model_factory.py`)

**Responsibility:** Initialize and manage LLM connections

**Supported Providers:**
- OpenAI (GPT-4o, GPT-4 Mini)
- Groq (Llama 4, DeepSeek)

**Key Function:**
```python
def get_llm(
    provider: str = None,
    model_name: str = None,
    temperature: float = None
) -> BaseLanguageModel:
    """
    Factory function to get the appropriate LLM instance

    Returns:
        Initialized LLM instance (ChatOpenAI or ChatGroq)
    """
```

**Configuration:**
- API keys from environment variables
- Default models from `config.py`
- Temperature control per request

---

#### 3.4 Evaluation Service

**Modules:**
- `evaluations/evaluation_core.py` - Core evaluation engine
- `evaluations/metric_evaluator.py` - 3-metric evaluator
- `evaluations/simple_db.py` - SQLite persistence

**3-Metric System:**

1. **Structure Correctness (20%)**
   - JSON schema validation
   - Required field checking
   - Data type verification

2. **Content Correctness (50%)**
   - Input vs. output comparison
   - Hallucination detection
   - Factual accuracy

3. **Translation Correctness (30%)**
   - Portuguese translation quality
   - Terminology consistency
   - Linguistic accuracy

**Evaluation Flow:**
```python
# 1. Evaluate each metric
structure_score = evaluate_structure(product_data, schema)
content_score = evaluate_content(product_data, input_text)
translation_score = evaluate_translation(product_data)

# 2. Calculate weighted overall score
overall_score = (
    structure_score * 0.2 +
    content_score * 0.5 +
    translation_score * 0.3
)

# 3. Store in database
store_evaluation(product_id, scores)
```

---

#### 3.5 Export Service

**Module:** `utils/batch_ui/handlers/export_handler.py`

**Supported Formats:**
- CSV (comma-separated values)
- Excel (XLSX)
- JSON (raw data)

**Features:**
- Flattening nested JSON structures
- Column ordering and naming
- Timestamp in filenames
- Dropbox upload integration

**Export Flow:**
```python
# 1. Flatten product data
flattened_results = flatten_product_data(results)

# 2. Create DataFrame
df = pd.DataFrame(flattened_results)

# 3. Export to format
df.to_csv(filename) or df.to_excel(filename)

# 4. Upload to Dropbox (optional)
if dropbox_enabled:
    upload_to_dropbox(filename)
```

---

### 4. Integration Layer

#### 4.1 LLM Integration

**OpenAI Integration** (`models/openai_model.py`)
- Uses `langchain-openai` package
- Supports GPT-4o, GPT-4o-mini
- API key from environment

**Groq Integration** (`models/groq_model.py`)
- Uses `langchain-groq` package
- Supports Llama 4, DeepSeek R1
- Fast inference for cost efficiency

**LangSmith Integration** (`utils/langsmith_utils.py`)
- Automatic tracing of LLM calls
- Evaluation dataset management
- Debug and performance monitoring

---

#### 4.2 Storage Integration

**Dropbox Integration** (`utils/dropbox_utils.py`)

**Features:**
- Automatic file upload
- Organized folder structure
- Timestamped backups
- Connection testing

**Functions:**
```python
def upload_to_dropbox(local_file_path, dropbox_path) -> bool
def get_dropbox_client() -> dropbox.Dropbox
def test_dropbox_connection() -> bool
```

---

### 5. Data Layer

#### 5.1 PostgreSQL (Supabase)

**Purpose:** User authentication, session management, activity tracking

**Schema:**

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    products_created INTEGER DEFAULT 0,
    evaluations_completed INTEGER DEFAULT 0
);

-- Sessions table
CREATE TABLE user_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Activity log table
CREATE TABLE user_activity (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    activity_details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `idx_users_username` on `users(username)`
- `idx_users_email` on `users(email)`
- `idx_sessions_user_id` on `user_sessions(user_id)`
- `idx_activity_user_id` on `user_activity(user_id)`

---

#### 5.2 SQLite (Evaluations Database)

**Purpose:** Store evaluation metrics and history

**Schema:**

```sql
-- Evaluations table
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    product_type TEXT,
    structure_score REAL,
    content_score REAL,
    translation_score REAL,
    overall_score REAL,
    model_provider TEXT,
    model_name TEXT,
    temperature REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_text TEXT,
    output_json TEXT,
    evaluation_details TEXT
);

-- Index on product_id for quick lookups
CREATE INDEX idx_evaluations_product_id ON evaluations(product_id);
CREATE INDEX idx_evaluations_created_at ON evaluations(created_at);
```

---

## Data Flow

### Product Extraction Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. USER INPUT                                                    │
│    - Product type selection                                      │
│    - Data source selection (PDF/Excel/Website)                   │
│    - Configuration submission                                    │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. DATA SOURCE PROCESSING                                        │
│    ┌──────────────┐  ┌──────────────┐  ┌───────────────┐       │
│    │ PDF Processor│  │Excel Processor│  │Web Processor │       │
│    │ - Extract    │  │ - Parse rows  │  │ - Scrape HTML│       │
│    │   text       │  │ - Handle      │  │ - Extract    │       │
│    │ - By page    │  │   headers     │  │   content    │       │
│    └──────┬───────┘  └──────┬────────┘  └───────┬──────┘       │
│           └──────────────────┴───────────────────┘               │
│                              │                                    │
│                   Consolidated Text Data                          │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. LLM PROCESSING                                                │
│    - Load product-specific prompt                                │
│    - Send to LLM (OpenAI/Groq)                                  │
│    - Parse JSON response                                         │
│    - Validate structure                                          │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. HSCODE CLASSIFICATION                                         │
│    - Extract HSCode-relevant fields                              │
│    - Send to DeepSeek/specialized model                          │
│    - Validate 8-digit code                                       │
│    - Place in correct location in JSON                           │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. QUALITY EVALUATION                                            │
│    - Evaluate structure (20%)                                    │
│    - Evaluate content (50%)                                      │
│    - Evaluate translation (30%)                                  │
│    - Calculate overall score                                     │
│    - Store in evaluations DB                                     │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. RESULT STORAGE & PRESENTATION                                 │
│    - Store in session state                                      │
│    - Display in results table                                    │
│    - Show quality scores                                         │
│    - Enable export options                                       │
└──────────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ USER ATTEMPTS LOGIN                                              │
│    - Enter username + password                                   │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ AUTHENTICATION SERVICE                                           │
│    - Query users table                                           │
│    - Verify password hash with salt                              │
│    - Check is_active status                                      │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ✅ Valid              ❌ Invalid
                    │                   │
                    ▼                   ▼
         ┌─────────────────┐   ┌──────────────┐
         │ CREATE SESSION  │   │ REJECT LOGIN │
         │  - Generate ID  │   │ - Log failed │
         │  - Set expiry   │   │   attempt    │
         │  - Store in DB  │   │ - Show error │
         └────────┬────────┘   └──────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ UPDATE USER     │
         │  - last_login   │
         │  - Log activity │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ STORE IN        │
         │ SESSION STATE   │
         │  - User data    │
         │  - Session ID   │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ REDIRECT TO     │
         │ MAIN APP        │
         └─────────────────┘
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────────┐
│         USERS               │
├─────────────────────────────┤
│ PK: id (UUID)               │
│ UK: username                │
│ UK: email                   │
│     name                    │
│     password_hash           │
│     salt                    │
│     role                    │
│     is_active               │
│     created_at              │
│     last_login              │
│     products_created        │
│     evaluations_completed   │
└──────────┬──────────────────┘
           │ 1
           │
           │ has many
           │
           │ N
┌──────────┴──────────────────┐
│    USER_SESSIONS            │
├─────────────────────────────┤
│ PK: session_id              │
│ FK: user_id → users.id      │
│     created_at              │
│     expires_at              │
│     is_active               │
└──────────┬──────────────────┘
           │
           │
           │
┌──────────┴──────────────────┐
│    USER_ACTIVITY            │
├─────────────────────────────┤
│ PK: id (SERIAL)             │
│ FK: user_id → users.id      │
│     activity_type           │
│     activity_details        │
│     ip_address              │
│     user_agent              │
│     created_at              │
└─────────────────────────────┘


┌─────────────────────────────┐
│    EVALUATIONS (SQLite)     │
├─────────────────────────────┤
│ PK: id (INTEGER)            │
│     product_id              │
│     product_type            │
│     structure_score         │
│     content_score           │
│     translation_score       │
│     overall_score           │
│     model_provider          │
│     model_name              │
│     temperature             │
│     created_at              │
│     input_text              │
│     output_json             │
│     evaluation_details      │
└─────────────────────────────┘
```

---

## Integration Architecture

### External Service Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION CORE                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
          ┌──────────┼──────────┬──────────────┬──────────────┐
          │          │          │              │              │
          ▼          ▼          ▼              ▼              ▼
     ┌────────┐ ┌────────┐ ┌────────┐    ┌─────────┐   ┌─────────┐
     │ OpenAI │ │  Groq  │ │LangSmith│   │ Supabase│   │ Dropbox │
     │  API   │ │  API   │ │   API   │   │PostgreSQL│  │   API   │
     └────────┘ └────────┘ └────────┘    └─────────┘   └─────────┘
         │          │          │              │              │
         │          │          │              │              │
    LLM Inference  Tracing   Auth/DB      File Storage
    & Processing  & Monitoring
```

### API Communication

**OpenAI/Groq (LLM Processing):**
```python
# Request
POST https://api.openai.com/v1/chat/completions
Headers:
  Authorization: Bearer {API_KEY}
  Content-Type: application/json
Body:
  {
    "model": "gpt-4o-mini",
    "messages": [...],
    "temperature": 0.4
  }

# Response
{
  "choices": [{
    "message": {
      "content": "{...JSON...}"
    }
  }]
}
```

**Supabase (PostgreSQL):**
```python
# Connection via psycopg2
conn = psycopg2.connect(
    host="project.supabase.co",
    port="6543",  # Pooler port
    database="postgres",
    user="postgres",
    password="...",
    sslmode="require"
)
```

**Dropbox (File Upload):**
```python
# Upload file
dbx = dropbox.Dropbox(access_token)
with open(local_path, 'rb') as f:
    dbx.files_upload(
        f.read(),
        dropbox_path,
        mode=dropbox.files.WriteMode.overwrite
    )
```

---

## Security Architecture

### Authentication & Authorization

**Password Security:**
- SHA-256 hashing with per-user salt
- Minimum password requirements enforced
- Secure password validation

**Session Security:**
- Cryptographically secure session IDs
- 7-day expiration
- Server-side session validation
- Automatic cleanup of expired sessions

**Role-Based Access Control (RBAC):**

| Feature | User | Admin |
|---------|------|-------|
| Create products | ✅ | ✅ |
| Execute batch processing | ✅ | ✅ |
| View own results | ✅ | ✅ |
| Export data | ✅ | ✅ |
| User management | ❌ | ✅ |
| View all user activity | ❌ | ✅ |
| System statistics | ❌ | ✅ |

**Data Protection:**
- PostgreSQL SSL/TLS connections
- Environment variable API keys
- No sensitive data in session state
- Activity logging for audit trails

---

## Scalability Considerations

### Current Architecture

**Stateless Processing:**
- Each product extraction is independent
- No shared state between requests
- Enables horizontal scaling

**Bottlenecks:**
1. **LLM API rate limits** - OpenAI/Groq request quotas
2. **Database connections** - Supabase connection pooling
3. **File uploads** - Dropbox API limits
4. **Memory** - Large PDFs/Excel files in memory

### Scaling Strategies

**Horizontal Scaling:**
- Deploy multiple Streamlit instances
- Use load balancer (e.g., Nginx, HAProxy)
- Share PostgreSQL and SQLite databases
- Centralize file storage (Dropbox, S3)

**Vertical Scaling:**
- Increase memory for larger files
- More CPU for faster processing
- SSD for database performance

**Optimization:**
- Implement caching for prompts
- Use connection pooling
- Batch API requests where possible
- Async processing for long-running tasks

**Future Enhancements:**
- Message queue (RabbitMQ, Celery) for background jobs
- Redis for session caching
- CDN for static assets
- Database read replicas

---

## Design Patterns

### 1. Factory Pattern

**Used in:** `models/model_factory.py`

```python
def get_llm(provider, model_name, temperature):
    """Factory for creating LLM instances"""
    if provider == "openai":
        return ChatOpenAI(...)
    elif provider == "groq":
        return ChatGroq(...)
```

**Benefits:**
- Centralized LLM creation logic
- Easy to add new providers
- Consistent interface

---

### 2. Strategy Pattern

**Used in:** Product type processing

```python
# Different strategies for different product types
if product_type == "cosmetics":
    prompt = COSMETICS_PROMPT
elif product_type == "fragrance":
    prompt = FRAGRANCE_PROMPT
elif product_type == "subtype":
    prompt = SUBTYPE_PROMPT
```

**Benefits:**
- Flexible product type handling
- Easy to add new types
- Encapsulated business logic

---

### 3. Repository Pattern

**Used in:** `auth.py` - UserManager class

```python
class UserManager:
    def _run_auth_query(self, query, params):
        """Centralized database access"""
        # Execute query
        # Handle errors
        # Return results
```

**Benefits:**
- Abstract database operations
- Centralized error handling
- Easy to switch databases

---

### 4. Facade Pattern

**Used in:** `utils/batch_ui/main.py`

```python
def render_batch_extraction_ui():
    """Simplified interface for complex batch processing"""
    migrate_product_configs()
    render_configure_tab()
    render_execute_tab()
```

**Benefits:**
- Simplified complex subsystems
- Clean public API
- Easier testing

---

### 5. Singleton Pattern

**Used in:** Database connections (via `@st.cache_resource`)

```python
@st.cache_resource
def _get_postgres_connection(_self):
    """Single shared connection instance"""
    return psycopg2.connect(...)
```

**Benefits:**
- Resource efficiency
- Connection reuse
- Controlled access

---

## Technology Stack

### Core Framework
- **Streamlit 1.32+** - Web application framework
- **Python 3.8+** - Programming language

### LLM & AI
- **LangChain** - LLM orchestration
- **LangSmith** - LLM tracing and monitoring
- **OpenAI** - GPT-4o, GPT-4o-mini models
- **Groq** - Llama 4, DeepSeek models

### Data Processing
- **Pandas** - DataFrame operations
- **NumPy** - Numerical operations
- **PyMuPDF** - PDF text extraction
- **BeautifulSoup4** - HTML parsing
- **openpyxl** - Excel file handling

### Databases
- **PostgreSQL (Supabase)** - User authentication
- **SQLite** - Evaluation metrics
- **psycopg2** - PostgreSQL driver

### Cloud & Storage
- **Dropbox** - Cloud file storage
- **Supabase** - Managed PostgreSQL

### Utilities
- **python-dotenv** - Environment variables
- **Pillow** - Image processing
- **plotly** - Data visualization
- **tiktoken** - Token counting

---

## Extensibility

### Adding New Product Types

**Required Changes:**
1. Create prompt file in `prompts/`
2. Add constant in `config.py`
3. Update dropdown in `configuration_form.py`
4. Add elif branch in `text_processor.py`

**Optional Changes:**
- Custom JSON structure handling
- Specialized HSCode placement
- Product-specific export logic

See [IMPLEMENTATION_PLAN_NEW_PROMPTS.md](../IMPLEMENTATION_PLAN_NEW_PROMPTS.md) for details.

---

### Adding New Data Sources

**Steps:**
1. Create processor in `processors/`
2. Implement `process_[source](file) -> str`
3. Add UI component in `configuration_form.py`
4. Integrate in batch processor

**Example: Adding Google Sheets**
```python
# 1. Create processors/sheets_processor.py
def process_google_sheet(sheet_url, sheet_name):
    # Connect to Google Sheets API
    # Extract data
    # Return as text
    return text

# 2. Add to configuration_form.py
sheets_url = st.text_input("Google Sheets URL")

# 3. Integrate in batch_processor.py
if config.sheets_url:
    text += process_google_sheet(config.sheets_url)
```

---

### Adding New LLM Providers

**Steps:**
1. Install provider package
2. Create `models/[provider]_model.py`
3. Update `model_factory.py`
4. Add API key to `.env`

**Example: Adding Anthropic Claude**
```python
# 1. Install: pip install langchain-anthropic

# 2. Create models/anthropic_model.py
from langchain_anthropic import ChatAnthropic

def get_anthropic_model(model_name, temperature):
    return ChatAnthropic(
        model=model_name,
        temperature=temperature,
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

# 3. Update model_factory.py
elif provider == "anthropic":
    return get_anthropic_model(model_name, temperature)

# 4. Add to .env
ANTHROPIC_API_KEY=your_key_here
```

---

## Performance Metrics

### Key Performance Indicators

| Metric | Target | Current |
|--------|--------|---------|
| Page Load Time | < 2s | ~1.5s |
| LLM Processing Time | < 30s per product | ~15-25s |
| PDF Extraction | < 5s per page | ~2-3s |
| Database Query Time | < 100ms | ~50-80ms |
| Session Creation | < 200ms | ~150ms |

### Optimization Opportunities

1. **Caching:** Implement Redis for prompt templates
2. **Async:** Use async/await for concurrent LLM calls
3. **Compression:** Compress large PDF thumbnails
4. **Lazy Loading:** Load UI components on demand
5. **Connection Pooling:** Use connection pool for PostgreSQL

---

**Last Updated:** 2025-10-10
**Version:** 3.0.0
**Author:** SweetCare Development Team
