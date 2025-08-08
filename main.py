import os
import pickle
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText
from typing import List, Dict
from job_email_generator import JobEmailGenerator

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

async def save_email_drafts(job_applications: List[Dict[str, str]], email_generator: JobEmailGenerator) -> List[Dict]:
    """
    Save personalized cold email drafts for job applications.
    
    Args:
        job_applications: List of dictionaries containing job application details
        email_generator: Instance of JobEmailGenerator to create personalized emails
    """
    try:
        # Get Gmail service
        service = get_gmail_service()
        
        # Create drafts for each application
        drafts = []
        for job in job_applications:
            try:
                # Generate the email content using Gemini
                email_content = await email_generator.generate_cold_email(job)
                
                # Create the draft
                message = MIMEText(email_content['body'])
                message['to'] = job['email']
                message['subject'] = email_content['subject']
                
                # Encode the message
                encoded_message = urlsafe_b64encode(message.as_bytes()).decode()
                
                draft = service.users().drafts().create(
                    userId='me',
                    body={
                        'message': {
                            'raw': encoded_message
                        }
                    }
                ).execute()
                print(f'Draft created for {job["company_name"]}: {draft["id"]}')
                drafts.append(draft)
            except Exception as e:
                print(f'Failed to create draft for {job["company_name"]}: {e}')
        
        return drafts
    
    except Exception as e:
        print(f'Failed to save drafts: {e}')
        return []

async def main():
    # Create an email generator instance
    email_generator = JobEmailGenerator(
        your_name="Your Name",
        your_role="Software Engineer",
        your_background="5 years of experience in full-stack development"  # API key will be loaded from .env file
    )
    
    # Example job application
    job_application = {
        'email': 'hiring.manager@company.com',
        'employer_name': 'John Smith',
        'employer_role': 'Engineering Manager',
        'company_name': 'Tech Corp',
        'job_role': 'Senior Software Engineer',
        'role_details': '''
        • 5+ years of experience in Python development
        • Experience with cloud services (AWS/GCP)
        • Strong background in API design and microservices
        '''
    }
    
    drafts = await save_email_drafts([job_application], email_generator)
    print(f'Successfully created {len(drafts)} drafts')

if __name__ == '__main__':
    asyncio.run(main())
