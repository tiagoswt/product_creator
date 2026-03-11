# AI Product Content Creator

An enterprise-grade Streamlit application for automated e-commerce product data extraction from multiple sources (PDFs, Excel files, websites). Uses LLMs (OpenAI GPT-4, Groq) to extract structured product information for cosmetics, fragrances, and supplements, with HS Code classification and a 3-metric quality evaluation system.

---

## Features

- **Multi-source extraction**: PDF catalogues, Excel sheets, and product web pages
- **Multiple product types**: Cosmetics, Fragrance, Supplements, Subtype/variants
- **HS Code classification**: Automated harmonized system code assignment
- **Quality evaluation**: 3-metric scoring (structure, content accuracy, translation quality)
- **User authentication**: PostgreSQL-backed RBAC with admin and user roles
- **Cloud backup**: Automatic upload of results to Dropbox
- **LangSmith tracing**: Optional LLM call monitoring and debugging

---

## Architecture

```
app.py                         ← Main entry point
├── auth.py                    ← User management (PostgreSQL/Supabase)
├── config.py                  ← All system configuration
├── models/
│   ├── model_factory.py       ← LLM provider abstraction
│   ├── openai_model.py
│   └── groq_model.py
├── processors/
│   ├── pdf_processor.py       ← PyMuPDF-based PDF extraction
│   ├── excel_processor.py     ← Pandas-based Excel/CSV processing
│   ├── web_processor.py       ← BeautifulSoup web scraping
│   └── text_processor.py      ← LLM orchestration + HS Code classification
├── evaluations/
│   ├── evaluation_core.py     ← Quality evaluation orchestrator
│   ├── metric_evaluator.py    ← OpenEvals 3-metric evaluator
│   └── simple_db.py           ← SQLite metrics storage
├── prompts/                   ← LLM prompt files (Markdown)
│   ├── cosmetics_prompt.md
│   ├── fragrance_prompt.md
│   ├── subtype_prompt.md
│   ├── supplement_prompt.md
│   └── hscode_prompt.md
└── utils/
    ├── batch_ui/              ← Streamlit UI components
    ├── state_manager.py
    ├── dropbox_utils.py
    └── langsmith_utils.py
```

---

## Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com) project (free tier works) for user authentication
- At least one LLM API key: [OpenAI](https://platform.openai.com) or [Groq](https://console.groq.com)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/sweetcare-ai-product-creator.git
cd sweetcare-ai-product-creator
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### 3.1 Environment variables

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key (`sk-...`) |
| `GROQ_API_KEY` | No | Groq API key (`gsk_...`) |
| `LANGSMITH_API_KEY` | No | LangSmith tracing key |
| `LANGSMITH_TRACING` | No | Set to `true` to enable tracing |
| `LANGSMITH_PROJECT` | No | LangSmith project name |
| `FIRECRAWL_API_KEY` | No | Firecrawl key for enhanced web scraping |
| `DROPBOX_ACCESS_TOKEN` | No | Dropbox token for auto cloud backup |
| `MASTER_PASSWORD` | Yes | Password for the initial admin account |

### 3.2 PostgreSQL / Supabase (user authentication)

Copy the example secrets file:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your Supabase project credentials:

```toml
[connections.postgresql]
dialect = "postgresql"
host = "aws-0-eu-west-3.pooler.supabase.com"
port = 6543
database = "postgres"
username = "your_db_username"
password = "your_db_password"
```

You can find these values in your Supabase project under **Settings → Database → Connection string (pooler)**.

The application will automatically create the required tables (`users`, `sessions`, `activity_logs`) on first run.

---

## Running the App

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

Log in with the default admin account:
- **Username**: value of `AUTH_USERNAME` in `.env` (default: `admin`)
- **Password**: value of `MASTER_PASSWORD` in `.env`

---

## Data Files

### Input files (uploaded at runtime via the UI)

The app does **not** require any pre-placed data files. All input is uploaded through the browser interface:

| Source type | Accepted formats | Notes |
|---|---|---|
| PDF catalogue | `.pdf` | Pages selectable in the UI |
| Excel / CSV | `.xlsx`, `.xls`, `.csv` | First row must be column headers |
| Website | URL | One URL per batch item |

**Excel file format**: The first row is always treated as the header row. Column names are passed directly to the LLM prompt — no fixed column names are required, but descriptive names improve extraction quality.

### Output files

| Output | Location | Format |
|---|---|---|
| Extracted product JSON | Dropbox `/Product_AI_Content_Creator/` | `{brand}_{YYYYMMDD_HHMMSS}.json` |
| Export (manual) | Downloaded via UI | `.csv` or `.xlsx` |
| Quality scores DB | `evaluations/evaluations.db` (local, git-ignored) | SQLite |

### Prompt files (committed, editable)

LLM extraction prompts live in `prompts/` and can be edited to tune extraction quality:

| File | Product type |
|---|---|
| `prompts/cosmetics_prompt.md` | Cosmetics |
| `prompts/fragrance_prompt.md` | Fragrances |
| `prompts/subtype_prompt.md` | Subtype / variants |
| `prompts/supplement_prompt.md` | Supplements |
| `prompts/hscode_prompt.md` | HS Code classification |

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLMs | OpenAI GPT-4, Groq (LLaMA, DeepSeek) |
| LLM framework | LangChain, LangSmith |
| PDF parsing | PyMuPDF |
| Excel/CSV | Pandas, openpyxl |
| Web scraping | BeautifulSoup4, Firecrawl |
| Authentication | PostgreSQL via Supabase |
| Evaluation | OpenEvals + SQLite |
| Cloud storage | Dropbox API |

---

## Experimental Code

The `category/` directory contains experimental classification strategies (LLM-based, embedding-based, hybrid) that are **not used** in the main application flow. They are kept for reference only.
