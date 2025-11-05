# Implementation Plan: Adding New Product Type Prompts

## Overview
This document outlines the changes needed to seamlessly add new product type prompts (e.g., `supplement_prompt.md`, `coffret_prompt.md`, etc.) to the AI Product Creator system.

## Current System Architecture

### Existing Product Types
Currently, the system supports 3 product types:
1. **cosmetics** - Uses `cosmetics_prompt.md`
2. **fragrance** - Uses `fragrance_prompt.md`
3. **subtype** - Uses `subtype_prompt.md`

### How It Works
The system uses a configuration-driven approach where:
- Product types are defined in `config.py`
- Prompt file paths are mapped to product types
- The UI presents product types as options in a dropdown
- Processing logic routes to the appropriate prompt based on product type

---

## Changes Required to Add New Prompts

### 1. **Create the New Prompt File**
**Location:** `prompts/`

**Action:**
- Create new `.md` file (e.g., `supplement_prompt.md`, `coffret_prompt.md`)
- Follow the same structure as existing prompts (see `fragrance_prompt.md` as reference)
- Define the expected JSON output schema
- Include extraction instructions and field definitions

**File:** `prompts/supplement_prompt.md` (example)
```markdown
You are a product data extraction specialist for supplements...

Extract the following details in JSON format:
{
  "product_name": "",
  "brand": "",
  "price": null,
  ...
}
```

---

### 2. **Update Configuration File**
**File:** `config.py`

**Changes Required:**

#### Add Prompt Constants (Lines 42-45)
```python
# Current prompts
COSMETICS_PROMPT = "cosmetics_prompt.md"
FRAGRANCE_PROMPT = "fragrance_prompt.md"
SUBTYPE_PROMPT = "subtype_prompt.md"
HSCODE_PROMPT = "hscode_prompt.md"

# ADD NEW PROMPTS:
SUPPLEMENT_PROMPT = "supplement_prompt.md"
COFFRET_PROMPT = "coffret_prompt.md"
# Add more as needed...
```

**Impact:** Low - Simple constant additions

---

### 3. **Update UI Configuration Form**
**File:** `utils/batch_ui/components/configuration_form.py`

**Changes Required:**

#### Update Product Type Dropdown (Line 48-53)
```python
# CURRENT:
product_type = st.selectbox(
    "Product Type",
    ["cosmetics", "fragrance", "subtype"],  # ← UPDATE THIS LIST
    help="Choose the type of product to extract",
    key="product_type_selector",
)

# UPDATED:
product_type = st.selectbox(
    "Product Type",
    ["cosmetics", "fragrance", "subtype", "supplement", "coffret"],  # ← Add new types
    help="Choose the type of product to extract",
    key="product_type_selector",
)
```

**Impact:** Low - Single line change to add new options

---

### 4. **Update Text Processor Logic**
**File:** `processors/text_processor.py`

**Changes Required:**

#### Update `process_with_llm()` Function (Lines 421-429)
```python
# CURRENT:
if product_type == "cosmetics":
    prompt_content = load_prompt_from_file(config.COSMETICS_PROMPT)
elif product_type == "fragrance":
    prompt_content = load_prompt_from_file(config.FRAGRANCE_PROMPT)
elif product_type == "subtype":
    prompt_content = load_prompt_from_file(config.SUBTYPE_PROMPT)
else:
    st.error(f"Unknown product type: {product_type}")
    return None

# UPDATED:
if product_type == "cosmetics":
    prompt_content = load_prompt_from_file(config.COSMETICS_PROMPT)
elif product_type == "fragrance":
    prompt_content = load_prompt_from_file(config.FRAGRANCE_PROMPT)
elif product_type == "subtype":
    prompt_content = load_prompt_from_file(config.SUBTYPE_PROMPT)
elif product_type == "supplement":
    prompt_content = load_prompt_from_file(config.SUPPLEMENT_PROMPT)
elif product_type == "coffret":
    prompt_content = load_prompt_from_file(config.COFFRET_PROMPT)
# Add more elif blocks for additional prompts
else:
    st.error(f"Unknown product type: {product_type}")
    return None
```

**Impact:** Low - Add elif branches for each new type

---

### 5. **Update HSCode Processing Logic (Optional)**
**File:** `processors/text_processor.py`

**Changes Required (if new product types have unique structures):**

#### Update `detect_response_format()` Function (Lines 11-36)
If new product types return different JSON structures (e.g., array vs object), update detection logic:

```python
def detect_response_format(response_json):
    """Detect the format of the LLM response"""
    if isinstance(response_json, list):
        return "subtype"  # or "supplement" if supplements also return arrays
    elif isinstance(response_json, dict):
        if "Subtypes" in response_json:
            return "cosmetics"
        elif "supplements" in response_json:  # NEW: for supplement bundles
            return "supplement"
        elif "items" in response_json:  # NEW: for coffret sets
            return "coffret"
        # ... existing logic
```

#### Update `place_hscode_in_correct_location()` Function (Lines 107-161)
Add cases for new product types:

```python
elif product_type == "supplement":
    # Define where HSCode should be placed in supplement structure
    if isinstance(product_data, dict):
        product_data["hscode"] = hscode

elif product_type == "coffret":
    # Define where HSCode should be placed in coffret structure
    if isinstance(product_data, dict):
        product_data["hscode"] = hscode
```

**Impact:** Medium - Only needed if new types have unique JSON structures

---

