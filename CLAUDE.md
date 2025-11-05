# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SweetCare AI Product Content Creator** - An enterprise-grade Streamlit application for automated e-commerce product data extraction from multiple sources (PDFs, Excel, websites). Uses LLMs (OpenAI GPT-4, Groq models) to extract structured product information for cosmetics, fragrances, and supplements with HS Code classification.

**Tech Stack**: Streamlit, LangChain, OpenAI/Groq APIs, PostgreSQL (Supabase), LangSmith tracing, Dropbox integration

## Running the Application

### Start the app
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

### Prerequisites
- Create `.env` file with API keys (see README.md Installation section)
- Configure `.streamlit/secrets.toml` with PostgreSQL credentials
- Install dependencies: `pip install -r requirements.txt`

## Development Commands

### Running with Python
```bash
python -m streamlit run app.py
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Activate virtual environment (if using)
```bash
# Windows
venv\Scripts\activate

# Unix/MacOS
source venv/bin/activate
```

## Architecture

### Core Application Flow

```
User (Browser)
    ↓
app.py (Main Entry Point)
    ↓
auth.py (UserManager) → PostgreSQL (Supabase)
    ↓ [Authenticated]
utils/batch_ui/main.py (Batch UI Orchestrator)
    ↓
├─ tabs/configure_tab.py (Product Configuration)
│   └─ components/configuration_form.py
├─ tabs/execute_tab.py (Batch Execution)
│   ├─ handlers/batch_processor.py
│   │   ├─ processors/pdf_processor.py (PyMuPDF)
│   │   ├─ processors/excel_processor.py (Pandas)
│   │   ├─ processors/web_processor.py (BeautifulSoup)
│   │   └─ processors/text_processor.py (LLM orchestration)
│   │       └─ models/model_factory.py
│   │           ├─ models/openai_model.py
│   │           └─ models/groq_model.py
│   └─ evaluations/evaluation_core.py (Quality scoring)
│       ├─ evaluations/metric_evaluator.py (3-metric system)
│       └─ evaluations/simple_db.py (SQLite metrics storage)
└─ tabs/reprocess_tab.py (Re-run failed extractions)
```

### Key Design Patterns

**1. Multi-Provider LLM Architecture**
- `models/model_factory.py` abstracts provider selection (OpenAI vs Groq)
- Each provider has dedicated module (`openai_model.py`, `groq_model.py`)
- Provider/model/temperature configurable per product type via `config.py`

**2. Product Type Flexibility**
- Three product types: `cosmetics`, `fragrance`, `subtype`
- Each has dedicated prompt file in `prompts/` directory
- Response format detection in `processors/text_processor.py:detect_response_format()`
  - `cosmetics`: Object with `Subtypes` array (flat + nested structure)
  - `fragrance`: Flat object with fragrance-specific fields
  - `subtype`: Array of product variants

**3. HS Code Classification Pipeline**
- Two-stage processing: 1) Extract product data, 2) Classify HS Code
- Uses dedicated model (configured in `config.py`: `HSCODE_MODEL`, `HSCODE_PROVIDER`)
- Prompt: `prompts/hscode_prompt.md`
- Logic in `processors/text_processor.py:classify_hscode()`

**4. Evaluation System (3-Metric Quality Scoring)**
- **OpenEvals Integration**: `evaluations/metric_evaluator.py` (primary)
- **Three Metrics**:
  - Structure Correctness (20%): JSON schema validation
  - Content Correctness (50%): Accuracy vs input, hallucination detection
  - Translation Correctness (30%): Portuguese translation quality
- Results stored in SQLite: `evaluations/evaluations.db`
- User attribution tracked (Phase 3 feature)

**5. Session State Management**
- `utils/state_manager.py` centralizes all Streamlit session state
- Product configurations stored in `st.session_state.products` (list of `ProductConfig` objects)
- User context in `st.session_state.current_user` (from auth system)

**6. User Authentication & Authorization**
- PostgreSQL backend via Supabase (connection via `.streamlit/secrets.toml`)
- `auth.py:UserManager` handles all user operations
- Role-Based Access Control (RBAC): `admin` and `user` roles
- Session duration: 7 days
- User context flows through batch processing → evaluation system

## Important File Locations

### Configuration
- `config.py` - All system configuration (models, prompts, evaluation settings)
- `.env` - API keys (OpenAI, Groq, LangSmith, Dropbox)
- `.streamlit/secrets.toml` - PostgreSQL credentials

### Core Modules
- `app.py` - Main entry point, authentication, app layout
- `auth.py` - Complete authentication system (PostgreSQL-backed)
- `models/model_factory.py` - LLM provider factory
- `processors/text_processor.py` - LLM orchestration, format detection, HS Code classification
- `evaluations/evaluation_core.py` - Quality evaluation orchestrator
- `evaluations/metric_evaluator.py` - OpenEvals 3-metric evaluator

### Product Type Prompts
- `prompts/cosmetics_prompt.md` - Cosmetics extraction prompt
- `prompts/fragrance_prompt.md` - Fragrance extraction prompt
- `prompts/subtype_prompt.md` - Subtype/variant extraction prompt
- `prompts/hscode_prompt.md` - HS Code classification prompt

### Batch UI Structure
- `utils/batch_ui/main.py` - UI orchestrator
- `utils/batch_ui/tabs/configure_tab.py` - Product configuration form
- `utils/batch_ui/tabs/execute_tab.py` - Batch processing execution
- `utils/batch_ui/handlers/batch_processor.py` - Core batch processing logic
- `utils/batch_ui/handlers/export_handler.py` - CSV/Excel export + Dropbox upload

## Key Implementation Details

### Adding a New Product Type

To add a new product type (e.g., "supplement"):

1. **Create prompt file**: `prompts/supplement_prompt.md`
   - Define JSON schema in prompt
   - Specify all required fields
   - Include examples

2. **Update `config.py`**:
   ```python
   SUPPLEMENT_PROMPT = "supplement_prompt.md"
   ```

3. **Update `utils/batch_ui/components/configuration_form.py`**:
   - Add "supplement" to product type dropdown options

4. **Update `processors/text_processor.py`**:
   - Add format detection logic in `detect_response_format()` if needed
   - Add HS Code extraction logic in `get_hscode_from_product_data()` if structure differs
   - Add HS Code injection logic in `set_hscode_in_product_data()`

5. **Test with real data** to validate extraction quality

### Modifying the Evaluation System

The evaluation system uses OpenEvals with 3 metrics (structure, content, translation):

- **Primary evaluator**: `evaluations/metric_evaluator.py:create_fixed_evaluator()`
- **Weights configured in `config.py`**:
  ```python
  EVALUATION_WEIGHTS = {
      "structure_correctness": 0.2,
      "content_correctness": 0.5,
      "translation_correctness": 0.3,
  }
  ```
- **Fallback evaluator**: If OpenEvals fails, falls back to simple prompt-based evaluation in `evaluation_core.py:_init_fallback_evaluator()`

To modify metric weights, edit `config.py:EVALUATION_WEIGHTS`.

### Understanding User Attribution (Phase 3)

User context flows through the entire pipeline:

1. **Login**: `auth.py:UserManager.get_current_user()` returns user dict
2. **Session State**: Stored in `st.session_state.current_user`
3. **Batch Processing**: `batch_processor.py:_get_current_user_context()` extracts user context
4. **Evaluation**: User context passed to `evaluation_core.py:evaluate_single_product(user_id, username, user_name)`
5. **Database**: Stored in SQLite `evaluations.db` with product metrics

### LangSmith Integration

LangSmith tracing is optional but recommended:

- **Initialization**: `utils/langsmith_utils.py:initialize_langsmith()`
- **Tracing**: Automatic via `@traceable` decorator on key functions
- **Configuration**: Set `LANGSMITH_API_KEY` in `.env`
- **Project**: Configured in `config.py:LANGSMITH_PROJECT`

### Dropbox Integration

Automatic cloud backup of results:

- **Handler**: `utils/dropbox_utils.py`
- **Usage**: Export buttons in `utils/batch_ui/components/export_buttons.py`
- **Configuration**: Set `DROPBOX_ACCESS_TOKEN` in `.env`
- **Base folder**: `/Product_AI_Content_Creator` (configured in `config.py`)

## Common Development Tasks

### Debugging LLM Extraction Issues

1. Check LangSmith traces (if enabled) for detailed LLM call logs
2. Review prompt file for the product type in `prompts/`
3. Check `processors/text_processor.py:process_with_llm()` for extraction logic
4. Verify JSON parsing in `process_with_llm()` (handles markdown code blocks)
5. Test with lower temperature for more deterministic output

### Troubleshooting Evaluation Failures

1. Check `evaluations/evaluation_core.py` for evaluation flow
2. Verify OpenEvals is available: `OPENEVALS_AVAILABLE = True`
3. Check evaluation model in `config.py:EVALUATION_MODEL`
4. Review SQLite database: `evaluations/evaluations.db`
5. Check fallback evaluator if OpenEvals fails

### Testing Authentication Changes

1. PostgreSQL connection: `auth.py:_get_postgres_connection()`
2. User table initialization: `auth.py:_ensure_users_table_exists()`
3. Default admin: `auth.py:_ensure_default_admin_exists()`
4. Session management: `auth.py:create_session()`, `validate_session()`
5. Test with/without valid credentials

### Working with Product Configurations

Product configurations are stored as `ProductConfig` objects:

```python
from utils.product_config import ProductConfig, add_product_config, get_product_configs

