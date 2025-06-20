# AI Email Agent

This project is an AI-powered email agent that reads emails from your Gmail inbox, generates intelligent responses using Google's Gemini (Vertex AI), and sends replies automatically.

## Features
- Reads unread emails from Gmail
- Uses Gemini (Vertex AI) to generate context-aware replies
- Sends responses via Gmail API
- Easy setup and configuration

## Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd ap_agent
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Google Cloud Setup
- Enable the Vertex AI API and Gmail API in your Google Cloud project.
- Download your service account key (for Vertex AI) and OAuth2 credentials (for Gmail).
- Place your credentials in a `config.json` or use environment variables.

### 4. Authentication
- For Gmail: Follow the [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python) to set up OAuth2 and get your `token.json`.
- For Vertex AI: Authenticate using your service account or `gcloud auth application-default login`.

### 5. Configuration
- Edit `config.json` or set environment variables for your credentials and settings.

### 6. Run the Agent
```bash
python email_ai.py
```

## Notes
- **Never commit your credentials to version control.**
- This project is for educational purposes. Review and adapt for production use.

## License
MIT 