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

# Default settings - Changed to GPT-4o and temperature 0.4
DEFAULT_GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.4

# Default provider and model for new configurations
DEFAULT_PROVIDER = "openai"  # Changed from "groq" to "openai"
DEFAULT_MODEL = "gpt-4o"  # Set to GPT-4o

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
STATE_DROPBOX_ACCESS_TOKEN = "dropbox_access_token"
STATE_DROPBOX_ENABLED = "dropbox_enabled"

# Environment variable names
ENV_GROQ_API_KEY = "GROQ_API_KEY"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_LANGSMITH_API_KEY = "LANGSMITH_API_KEY"
ENV_LANGSMITH_TRACING = "LANGSMITH_TRACING"
ENV_LANGSMITH_PROJECT = "LANGSMITH_PROJECT"
ENV_LANGSMITH_ENDPOINT = "LANGSMITH_ENDPOINT"
ENV_DROPBOX_ACCESS_TOKEN = "DROPBOX_ACCESS_TOKEN"

# File upload settings
PDF_TYPE = "pdf"
EXCEL_TYPES = ["xlsx", "xls"]

# PDF preview settings - Updated for higher resolution
PDF_PREVIEW_SCALE = 0.8  # Increased from 0.5 for better quality and bigger images

# Dropbox settings - Updated to use the new folder
DROPBOX_BASE_FOLDER = "/Product_AI_Content_Creator"
DROPBOX_TIMEOUT = 60  # seconds
DROPBOX_AUTO_ORGANIZE = False  # Changed to False since we're using a single folder
DROPBOX_ADD_TIMESTAMP = True  # Add timestamp to avoid conflicts

# PDF preview settings - Updated for higher resolution
PDF_PREVIEW_SCALE = 0.7  # Increased from 0.5 for better quality and bigger images

# Evaluation System Configuration
EVALUATION_ENABLED = True  # Master switch for evaluation system
EVALUATION_MODEL = "gpt-4o-mini"  # Cost-effective model for evaluation
EVALUATION_PROVIDER = "openai"  # Provider for evaluation model

# PHASE 3: OpenEvals Configuration
USE_OPENEVALS = True  # MAIN SWITCH: Enable OpenEvals 3-metric evaluator
OPENEVALS_MODEL = "gpt-4o-mini"  # Model for OpenEvals evaluations
OPENEVALS_PROVIDER = "openai"  # Provider for OpenEvals evaluations
OPENEVALS_TEMPERATURE = 0.1  # Low temperature for consistent evaluation
OPENEVALS_DEBUG = True  # Enable debug logging for OpenEvals

# OpenEvals 3-Metric System Configuration
EVALUATION_METRICS = [
    "structure_correctness",  # JSON structure and schema validation
    "content_correctness",  # Accuracy vs input, hallucination detection
    "translation_correctness",  # Portuguese translation quality
]

# Evaluation scoring weights for overall score calculation
EVALUATION_WEIGHTS = {
    "structure_correctness": 0.2,  # 20% - Structure compliance
    "content_correctness": 0.5,  # 50% - Content accuracy (most important)
    "translation_correctness": 0.3,  # 30% - Translation quality
}

# LangSmith Integration for Evaluations
LANGSMITH_EVALUATION_PROJECT = (
    "product_extraction_quality"  # Separate project for evaluations
)
EVALUATION_DATASET_NAME = "product_extraction_evals"
EVALUATION_DATASET_AUTO_CREATE = True  # Auto-create datasets in LangSmith
EVALUATION_CACHE_ENABLED = True  # Cache evaluation results for identical inputs
