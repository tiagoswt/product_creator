# 📖 User Guide

**SweetCare AI Product Content Creator**

*Complete step-by-step guide for end users*

---

## Table of Contents

- [Getting Started](#getting-started)
- [User Interface Overview](#user-interface-overview)
- [Authentication](#authentication)
- [Configuring Products](#configuring-products)
- [Executing Batch Processing](#executing-batch-processing)
- [Reviewing Results](#reviewing-results)
- [Exporting Data](#exporting-data)
- [Reprocessing Failed Items](#reprocessing-failed-items)
- [Admin Features](#admin-features)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Getting Started

### System Requirements

Before using the application, ensure you have:
- **Modern web browser** (Chrome, Firefox, Safari, Edge - latest version)
- **Stable internet connection** (for API calls)
- **User account** (provided by administrator)

### First Time Access

1. **Open the application:**
   - Navigate to the application URL provided by your administrator
   - Example: `http://localhost:8501` or `https://your-company.com/product-creator`

2. **Login:**
   - Enter your username
   - Enter your password
   - Click "Login"

3. **Verify access:**
   - You should see the main application interface
   - Check your name and role in the top-right corner

---

## User Interface Overview

### Main Layout

```
┌─────────────────────────────────────────────────────────────┐
│  💚 Logo    Product Content Creator         👤 Your Name    │
│                                              Role: User/Admin │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────┬─────────────────────┐              │
│  │ Configure Products  │ Execute Batch       │              │
│  └─────────────────────┴─────────────────────┘              │
│                                                               │
│  [Main content area - changes based on tab]                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
│ Sidebar (collapsed by default)                               │
│ - Configuration                                               │
│ - LangSmith Status                                            │
│ - Dropbox Integration                                         │
│ - Reset/Clear Options                                         │
└─────────────────────────────────────────────────────────────┘
```

### Navigation

- **Tab 1: Configure Products** - Add new product configurations
- **Tab 2: Execute Batch** - Process configured products
- **Sidebar** - System settings and admin tools (click ">>" to expand)

---

## Authentication

### Logging In

1. **Enter credentials:**
   ```
   Username: [your username]
   Password: [your password]
   ```

2. **Click "Login"**
   - On success: Redirected to main application
   - On failure: Error message displayed

### First-Time Registration

If you don't have an account:

1. Click **"Register"** button on login page
2. Fill in registration form:
   - **Username** (3+ characters, unique)
   - **Email** (valid email format, unique)
   - **Full Name** (2+ characters)
   - **Password** (see requirements below)
   - **Confirm Password** (must match)

3. **Password Requirements:**
   - Minimum 8 characters
   - At least 1 uppercase letter (A-Z)
   - At least 1 lowercase letter (a-z)
   - At least 1 number (0-9)
   - Example: `SecurePass123`

4. Click **"Create Account"**
5. On success, login with your new credentials

### Logging Out

1. Open sidebar (click ">>" icon)
2. Scroll to bottom
3. Click **"Logout"** button
4. You'll be returned to login page

### Session Management

- **Session duration:** 7 days
- **Auto-logout:** After session expires
- **Multi-device:** You can login on multiple devices simultaneously

---

## Configuring Products

### Step-by-Step Product Configuration

#### 1. Select Product Type

Navigate to **"Configure Products"** tab

1. **Product Type Dropdown:**
   - Choose from: `cosmetics`, `fragrance`, `subtype`
   - Each type has specialized extraction logic

2. **Base Product Field (Subtype only):**
   - If you select `subtype`, enter the base product type
   - Examples: `lipbalm`, `serum`, `cream`, `cleanser`
   - This will be used in the filename

---

#### 2. Choose Data Sources

You can select **one or multiple** data sources:

##### A. PDF Source

1. **Upload PDF file:**
   - Click **"Upload PDF"** button
   - Select PDF file from your computer
   - Wait for preview to load

2. **Select pages:**
   - Review page thumbnails
   - Click individual pages to select/deselect
   - Or use quick actions:
     - **"Select All"** - Select all pages
     - **"Clear All"** - Deselect all pages

3. **Verify selection:**
   - Green checkmark (✅) indicates selected pages
   - Summary shows count: "Selected 5 pages: 1, 2, 3, 4, 5"

**Tips for PDF:**
- Preview helps identify relevant pages
- You can select non-consecutive pages (e.g., 1, 3, 7)
- Larger PDFs may take longer to preview

---

##### B. Excel/CSV Source

1. **Upload Excel/CSV file:**
   - Click **"Upload Excel/CSV"** button
   - Select .xlsx, .xls, or .csv file
   - Wait for preview to load

2. **Identify header row:**
   - Review raw data preview (first 20 rows)
   - Select the row containing column headers
   - Example: If headers are in row 0, select "Row 0 - Product Name | Price | Brand"

3. **Apply header row:**
   - Click **"Apply Header Row"** button
   - Data will be processed with correct columns

4. **Select rows to process:**
   - Choose selection method:
     - **"Select All"** - Process all rows
     - **"Row Range"** - Enter start and end row (e.g., 0 to 10)
     - **"Individual Rows"** - Enter comma-separated rows (e.g., 0,2,4,7)

5. **Verify selection:**
   - Summary shows selected row count

**Tips for Excel/CSV:**
- Always verify header row is correct
- Row numbers start from 0 (after header)
- Preview helps identify data quality issues

---

##### C. Website Source

1. **Enter website URL(s):**
   - Type or paste URL in the text field
   - For multiple URLs, separate with commas
   - Example:
     ```
     https://example.com/product1,
     https://shop.example.com/item2,
     https://another-site.com/product3
     ```

2. **Verify URLs:**
   - URL count is displayed: "3 URL(s) to process"
   - Make sure URLs are accessible

**Tips for Websites:**
- Use direct product page URLs
- Avoid login-protected pages
- Test URLs in browser first

---

#### 3. Submit Configuration

1. **Review your configuration:**
   - Product type: `cosmetics`
   - Data sources: `PDF: 5 pages | Excel: 10 rows | Website: 2 URLs`

2. **Click "Add Product Configuration"**

3. **Success confirmation:**
   ```
   ✅ Product configuration added successfully!

   Data Sources: 📄 PDF: 5 pages | 📊 Excel: 10 rows | 🌐 Websites: 2 URLs
   ```

4. **Configuration is now ready for processing**

---

## Executing Batch Processing

### Processing Configured Products

#### 1. Navigate to "Execute Batch" Tab

You'll see a table of all configured products:

| ID | Product Type | Data Sources | Status | Actions |
|----|-------------|--------------|--------|---------|
| 1  | cosmetics   | PDF: 5 pages | Pending | - |
| 2  | fragrance   | Excel: 3 rows | Pending | - |

#### 2. Review Configurations

- **Check product count:** How many products will be processed
- **Verify data sources:** Ensure correct files/pages selected
- **Check status:** All should be "Pending"

#### 3. Start Processing

1. **Click "Start Batch Processing"** button
2. **Processing begins:**
   - Progress bar appears
   - Status updates in real-time
   - Individual product progress shown

#### 4. Monitor Progress

**Progress Indicators:**
```
Processing products... 2 / 5 completed

Product 1: ✅ Completed - Overall Score: 85%
Product 2: ✅ Completed - Overall Score: 92%
Product 3: 🔄 Processing...
Product 4: ⏳ Pending
Product 5: ⏳ Pending
```

**Status Types:**
- ⏳ **Pending** - Waiting to be processed
- 🔄 **Processing** - Currently being extracted
- ✅ **Completed** - Successfully extracted
- ❌ **Failed** - Error occurred

#### 5. Processing Complete

Once all products are processed:
```
✅ Batch processing complete!

Total: 5 products
Successful: 4 products (80%)
Failed: 1 product (20%)

View results in the table below.
```

---

## Reviewing Results

### Understanding the Results Table

After processing, results are displayed in a detailed table:

#### Column Descriptions

| Column | Description | Example |
|--------|-------------|---------|
| **Product ID** | Unique identifier | `prod_abc123` |
| **Product Type** | Type of extraction | `cosmetics` |
| **Product Name** | Extracted product name | `Anti-Aging Cream` |
| **Brand** | Extracted brand | `LuxeDerm` |
| **Price** | Extracted price | `49.99 EUR` |
| **Status** | Processing status | `Completed` / `Failed` |
| **Structure Score** | JSON structure quality | `95%` 🟢 |
| **Content Score** | Content accuracy | `88%` 🟢 |
| **Translation Score** | Translation quality | `82%` 🟢 |
| **Overall Score** | Weighted average | `87%` 🟢 |
| **Actions** | Available actions | `View` `Reprocess` |

#### Quality Score Colors

- 🟢 **Green (80-100%):** Excellent quality
- 🟡 **Yellow (60-79%):** Good quality, minor issues
- 🔴 **Red (< 60%):** Needs review or reprocessing

---

### Viewing Detailed Results

1. **Click "View" button** on any product row
2. **Popup displays:**
   - Complete extracted JSON data
   - All fields with values
   - Formatted for readability

**Example:**
```json
{
  "TitleEN": "Hydrating Anti-Aging Night Cream",
  "TitlePT": "Creme Noturno Hidratante Anti-Envelhecimento",
  "DescriptionEN": "Intensive overnight repair...",
  "brand": "LuxeDerm",
  "Subtypes": [
    {
      "ItemDescriptionEN": "50ml Jar",
      "price": 49.99,
      "HSCode": "33049900"
    }
  ]
}
```

3. **Close popup** when done reviewing

---

### Identifying Issues

#### Low Quality Scores

If a product has low scores:

1. **Check Structure Score:**
   - Low score → Missing required fields or wrong JSON format
   - Review input data quality

2. **Check Content Score:**
   - Low score → Extracted data doesn't match input
   - Possible hallucinations or misinterpretations

3. **Check Translation Score:**
   - Low score → Poor Portuguese translation
   - May need reprocessing

#### Failed Extractions

If status shows **"Failed"**:

1. **Check error message** (if displayed)
2. **Common causes:**
   - Invalid input data format
   - LLM API error (rate limit, timeout)
   - Corrupted file
   - Network issues

3. **Solutions:**
   - Reprocess the item
   - Check input data quality
   - Try different model/temperature
   - Contact administrator if persistent

---

## Exporting Data

### Export to CSV

1. **Click "Export to CSV"** button
2. **File is generated:**
   - Filename: `batch_results_YYYYMMDD_HHMMSS.csv`
   - Example: `batch_results_20250110_143022.csv`

3. **Download file:**
   - Browser automatically downloads
   - Check your Downloads folder

4. **CSV Structure:**
   ```csv
   product_id,product_type,product_name,brand,price,currency,...
   prod_001,cosmetics,Anti-Aging Cream,LuxeDerm,49.99,EUR,...
   prod_002,fragrance,Rose Perfume,ScentLux,89.99,EUR,...
   ```

### Export to Excel

1. **Click "Export to Excel"** button
2. **File is generated:**
   - Filename: `batch_results_YYYYMMDD_HHMMSS.xlsx`
   - Example: `batch_results_20250110_143022.xlsx`

3. **Download file:**
   - Browser automatically downloads
   - Open in Microsoft Excel, Google Sheets, or LibreOffice

4. **Excel Features:**
   - Formatted columns
   - Header row with bold text
   - Multiple sheets (if needed)

### Upload to Dropbox

If Dropbox integration is enabled:

1. **Enable "Upload to Dropbox" checkbox**
2. **Click export button** (CSV or Excel)
3. **File is uploaded to:**
   ```
   /Product_AI_Content_Creator/batch_results_YYYYMMDD_HHMMSS.csv
   ```

4. **Success message:**
   ```
   ✅ File exported and uploaded to Dropbox successfully!
   ```

5. **Access file:**
   - Login to Dropbox
   - Navigate to `/Product_AI_Content_Creator/` folder
   - Download or share file

---

## Reprocessing Failed Items

### When to Reprocess

Reprocess a product if:
- Initial processing failed
- Quality scores are too low
- HSCode is incorrect
- Translation needs improvement

### Reprocessing Steps

#### Full Reprocessing

1. **Locate product** in results table
2. **Click "Reprocess"** button
3. **Reprocessing modal appears:**
   - Current configuration shown
   - Option to adjust settings

4. **Click "Start Reprocessing"**
5. **Monitor progress:**
   - New extraction is performed
   - New quality scores calculated

6. **Review new results:**
   - Compare with previous attempt
   - Check if quality improved

#### HSCode-Only Reprocessing

If only HSCode needs updating:

1. **Click "Reprocess"** button
2. **Select "HSCode Only"** option
3. **Click "Start Reprocessing"**
4. **Only HSCode is re-classified:**
   - Faster than full reprocessing
   - Preserves other extracted data

---

## Admin Features

### User Management (Admin Only)

If you have **Admin** role:

#### Accessing User Management

1. **Open sidebar**
2. **Look for "Admin Panel"** section
3. **Click "Manage Users"** button

#### Viewing Users

**User List displays:**
- Username and full name
- Email address
- Role (User or Admin)
- Status (Active or Inactive)
- Created date
- Last login date
- Products created count

#### Managing Users

**Available Actions:**

1. **Activate/Deactivate User:**
   - Click "Deactivate" to disable user
   - Click "Activate" to re-enable user
   - Deactivated users cannot login

2. **Change User Role:**
   - Click "Make Admin" to promote user
   - Click "Make User" to demote admin
   - Cannot modify main admin account

3. **View User Activity:**
   - See products created
   - See evaluations completed

#### Creating New Users

Users can self-register, or admin can inform them to use registration form.

---

### System Statistics (Admin Only)

**Sidebar Admin Panel shows:**

```
👑 Admin Panel

Total Users: 12
Active Users: 8
Products Created: 145
```

**Metrics:**
- **Total Users:** All registered users (active + inactive)
- **Active Users:** Users logged in within last 30 days
- **Products Created:** Total products extracted

---

## Best Practices

### Optimizing Extraction Quality

#### 1. Prepare Clean Input Data

**PDF Files:**
- Use high-quality scans
- Ensure text is readable (not image-only)
- Avoid handwritten content
- Remove unnecessary pages before upload

**Excel/CSV Files:**
- Clear column headers in first row
- Consistent data format in each column
- No merged cells
- No hidden columns or formulas

**Website URLs:**
- Use direct product page URLs
- Avoid dynamically loaded content
- Ensure pages are publicly accessible
- Test URLs in browser first

---

#### 2. Select Relevant Data

**For PDF:**
- Only select pages with product information
- Avoid cover pages, TOC, or advertisements
- Include pages with technical specifications

**For Excel:**
- Only select rows with complete data
- Skip empty rows or template rows
- Exclude header/footer rows in data range

---

#### 3. Review Before Processing

- **Double-check product type** selection
- **Verify data sources** are correct
- **Preview data** to spot issues early
- **Test with 1-2 products** before bulk processing

---

#### 4. Monitor Quality Scores

- **Aim for ≥ 80% overall score**
- **Reprocess if < 70%**
- **Review manually if 70-79%**
- **Trust if ≥ 80%**

---

#### 5. Handle Failures Promptly

- **Investigate error messages**
- **Check input data quality**
- **Retry with adjusted settings**
- **Contact admin if persistent**

---

## Troubleshooting

### Common Issues and Solutions

#### "Unable to initialize the language model"

**Cause:** API key issue

**Solution:**
1. Contact administrator
2. Verify API keys are configured
3. Check internet connection

---

#### "Error parsing product data"

**Cause:** LLM returned invalid JSON

**Solution:**
1. Click "Reprocess" button
2. Try again (may be temporary API issue)
3. If persistent, check input data format

---

#### PDF Upload Fails

**Cause:** Corrupted or unsupported PDF

**Solution:**
1. Verify PDF opens in standard PDF viewer
2. Try re-saving PDF from original source
3. Check file size (< 10MB recommended)
4. Ensure PDF contains text (not scanned images only)

---

#### Excel Shows Wrong Data

**Cause:** Incorrect header row selected

**Solution:**
1. Review raw preview carefully
2. Identify correct header row
3. Select correct row number
4. Click "Apply Header Row" again

---

#### Low Quality Scores

**Cause:** Poor input data or extraction issues

**Solution:**
1. Review input data quality
2. Check if all required information is present
3. Reprocess with different settings
4. Try different product type if applicable

---

#### Website Extraction Fails

**Cause:** Website structure not supported

**Solution:**
1. Verify URL is accessible
2. Check if website requires login
3. Try copying content to Excel instead
4. Contact administrator for custom website support

---

#### "Session expired" Error

**Cause:** Session timeout (7 days)

**Solution:**
1. Click "OK" on error message
2. Login again with credentials
3. Your work is saved, continue where you left off

---

## FAQ

### General Questions

**Q: How many products can I process at once?**
A: No hard limit, but recommend batches of 10-20 for optimal performance.

**Q: How long does processing take?**
A: Average 15-30 seconds per product, depending on data complexity.

**Q: Can I cancel processing midway?**
A: No, once started, let it complete. Products are processed sequentially.

**Q: Are my results saved automatically?**
A: Yes, in session state. Export to CSV/Excel for permanent storage.

---

### Data Sources

**Q: Can I use multiple data sources for one product?**
A: Yes! Combine PDF + Excel + Website for comprehensive extraction.

**Q: What if my PDF has 100+ pages?**
A: Select only relevant pages. Processing all pages may be slow.

**Q: Can I upload the same file multiple times?**
A: Yes, but results are independent. Export previous results first.

**Q: What website formats are supported?**
A: Most e-commerce product pages. Complex JavaScript sites may not work.

---

### Quality & Accuracy

**Q: What does "Overall Score 85%" mean?**
A: Weighted average of Structure (20%), Content (50%), Translation (30%) scores.

**Q: Should I trust results with 70% score?**
A: Review manually. May need minor corrections.

**Q: Can I edit extracted data before export?**
A: Not in UI. Export to Excel and edit there.

**Q: What is HSCode and why is it important?**
A: 8-digit international trade classification code, required for customs.

---

### Export & Storage

**Q: What's the difference between CSV and Excel export?**
A: CSV is plain text (universal), Excel has formatting and multiple sheets.

**Q: Can I export individual products?**
A: Current version exports all results. Use filters in Excel after export.

**Q: How long are results stored?**
A: In session state until logout or browser refresh. Always export!

**Q: Is Dropbox required?**
A: No, it's optional. You can download files locally.

---

### Account & Access

**Q: Can I change my password?**
A: Not in current version. Contact administrator.

**Q: What's the difference between User and Admin roles?**
A: Admins can manage users and view system stats. Users can only process products.

**Q: Can multiple users work on same project?**
A: Each user has independent session. Share exports for collaboration.

**Q: What happens if I forget my password?**
A: Contact administrator for password reset.

---

### Technical

**Q: Which browsers are supported?**
A: Chrome, Firefox, Safari, Edge (latest versions).

**Q: Can I use the app on mobile/tablet?**
A: UI is accessible but optimized for desktop use.

**Q: Does the app work offline?**
A: No, requires internet for LLM API calls.

**Q: Can I integrate with my own systems?**
A: Contact administrator for API access or custom integrations.

---

## Getting Help

### Support Channels

1. **Documentation:**
   - This User Guide
   - [Architecture Guide](ARCHITECTURE.md)
   - [Developer Guide](DEVELOPER_GUIDE.md)

2. **Administrator:**
   - Email your admin contact
   - Report bugs or feature requests

3. **Technical Support:**
   - Email: admin@sweetcare.com
   - Include error messages and screenshots

### Reporting Issues

When reporting issues, include:
1. **Description:** What were you trying to do?
2. **Steps to reproduce:** How can we replicate the issue?
3. **Error message:** Exact text of any errors
4. **Screenshots:** Visual context helps
5. **Environment:** Browser type and version

---

## Quick Reference Card

### Common Tasks

| Task | Steps |
|------|-------|
| **Add Product Config** | Configure Products tab → Select type → Choose sources → Submit |
| **Process Products** | Execute Batch tab → Review configs → Start Processing |
| **Export Results** | Execute Batch tab → Export to CSV/Excel |
| **Reprocess Failed** | Results table → Click Reprocess → Confirm |
| **View Details** | Results table → Click View button |
| **Logout** | Sidebar → Logout button |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + R` | Refresh page |
| `Ctrl + S` | Save/Export (when in export mode) |
| `Esc` | Close popup/modal |

---

**Last Updated:** 2025-10-10
**Version:** 3.0.0
**For:** SweetCare AI Product Content Creator