### 6. **Update Export Handlers (Optional)**
**File:** `utils/batch_ui/handlers/export_handler.py`

**Changes Required (if new product types need custom export logic):**

If supplements or coffrets have unique fields that need special formatting during CSV/Excel export, add custom handlers.

**Impact:** Low to Medium - Only needed for complex export requirements

---

### 7. **Update Analytics Dashboard (Optional)**
**File:** `evaluations/tabbed_analytics_dashboard.py`

**Changes Required (if you want product-type-specific analytics):**

Add filters and visualization for new product types in the analytics dashboard.

**Impact:** Low - UI enhancement, not critical for functionality

---

## Recommended Implementation Order

### Phase 1: Basic Support (Essential)
1. ✅ Create new prompt file (`supplement_prompt.md`)
2. ✅ Update `config.py` - Add prompt constant
3. ✅ Update `configuration_form.py` - Add to dropdown
4. ✅ Update `text_processor.py` - Add to processing logic

**Result:** New product type will be fully functional

### Phase 2: Structure Handling (If Needed)
5. ⚠️ Update `detect_response_format()` if JSON structure differs
6. ⚠️ Update `place_hscode_in_correct_location()` if HSCode placement differs
7. ⚠️ Update `extract_hscode_fields()` if field names differ

**Result:** HSCode processing works correctly for new type

### Phase 3: Enhancements (Optional)
8. 💡 Update export handlers for custom export logic
9. 💡 Update analytics dashboard for product-type filters
10. 💡 Add validation rules specific to new product types

**Result:** Enhanced user experience and data quality

---

## Step-by-Step Example: Adding "Supplement" Product Type

### Step 1: Create Prompt File
**File:** `prompts/supplement_prompt.md`
```markdown
You are a supplement product data extraction specialist...

Extract the following details in JSON format:
{
  "product_name": "",
  "brand": "",
  "supplement_type": "",
  "ingredients": [],
  "dosage": "",
  "price": null,
  ...
}
```

### Step 2: Update Config
**File:** `config.py` (after line 44)
```python
SUPPLEMENT_PROMPT = "supplement_prompt.md"
```

### Step 3: Update UI Dropdown
**File:** `utils/batch_ui/components/configuration_form.py` (line 50)
```python
["cosmetics", "fragrance", "subtype", "supplement"],
```

### Step 4: Update Processor
**File:** `processors/text_processor.py` (after line 426)
```python
elif product_type == "supplement":
    prompt_content = load_prompt_from_file(config.SUPPLEMENT_PROMPT)
```

### Step 5: Test
1. Run the application: `streamlit run app.py`
2. Select "supplement" from dropdown
3. Upload test data (PDF/Excel/Website)
4. Verify extraction works correctly
5. Check HSCode is processed
6. Validate exported CSV

---

## Testing Checklist

For each new product type, verify:
- [ ] Prompt file loads correctly
- [ ] Product type appears in UI dropdown
- [ ] LLM processes data using correct prompt
- [ ] JSON response parses correctly
- [ ] HSCode is extracted/generated properly
- [ ] Results display in UI correctly
- [ ] Export to CSV/Excel works
- [ ] Dropbox upload succeeds (if enabled)
- [ ] Evaluation metrics calculate correctly
- [ ] Analytics dashboard shows data

---

## Future Improvements: Making It Fully Dynamic

### Option A: Configuration-Based (Recommended)
Create a product type registry in `config.py`:

```python
PRODUCT_TYPES = {
    "cosmetics": {
        "prompt_file": "cosmetics_prompt.md",
        "display_name": "Cosmetics",
        "structure": "flat_with_subtypes",
        "requires_base_product": False,
    },
    "fragrance": {
        "prompt_file": "fragrance_prompt.md",
        "display_name": "Fragrance",
        "structure": "flat",
        "requires_base_product": False,
    },
    "supplement": {
        "prompt_file": "supplement_prompt.md",
        "display_name": "Supplement",
        "structure": "flat",
        "requires_base_product": False,
    },
    # Easy to add more...
}
```

Then update code to read from this registry instead of hardcoded if/elif chains.

### Option B: Auto-Discovery
Automatically discover prompt files in `prompts/` directory:
- Scan for `*_prompt.md` files
- Auto-generate product type names
- Dynamically populate dropdown

**Impact:** High initial effort, but makes adding new types trivial

---

## Summary

### Minimal Changes Required (For Each New Prompt):
1. **1 new file**: Create prompt `.md` file
2. **3 file edits**:
   - `config.py`: Add 1 constant
   - `configuration_form.py`: Add to list (1 line)
   - `text_processor.py`: Add elif block (2 lines)

### Total Effort Per New Product Type:
- **Time:** ~15-30 minutes
- **Complexity:** Low
- **Risk:** Very low (isolated changes)

### Benefits:
✅ Clean separation of concerns
✅ Easy to maintain
✅ Scalable architecture
✅ No breaking changes to existing types
✅ Each product type is independent

---

## Notes & Recommendations

1. **Naming Convention**: Use `<type>_prompt.md` format consistently
2. **JSON Schema**: Document expected JSON structure in each prompt
3. **Testing**: Always test with real data before production use
4. **Version Control**: Keep old prompt versions for rollback
5. **Documentation**: Update prompt files with logs (see `prompts/cosmetics_prompt/cosmetics_prompt_logs.md`)

---

**Last Updated:** 2025-10-10
**Status:** Ready for Implementation
