import os
import pickle
import random
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Returns a Gmail API service instance.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def generate_personalized_content(recipient_email):
    """
    Generate personalized content for each recipient.
    In a real application, this would be more sophisticated.
    """
    templates = [
        {
            'subject': 'Exciting Partnership Opportunity',
            'body': f'''Dear {recipient_email.split('@')[0]},

I hope this email finds you well. I came across your profile and I'm impressed with your work.

{random.choice([
    "I believe there's potential for a valuable collaboration between us.",
    "I wanted to discuss a possible partnership opportunity.",
    "I think we could create something amazing together."
])}

Would you be interested in scheduling a brief call to discuss this further?

Best regards,
[Your Name]'''
        },
        {
            'subject': 'Quick Question About Your Work',
            'body': f'''Hi {recipient_email.split('@')[0]},

I recently discovered your work and I'm really intrigued by what you're doing.

{random.choice([
    "Your approach to problem-solving is fascinating.",
    "Your recent projects caught my attention.",
    "Your expertise in the field is remarkable."
])}

I'd love to learn more about your experiences.

Best,
[Your Name]'''
        }
    ]
    
    return random.choice(templates)

def create_draft_email(service, recipient_email):
    """Create and save an email draft."""
    content = generate_personalized_content(recipient_email)
    
    message = MIMEText(content['body'])
    message['to'] = recipient_email
    message['subject'] = content['subject']
    
    # Encode the message
    encoded_message = urlsafe_b64encode(message.as_bytes()).decode()
    
    try:
        draft = service.users().drafts().create(
            userId='me',
            body={
                'message': {
                    'raw': encoded_message
                }
            }
        ).execute()
        print(f'Draft created for {recipient_email}: {draft["id"]}')
        return draft
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

def save_email_drafts(email_list):
    """
    Save personalized email drafts for a list of recipients.
    
    Args:
        email_list (list): List of recipient email addresses
    """
    try:
        # Get Gmail service
        service = get_gmail_service()
        
        # Create drafts for each recipient
        drafts = []
        for email in email_list:
            draft = create_draft_email(service, email)
            if draft:
                drafts.append(draft)
        
        return drafts
    
    except Exception as e:
        print(f'Failed to save drafts: {e}')
        return []

if __name__ == '__main__':
    # Example usage
    test_emails = [
        'test1@example.com',
        'test2@example.com',
        'test3@example.com'
    ]
    
    drafts = save_email_drafts(test_emails)
    print(f'Successfully created {len(drafts)} drafts')