# Create new configuration
config = ProductConfig(
    product_type="cosmetics",
    model="gpt-4o-mini-2024-07-18",
    temperature=0.4,
    provider="openai",
    pdf_file=uploaded_file,
    selected_pages=[0, 1, 2]
)

# Add to session state
add_product_config(config)

# Retrieve all configurations
configs = get_product_configs()
```

### Modifying Export Functionality

Export logic in `utils/batch_ui/handlers/export_handler.py`:

- **CSV Export**: `export_handler.py:export_to_csv()`
- **Excel Export**: `export_handler.py:export_to_excel()`
- **Dropbox Upload**: `export_handler.py:upload_to_dropbox()`

All exports include:
- Extracted product data
- Quality scores (structure, content, translation, overall)
- User attribution (username, user_name)
- Timestamps

## Testing Notes

- No formal test suite currently exists
- Manual testing workflow:
  1. Start app with `streamlit run app.py`
  2. Login with test credentials
  3. Configure product (upload PDF/Excel or enter URL)
  4. Execute batch processing
  5. Verify extraction results and quality scores
  6. Test export to CSV/Excel

## Code Quality Notes

- **Error Handling**: Most functions have try-except blocks, but error messages could be more descriptive
- **Logging**: Limited logging; primarily uses Streamlit `st.error()` and `st.warning()`
- **Type Hints**: Partial type hints in newer code (e.g., `batch_processor.py`)
- **Documentation**: Docstrings present in core modules but inconsistent

## Known Limitations

1. **Single-User Sessions**: Session state is per-user, but no multi-tenancy isolation
2. **SQLite for Evaluations**: SQLite used for metrics (not PostgreSQL) - consider consolidating
3. **No Async Processing**: All LLM calls are synchronous - could benefit from async/concurrent processing
4. **Limited Error Recovery**: Failed extractions can be reprocessed, but no automatic retry logic
5. **Hardcoded Prompts**: Prompts in markdown files, not dynamically editable via UI

## Environment Variables Required

```env
# Required
OPENAI_API_KEY=sk-...

# Optional but recommended
GROQ_API_KEY=gsk_...
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=ai_product_creator
DROPBOX_ACCESS_TOKEN=sl....

# Authentication
MASTER_PASSWORD=your_secure_password
```

## PostgreSQL Schema (Supabase)

User authentication tables created by `auth.py`:

```sql
-- Users table
users (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE,
    name TEXT,
    email TEXT,
    password_hash TEXT,
    role TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_login TIMESTAMP
)

-- Sessions table
sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token TEXT UNIQUE,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
)

-- Activity logs table
activity_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action TEXT,
    details JSONB,
    created_at TIMESTAMP
)
```

## Experimental/Legacy Code

The `category/` directory contains experimental classification strategies:
- `llm_strat/` - LLM-based product categorization
- `embed_strat/` - Embedding-based categorization
- `hybrid_strat/` - Hybrid approach

These are **not** used in the main application flow and can be ignored for most development work.
