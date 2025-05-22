# Configuration file for the E-commerce Product Extractor

# LLM Models
GROQ_MODELS = [
    "deepseek-r1-distill-llama-70b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.3-70b-versatile",
]

OPENAI_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
]

# Default settings
DEFAULT_GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.2

# Dedicated model for HScode classification
HSCODE_MODEL = "deepseek-r1-distill-llama-70b"
HSCODE_PROVIDER = "groq"
HSCODE_TEMPERATURE = 0.1

# LangSmith settings
LANGSMITH_PROJECT = "ai_product_creator"
LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"

# Prompt file paths
PROMPT_DIRECTORY = "prompts"
COSMETICS_PROMPT = "cosmetics_prompt.md"
FRAGRANCE_PROMPT = "fragrance_prompt.md"
SUBTYPE_PROMPT = "subtype_prompt.md"
HSCODE_PROMPT = "hscode_prompt.md"

# Session state keys
STATE_PRODUCTS = "products"
STATE_EXCEL_HEADER_ROW = "excel_header_row"
STATE_LANGSMITH_ENABLED = "langsmith_enabled"
STATE_GROQ_API_KEY = "groq_api_key"
STATE_OPENAI_API_KEY = "openai_api_key"

# Environment variable names
ENV_GROQ_API_KEY = "GROQ_API_KEY"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_LANGSMITH_API_KEY = "LANGSMITH_API_KEY"
ENV_LANGSMITH_TRACING = "LANGSMITH_TRACING"
ENV_LANGSMITH_PROJECT = "LANGSMITH_PROJECT"
ENV_LANGSMITH_ENDPOINT = "LANGSMITH_ENDPOINT"

# File upload settings
PDF_TYPE = "pdf"
EXCEL_TYPES = ["xlsx", "xls", "csv"]  # Added CSV support

# PDF preview settings
PDF_PREVIEW_SCALE = 0.5  # Scale down factor for preview
