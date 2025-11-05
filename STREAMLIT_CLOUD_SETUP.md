# Streamlit Cloud Setup Guide

This guide explains how to configure your SweetCare AI Product Creator application in Streamlit Cloud with proper secrets management for production deployment.

## Overview

Streamlit Cloud uses a **secrets management system** that differs from local `.env` files. All API keys and sensitive configuration must be added through the Streamlit Cloud dashboard.

## Changes Made for Cloud Compatibility

### What Was Fixed

The application now uses a **dual-lookup system** that checks both:
1. **Streamlit Secrets** (for Cloud deployment) - Priority 1
2. **Environment Variables** (for local development with `.env`) - Fallback

This ensures:
- ✅ Works in Streamlit Cloud without code changes
- ✅ Works locally with `.env` files
- ✅ No security concerns with committed secrets

### Files Modified

1. **[config.py](config.py)** - Added `get_secret_or_env()` helper function
2. **[utils/langsmith_utils.py](utils/langsmith_utils.py)** - Uses new helper for LangSmith
3. **[models/openai_model.py](models/openai_model.py)** - Uses new helper for OpenAI API key
4. **[models/groq_model.py](models/groq_model.py)** - Uses new helper for Groq API key

## Streamlit Cloud Secrets Configuration

### Step 1: Access Secrets Management

1. Go to your Streamlit Cloud dashboard: https://share.streamlit.io/
2. Click on your deployed app
3. Click **⚙️ Settings** (gear icon in the top right)
4. Click **Secrets** in the left sidebar

### Step 2: Add Required Secrets

Copy and paste this template into the secrets editor, replacing the placeholder values with your actual keys:

```toml
# ============================================
# API Keys (Required - Root Level)
# ============================================

# OpenAI API Key (Required for GPT models)
OPENAI_API_KEY = "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Groq API Key (Optional - for alternative models)
GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ============================================
# LangSmith Observability (Optional but Recommended - Root Level)
# ============================================

# LangSmith API Key for tracing and monitoring
LANGSMITH_API_KEY = "lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Enable LangSmith tracing (set to "true" to enable)
LANGSMITH_TRACING = "true"

# LangSmith project name (optional - defaults to "ai_product_creator")
LANGSMITH_PROJECT = "ai_product_creator"

# LangSmith endpoint (optional - defaults to official endpoint)
LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"

# ============================================
# Cloud Storage (Optional - Root Level)
# ============================================

# Dropbox access token for automatic file uploads
DROPBOX_ACCESS_TOKEN = "sl.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ============================================
# PostgreSQL Database (Required for Auth - Separate Section)
# ============================================

# IMPORTANT: PostgreSQL settings MUST be in [postgres] section
# DO NOT put other API keys inside this section!

[postgres]
host = "aws-0-eu-west-3.pooler.supabase.com"
database = "postgres"
user = "postgres.ubmzhttmrvqcqtvzlmah"
password = "your-database-password"
port = "6543"
sslmode = "require"
connect_timeout = "20"
application_name = "ai_product_creator_app"
```

**⚠️ IMPORTANT:** Keep all API keys (OPENAI, GROQ, LANGSMITH, DROPBOX) at the **root level** of your secrets file. Only PostgreSQL connection parameters should be inside the `[postgres]` section. Mixing them will cause connection errors!

### Step 3: Save and Deploy

1. Click **Save** in the secrets editor
2. Your app will automatically redeploy with the new secrets
3. Wait for the deployment to complete (usually 1-2 minutes)

## Verifying LangSmith Integration

After deployment, check the sidebar in your app:

### Success Indicators

✅ **LangSmith tracing enabled** (green message in sidebar)
- This means LangSmith is properly configured
- All LLM calls will be traced in your LangSmith dashboard
- Go to https://smith.langchain.com/ to view traces

### Failure Indicators

⚠️ **Failed to initialize LangSmith: [error]** (yellow warning)
- Check that `LANGSMITH_API_KEY` is correct
- Verify the API key has not expired
- Check LangSmith service status

💡 **LangSmith not configured** (blue info)
- `LANGSMITH_API_KEY` is missing from secrets
- Add the key following Step 2 above

## Understanding the New Behavior

### Before (❌ Broken in Cloud)

