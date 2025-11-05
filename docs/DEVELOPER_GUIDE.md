# 👨‍💻 Developer Guide

**SweetCare AI Product Content Creator**

*Complete guide for developers contributing to the project*

---

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Adding New Features](#adding-new-features)
- [Testing](#testing)
- [Debugging](#debugging)
- [Contributing](#contributing)
- [Deployment](#deployment)
- [API Integration](#api-integration)
- [Database Management](#database-management)
- [Performance Optimization](#performance-optimization)
- [Security Considerations](#security-considerations)

---

## Development Environment Setup

### Prerequisites

Install the following tools:

```bash
# Check Python version
python --version  # Should be 3.8 or higher

# Install Git (if not already installed)
git --version

# Install pip
python -m pip --version
```

### Initial Setup

#### 1. Clone Repository

```bash
git clone <repository-url>
cd ai_product_creator_DEV
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install development dependencies (if available)
pip install -r requirements-dev.txt
```

#### 4. Configure Environment Variables

Create `.env` file in project root:

```env
# OpenAI API
OPENAI_API_KEY=sk-...your_key_here...

# Groq API (optional)
GROQ_API_KEY=gsk_...your_key_here...

# LangSmith (optional)
LANGSMITH_API_KEY=lsv2_...your_key_here...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=ai_product_creator_dev

# Dropbox (optional)
DROPBOX_ACCESS_TOKEN=sl....your_token_here...

# Authentication
MASTER_PASSWORD=YourSecurePassword123
```

#### 5. Configure Streamlit Secrets

Create `.streamlit/secrets.toml`:

```toml
# PostgreSQL Configuration (Supabase)
[postgres]
host = "your-project.supabase.co"
port = "5432"
database = "postgres"
user = "postgres"
password = "your-database-password"
```

#### 6. Initialize Database

```bash
# The database tables will be created automatically on first run
# Or manually run the schema creation:
python -c "from auth import UserManager; UserManager()"
```

#### 7. Run Application

```bash
streamlit run app.py
```

Access at: `http://localhost:8501`

---

## Project Structure

### Directory Overview

```
ai_product_creator_DEV/
├── app.py                      # Main application entry point
├── auth.py                     # Authentication system
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create manually)
│
├── .streamlit/                 # Streamlit configuration
│   └── secrets.toml           # Database credentials (create manually)
│
├── models/                     # LLM model integration
│   ├── __init__.py
│   ├── model_factory.py       # Model factory
│   ├── openai_model.py        # OpenAI integration
│   └── groq_model.py          # Groq integration
│
├── processors/                 # Data processors
│   ├── __init__.py
│   ├── text_processor.py      # Main LLM processing
│   ├── pdf_processor.py       # PDF extraction
│   ├── excel_processor.py     # Excel/CSV processing
│   └── web_processor.py       # Web scraping
│
├── prompts/                    # Product extraction prompts
│   ├── cosmetics_prompt.md
│   ├── fragrance_prompt.md
│   ├── subtype_prompt.md
│   └── hscode_prompt.md
│
├── evaluations/                # Quality evaluation system
│   ├── __init__.py
│   ├── evaluation_core.py
│   ├── metric_evaluator.py
│   ├── simple_db.py
│   ├── evaluation_ui.py
│   └── tabbed_analytics_dashboard.py
│
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── state_manager.py
│   ├── product_config.py
│   ├── langsmith_utils.py
│   ├── dropbox_utils.py
│   │
│   └── batch_ui/              # Batch processing UI
│       ├── __init__.py
│       ├── main.py
│       ├── tabs/              # UI tabs
│       ├── components/        # Reusable components
│       ├── handlers/          # Business logic
│       └── utils/             # Helpers
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md     # This file
│   └── API_REFERENCE.md
│
└── category/                   # Experimental classification
    ├── llm_strat/
    ├── embed_strat/
    └── hybrid_strat/
```

### Key Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `app.py` | Main entry point | `main()` |
| `auth.py` | Authentication | `UserManager` class |
| `config.py` | Configuration | Constants and settings |
| `text_processor.py` | LLM processing | `process_with_llm()` |
| `model_factory.py` | Model initialization | `get_llm()` |
| `product_config.py` | Product configuration | `ProductConfig` class |

---

## Coding Standards

### Python Style Guide

Follow **PEP 8** style guidelines:

```python
# Good naming conventions
class ProductConfig:  # PascalCase for classes
    def __init__(self):
        self.product_type = "cosmetics"  # snake_case for variables

    def process_data(self):  # snake_case for methods
        """Process product data"""  # Docstrings for all functions
        pass

# Constants in UPPER_CASE
DEFAULT_TEMPERATURE = 0.4
MAX_RETRIES = 3

# Private methods with leading underscore
def _internal_helper():
    pass
```

### Code Formatting

Use **Black** formatter (recommended):

```bash
# Install Black
pip install black

# Format code
black app.py

# Format entire project
black .
```

### Import Organization

```python
# Standard library imports
import os
import json
from datetime import datetime

# Third-party imports
import streamlit as st
import pandas as pd
from langchain_core.prompts import PromptTemplate

# Local imports
from models.model_factory import get_llm
from utils.product_config import ProductConfig
import config
```

### Docstrings

Use **Google-style docstrings**:

```python
def process_with_llm(text: str, product_type: str, llm) -> dict:
    """
    Process text with LLM to extract product information.

    Args:
        text (str): Input text to process
        product_type (str): Type of product (cosmetics, fragrance, subtype)
        llm: Language model instance

    Returns:
        dict: Extracted product data in JSON format

    Raises:
        ValueError: If product_type is invalid
        Exception: If LLM processing fails

    Example:
        >>> llm = get_llm("openai", "gpt-4o-mini")
        >>> result = process_with_llm("Product info...", "cosmetics", llm)
        >>> print(result["product_name"])
        "Hydrating Cream"
    """
    pass
```

### Type Hints

Use type hints for function signatures:

```python
from typing import Dict, List, Optional, Tuple

def authenticate_user(
    username: str,
    password: str
) -> Tuple[bool, Optional[Dict], str]:
    """Authenticate a user and return status, user data, and message"""
    pass

def get_product_configs() -> List[ProductConfig]:
    """Get list of product configurations"""
    pass
```

---

## Adding New Features

### Adding a New Product Type

See [IMPLEMENTATION_PLAN_NEW_PROMPTS.md](../IMPLEMENTATION_PLAN_NEW_PROMPTS.md) for detailed instructions.

**Quick Summary:**

1. **Create prompt file:**
   ```bash
   touch prompts/supplement_prompt.md
   ```

2. **Add constant to `config.py`:**
   ```python
   SUPPLEMENT_PROMPT = "supplement_prompt.md"
   ```

3. **Update UI dropdown in `configuration_form.py`:**
   ```python
   product_type = st.selectbox(
       "Product Type",
       ["cosmetics", "fragrance", "subtype", "supplement"],
       ...
   )
   ```

4. **Add processing logic in `text_processor.py`:**
   ```python
   elif product_type == "supplement":
       prompt_content = load_prompt_from_file(config.SUPPLEMENT_PROMPT)
   ```

---

### Adding a New Data Source

**Example: Adding Google Sheets support**

#### 1. Create Processor Module

Create `processors/sheets_processor.py`:

```python
"""Google Sheets processor for extracting data"""

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

def process_google_sheet(
    sheet_url: str,
    sheet_name: str = "Sheet1",
    credentials_json: str = None
) -> str:
    """
    Extract data from Google Sheets.

    Args:
        sheet_url (str): Full Google Sheets URL
        sheet_name (str): Name of sheet to extract
        credentials_json (str): Path to credentials file

    Returns:
        str: Extracted text content from sheet
    """
    try:
        # Extract sheet ID from URL
        sheet_id = extract_sheet_id(sheet_url)

        # Authenticate
        credentials = service_account.Credentials.from_service_account_file(
            credentials_json,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )

        # Build service
        service = build('sheets', 'v4', credentials=credentials)

        # Get data
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=sheet_name
        ).execute()

        values = result.get('values', [])

        # Convert to text
        text = "\n".join([" | ".join(row) for row in values])

        return text

    except Exception as e:
        st.error(f"Error processing Google Sheet: {e}")
        return ""

def extract_sheet_id(url: str) -> str:
    """Extract sheet ID from Google Sheets URL"""
    # Implementation...
    pass
```

#### 2. Add UI Component

Update `utils/batch_ui/components/configuration_form.py`:

```python
def _render_sheets_section(self):
    """Render Google Sheets input section"""
    st.write("**📊 Google Sheets Source**")

    sheets_url = st.text_input(
        "Google Sheets URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Paste the full Google Sheets URL"
    )

    sheet_name = st.text_input(
        "Sheet Name",
        value="Sheet1",
        help="Name of the sheet tab to extract"
    )

    return sheets_url, sheet_name
```

#### 3. Integrate in Batch Processor

Update `utils/batch_ui/handlers/batch_processor.py`:

```python
from processors.sheets_processor import process_google_sheet

def consolidate_data_sources(config: ProductConfig) -> str:
    """Consolidate data from all sources"""
    consolidated_text = ""

    # Existing sources...

    # Add Google Sheets
    if config.sheets_url:
        st.info(f"Processing Google Sheets: {config.sheets_url}")
        sheets_text = process_google_sheet(
            config.sheets_url,
            config.sheet_name
        )
        consolidated_text += f"\n\n=== Google Sheets Data ===\n{sheets_text}"

    return consolidated_text
```

#### 4. Update Product Config

Add sheets fields to `utils/product_config.py`:

```python
class ProductConfig:
    def __init__(
        self,
        # ... existing parameters ...
        sheets_url: str = None,
        sheet_name: str = "Sheet1",
    ):
        # ... existing initialization ...
        self.sheets_url = sheets_url
        self.sheet_name = sheet_name
```

---

### Adding a New LLM Provider

**Example: Adding Anthropic Claude**

#### 1. Install Package

```bash
pip install langchain-anthropic
```

#### 2. Create Model Module

Create `models/anthropic_model.py`:

```python
"""Anthropic Claude integration"""

import os
from langchain_anthropic import ChatAnthropic

def get_anthropic_model(
    model_name: str = "claude-3-opus-20240229",
    temperature: float = 0.4
) -> ChatAnthropic:
    """
    Initialize Anthropic Claude model.

    Args:
        model_name (str): Anthropic model identifier
        temperature (float): Sampling temperature

    Returns:
        ChatAnthropic: Initialized model instance
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")

    return ChatAnthropic(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        max_tokens=4096
    )
```

#### 3. Update Model Factory

Update `models/model_factory.py`:

```python
from models.anthropic_model import get_anthropic_model

def get_llm(
    provider: str = None,
    model_name: str = None,
    temperature: float = None
) -> BaseLanguageModel:
    """Factory function to get LLM instance"""

    # ... existing code ...

    elif provider == "anthropic":
        model_name = model_name or "claude-3-opus-20240229"
        return get_anthropic_model(model_name, temperature)

    else:
        raise ValueError(f"Unsupported provider: {provider}")
```

#### 4. Update Config

Add to `config.py`:

```python
# Anthropic models
ANTHROPIC_MODELS = [
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307"
]

# Default Anthropic model
DEFAULT_ANTHROPIC_MODEL = "claude-3-sonnet-20240229"
```

#### 5. Add API Key to .env

```env
ANTHROPIC_API_KEY=sk-ant-...your_key_here...
```

---

## Testing

### Unit Testing

Create test files in `tests/` directory:

```python
# tests/test_text_processor.py

import unittest
from processors.text_processor import process_with_llm, load_prompt_from_file

class TestTextProcessor(unittest.TestCase):

    def test_load_prompt_from_file(self):
        """Test loading prompt from file"""
        prompt = load_prompt_from_file("cosmetics_prompt.md")
        self.assertIsNotNone(prompt)
        self.assertIn("Extract", prompt)

    def test_process_with_llm(self):
        """Test LLM processing"""
        # Mock LLM for testing
        mock_llm = MockLLM()
        result = process_with_llm(
            "Test product info",
            "cosmetics",
            mock_llm
        )
        self.assertIsInstance(result, dict)
        self.assertIn("product_name", result)

    def setUp(self):
        """Set up test fixtures"""
        pass

    def tearDown(self):
        """Clean up after tests"""
        pass

if __name__ == '__main__':
    unittest.main()
```

### Running Tests

```bash
# Run all tests
python -m unittest discover tests/

# Run specific test file
python -m unittest tests/test_text_processor.py

# Run with verbose output
python -m unittest discover tests/ -v
```

### Integration Testing

Test full workflow:

```python
# tests/test_integration.py

import unittest
from models.model_factory import get_llm
from processors.text_processor import process_with_llm
from utils.product_config import ProductConfig

class TestIntegration(unittest.TestCase):

    def test_full_extraction_workflow(self):
        """Test complete extraction workflow"""
        # 1. Create config
        config = ProductConfig(
            product_type="fragrance",
            website_url="https://example.com/product"
        )

        # 2. Get LLM
        llm = get_llm("openai", "gpt-4o-mini", 0.4)

        # 3. Process data
        result = process_with_llm(
            "Sample product data",
            "fragrance",
            llm
        )

        # 4. Verify result
        self.assertIsNotNone(result)
        self.assertIn("product_name", result)
        self.assertIn("hscode", result)
```

### Manual Testing Checklist

Before deploying:

- [ ] Login/logout works
- [ ] User registration works
- [ ] PDF upload and page selection
- [ ] Excel upload and row selection
- [ ] Website URL processing
- [ ] Batch processing completes
- [ ] Quality scores calculate correctly
- [ ] CSV export works
- [ ] Excel export works
- [ ] Dropbox upload works (if configured)
- [ ] Reprocessing works
- [ ] Admin user management works
- [ ] All error messages display correctly

---

## Debugging

### Streamlit Debugging

#### Enable Debug Mode

```bash
streamlit run app.py --server.runOnSave true --logger.level debug
```

#### Print Debugging

```python
import streamlit as st

# Display variable values
st.write("Debug - product_type:", product_type)
st.write("Debug - config:", config.to_dict())

# Display in expander
with st.expander("Debug Info"):
    st.json({"key": "value"})
```

#### Session State Inspection

```python
# Display all session state
st.write("Session State:", st.session_state)

# Check specific keys
if "product_configs" in st.session_state:
    st.write("Configs:", len(st.session_state.product_configs))
```

### LLM Debugging

#### LangSmith Tracing

```python
from langsmith import traceable

@traceable(name="custom_function", tags=["debugging"])
def my_function(arg1, arg2):
    # Function will be traced in LangSmith
    pass
```

View traces at: https://smith.langchain.com/

#### Log LLM Requests/Responses

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_with_llm(text, product_type, llm):
    logger.debug(f"Processing with {product_type}")
    logger.debug(f"Input text length: {len(text)}")

    response = llm.invoke(text)

    logger.debug(f"Response: {response}")
    return response
```

### Database Debugging

#### Test PostgreSQL Connection

```python
import psycopg2

try:
    conn = psycopg2.connect(
        host="your-project.supabase.co",
        port="5432",
        database="postgres",
        user="postgres",
        password="your-password"
    )
    print("✅ Connection successful")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

#### Query Database Directly

```python
from auth import UserManager

auth = UserManager()

# Test query
users = auth._run_auth_query("SELECT * FROM users")
print(f"Found {len(users)} users")
```

---

## Contributing

### Git Workflow

#### 1. Create Feature Branch

```bash
git checkout -b feature/add-supplement-type
```

#### 2. Make Changes

```bash
# Edit files
# Test changes
# Commit frequently
```

#### 3. Commit Changes

```bash
git add .
git commit -m "feat: Add supplement product type support

- Created supplement_prompt.md
- Updated config.py with SUPPLEMENT_PROMPT
- Added supplement to UI dropdown
- Added processing logic in text_processor.py"
```

#### 4. Push Branch

```bash
git push origin feature/add-supplement-type
```

#### 5. Create Pull Request

1. Go to repository on GitHub/GitLab
2. Click "New Pull Request"
3. Select your feature branch
4. Fill in PR template
5. Request review

### Commit Message Conventions

Use **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Build/tooling changes

**Examples:**

```bash
git commit -m "feat(processors): Add Google Sheets processor"

git commit -m "fix(auth): Fix session expiration logic"

git commit -m "docs: Update developer guide with testing section"

git commit -m "refactor(text_processor): Extract HSCode logic to separate function"
```

### Code Review Checklist

**Before submitting PR:**

- [ ] Code follows PEP 8 style guide
- [ ] All functions have docstrings
- [ ] Type hints added to function signatures
- [ ] No hardcoded credentials or secrets
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with main
- [ ] No merge conflicts

**Reviewer checklist:**

- [ ] Code is readable and maintainable
- [ ] No security vulnerabilities introduced
- [ ] Error handling is appropriate
- [ ] Tests cover edge cases
- [ ] Performance impact is acceptable
- [ ] Documentation is accurate

---

## Deployment

### Production Deployment

#### 1. Prepare Environment

```bash
# Create production .env
cp .env.example .env.production

# Edit with production values
nano .env.production
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt --no-dev
```

#### 3. Run with Production Settings

```bash
# Set production environment
export STREAMLIT_ENV=production

# Run with production config
streamlit run app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
```

### Docker Deployment

#### Create Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### Build and Run

```bash
# Build image
docker build -t sweetcare-product-creator:latest .

# Run container
docker run -d \
  -p 8501:8501 \
  --env-file .env.production \
  --name product-creator \
  sweetcare-product-creator:latest
```

### Using Docker Compose

#### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8501:8501"
    env_file:
      - .env.production
    volumes:
      - ./evaluations:/app/evaluations
    restart: unless-stopped
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: sweetcare
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

#### Deploy with Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## API Integration

### Creating a REST API Wrapper

To expose functionality via REST API:

```python
# api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from processors.text_processor import process_with_llm
from models.model_factory import get_llm

app = FastAPI(title="Product Extraction API")

class ExtractionRequest(BaseModel):
    text: str
    product_type: str
    model_provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.4

class ExtractionResponse(BaseModel):
    product_data: dict
    processing_time: float
    status: str

@app.post("/extract", response_model=ExtractionResponse)
async def extract_product(request: ExtractionRequest):
    """Extract product information from text"""
    try:
        import time
        start_time = time.time()

        # Get LLM
        llm = get_llm(
            request.model_provider,
            request.model_name,
            request.temperature
        )

        # Process
        result = process_with_llm(
            request.text,
            request.product_type,
            llm
        )

        processing_time = time.time() - start_time

        return ExtractionResponse(
            product_data=result,
            processing_time=processing_time,
            status="success"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run with: uvicorn api:app --reload
```

---

## Database Management

### Database Migrations

#### Manual Migration Script

```python
# migrations/001_add_user_stats.py

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def migrate():
    """Add user statistics columns"""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    cursor = conn.cursor()

    try:
        # Add columns
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS products_created INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS evaluations_completed INTEGER DEFAULT 0
        """)

        conn.commit()
        print("✅ Migration successful")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
```

### Backup and Restore

#### Backup PostgreSQL

```bash
# Backup database
pg_dump -h your-project.supabase.co \
        -U postgres \
        -d postgres \
        -F c \
        -f backup_$(date +%Y%m%d).dump

# Backup SQLite
cp evaluations/evaluations.db evaluations/evaluations_backup_$(date +%Y%m%d).db
```

#### Restore PostgreSQL

```bash
# Restore database
pg_restore -h your-project.supabase.co \
           -U postgres \
           -d postgres \
           -c \
           backup_20250110.dump
```

---

## Performance Optimization

### Profiling

#### Python Profiler

```python
import cProfile
import pstats

def profile_function():
    """Profile a specific function"""
    profiler = cProfile.Profile()
    profiler.enable()

    # Run function
    process_with_llm(text, product_type, llm)

    profiler.disable()

    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

### Caching

#### Streamlit Caching

```python
import streamlit as st

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_prompt_template(prompt_file):
    """Load and cache prompt template"""
    with open(f"prompts/{prompt_file}") as f:
        return f.read()

@st.cache_resource
def get_database_connection():
    """Cache database connection"""
    return psycopg2.connect(...)
```

### Async Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_batch_async(configs):
    """Process batch asynchronously"""
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                process_single_product,
                config
            )
            for config in configs
        ]
        results = await asyncio.gather(*tasks)
    return results
```

---

## Security Considerations

### Input Validation

```python
def validate_url(url: str) -> bool:
    """Validate URL format and security"""
    import re
    from urllib.parse import urlparse

    # Check format
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if not pattern.match(url):
        return False

    # Check blacklist
    parsed = urlparse(url)
    blacklist = ['file://', 'javascript:', 'data:']
    if any(parsed.scheme.startswith(b) for b in blacklist):
        return False

    return True
```

### API Key Management

```python
import os
from cryptography.fernet import Fernet

class SecureConfig:
    """Secure configuration manager"""

    def __init__(self):
        # Generate key: Fernet.generate_key()
        self.key = os.getenv("ENCRYPTION_KEY").encode()
        self.cipher = Fernet(self.key)

    def encrypt_value(self, value: str) -> str:
        """Encrypt sensitive value"""
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted: str) -> str:
        """Decrypt sensitive value"""
        return self.cipher.decrypt(encrypted.encode()).decode()
```

### SQL Injection Prevention

```python
# ✅ GOOD - Use parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE username = %s",
    (username,)
)

# ❌ BAD - String formatting (vulnerable to SQL injection)
cursor.execute(
    f"SELECT * FROM users WHERE username = '{username}'"
)
```

---

## Resources

### Documentation

- [Streamlit Docs](https://docs.streamlit.io/)
- [LangChain Docs](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Supabase Docs](https://supabase.com/docs)

### Tools

- [Black Formatter](https://black.readthedocs.io/)
- [Ruff Linter](https://docs.astral.sh/ruff/)
- [mypy Type Checker](https://mypy.readthedocs.io/)

---

**Last Updated:** 2025-10-10
**Version:** 3.0.0
**Maintainer:** SweetCare Development Team
