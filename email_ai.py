import os
import json
import base64
from email.mime.text import MIMEText
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

import vertexai
from vertexai.generative_models import GenerativeModel
import pandas as pd

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
CONFIG_PATH = "config.json"
TOKEN_PATH = "token.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def gmail_authenticate(client_secret):
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_unread_emails(service, user_id='me'):
    try:
        results = service.users().messages().list(userId=user_id, labelIds=['CATEGORY_PERSONAL'], q="is:unread").execute()
        messages = results.get('messages', [])
        emails = []
        for msg in messages:
            msg_data = service.users().messages().get(userId=user_id, id=msg['id']).execute()
            payload = msg_data['payload']
            headers = payload['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "")
            body = ""
            if 'data' in payload.get('body', {}):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            else:
                for part in payload.get('parts', []):
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            emails.append({
                'id': msg['id'],
                'subject': subject,
                'sender': sender,
                'body': body
            })
        return emails
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def mark_as_read(service, msg_id, user_id='me'):
    service.users().messages().modify(userId=user_id, id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()

def send_email(service, to, subject, message_text, user_id='me'):
    message = MIMEText(message_text)
    message['to'] = to
    message['subject'] = "Re: " + subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw}
    service.users().messages().send(userId=user_id, body=body).execute()

def load_property_data(excel_path="Properties Listing.xlsx"):
    try:
        df = pd.read_excel(excel_path)
        property_info = "PROPERTY INFORMATION:\n"
        for i, (index, row) in enumerate(df.iterrows()):
            property_info += f"\nProperty {i + 1}:\n"
            for column, value in row.items():
                property_info += f"  {column}: {value}\n"
        return property_info
    except FileNotFoundError:
        print(f"Warning: {excel_path} not found. Running without property context.")
        return ""
    except Exception as e:
        print(f"Error loading property data: {e}")
        return ""

def load_conversation_history(sender_email):
    try:
        with open('conversation_history.json', 'r') as f:
            history = json.load(f)
        return history.get(sender_email, [])
    except FileNotFoundError:
        return []

def save_conversation_history(sender_email, email_body, reply):
    try:
        with open('conversation_history.json', 'r') as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}
    
    if sender_email not in history:
        history[sender_email] = []
    
    history[sender_email].append({
        'timestamp': datetime.now().isoformat(),
        'incoming': email_body,
        'outgoing': reply
    })
    
    history[sender_email] = history[sender_email][-5:]
    
    with open('conversation_history.json', 'w') as f:
        json.dump(history, f, indent=2)

def generate_reply_with_gemini(project, location, email_body, sender_email):
    config = load_config()
    credentials = service_account.Credentials.from_service_account_file(
        config['service_account_key'],
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    vertexai.init(project=project, location=location, credentials=credentials)
    model = GenerativeModel("gemini-2.0-flash-001")
    
    property_context = load_property_data()
    conversation_history = load_conversation_history(sender_email)
    
    history_context = ""
    if conversation_history:
        history_context = "\n\nPREVIOUS CONVERSATION HISTORY:\n"
        for conv in conversation_history:
            history_context += f"\nTenant: {conv['incoming'][:200]}...\n"
            history_context += f"Pandora: {conv['outgoing'][:200]}...\n"
    
    system_prompt = """You are Pandora, an experienced and professional property manager. You have in-depth knowledge of each property you oversee, including amenities, lease terms, neighborhood features, and application procedures. Your tone is friendly, clear, and helpful. When composing replies, you should:
	•	Write a concise, natural subject line (no "Re:" prefixes and do not include "Subject:" in the body).
	•	Greet the sender by name (if provided).
	•	Thank them genuinely for their interest.
	•	Answer each of their questions thoroughly and accurately.
	•	Offer any next steps (availability, showing times, application links).
	•	Invite further questions and provide your contact information.
"""
    
    user_prompt = f"""You are Pandora, the property manager. Below is an email from a prospective tenant asking questions about one of your listings. Draft a warm, informative reply with an organic subject line (no "Re:" prefix) and no explicit "Subject:" label inside the email body:

{property_context}{history_context}

Email from prospective tenant:
{email_body}"""
    
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    response = model.generate_content(full_prompt)
    return response.text

def main():
    config = load_config()
    gmail_service = gmail_authenticate(config['gmail_client_secret'])
    emails = get_unread_emails(gmail_service)
    if not emails:
        print("No unread emails found.")
        return

    email = emails[0]
    print(f"Processing email from {email['sender']} with subject '{email['subject']}'")
    
    sender_email = email['sender'].split('<')[1].split('>')[0] if '<' in email['sender'] else email['sender']
    
    reply = generate_reply_with_gemini(
        project=config['gcp_project'],
        location=config['gcp_location'],
        email_body=email['body'],
        sender_email=sender_email
    )
    
    save_conversation_history(sender_email, email['body'], reply)
    
    send_email(
        gmail_service,
        to=email['sender'],
        subject=email['subject'],
        message_text=reply
    )
    mark_as_read(gmail_service, email['id'])
    print(f"Replied to {email['sender']}.")

if __name__ == "__main__":
    main()
