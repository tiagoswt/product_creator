# Quick Testing Guide - Website URL Batch Mode

## ✅ Pre-Test Verification

All components verified:
- ✅ `config.py` syntax: OK
- ✅ `configuration_form.py` syntax: OK
- ✅ `batch_processor.py` syntax: OK
- ✅ Streamlit app running at http://localhost:8501

## 🧪 Quick Test (5 minutes)

### Step 1: Access the Feature
1. Open browser: `http://localhost:8501`
2. Login with your credentials
3. Click "Configure Products" tab
4. Scroll down to **"🌐 Website Source"** section

### Step 2: Verify UI Changes
You should see:
```
🌐 Website Source
☐ Batch Mode: Each URL = 1 product
```

### Step 3: Test Normal Mode (Baseline)
**Keep checkbox UNCHECKED**
```
Website URLs: [text input field]
Placeholder: https://example.com/product-page, https://shop.example.com/item...
```
- This is the existing behavior (comma-separated)
- Confirms we didn't break normal mode

### Step 4: Enable Batch Mode
**CHECK the checkbox**

**Expected changes:**
- Text input changes to **text area**
- Placeholder changes to show one URL per line
- Height increases (150px)

### Step 5: Paste Test URLs
Copy and paste these 3 URLs into the text area:
```
https://example.com
https://httpbin.org/html
https://www.python.org
```

**Expected feedback:**
```
✨ Batch Mode Active: Creating 3 product configurations

Preview (first 3 URLs):
  1. https://example.com
  2. https://httpbin.org/html
  3. https://www.python.org
```

### Step 6: Select Product Type
- Product Type: **cosmetics** (or any other)
- Leave other fields as default

### Step 7: Submit
Click **"Add Product Configuration"** button

**Expected:**
```
✅ Successfully created 3 product configuration(s) from website URLs!

Batch Processing Summary:
- Total URLs: 3
- Configurations created: 3
- Product type: cosmetics
- Model: gpt-4o-mini-2024-07-18
- Temperature: 0.4

Next Step: Go to the "Execute Batch" tab to process these configurations.
```

### Step 8: Verify Configurations Created
1. Navigate to **"Execute Batch"** tab
2. You should see **3 separate product configurations**
3. Each should show:
   - Status: "pending"
   - Source: Website URL (different URL for each)
   - Product Type: cosmetics

### Step 9: Test Rate Limiting (Optional)
1. Click **"Start Batch Extraction"** button
2. Watch the progress messages
3. **Expected:** Between URLs 2 and 3, you should see:
   ```
   ⏳ Rate limiting delay (2.0s) before scraping website (2/3)
   ```
4. Notice 2-second pause between website scrapes

## 🔥 Advanced Tests

### Test Invalid URLs
Paste this mix:
```
https://example.com
not-a-valid-url
https://google.com
just some text
```

**Expected:**
```
⚠️ 2 invalid URLs will be skipped
▼ Show invalid URLs
  ❌ not-a-valid-url
  ❌ just some text
```

### Test Maximum Limit
Try pasting 101 URLs (repeat same URL 101 times)

**Expected:**
```
❌ Maximum 100 URLs per batch. You have 101 URLs. Please reduce the number.
```

### Test Auto-Protocol Addition
Paste URLs without `https://`:
```
example.com
google.com
python.org
```

**Expected:** All URLs get `https://` added automatically

### Test Batch Mode Exclusivity
1. Enable Batch Mode
2. Also upload a PDF file and select pages
3. Try to submit

**Expected:**
```
❌ Website batch mode does not support PDF sources. Please remove PDF or disable batch mode.
```

## 📊 Success Criteria

| Feature | Status |
|---------|--------|
| Batch mode checkbox appears | ☐ |
| Text area replaces text input | ☐ |
| URL validation shows real-time | ☐ |
| Preview shows first 3 URLs | ☐ |
| Creates N configs for N URLs | ☐ |
| Rate limiting works (2s delay) | ☐ |
| Invalid URLs skipped | ☐ |
| Maximum limit enforced (100) | ☐ |
| Auto-adds https:// | ☐ |
| No conflicts with PDF/Excel | ☐ |

## 🐛 If Something Goes Wrong

### Issue: Checkbox doesn't appear
**Solution:**
1. Refresh browser (Ctrl+F5)
2. If still missing, restart Streamlit:
   ```bash
   # Stop current app (Ctrl+C in terminal)
   streamlit run app.py
   ```

### Issue: No preview shown
**Check:** Are you pasting valid URLs?
**Try:** Use the sample URLs from Step 5

### Issue: Error when submitting
**Check:**
- Are you in batch mode?
- Do you have valid URLs?
- Did you select a product type?

### Issue: Configs not created
**Check:** Browser console (F12) for errors
**Look for:** Red error messages in Streamlit

### Issue: Rate limiting not visible
**Note:** Rate limiting only shows when processing 2+ consecutive website URLs
**Try:** Create at least 2 website batch configs

## 📝 Test Results Template

Copy this to track your testing:

```
WEBSITE URL BATCH MODE - Test Results
Date: ___________
Tester: ___________

□ UI Elements Present
  □ Batch mode checkbox visible
  □ Text area appears when enabled
  □ Preview shows URL count

□ Functionality
  □ Normal mode still works (comma-separated)
  □ Batch mode creates multiple configs
  □ URL validation works correctly
  □ Invalid URLs handled gracefully

□ Edge Cases
  □ URLs without protocol auto-corrected
  □ Empty lines filtered
  □ Maximum limit enforced (100)
  □ Conflicts with PDF/Excel prevented

□ Rate Limiting
  □ 2s delay between website scrapes
  □ Status message shows during delay

Issues Found:
_______________________________________________
_______________________________________________

Overall Status: PASS / FAIL
```

## 🎉 After Successful Testing

Once all tests pass, the feature is ready for production use!

You can:
1. Use it to batch-process competitor product pages
2. Scrape multiple product URLs from same brand
3. Extract data from product listing pages
4. Combine with Excel mode for hybrid workflows

Enjoy your new Website URL Batch Mode! 🚀
