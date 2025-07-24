# Cloud Functions Deployment Guide

## Functions Overview

1. **get_properties** - ✅ Already deployed
   - URL: https://us-central1-doc-extract-454213.cloudfunctions.net/get_properties
   - Purpose: Retrieves property data from Firestore

2. **cloud_draft_ai** - 🔄 Ready to deploy (Updated with LangChain)
   - Purpose: Processes emails and creates AI-powered draft replies
   - Uses decoupled LangChain manager for conversation management
   - Calls get_properties function for data

## File Structure

```
ap_agent/
├── cloud_draft_ai.py          # Main Cloud Function (email processing)
├── langchain_manager.py       # Decoupled LangChain conversation manager
├── get_properties_function/   # Properties Cloud Function
├── test_langchain_manager.py  # Test script for conversation manager
├── requirements.txt           # Dependencies
└── DEPLOYMENT_GUIDE.md        # This file
```

## Deployment Steps

### Deploy Cloud Draft AI Function (Updated)

```bash
# Make sure you're in the root directory
gcloud functions deploy cloud_draft_ai \
  --runtime python310 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --region us-central1
```

## Environment Variables

The function uses these environment variables:
- `GCP_PROJECT` - Your GCP project ID (default: doc-extract-454213)
- `GCP_LOCATION` - GCP region (default: us-central1)
- `PROPERTIES_FUNCTION_URL` - URL of the properties function (auto-detected)
- `GMAIL_CLIENT_SECRET` - Path to Gmail OAuth credentials

## Testing

### 1. Test LangChain Manager Locally
```bash
python test_langchain_manager.py
```

### 2. Test Properties Function
```bash
curl https://us-central1-doc-extract-454213.cloudfunctions.net/get_properties
```

### 3. Test Cloud Draft AI Function
```bash
curl https://us-central1-doc-extract-454213.cloudfunctions.net/cloud_draft_ai
```

## Architecture (Updated)

```
Cloud Draft AI Function
├── Imports langchain_manager.py → Manages conversation state in Firestore
├── Calls get_properties function → Gets property data
├── Uses Gemini AI → Generates intelligent replies
└── Creates Gmail draft → Sends response
```

## LangChain Manager Benefits

- ✅ **Decoupled design** - Separate, reusable conversation management
- ✅ **Built-in conversation management** - No manual JSON handling
- ✅ **Automatic context window management** - Handles token limits intelligently
- ✅ **Professional conversation state** - Industry-standard approach
- ✅ **Easy to extend** - Can add more LangChain features
- ✅ **Better conversation flow** - Maintains context across interactions

## Firestore Structure

```
conversations collection:
├── user1@example.com (document)
│   ├── email: "user1@example.com"
│   ├── messages: [LangChain conversation objects]
│   └── last_updated: timestamp
├── user2@example.com (document)
│   ├── email: "user2@example.com"
│   ├── messages: [LangChain conversation objects]
│   └── last_updated: timestamp
```

## Why Decoupled?

- **Reusability** - `langchain_manager.py` can be used by other functions
- **Cleaner code** - Separation of concerns
- **Easier testing** - Can test conversation management independently
- **No HTTP overhead** - Direct Firestore calls, no function-to-function calls
- **Better maintainability** - Each component has a single responsibility

## Next Steps

1. Deploy the updated cloud_draft_ai function
2. Set up Cloud Scheduler to trigger email processing
3. Configure Gmail authentication for production use
4. Test conversation continuity across multiple emails 