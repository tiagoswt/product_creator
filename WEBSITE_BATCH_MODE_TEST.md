# Website URL Batch Mode - Testing Guide

## Feature Overview
Website URL Batch Mode allows users to paste multiple URLs (one per line) and create separate product configurations for each URL. This complements the existing Excel batch mode.

## What Was Implemented

### 1. Configuration Constants (`config.py`)
- `MAX_WEBSITE_BATCH_SIZE = 100` - Maximum URLs per batch
- `WEBSITE_SCRAPE_DELAY_SECONDS = 2.0` - Delay between consecutive website scrapes

### 2. UI Changes (`configuration_form.py`)
- Added batch mode toggle in Website URLs section
- Two modes:
  - **Normal Mode**: Comma-separated URLs (existing behavior)
  - **Batch Mode**: One URL per line in text area
- Real-time URL validation and preview
- Shows first 3 URLs + count
- Displays invalid URLs with warnings

### 3. Backend Changes
- `_create_website_batch_configurations()` - Creates one ProductConfig per URL
- `_handle_form_submission()` - Routes batch mode requests
- `batch_processor.py` - Rate limiting between consecutive website scrapes

## Testing Checklist

### Test 1: Basic Batch Mode UI
1. Start the app: `streamlit run app.py`
2. Login with your credentials
3. Navigate to "Configure Products" tab
4. Scroll to "Website Source" section
5. **Verify**: You should see a checkbox "Batch Mode: Each URL = 1 product"

### Test 2: Normal Mode (Existing Behavior)
1. Keep "Batch Mode" checkbox **unchecked**
2. Enter comma-separated URLs in text input:
   ```
   https://example.com, https://google.com
   ```
3. Click "Add Product Configuration"
4. **Expected**: Creates 1 config with both URLs (existing behavior preserved)

### Test 3: Batch Mode with Valid URLs
1. Check "Batch Mode: Each URL = 1 product"
2. **Verify**: Text input changes to text area
3. Paste these URLs (one per line):
   ```
   https://example.com
   https://google.com
   https://python.org
   ```
4. **Expected**:
   - Shows: "✨ Batch Mode Active: Creating 3 product configurations"
   - Shows preview of first 3 URLs
   - Click "Add Product Configuration"
   - Creates 3 separate ProductConfigs

### Test 4: Maximum Limit (100 URLs)
1. Enable Batch Mode
2. Paste 101 URLs in text area
3. **Expected**: Error message "❌ Maximum 100 URLs per batch"

### Test 5: Invalid URLs Handling
1. Enable Batch Mode
2. Paste mixed valid/invalid URLs:
   ```
   https://example.com
   invalid-url
   https://google.com
   not a url at all
   ```
3. **Expected**:
   - Shows "⚠️ 2 invalid URLs will be skipped"
   - Expandable section shows which URLs are invalid
   - Creates configs only for valid URLs

### Test 6: Empty Lines Handling
1. Enable Batch Mode
2. Paste URLs with empty lines:
   ```
   https://example.com

   https://google.com

   ```
3. **Expected**: Empty lines automatically filtered, creates 2 configs

### Test 7: URLs Without Protocol
1. Enable Batch Mode
2. Paste URLs without https://
   ```
   example.com
   google.com
   ```
3. **Expected**: Auto-adds https:// prefix, creates valid configs

### Test 8: Batch Mode Exclusivity (No PDF/Excel)
1. Enable Batch Mode
2. Upload a PDF file AND select pages
3. Paste URLs in batch text area
4. Click "Add Product Configuration"
5. **Expected**: Error "❌ Website batch mode does not support PDF sources"

### Test 9: Rate Limiting During Execution
1. Create 5 website batch configs
2. Go to "Execute Batch" tab
3. Click "Start Batch Extraction"
4. **Expected**:
   - First URL processes immediately
   - Between URLs 2-5, shows: "⏳ Rate limiting delay (2.0s) before scraping website"
   - 2-second delay between consecutive website scrapes

### Test 10: Mixed Batch (Excel + Website Batch in Same Session)
1. Create Excel batch configs (e.g., 10 rows)
2. Then create Website batch configs (e.g., 5 URLs)
3. **Expected**: Both sets coexist, total 15 configs ready to process

### Test 11: Subtype Product Type
1. Enable Batch Mode
2. Select product_type = "subtype"
3. Enter base product (e.g., "Face Cream")
4. Paste URLs
5. **Expected**: Creates configs with base_product field populated

## Sample Test URLs

Safe URLs for testing (won't hit rate limits):
```
https://example.com
https://example.org
https://example.net
https://httpbin.org/html
https://www.python.org
```

## Expected Session State Keys

When batch mode is active, these session keys should exist:
- `website_batch_mode_{form_counter}` - Boolean
- `website_urls_batch_{form_counter}` - String (text area content)
- `batch_website_count_{form_counter}` - Integer (valid URL count)
- `batch_website_urls_{form_counter}` - List of validated URLs

## Error Scenarios to Test

1. **No URLs entered**: Should show error when submitting
2. **All invalid URLs**: Should show error "No valid URLs to process"
3. **Over 100 URLs**: Should show error before submission
4. **Batch mode + PDF selected**: Should show conflict error
5. **Batch mode + Excel selected**: Should show conflict error

## Success Indicators

✅ Batch mode toggle works
✅ Text area appears in batch mode
✅ URL validation shows real-time feedback
✅ Creates N configs for N URLs
✅ Rate limiting works (2s delay)
✅ No conflicts with Excel batch mode
✅ Invalid URLs skipped gracefully
✅ Maximum limit enforced
✅ Auto-adds https:// to URLs without protocol

## Debugging

If issues occur, check:
1. Browser console for JavaScript errors
2. Streamlit terminal for Python exceptions
3. Session state values: `st.session_state` in Streamlit
4. ProductConfig objects: Check if website_url is single URL (not comma-separated)

## File Locations

Modified files:
- `config.py` (lines 107-109)
- `utils/batch_ui/components/configuration_form.py` (lines 679-776, 792-828, 1333-1422)
- `utils/batch_ui/handlers/batch_processor.py` (lines 86-118)

## Next Steps After Testing

If all tests pass:
1. Update CLAUDE.md with Website Batch Mode documentation
2. Add user-facing documentation/tooltips if needed
3. Consider adding batch mode to other input methods (if requested)
4. Monitor rate limiting effectiveness with real websites

## Known Limitations

1. All URLs in a batch use same product_type/model/temperature
2. For per-URL customization, use Excel hybrid mode instead
3. Rate limiting is basic (fixed 2s delay, no exponential backoff)
4. No retry logic for failed scrapes (use Reprocess tab)
5. Sequential processing only (no parallel scraping)

## Troubleshooting

**Issue**: Batch mode checkbox doesn't appear
- **Fix**: Restart Streamlit app, clear browser cache

**Issue**: Rate limiting not working
- **Fix**: Check config.WEBSITE_SCRAPE_DELAY_SECONDS is imported

**Issue**: URLs not validated
- **Fix**: Check processors.web_processor.validate_urls() function

**Issue**: Configs not created
- **Fix**: Check session state keys exist, check browser console