```python
# Only checked environment variables
api_key = os.getenv("LANGSMITH_API_KEY")
```

- ❌ Failed in Streamlit Cloud (no `.env` file deployed)
- ✅ Worked locally with `.env` file

### After (✅ Works Everywhere)

```python
# Checks Streamlit secrets FIRST, then environment variables
api_key = config.get_secret_or_env("LANGSMITH_API_KEY")
```

- ✅ Works in Streamlit Cloud (reads from secrets)
- ✅ Works locally with `.env` file (fallback)
- ✅ No code changes needed between environments

## LangSmith Observability Features

With LangSmith properly configured, you get:

### 1. **Automatic Tracing**
- Every LLM call is logged with full context
- Input prompts, output responses, and metadata
- Performance metrics (latency, token usage)

### 2. **Quality Monitoring**
- Track evaluation scores over time
- Identify failing extractions
- Monitor hallucination rates

### 3. **Debugging**
- Full conversation history for each extraction
- Error stack traces
- Model comparison across runs

### 4. **Cost Tracking**
- Token usage per request
- Cost per product extraction
- Provider comparison (OpenAI vs Groq)

## Troubleshooting

### Issue: "LangSmith not configured"

**Cause:** Missing `LANGSMITH_API_KEY` in secrets

**Solution:**
1. Get your API key from https://smith.langchain.com/settings
2. Add to Streamlit Cloud secrets (see Step 2)
3. Redeploy your app

### Issue: "Failed to initialize LangSmith"

**Cause:** Invalid API key or network issues

**Solution:**
1. Verify API key is correct (starts with `lsv2_pt_`)
2. Check API key hasn't expired
3. Try regenerating the key in LangSmith dashboard

### Issue: Traces not appearing in LangSmith

**Cause:** `LANGSMITH_TRACING` not set to `"true"`

**Solution:**
1. Add `LANGSMITH_TRACING = "true"` to secrets
2. Ensure it's lowercase "true" (not "True" or "TRUE")
3. Redeploy your app

### Issue: Wrong project in LangSmith

**Cause:** Default project name being used

**Solution:**
1. Add `LANGSMITH_PROJECT = "your_project_name"` to secrets
2. Create the project first in LangSmith dashboard
3. Redeploy your app

## Local Development

For local development, continue using your `.env` file:

```bash
# .env file (not committed to Git)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=ai_product_creator
DROPBOX_ACCESS_TOKEN=sl.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MASTER_PASSWORD=your_secure_password_here
```

The application will automatically use the `.env` file when running locally.

## Security Best Practices

### ✅ Do

- Use Streamlit Cloud secrets for all API keys
- Regularly rotate API keys
- Use separate keys for development and production
- Monitor API usage in provider dashboards

### ❌ Don't

- Commit `.env` files to Git
- Share API keys in chat or email
- Use production keys in local development
- Hardcode secrets in source code

## Getting API Keys

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Click **Create new secret key**
3. Copy the key (starts with `sk-proj-`)

### Groq
1. Go to https://console.groq.com/keys
2. Click **Create API Key**
3. Copy the key (starts with `gsk_`)

### LangSmith
1. Go to https://smith.langchain.com/settings
2. Click **Create API Key**
3. Copy the key (starts with `lsv2_pt_`)

### Dropbox
1. Go to https://www.dropbox.com/developers/apps
2. Create a new app with "Full Dropbox" access
3. Generate access token in app settings
4. Copy the token (starts with `sl.`)

## Support

If you encounter issues:

1. Check the Streamlit Cloud logs (click **Manage app** → **Logs**)
2. Verify all required secrets are configured
3. Test locally first with `.env` file
4. Check provider service status pages

## Summary

✅ **What Changed:**
- Added `config.get_secret_or_env()` helper function
- All API key lookups now check Streamlit secrets first
- LangSmith tracing now works in production

✅ **What You Need to Do:**
1. Add all API keys to Streamlit Cloud secrets
2. Set `LANGSMITH_TRACING = "true"`
3. Redeploy your app

✅ **Expected Result:**
- ✅ LangSmith tracing enabled (sidebar shows green checkmark)
- ✅ All extractions traced in LangSmith dashboard
- ✅ Quality monitoring and debugging enabled
