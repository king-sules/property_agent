import os
import json
import base64
import requests
from email.mime.text import MIMEText
from datetime import datetime
import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

import vertexai
from vertexai.generative_models import GenerativeModel


from langchain_manager import LangChainConversationManager
from google.cloud import firestore

def load_config():
    
    return {
        'gmail_client_secret': os.environ.get('GMAIL_CLIENT_SECRET'),
        'gmail_client_id': os.environ.get('GMAIL_CLIENT_ID'),
        'gcp_project': os.environ.get('GCP_PROJECT', 'doc-extract-454213'),
        'gcp_location': os.environ.get('GCP_LOCATION', 'us-central1'),
        'service_account_key': os.environ.get('SERVICE_ACCOUNT_KEY'),
        'property_excel': os.environ.get('PROPERTY_EXCEL'),
        'gmail_user_email': os.environ.get('GMAIL_USER_EMAIL'), 
        'gmail_refresh_token': os.environ.get('GMAIL_REFRESH_TOKEN') 
    }

def get_properties_from_firestore():
    try:
        
        db = firestore.Client()
        
        
        properties_ref = db.collection('properties')
        docs = properties_ref.stream()
        
        properties = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id  
            properties.append(data)
        
        print(f"Retrieved {len(properties)} properties from Firestore")
        return properties
        
    except Exception as e:
        print(f"Error getting properties from Firestore: {e}")
        return []

def gmail_authenticate():
    try:
        config = load_config()
        
        
        if config.get('gmail_refresh_token') and config.get('gmail_client_id') and config.get('gmail_client_secret'):
            
            credentials = Credentials(
                token=None,
                refresh_token=config['gmail_refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=config['gmail_client_id'],
                client_secret=config['gmail_client_secret'],
                scopes=[
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.modify',
                    'https://www.googleapis.com/auth/gmail.compose'
                ]
            )
            
            
            if credentials.expired:
                credentials.refresh(Request())
            
            return build('gmail', 'v1', credentials=credentials)
        
        
        elif config.get('service_account_key') and config.get('gmail_user_email'):
            print("Using service account with domain-wide delegation")
            service_account_key_json = config['service_account_key']
            service_account_info = json.loads(service_account_key_json)
            
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=[
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.modify',
                    'https://www.googleapis.com/auth/gmail.compose'
                ]
            )
            
            
            credentials = credentials.with_subject(config['gmail_user_email'])
            return build('gmail', 'v1', credentials=credentials)
        
        else:
            raise Exception("No valid Gmail authentication credentials found. Please set either OAuth2 credentials (GMAIL_REFRESH_TOKEN, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET) or service account with domain-wide delegation (SERVICE_ACCOUNT_KEY, GMAIL_USER_EMAIL)")
        
    except Exception as e:
        print(f"Error authenticating with Gmail: {e}")
        raise

def get_unread_emails(service, user_id='me'):
    try:
        results = service.users().messages().list(userId=user_id, labelIds=['INBOX'], q="is:unread").execute()
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

def generate_reply_with_langchain(project, location, email_body, sender_email):
    try:
        conv_manager = LangChainConversationManager()
        
        conv_manager.add_message(sender_email, email_body, is_human=True)
        
        conversation_context = conv_manager.get_conversation_context(sender_email)
        
        properties = get_properties_from_firestore()
        property_context = "PROPERTY INFORMATION:\n"
        if properties:
            for i, prop in enumerate(properties):
                property_context += f"\nProperty {i + 1}:\n"
                for key, value in prop.items():
                    property_context += f"  {key}: {value}\n"
        else:
            property_context = "No property information available."
        
        vertexai.init(project=project, location=location)
        model = GenerativeModel("gemini-2.0-flash-001")
        
        system_prompt = """You are Pandora, an experienced and professional property manager. You have in-depth knowledge of each property you oversee, including amenities, lease terms, neighborhood features, and application procedures. Your tone is friendly, clear, and helpful. When composing replies, you:
• Greet the sender by name (if provided)
• Thank them for their interest
• Answer each of their questions thoroughly and accurately
• Provide any additional relevant details (availability, next steps, showing times)
• Invite further questions and offer your contact information
• Reference previous conversations when relevant to provide continuity"""
        
        user_prompt = f"""Below is an email from a prospective tenant asking questions about one of your listings. Read the message carefully and draft a warm, informative reply that addresses each question and guides them toward the next steps, do not include Re: in the beginning of the response.

{property_context}{conversation_context}

Email from prospective tenant:
{email_body}"""
        
        response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
        reply = response.text
        
        conv_manager.add_message(sender_email, reply, is_human=False)
        
        return reply
        
    except Exception as e:
        print(f"Error generating reply: {e}")
        return "Thank you for your email. I'll get back to you shortly."

def create_draft_email(service, to, subject, message_text, user_id='me'):
    message = MIMEText(message_text)
    message['to'] = to
    message['subject'] = "Re: " + subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'message': {'raw': raw}}
    draft = service.users().drafts().create(userId=user_id, body=body).execute()
    print(f"Draft created for {to} with subject '{subject}'")
    return draft

def mark_as_read(service, msg_id, user_id='me'):
    service.users().messages().modify(userId=user_id, id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()

def main(request):
    config = load_config()
    gmail_service = gmail_authenticate()
    emails = get_unread_emails(gmail_service)
    if not emails:
        print("No unread emails found.")
        return 'No unread emails found.', 200
    
    email = emails[0]
    print(f"Processing email from {email['sender']} with subject '{email['subject']}'")
    sender_email = email['sender'].split('<')[1].split('>')[0] if '<' in email['sender'] else email['sender']
    
    reply = generate_reply_with_langchain(
        project=config['gcp_project'],
        location=config['gcp_location'],
        email_body=email['body'],
        sender_email=sender_email
    )
    
    create_draft_email(
        gmail_service,
        to=email['sender'],
        subject=email['subject'],
        message_text=reply
    )
    print(f"Draft created for sender: {email['sender']}")
    mark_as_read(gmail_service, email['id'])
    return 'Draft created.', 200 