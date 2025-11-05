# 📚 API Reference

**SweetCare AI Product Content Creator**

*Complete API documentation for all modules and functions*

---

## Table of Contents

- [Core Modules](#core-modules)
  - [app.py](#apppy)
  - [auth.py](#authpy)
  - [config.py](#configpy)
- [Model Modules](#model-modules)
  - [model_factory.py](#model_factorypy)
  - [openai_model.py](#openai_modelpy)
  - [groq_model.py](#groq_modelpy)
- [Processor Modules](#processor-modules)
  - [text_processor.py](#text_processorpy)
  - [pdf_processor.py](#pdf_processorpy)
  - [excel_processor.py](#excel_processorpy)
  - [web_processor.py](#web_processorpy)
- [Evaluation Modules](#evaluation-modules)
  - [evaluation_core.py](#evaluation_corepy)
  - [metric_evaluator.py](#metric_evaluatorpy)
- [Utility Modules](#utility-modules)
  - [product_config.py](#product_configpy)
  - [state_manager.py](#state_managerpy)
  - [dropbox_utils.py](#dropbox_utilspy)

---

## Core Modules

### app.py

Main application entry point and controller.

#### `main()`

Main application function that initializes and runs the Streamlit app.

```python
def main() -> None:
    """
    Initialize and run the main Streamlit application.

    This function:
    1. Sets up page configuration
    2. Initializes authentication system
    3. Requires user authentication
    4. Initializes LangSmith tracing
    5. Renders the main UI

    Returns:
        None
    """
```

**Usage:**
```python
if __name__ == "__main__":
    main()
```

---

### auth.py

User authentication and management system.

#### Class: `UserManager`

Main class for managing user authentication, sessions, and user management.

##### `__init__()`

```python
def __init__(self) -> None:
    """
    Initialize the UserManager with database connection.

    Creates:
    - PostgreSQL connection (cached)
    - Users table
    - Sessions table
    - Activity log table
    - Default admin user (if no users exist)
    """
```

##### `authenticate_user(username, password)`

```python
def authenticate_user(
    self,
    username: str,
    password: str
) -> Tuple[bool, Optional[Dict], str]:
    """
    Authenticate a user with username and password.

    Args:
        username (str): User's username
        password (str): User's plain-text password

    Returns:
        Tuple[bool, Optional[Dict], str]:
            - Success status (True/False)
            - User data dict (if successful, else None)
            - Message string (success or error message)

    Example:
        >>> auth = UserManager()
        >>> success, user, msg = auth.authenticate_user("john", "Pass123")
        >>> if success:
        ...     print(f"Welcome {user['name']}")
    """
```

##### `create_user(username, email, name, password, role)`

```python
def create_user(
    self,
    username: str,
    email: str,
    name: str,
    password: str,
    role: str = "user"
) -> Tuple[bool, str]:
    """
    Create a new user account.

    Args:
        username (str): Unique username (3+ characters)
        email (str): Valid email address (unique)
        name (str): Full name (2+ characters)
        password (str): Password meeting requirements
        role (str): User role ('user' or 'admin'), default 'user'

    Returns:
        Tuple[bool, str]:
            - Success status (True/False)
            - Message string (success or error details)

    Password Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number

    Example:
        >>> auth = UserManager()
        >>> success, msg = auth.create_user(
        ...     "john_doe",
        ...     "john@example.com",
        ...     "John Doe",
        ...     "SecurePass123"
        ... )
        >>> print(msg)
    """
```

##### `get_current_user()`

```python
def get_current_user(self) -> Optional[Dict]:
    """
    Get current authenticated user from session state.

    Returns:
        Optional[Dict]: User data dictionary if authenticated, else None

    User Dictionary Keys:
        - id (str): User UUID
        - username (str): Username
        - email (str): Email address
        - name (str): Full name
        - role (str): User role ('user' or 'admin')
        - created_at (str): ISO format timestamp
        - last_login (str): ISO format timestamp
        - session_id (str): Current session ID

    Example:
        >>> auth = UserManager()
        >>> user = auth.get_current_user()
        >>> if user:
        ...     print(f"Role: {user['role']}")
    """
```

##### `is_authenticated()`

```python
def is_authenticated(self) -> bool:
    """
    Check if a user is currently authenticated.

    Returns:
        bool: True if user is authenticated, False otherwise

    Example:
        >>> auth = UserManager()
        >>> if auth.is_authenticated():
        ...     print("User is logged in")
    """
```

##### `is_admin()`

```python
def is_admin(self) -> bool:
    """
    Check if current user has admin role.

    Returns:
        bool: True if current user is admin, False otherwise

    Example:
        >>> auth = UserManager()
        >>> if auth.is_admin():
        ...     print("Admin access granted")
    """
```

##### `logout_user(session_id)`

```python
def logout_user(self, session_id: str) -> None:
    """
    Logout user by invalidating their session.

    Args:
        session_id (str): Session ID to invalidate

    Example:
        >>> auth = UserManager()
        >>> user = auth.get_current_user()
        >>> auth.logout_user(user['session_id'])
    """
```

##### `get_user_statistics()`

```python
def get_user_statistics(self) -> Dict:
    """
    Get system-wide user statistics (admin only).

    Returns:
        Dict: Statistics dictionary with keys:
            - total_users (int): Total active users
            - active_users (int): Users logged in within 30 days
            - total_products (int): Total products created

    Example:
        >>> auth = UserManager()
        >>> stats = auth.get_user_statistics()
        >>> print(f"Total users: {stats['total_users']}")
    """
```

#### Function: `require_auth(auth_manager)`

```python
def require_auth(auth_manager: UserManager) -> None:
    """
    Decorator function to require authentication.

    Shows login page if user is not authenticated and stops execution.

    Args:
        auth_manager (UserManager): UserManager instance

    Example:
        >>> auth = UserManager()
        >>> require_auth(auth)  # Will show login if not authenticated
    """
```

---

### config.py

Application configuration constants.

#### Model Configuration

```python
# LLM Models
GROQ_MODELS: List[str]
OPENAI_MODELS: List[str]

# Default settings
DEFAULT_GROQ_MODEL: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
DEFAULT_OPENAI_MODEL: str = "gpt-4o-mini-2024-07-18"
DEFAULT_TEMPERATURE: float = 0.4
DEFAULT_PROVIDER: str = "openai"
DEFAULT_MODEL: str = "gpt-4o-mini-2024-07-18"

# HSCode classification
HSCODE_MODEL: str = "openai/gpt-oss-120b"
HSCODE_PROVIDER: str = "groq"
HSCODE_TEMPERATURE: float = 0.1
```

#### Prompt Configuration

```python
PROMPT_DIRECTORY: str = "prompts"
COSMETICS_PROMPT: str = "cosmetics_prompt.md"
FRAGRANCE_PROMPT: str = "fragrance_prompt.md"
SUBTYPE_PROMPT: str = "subtype_prompt.md"
HSCODE_PROMPT: str = "hscode_prompt.md"
```

#### Session State Keys

```python
STATE_PRODUCTS: str = "products"
STATE_EXCEL_HEADER_ROW: str = "excel_header_row"
STATE_LANGSMITH_ENABLED: str = "langsmith_enabled"
STATE_GROQ_API_KEY: str = "groq_api_key"
STATE_OPENAI_API_KEY: str = "openai_api_key"
STATE_DROPBOX_ACCESS_TOKEN: str = "dropbox_access_token"
STATE_DROPBOX_ENABLED: str = "dropbox_enabled"
```

#### Evaluation Configuration

```python
# Evaluation system
EVALUATION_ENABLED: bool = True
USE_OPENEVALS: bool = True
OPENEVALS_MODEL: str = "gpt-4o-mini"
OPENEVALS_PROVIDER: str = "openai"
OPENEVALS_TEMPERATURE: float = 0.1

# Metrics
EVALUATION_METRICS: List[str] = [
    "structure_correctness",
    "content_correctness",
    "translation_correctness",
]

# Weights
EVALUATION_WEIGHTS: Dict[str, float] = {
    "structure_correctness": 0.2,
    "content_correctness": 0.5,
    "translation_correctness": 0.3,
}
```

---

## Model Modules

### model_factory.py

Factory for creating LLM instances.

#### `get_llm(provider, model_name, temperature)`

```python
def get_llm(
    provider: str = None,
    model_name: str = None,
    temperature: float = None
) -> BaseLanguageModel:
    """
    Factory function to get the appropriate LLM instance.

    Args:
        provider (str, optional): LLM provider ('openai' or 'groq')
            Defaults to config.DEFAULT_PROVIDER
        model_name (str, optional): Specific model identifier
            Defaults to provider's default model
        temperature (float, optional): Sampling temperature (0.0-2.0)
            Defaults to config.DEFAULT_TEMPERATURE

    Returns:
        BaseLanguageModel: Initialized LLM instance
            - ChatOpenAI for OpenAI provider
            - ChatGroq for Groq provider

    Raises:
        ValueError: If provider is not supported
        ValueError: If API key is missing

    Example:
        >>> # Use default provider and model
        >>> llm = get_llm()

        >>> # Use specific provider and model
        >>> llm = get_llm("openai", "gpt-4o-mini", 0.4)

        >>> # Use Groq with Llama
        >>> llm = get_llm("groq", "llama-3.3-70b-versatile", 0.2)
    """
```

---

### openai_model.py

OpenAI model integration.

#### `get_openai_model(model_name, temperature)`

```python
def get_openai_model(
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.4
) -> ChatOpenAI:
    """
    Initialize an OpenAI ChatGPT model.

    Args:
        model_name (str): OpenAI model identifier
            Examples: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"
        temperature (float): Sampling temperature (0.0-2.0)
            Lower = more deterministic, Higher = more creative

    Returns:
        ChatOpenAI: Initialized OpenAI model instance

    Raises:
        ValueError: If OPENAI_API_KEY not found in environment

    Example:
        >>> model = get_openai_model("gpt-4o-mini", 0.4)
        >>> response = model.invoke("Hello, world!")
    """
```

---

### groq_model.py

Groq model integration.

#### `get_groq_model(model_name, temperature)`

```python
def get_groq_model(
    model_name: str = "llama-3.3-70b-versatile",
    temperature: float = 0.4
) -> ChatGroq:
    """
    Initialize a Groq model.

    Args:
        model_name (str): Groq model identifier
            Examples: "llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"
        temperature (float): Sampling temperature (0.0-2.0)

    Returns:
        ChatGroq: Initialized Groq model instance

    Raises:
        ValueError: If GROQ_API_KEY not found in environment

    Example:
        >>> model = get_groq_model("llama-3.3-70b-versatile", 0.2)
        >>> response = model.invoke("Hello, world!")
    """
```

---

## Processor Modules

### text_processor.py

Main LLM text processing module.

#### `load_prompt_from_file(prompt_file)`

```python
def load_prompt_from_file(prompt_file: str) -> Optional[str]:
    """
    Load prompt template from markdown file.

    Args:
        prompt_file (str): Filename in prompts directory
            Example: "cosmetics_prompt.md"

    Returns:
        Optional[str]: Prompt content as string, or None if error

    Example:
        >>> prompt = load_prompt_from_file("fragrance_prompt.md")
        >>> print(prompt[:100])
    """
```

#### `process_with_llm(text, product_type, llm, run_name)`

```python
def process_with_llm(
    text: str,
    product_type: str,
    llm,
    run_name: str = None
) -> Optional[Union[Dict, List]]:
    """
    Process text with LLM to extract product information.

    Args:
        text (str): Input text to process
        product_type (str): Product type ('cosmetics', 'fragrance', 'subtype')
        llm: Language model instance from get_llm()
        run_name (str, optional): Name for LangSmith run

    Returns:
        Optional[Union[Dict, List]]: Extracted product data
            - Dict for cosmetics and fragrance
            - List for subtype
            - None if error

    Raises:
        None (errors logged to Streamlit)

    Example:
        >>> llm = get_llm("openai", "gpt-4o-mini")
        >>> text = "Product: Anti-Aging Cream, Brand: LuxeDerm..."
        >>> result = process_with_llm(text, "cosmetics", llm)
        >>> print(result["TitleEN"])
    """
```

#### `process_hscode_with_deepseek(product_data, product_type)`

```python
def process_hscode_with_deepseek(
    product_data: Union[Dict, List],
    product_type: str = None
) -> Optional[str]:
    """
    Process product data to determine HSCode using specialized model.

    Args:
        product_data (Union[Dict, List]): Extracted product data
        product_type (str, optional): Product type for context

    Returns:
        Optional[str]: 8-digit HSCode, or None if error

    Example:
        >>> product = {"product_name": "Face Cream", ...}
        >>> hscode = process_hscode_with_deepseek(product, "cosmetics")
        >>> print(hscode)  # "33049900"
    """
```

#### `extract_hscode_fields(product_data, product_type)`

```python
def extract_hscode_fields(
    product_data: Union[Dict, List],
    product_type: str = None
) -> Dict:
    """
    Extract HSCode-relevant fields from product data.

    Args:
        product_data (Union[Dict, List]): Product data in any format
        product_type (str, optional): Product type for context

    Returns:
        Dict: Standardized fields with keys:
            - product_name (str)
            - brand (str)
            - product_type (str)
            - description (str)
            - ingredients (str)
            - how_to_use (str)

    Example:
        >>> data = {"TitleEN": "Face Cream", ...}
        >>> fields = extract_hscode_fields(data, "cosmetics")
        >>> print(fields["product_name"])  # "Face Cream"
    ```
```

---

### pdf_processor.py

PDF file processing module.

#### `process_pdf_file(pdf_file, selected_pages)`

```python
def process_pdf_file(
    pdf_file,
    selected_pages: List[int]
) -> str:
    """
    Extract text from selected PDF pages.

    Args:
        pdf_file: Streamlit UploadedFile object
        selected_pages (List[int]): List of page indices (0-indexed)

    Returns:
        str: Extracted text from all selected pages

    Example:
        >>> pdf = st.file_uploader("Upload PDF")
        >>> text = process_pdf_file(pdf, [0, 1, 2])  # First 3 pages
        >>> print(text[:100])
    """
```

#### `render_pdf_preview(pdf_file)`

```python
def render_pdf_preview(pdf_file) -> List[Tuple[int, bytes]]:
    """
    Generate thumbnail previews for all PDF pages.

    Args:
        pdf_file: Streamlit UploadedFile object

    Returns:
        List[Tuple[int, bytes]]: List of (page_number, image_bytes) tuples

    Example:
        >>> pdf = st.file_uploader("Upload PDF")
        >>> previews = render_pdf_preview(pdf)
        >>> for page_num, img_bytes in previews:
        ...     st.image(img_bytes)
    """
```

---

### excel_processor.py

Excel/CSV file processing module.

#### `process_excel_file(excel_file, header, nrows, selected_rows)`

```python
def process_excel_file(
    excel_file,
    header: int = 0,
    nrows: int = None,
    selected_rows: List[int] = None
) -> Optional[pd.DataFrame]:
    """
    Process Excel or CSV file with configurable options.

    Args:
        excel_file: Streamlit UploadedFile object
        header (int): Row index for column headers (default: 0)
        nrows (int, optional): Number of rows to read (for preview)
        selected_rows (List[int], optional): Specific rows to extract

    Returns:
        Optional[pd.DataFrame]: Processed DataFrame, or None if error

    Supported Formats:
        - .xlsx (Excel 2007+)
        - .xls (Excel 97-2003)
        - .csv (Comma-separated values)

    Example:
        >>> excel = st.file_uploader("Upload Excel")
        >>> # Preview first 10 rows
        >>> preview_df = process_excel_file(excel, header=0, nrows=10)
        >>> # Extract specific rows
        >>> data_df = process_excel_file(excel, header=0, selected_rows=[1,2,3])
    """
```

---

### web_processor.py

Website scraping module.

#### `process_website_urls(urls)`

```python
def process_website_urls(urls: str) -> str:
    """
    Extract content from one or more website URLs.

    Args:
        urls (str): Comma-separated list of URLs
            Example: "https://example.com/product1,https://shop.com/item2"

    Returns:
        str: Concatenated text content from all URLs

    Features:
        - Handles multiple URLs
        - Extracts main content
        - Removes navigation/footer
        - Handles redirects

    Example:
        >>> urls = "https://example.com/product1,https://shop.com/item2"
        >>> text = process_website_urls(urls)
        >>> print(text[:100])
    """
```

---

## Evaluation Modules

### evaluation_core.py

Core evaluation engine.

#### `evaluate_product(product_data, input_text, product_type)`

```python
def evaluate_product(
    product_data: Dict,
    input_text: str,
    product_type: str
) -> Dict[str, float]:
    """
    Evaluate extracted product data quality.

    Args:
        product_data (Dict): Extracted product data
        input_text (str): Original input text
        product_type (str): Product type

    Returns:
        Dict[str, float]: Scores dictionary with keys:
            - structure_score (float): 0.0-100.0
            - content_score (float): 0.0-100.0
            - translation_score (float): 0.0-100.0
            - overall_score (float): 0.0-100.0

    Example:
        >>> scores = evaluate_product(product_data, input_text, "cosmetics")
        >>> print(f"Overall: {scores['overall_score']:.1f}%")
    """
```

---

### metric_evaluator.py

Individual metric evaluators.

#### `evaluate_structure_correctness(product_data, schema)`

```python
def evaluate_structure_correctness(
    product_data: Union[Dict, List],
    schema: Dict
) -> float:
    """
    Evaluate JSON structure correctness.

    Checks:
        - Required fields present
        - Correct data types
        - Array vs object format
        - Nested structure validity

    Args:
        product_data (Union[Dict, List]): Product data
        schema (Dict): Expected JSON schema

    Returns:
        float: Score from 0.0 to 100.0

    Example:
        >>> schema = {"required": ["product_name", "brand"]}
        >>> score = evaluate_structure_correctness(product_data, schema)
        >>> print(f"Structure: {score}%")
    """
```

#### `evaluate_content_correctness(product_data, input_text)`

```python
def evaluate_content_correctness(
    product_data: Union[Dict, List],
    input_text: str
) -> float:
    """
    Evaluate content accuracy vs. input.

    Checks:
        - Data matches input
        - No hallucinations
        - Factual consistency
        - Complete extraction

    Args:
        product_data (Union[Dict, List]): Product data
        input_text (str): Original input text

    Returns:
        float: Score from 0.0 to 100.0

    Example:
        >>> score = evaluate_content_correctness(product_data, input_text)
        >>> print(f"Content: {score}%")
    """
```

#### `evaluate_translation_correctness(product_data)`

```python
def evaluate_translation_correctness(
    product_data: Union[Dict, List]
) -> float:
    """
    Evaluate Portuguese translation quality.

    Checks:
        - Translation presence
        - Linguistic accuracy
        - Terminology consistency
        - Grammar and spelling

    Args:
        product_data (Union[Dict, List]): Product data with translations

    Returns:
        float: Score from 0.0 to 100.0

    Example:
        >>> score = evaluate_translation_correctness(product_data)
        >>> print(f"Translation: {score}%")
    """
```

---

## Utility Modules

### product_config.py

Product configuration classes.

#### Class: `ProductConfig`

Configuration for a single product extraction.

##### `__init__(...)`

```python
def __init__(
    self,
    product_type: str = "cosmetics",
    base_product: str = "",
    prompt_file: str = None,
    pdf_file = None,
    pdf_pages: List[int] = None,
    excel_file = None,
    excel_rows: List[int] = None,
    excel_header_row: int = 0,
    website_url: str = None,
    model_provider: str = "groq",
    model_name: str = None,
    temperature: float = 0.2,
    custom_instructions: str = "",
    user_context: Dict = None,
) -> None:
    """
    Initialize product configuration.

    Args:
        product_type (str): Product type ('cosmetics', 'fragrance', 'subtype')
        base_product (str): Base product for subtype (e.g., 'lipbalm')
        prompt_file (str): Custom prompt file path
        pdf_file: Streamlit UploadedFile for PDF
        pdf_pages (List[int]): List of page indices to process
        excel_file: Streamlit UploadedFile for Excel/CSV
        excel_rows (List[int]): List of row indices to process
        excel_header_row (int): Row index for column headers
        website_url (str): Website URL(s) to scrape
        model_provider (str): LLM provider ('openai', 'groq')
        model_name (str): Specific model name
        temperature (float): Sampling temperature
        custom_instructions (str): Additional instructions for LLM
        user_context (Dict): User attribution data

    Example:
        >>> config = ProductConfig(
        ...     product_type="fragrance",
        ...     pdf_file=pdf,
        ...     pdf_pages=[0, 1, 2],
        ...     model_provider="openai",
        ...     temperature=0.4
        ... )
    """
```

##### `add_processing_attempt(...)`

```python
def add_processing_attempt(
    self,
    model_provider: str,
    model_name: str,
    temperature: float,
    custom_instructions: str,
    result: Dict = None,
    status: str = "pending",
    processing_time: float = None,
    error_message: str = None,
    user_context: Dict = None,
) -> ProcessingAttempt:
    """
    Add a processing attempt to history.

    Args:
        model_provider (str): LLM provider used
        model_name (str): Model name used
        temperature (float): Temperature used
        custom_instructions (str): Instructions used
        result (Dict): Extraction result
        status (str): 'pending', 'processing', 'completed', 'failed'
        processing_time (float): Time taken in seconds
        error_message (str): Error message if failed
        user_context (Dict): User who processed

    Returns:
        ProcessingAttempt: Created attempt object

    Example:
        >>> attempt = config.add_processing_attempt(
        ...     "openai",
        ...     "gpt-4o-mini",
        ...     0.4,
        ...     "",
        ...     result=product_data,
        ...     status="completed",
        ...     processing_time=15.2
        ... )
    """
```

##### `has_data_source()`

```python
def has_data_source(self) -> bool:
    """
    Check if configuration has at least one data source.

    Returns:
        bool: True if has PDF, Excel, or Website source

    Example:
        >>> if config.has_data_source():
        ...     print("Ready to process")
    """
```

##### `source_summary()`

```python
def source_summary(self) -> str:
    """
    Get human-readable summary of data sources.

    Returns:
        str: Summary string

    Example:
        >>> print(config.source_summary())
        "PDF: product.pdf (Pages: 1, 2, 3) | Excel: data.xlsx (Rows: 0, 1, 2)"
    """
```

#### Functions

##### `get_product_configs()`

```python
def get_product_configs() -> List[ProductConfig]:
    """
    Get all product configurations from session state.

    Returns:
        List[ProductConfig]: List of configurations

    Example:
        >>> configs = get_product_configs()
        >>> print(f"Total configs: {len(configs)}")
    """
```

##### `add_product_config(config)`

```python
def add_product_config(config: ProductConfig) -> None:
    """
    Add product configuration to session state.

    Args:
        config (ProductConfig): Configuration to add

    Example:
        >>> config = ProductConfig(...)
        >>> add_product_config(config)
    """
```

##### `remove_product_config(config_id)`

```python
def remove_product_config(config_id: str) -> None:
    """
    Remove product configuration by ID.

    Args:
        config_id (str): UUID of configuration to remove

    Example:
        >>> remove_product_config("abc-123-def-456")
    """
```

---

### state_manager.py

Session state management.

#### `initialize_state()`

```python
def initialize_state() -> None:
    """
    Initialize Streamlit session state with default values.

    Creates:
        - product_configs list
        - langsmith_enabled flag
        - form counters
        - session tracking

    Example:
        >>> initialize_state()
    """
```

#### `reset_application()`

```python
def reset_application() -> None:
    """
    Reset application state to defaults.

    Clears:
        - Product configurations
        - Results
        - Cache
        - Form data

    Example:
        >>> if st.button("Reset"):
        ...     reset_application()
        ...     st.rerun()
    """
```

---

### dropbox_utils.py

Dropbox cloud storage integration.

#### `upload_to_dropbox(local_file_path, dropbox_path)`

```python
def upload_to_dropbox(
    local_file_path: str,
    dropbox_path: str = None
) -> bool:
    """
    Upload file to Dropbox.

    Args:
        local_file_path (str): Path to local file
        dropbox_path (str, optional): Destination path in Dropbox
            Defaults to /Product_AI_Content_Creator/filename

    Returns:
        bool: True if upload successful, False otherwise

    Example:
        >>> success = upload_to_dropbox(
        ...     "results/batch_20250110.csv",
        ...     "/Product_AI_Content_Creator/batch_20250110.csv"
        ... )
        >>> if success:
        ...     print("Uploaded to Dropbox")
    """
```

#### `get_dropbox_client()`

```python
def get_dropbox_client() -> Optional[dropbox.Dropbox]:
    """
    Get authenticated Dropbox client.

    Returns:
        Optional[dropbox.Dropbox]: Dropbox client or None if error

    Example:
        >>> dbx = get_dropbox_client()
        >>> if dbx:
        ...     files = dbx.files_list_folder("/")
    """
```

#### `test_dropbox_connection()`

```python
def test_dropbox_connection() -> bool:
    """
    Test Dropbox connection and credentials.

    Returns:
        bool: True if connection successful, False otherwise

    Example:
        >>> if test_dropbox_connection():
        ...     print("Dropbox connected")
        >>> else:
        ...     print("Dropbox connection failed")
    """
```

---

## Data Types

### Type Definitions

```python
from typing import Dict, List, Optional, Tuple, Union

# Product data can be dict or list depending on type
ProductData = Union[Dict, List[Dict]]

# User data structure
UserData = Dict[str, Union[str, int, bool]]

# Evaluation scores
EvaluationScores = Dict[str, float]  # Keys: structure, content, translation, overall

# Processing status
ProcessingStatus = Literal["pending", "processing", "completed", "failed"]
```

---

## Error Handling

### Common Exceptions

#### `ValueError`
- Invalid product type
- Missing required configuration
- Invalid API key format

#### `FileNotFoundError`
- Prompt file not found
- Database file not found

#### `ConnectionError`
- Database connection failed
- API connection timeout

#### `JSONDecodeError`
- LLM returned invalid JSON
- Corrupted response data

### Example Error Handling

```python
try:
    result = process_with_llm(text, product_type, llm)
    if result is None:
        st.error("Processing failed")
except ValueError as e:
    st.error(f"Invalid configuration: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
    logger.exception("Processing error")
```

---

## Environment Variables

Required environment variables:

```bash
# Required
OPENAI_API_KEY=sk-...          # OpenAI API key

# Optional
GROQ_API_KEY=gsk_...           # Groq API key
LANGSMITH_API_KEY=lsv2_...     # LangSmith API key
LANGSMITH_TRACING=true         # Enable tracing
LANGSMITH_PROJECT=project_name # Project name
DROPBOX_ACCESS_TOKEN=sl...     # Dropbox token
MASTER_PASSWORD=SecurePass123  # Default admin password
```

---

## Constants

### HTTP Status Codes

```python
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500
```

### Session Expiration

```python
SESSION_DURATION_DAYS = 7
SESSION_CLEANUP_HOURS = 24
```

---

## Version History

- **v3.0.0** (2025-10) - User authentication, RBAC, analytics
- **v2.0.0** (2024-09) - Evaluation system, Dropbox integration
- **v1.0.0** (2024-08) - Initial release

---

**Last Updated:** 2025-10-10
**API Version:** 3.0.0
**Python Version:** 3.8+
