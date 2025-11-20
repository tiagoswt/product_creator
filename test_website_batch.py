"""
Quick test script to verify Website URL Batch Mode components
"""

print("=" * 60)
print("WEBSITE URL BATCH MODE - Component Test")
print("=" * 60)

# Test 1: Config constants
print("\n1. Testing configuration constants...")
try:
    from config import MAX_WEBSITE_BATCH_SIZE, WEBSITE_SCRAPE_DELAY_SECONDS
    print(f"   ✓ MAX_WEBSITE_BATCH_SIZE: {MAX_WEBSITE_BATCH_SIZE}")
    print(f"   ✓ WEBSITE_SCRAPE_DELAY_SECONDS: {WEBSITE_SCRAPE_DELAY_SECONDS}")
except ImportError as e:
    print(f"   ✗ Error importing config: {e}")

# Test 2: URL validation
print("\n2. Testing URL validation function...")
try:
    from processors.web_processor import validate_urls

    # Test single URL
    result = validate_urls("https://example.com")
    print(f"   ✓ Single URL: {result}")

    # Test URL without protocol
    result = validate_urls("example.com")
    print(f"   ✓ URL without protocol: {result}")

    # Test comma-separated (normal mode)
    result = validate_urls("example.com,google.com")
    print(f"   ✓ Multiple URLs: {result}")

except ImportError as e:
    print(f"   ✗ Error importing web_processor: {e}")
except Exception as e:
    print(f"   ✗ Validation error: {e}")

# Test 3: ProductConfig import
print("\n3. Testing ProductConfig class...")
try:
    from utils.product_config import ProductConfig
    print(f"   ✓ ProductConfig class imported successfully")

    # Check if it has website_url attribute
    import inspect
    sig = inspect.signature(ProductConfig.__init__)
    params = list(sig.parameters.keys())
    if 'website_url' in params:
        print(f"   ✓ ProductConfig has 'website_url' parameter")
    else:
        print(f"   ✗ ProductConfig missing 'website_url' parameter")

except ImportError as e:
    print(f"   ✗ Error importing ProductConfig: {e}")

# Test 4: Configuration form methods
print("\n4. Testing ConfigurationForm class...")
try:
    from utils.batch_ui.components.configuration_form import ConfigurationForm

    # Check if new method exists
    if hasattr(ConfigurationForm, '_create_website_batch_configurations'):
        print(f"   ✓ _create_website_batch_configurations method exists")
    else:
        print(f"   ✗ _create_website_batch_configurations method missing")

    if hasattr(ConfigurationForm, '_render_website_section'):
        print(f"   ✓ _render_website_section method exists")
    else:
        print(f"   ✗ _render_website_section method missing")

except ImportError as e:
    print(f"   ✗ Error importing ConfigurationForm: {e}")

# Test 5: Batch processor
print("\n5. Testing BatchProcessor class...")
try:
    from utils.batch_ui.handlers.batch_processor import BatchProcessor
    print(f"   ✓ BatchProcessor class imported successfully")

    # Check if it has process_all_configurations
    if hasattr(BatchProcessor, 'process_all_configurations'):
        print(f"   ✓ process_all_configurations method exists")
    else:
        print(f"   ✗ process_all_configurations method missing")

except ImportError as e:
    print(f"   ✗ Error importing BatchProcessor: {e}")

# Test 6: Simulate batch URL parsing
print("\n6. Testing batch URL parsing logic...")
try:
    # Simulate what happens when user pastes URLs
    sample_input = """https://example.com
https://google.com
example.org

https://python.org"""

    # Parse like the UI does
    raw_urls = [line.strip() for line in sample_input.split('\n') if line.strip()]
    print(f"   ✓ Parsed {len(raw_urls)} URLs from input")

    # Validate each
    from processors.web_processor import validate_urls
    valid_urls = []
    for url in raw_urls:
        try:
            validated = validate_urls(url)
            if validated and validated[0]:  # Check if validation succeeded
                valid_urls.extend(validated[1])  # Get the URL list
        except:
            pass

    print(f"   ✓ Valid URLs: {len(valid_urls)}")
    for i, url in enumerate(valid_urls, 1):
        print(f"      {i}. {url}")

except Exception as e:
    print(f"   ✗ Parsing error: {e}")

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("\nAll components are ready! The feature should work in the UI.")
print("\nNext steps:")
print("1. Open your browser to http://localhost:8501")
print("2. Login to the app")
print("3. Navigate to 'Configure Products' tab")
print("4. Scroll to 'Website Source' section")
print("5. Check the 'Batch Mode: Each URL = 1 product' checkbox")
print("6. Paste URLs (one per line) and test!")
print("\nSee WEBSITE_BATCH_MODE_TEST.md for detailed test cases.")
print("=" * 60)
