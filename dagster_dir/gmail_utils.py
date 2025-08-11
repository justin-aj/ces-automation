"""
Gmail API utilities for creating draft emails.

This module provides functions to authenticate with Gmail API
and create draft emails in the user's Gmail account.
"""

import os
import pickle
from typing import Dict, List, Optional
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Returns a Gmail API service instance.
    """
    from pathlib import Path
    
    # Get absolute paths to the credential files
    project_root = Path(__file__).parent.parent
    token_path = project_root / 'token.pickle'
    credentials_path = project_root / 'credentials.json'
    
    print(f"Looking for token at: {token_path} (exists: {token_path.exists()})")
    print(f"Looking for credentials at: {credentials_path} (exists: {credentials_path.exists()})")
    
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if token_path.exists():
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                print(f"Loaded credentials from {token_path}")
        except Exception as e:
            print(f"Error loading credentials from {token_path}: {e}")
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired credentials")
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
            
            print(f"Starting OAuth flow with credentials from {credentials_path}")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
            print("Successfully obtained new credentials")
        
        # Save the credentials for the next run
        try:
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
                print(f"Saved new credentials to {token_path}")
        except Exception as e:
            print(f"Error saving credentials to {token_path}: {e}")

    return build('gmail', 'v1', credentials=creds)


def create_gmail_draft(job: Dict) -> Optional[str]:
    """
    Create a Gmail draft for a job application.
    
    Args:
        job: Dictionary containing job details and email content
        
    Returns:
        Draft ID if successful, None otherwise
    """
    import traceback
    
    try:
        # Debug the input job dict
        print(f"Creating draft for job ID: {job.get('job_id')}")
        print(f"Email ID: {job.get('email_id')}")
        print(f"Company Name: {job.get('company_name')}")
        
        # More detailed debugging of email content
        if 'email_content' not in job:
            print("ERROR: 'email_content' key missing from job dict")
            return None
        
        email_content = job['email_content']
        print(f"Email content type: {type(email_content)}")
        
        if not isinstance(email_content, dict):
            print(f"ERROR: email_content is not a dict, it's {type(email_content)}")
            # Try to convert if it's a string that might be JSON
            if isinstance(email_content, str):
                import json
                try:
                    email_content = json.loads(email_content)
                    print("Successfully converted string email_content to dict")
                except:
                    print("Failed to convert string email_content to dict")
                    return None
            else:
                return None
        
        # Check required fields
        if 'subject' not in email_content:
            print("ERROR: 'subject' missing from email_content")
            return None
            
        if 'body' not in email_content:
            print("ERROR: 'body' missing from email_content")
            return None
            
        print(f"Subject: {email_content['subject'][:30]}...")
        print(f"Body length: {len(email_content['body'])} chars")
        
        # Get Gmail service
        service = get_gmail_service()
        
        # Create the draft
        message = MIMEText(email_content['body'])
        message['to'] = job['email_id']
        message['subject'] = email_content['subject']
        
        print(f"Creating draft for: {message['to']}")
        print(f"With subject: {message['subject']}")
        
        # Encode the message
        encoded_message = urlsafe_b64encode(message.as_bytes()).decode()
        
        print("Calling Gmail API to create draft...")
        draft = service.users().drafts().create(
            userId='me',
            body={
                'message': {
                    'raw': encoded_message
                }
            }
        ).execute()
        
        draft_id = draft.get('id')
        print(f"SUCCESS! Draft created with ID: {draft_id}")
        return draft_id
        
    except Exception as e:
        print(f"Failed to create draft: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return None
