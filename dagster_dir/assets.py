"""
Cold Email Automation System - Dagster Assets

This module defines the Dagster assets for the cold email automation workflow.
The workflow consists of several steps:
1. Load contacts data from CSV
2. Initialize or update the job status tracker
3. Scrape job details from job links
4. Load resume content
5. Generate personalized cold emails
6. Create Gmail drafts
7. Generate tracking reports
"""

import os
import json
import uuid
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import sys

from dagster import (
    asset,
    AssetExecutionContext,
    AssetIn,
    MetadataValue,
    Output,
    get_dagster_logger,
)

# Add parent directory to sys.path to import modules
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import project modules
from dagster_dir.models import JobStatus, JobStatusTracker
from job_email_generator import JobEmailGenerator
from job_scraper import JobScraper


logger = get_dagster_logger()


@asset(
    name="contacts_data",
    group_name="input_data",
    description="Raw contacts data from CSV file",
)
def load_contacts_data(context: AssetExecutionContext) -> pd.DataFrame:
    """
    Load contacts data from the CSV file exported by the Chrome extension.
    """
    csv_path = "contacts.csv"
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Contacts file not found: {csv_path}")
    
    # Load the CSV file
    df = pd.read_csv(csv_path)
    
    # Validate required columns
    required_columns = ["employer_name", "employer_role", "email_id", "job_link"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in CSV: {', '.join(missing_columns)}")
    
    # Log some stats
    context.log.info(f"Loaded {len(df)} contacts from {csv_path}")
    context.add_output_metadata({
        "num_contacts": len(df),
        "columns": MetadataValue.json(list(df.columns)),
        "preview": MetadataValue.md(df.head().to_markdown()),
    })
    
    return df


@asset(
    name="job_status_tracker",
    group_name="tracking",
    description="Job status tracker for monitoring application progress",
    deps=["contacts_data"],
)
def initialize_job_tracker(context: AssetExecutionContext, contacts_data: pd.DataFrame) -> JobStatusTracker:
    """
    Initialize or load the job status tracker and update it with new contacts.
    """
    # Initialize the tracker
    tracker = JobStatusTracker("job_status.json")
    
    # Get existing job IDs by job link
    existing_links = {job.job_link: job.job_id for job in tracker.list_jobs()}
    
    # Add new jobs from contacts
    new_jobs = 0
    for _, row in contacts_data.iterrows():
        job_link = row["job_link"]
        
        # Skip if the job link is already being tracked
        if job_link in existing_links:
            continue
        
        # Create a new job status
        job_id = str(uuid.uuid4())
        job = JobStatus(
            job_id=job_id,
            job_link=job_link,
            employer_name=row["employer_name"],
            employer_role=row["employer_role"],
            email_id=row["email_id"],
        )
        
        # Add to tracker
        tracker.add_job(job)
        new_jobs += 1
    
    context.log.info(f"Added {new_jobs} new jobs to tracker")
    context.log.info(f"Total jobs being tracked: {len(tracker.list_jobs())}")
    
    return tracker


@asset(
    name="scraped_job_details",
    group_name="job_scraping",
    description="Job details scraped from job links",
    deps=["job_status_tracker"],
)
def scrape_job_details(context: AssetExecutionContext, job_status_tracker: JobStatusTracker) -> pd.DataFrame:
    """
    Scrape job details for jobs that haven't been scraped yet.
    """
    # Initialize the scraper
    scraper = JobScraper()
    
    # Get jobs that need to be scraped
    jobs_to_scrape = [job for job in job_status_tracker.list_jobs() 
                     if job.scrape_status == "pending"]
    
    context.log.info(f"Found {len(jobs_to_scrape)} jobs to scrape")
    
    if not jobs_to_scrape:
        # If no jobs to scrape, return empty DataFrame
        return pd.DataFrame()
    
    # Create async event loop to scrape jobs
    scraped_jobs = []
    
    # We need to use a synchronous approach for Dagster
    for job in jobs_to_scrape:
        context.log.info(f"Scraping job: {job.job_link}")
        try:
            # Create a new event loop for each job
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Scrape the job page
            job_content = loop.run_until_complete(scraper.scrape_job_page(job.job_link))
            
            if not job_content:
                # Handle failed scraping
                error_msg = "Failed to scrape job content"
                context.log.error(f"{error_msg}: {job.job_link}")
                job.mark_scraped(False, error=error_msg)
                job_status_tracker.save()
                
                # Stop pipeline on first failure
                raise RuntimeError(f"Job scraping failed: {error_msg}")
            
            # Extract job details
            job_details = loop.run_until_complete(scraper.extract_job_details(job_content))
            loop.close()
            
            if not job_details:
                # Handle failed extraction
                error_msg = "Failed to extract job details"
                context.log.error(f"{error_msg}: {job.job_link}")
                job.mark_scraped(False, error=error_msg)
                job_status_tracker.save()
                
                # Stop pipeline on first failure
                raise RuntimeError(f"Job details extraction failed: {error_msg}")
            
            # Update job status
            job.mark_scraped(True, job_details=job_details)
            job_status_tracker.save()
            
            # Add to results
            scraped_jobs.append({
                "job_id": job.job_id,
                "job_link": job.job_link,
                "company_name": job_details.get("company_name", ""),
                "job_name": job_details.get("job_name", ""),
                "role_details": job_details.get("role_details", ""),
                "employer_name": job.employer_name,
                "employer_role": job.employer_role,
                "email_id": job.email_id,
                "scraped_at": job.scraped_at,
            })
            
        except Exception as e:
            # Log the error
            context.log.error(f"Error scraping job {job.job_link}: {str(e)}")
            
            # Update job status
            job.mark_scraped(False, error=str(e))
            job_status_tracker.save()
            
            # Stop pipeline on first failure
            raise RuntimeError(f"Job scraping failed: {str(e)}")
    
    # Convert to DataFrame
    df = pd.DataFrame(scraped_jobs)
    
    # Save to Excel
    if not df.empty:
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        excel_path = project_root / "job_details_scraped.xlsx"
        df.to_excel(str(excel_path), index=False)
        context.log.info(f"Saved {len(df)} scraped job details to {excel_path}")
    
    return df


@asset(
    name="resume_content",
    group_name="input_data",
    description="Resume content loaded from file",
)
def load_resume_content(context: AssetExecutionContext) -> str:
    """
    Load the resume content from a file.
    """
    resume_path = "resume.txt"
    
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume file not found: {resume_path}")
    
    with open(resume_path, "r", encoding="utf-8") as f:
        resume_text = f.read()
    
    # Log some stats
    context.log.info(f"Loaded resume from {resume_path}")
    context.log.info(f"Resume length: {len(resume_text)} characters")
    
    return resume_text


@asset(
    name="generated_emails",
    group_name="email_generation",
    description="Generated cold emails for job applications",
    deps=["scraped_job_details", "resume_content", "job_status_tracker"],
)
def generate_emails(
    context: AssetExecutionContext,
    scraped_job_details: pd.DataFrame,
    resume_content: str,
    job_status_tracker: JobStatusTracker,
) -> pd.DataFrame:
    """
    Generate cold emails for scraped job details.
    """
    if scraped_job_details.empty:
        context.log.info("No new job details to generate emails for")
        return pd.DataFrame()
    
    # Initialize the email generator
    email_generator = JobEmailGenerator(
        your_name="Ajin Frank Justin",
        your_role="Data Scientist",
        resume_text=resume_content
    )
    
    # Generate emails
    generated_emails = []
    
    # Get job IDs to process
    job_ids = scraped_job_details["job_id"].tolist()
    context.log.info(f"Found {len(job_ids)} jobs to generate emails for")
    
    # Create a single event loop for all emails
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Process counter for progress tracking
    processed = 0
    
    try:
        for job_id in job_ids:
            # Log progress
            processed += 1
            context.log.info(f"Processing job {processed}/{len(job_ids)}: {job_id}")
            
            # Get job from tracker
            job = job_status_tracker.get_job(job_id)
            if not job:
                context.log.error(f"Job ID not found in tracker: {job_id}")
                continue
            
            # Skip if already generated
            if job.email_status != "pending":
                context.log.info(f"Email already generated for job {job_id}, skipping")
                continue
            
            # Get job details from DataFrame
            try:
                job_row = scraped_job_details[scraped_job_details["job_id"] == job_id].iloc[0]
            except IndexError:
                context.log.error(f"Job ID {job_id} not found in scraped_job_details DataFrame")
                continue
            
            # Create job details dict for email generation
            job_details_dict = {
                "employer_name": job_row["employer_name"],
                "employer_role": job_row["employer_role"],
                "company_name": job_row["company_name"],
                "job_role": job_row["job_name"],
                "role_details": job_row["role_details"],
            }
            
            try:
                # Generate email with timeout
                context.log.info(f"Generating email for job {job_id}")
                
                # Run with timeout to avoid hanging
                try:
                    email_content = loop.run_until_complete(
                        asyncio.wait_for(
                            email_generator.generate_cold_email(job_details_dict),
                            timeout=60  # 60-second timeout
                        )
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Email generation timed out after 60 seconds for job {job_id}")
                
                if not email_content:
                    # Handle failed generation
                    error_msg = "Failed to generate email content"
                    context.log.error(f"{error_msg} for job {job_id}")
                    job.mark_email_generated(False, error=error_msg)
                    job_status_tracker.save()
                    continue  # Skip this job but continue with others
                
                # Update job status
                job.mark_email_generated(True, email_content=email_content)
                job_status_tracker.save()
                
                # Add to results
                generated_emails.append({
                    "job_id": job.job_id,
                    "company_name": job.company_name,
                    "job_role": job.job_role,
                    "employer_name": job.employer_name,
                    "email_id": job.email_id,
                    "subject": email_content["subject"],
                    "body": email_content["body"],
                    "generated_at": job.email_generated_at,
                })
                context.log.info(f"Successfully generated email for job {job_id}")
                
            except Exception as e:
                # Log the error
                context.log.error(f"Error generating email for job {job_id}: {str(e)}")
                
                # Update job status
                job.mark_email_generated(False, error=str(e))
                job_status_tracker.save()
                
                # Continue with next job rather than stopping the whole pipeline
                continue
    
    finally:
        # Always close the loop when done
        loop.close()
    
    # Convert to DataFrame
    df = pd.DataFrame(generated_emails)
    
    # Save to Excel
    if not df.empty:
        # Create absolute path for Excel file
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        excel_path = project_root / "generated_emails.xlsx"
        
        df.to_excel(str(excel_path), index=False)
        context.log.info(f"Saved {len(df)} generated emails to {excel_path}")
    
    return df


@asset(
    name="gmail_drafts",
    group_name="email_generation",
    description="Gmail drafts created from generated emails",
    deps=["generated_emails", "job_status_tracker"],
)
def create_gmail_drafts(
    context: AssetExecutionContext,
    generated_emails: pd.DataFrame,
    job_status_tracker: JobStatusTracker,
) -> pd.DataFrame:
    """
    Create Gmail drafts for generated emails.
    """
    if generated_emails.empty:
        context.log.info("No emails to create drafts for")
        return pd.DataFrame()
    
    # Import the Gmail utility functions and necessary authentication modules
    from dagster_dir.gmail_utils import create_gmail_draft
    import os
    from pathlib import Path
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    import pickle
    
    # Debug Gmail authentication directly
    context.log.info("Debugging Gmail API authentication")
    
    # Gmail API scope for drafts
    SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
    
    # Get absolute paths to the credential files
    project_root = Path(__file__).parent.parent
    token_path = project_root / 'token.pickle'
    credentials_path = project_root / 'credentials.json'
    
    # Check if files exist
    context.log.info(f"Checking for token.pickle at: {token_path} (exists: {token_path.exists()})")
    context.log.info(f"Checking for credentials.json at: {credentials_path} (exists: {credentials_path.exists()})")
    
    # Test Gmail authentication directly
    try:
        context.log.info("Attempting direct Gmail authentication test")
        creds = None
        
        # Load credentials if they exist
        if token_path.exists():
            with open(token_path, 'rb') as token:
                context.log.info("Loading credentials from token.pickle")
                try:
                    creds = pickle.load(token)
                    context.log.info("Successfully loaded credentials")
                    context.log.info(f"Credentials valid: {creds.valid if creds else 'No creds'}")
                    context.log.info(f"Credentials expired: {creds.expired if creds and hasattr(creds, 'expired') else 'Unknown'}")
                    context.log.info(f"Has refresh token: {bool(creds.refresh_token) if creds and hasattr(creds, 'refresh_token') else 'Unknown'}")
                except Exception as e:
                    context.log.error(f"Failed to load credentials: {str(e)}")
        else:
            context.log.warning("No token.pickle file found")
            
        # If credentials file doesn't exist, log a clear message
        if not credentials_path.exists():
            context.log.error(f"CRITICAL ERROR: credentials.json file not found at {credentials_path}")
            context.log.error("Please download OAuth credentials from Google Cloud Console")
            context.log.error("See: https://developers.google.com/gmail/api/quickstart/python")
    except Exception as e:
        context.log.error(f"Error during authentication test: {str(e)}")
    
    # Initialize counters and tracking
    total_jobs = len(generated_emails)
    drafts_created = 0
    draft_failures = 0
    processed = 0
    
    context.log.info(f"Creating Gmail drafts for {total_jobs} generated emails")
    
    # Process each generated email with progress tracking
    for _, row in generated_emails.iterrows():
        processed += 1
        job_id = row["job_id"]
        context.log.info(f"Processing job {processed}/{total_jobs}: {job_id}")
        
        # Get job from tracker
        job = job_status_tracker.get_job(job_id)
        if not job:
            context.log.error(f"Job ID not found in tracker: {job_id}")
            continue
        
        # Skip if already has a Gmail draft ID
        if job.gmail_draft_id:
            context.log.info(f"Draft already created for job {job_id}, skipping")
            continue
            
        # Make sure email content exists and is valid
        context.log.info(f"Checking email content for job {job_id}")
        
        # Get job data directly from dictionary representation for more reliability
        job_dict = job.to_dict()
        context.log.info(f"Job dictionary representation keys: {list(job_dict.keys())}")
        
        # Get email content from the dictionary or directly from job
        email_content = None
        if 'email_content' in job_dict and job_dict['email_content']:
            context.log.info(f"Found email_content in job_dict")
            email_content = job_dict['email_content']
        elif hasattr(job, 'email_content') and job.email_content:
            context.log.info(f"Found email_content in job object")
            email_content = job.email_content
        else:
            # Try to recover from job_status.json directly as a last resort
            context.log.info(f"Attempting to recover email_content from job_status.json")
            try:
                import json
                with open(job_status_tracker.storage_path, "r") as f:
                    data = json.load(f)
                    if job_id in data and 'email_content' in data[job_id]:
                        context.log.info(f"Recovered email_content from JSON file")
                        email_content = data[job_id]['email_content']
            except Exception as e:
                context.log.error(f"Error recovering from JSON: {e}")
                
        # Check if we have email content
        if not email_content:
            context.log.error(f"Could not find email_content for job {job_id}")
            draft_failures += 1
            continue
            
        context.log.info(f"Email content type: {type(email_content)}")
        context.log.info(f"Email content value: {email_content}")
        
        # Convert to dict if necessary - fix common serialization issues
        email_content_dict = {}
        if isinstance(email_content, dict):
            email_content_dict = email_content
        elif isinstance(email_content, str):
            # Try to parse as JSON
            try:
                import json
                email_content_dict = json.loads(email_content)
                context.log.info(f"Successfully parsed email_content from string to dict")
            except Exception as e:
                context.log.error(f"Failed to parse email_content string as JSON: {e}")
                draft_failures += 1
                continue
        else:
            context.log.error(f"Invalid email content type: {type(email_content)}")
            draft_failures += 1
            continue
        
        # Check required fields
        if "subject" not in email_content_dict or "body" not in email_content_dict:
            context.log.error(f"Email content missing subject or body for job {job_id}")
            context.log.error(f"Email content keys: {list(email_content_dict.keys())}")
            draft_failures += 1
            continue
            
        # Validate email address
        if not job.email_id or "@" not in job.email_id:
            context.log.error(f"Invalid email address for job {job_id}: {job.email_id}")
            draft_failures += 1
            continue
        
        # Create a job dict with all necessary information
        job_dict = {
            "job_id": job.job_id,
            "email_id": job.email_id,
            "company_name": job.company_name,
            "email_content": email_content_dict,
        }
        
        try:
            # Create the draft with better debugging and error handling
            context.log.info(f"Creating Gmail draft for job {job_id}")
            
            # Try direct call instead of threading for better error visibility
            try:
                # Detailed logging before API call
                context.log.info(f"Calling Gmail API with: email_id={job.email_id}, company={job.company_name}")
                context.log.info(f"Email content keys: {list(email_content_dict.keys()) if email_content_dict else 'None'}")
                
                # Direct call for better error tracking
                draft_id = create_gmail_draft(job_dict)
                
                if draft_id:
                    # Update job status with draft ID and mark email status as success
                    job.mark_email_generated(True, draft_id=draft_id)
                    job_status_tracker.save()
                    drafts_created += 1
                    context.log.info(f"Gmail draft created for job {job_id}: {draft_id}")
                else:
                    # If no draft_id but also no exception, log the issue
                    draft_failures += 1
                    error_msg = "Failed to create Gmail draft - no draft ID returned but no exception thrown"
                    context.log.error(f"{error_msg} for job {job_id}")
                    job.mark_email_generated(False, error=error_msg)
                    job_status_tracker.save()
                    
                    # Log email content details for debugging
                    context.log.info(f"Debug email content for job {job_id}:")
                    context.log.info(f"Keys: {list(email_content_dict.keys()) if email_content_dict else 'None'}")
                    context.log.info(f"Subject: {email_content_dict.get('subject', 'MISSING')[:30] if email_content_dict else 'NONE'}")
            except Exception as e:
                # Detailed error logging
                draft_failures += 1
                context.log.error(f"Gmail draft creation failed for job {job_id}")
                context.log.error(f"Error type: {type(e).__name__}")
                context.log.error(f"Error message: {str(e)}")
                
                # Try to get more details about the error
                import traceback
                tb_str = traceback.format_exc()
                context.log.error(f"Full traceback:\n{tb_str}")
                
                # Additional debugging of the job dict
                context.log.info(f"Debug job_dict for job {job_id}:")
                for key, value in job_dict.items():
                    if key == 'email_content' and isinstance(value, dict):
                        context.log.info(f"  {key}: {list(value.keys())}")
                    else:
                        context.log.info(f"  {key}: {value}")
                
                # Save error to job status and mark email as failed
                job.mark_email_generated(False, error=f"Gmail draft creation failed: {type(e).__name__}: {str(e)}")
                job_status_tracker.save()
        
        except Exception as e:
            draft_failures += 1
            context.log.error(f"Error creating Gmail draft for job {job_id}: {str(e)}")
            
            # Save any error to the job status and mark email as failed
            job.mark_email_generated(False, error=f"Gmail draft creation failed: {str(e)}")
            job_status_tracker.save()
    
    # Log summary
    context.log.info(f"Gmail drafts created: {drafts_created}/{total_jobs}")
    context.log.info(f"Gmail draft failures: {draft_failures}/{total_jobs}")
    
    # Return the updated job status as a DataFrame
    result_df = job_status_tracker.to_dataframe()
    
    # Save report to Excel with proper path
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    excel_path = project_root / "gmail_drafts_report.xlsx"
    result_df.to_excel(str(excel_path), index=False)
    context.log.info(f"Saved Gmail drafts report to {excel_path}")
    
    return result_df


@asset(
    name="email_tracking_report",
    group_name="reporting",
    description="Report on job application and email generation status",
    deps=["job_status_tracker", "gmail_drafts"],
)
def generate_tracking_report(context: AssetExecutionContext, job_status_tracker: JobStatusTracker) -> pd.DataFrame:
    """
    Generate a report on job application and email generation status.
    """
    # Convert tracker to DataFrame
    df = job_status_tracker.to_dataframe()
    
    # Calculate statistics
    total_jobs = len(df)
    scraped_jobs = len(df[df["scrape_status"] == "success"])
    failed_scrapes = len(df[df["scrape_status"] == "failed"])
    pending_scrapes = len(df[df["scrape_status"] == "pending"])
    
    generated_emails = len(df[df["email_status"] == "success"])
    failed_emails = len(df[df["email_status"] == "failed"])
    pending_emails = len(df[df["email_status"] == "pending"])
    
    # Log statistics
    context.log.info(f"Total jobs: {total_jobs}")
    context.log.info(f"Scraped jobs: {scraped_jobs}/{total_jobs} ({scraped_jobs/total_jobs*100:.1f}%)")
    context.log.info(f"Generated emails: {generated_emails}/{scraped_jobs} ({generated_emails/scraped_jobs*100:.1f}% of scraped)" if scraped_jobs > 0 else "Generated emails: 0/0 (0%)")
    
    # Add metadata
    context.add_output_metadata({
        "total_jobs": total_jobs,
        "scraped_jobs": scraped_jobs,
        "failed_scrapes": failed_scrapes,
        "pending_scrapes": pending_scrapes,
        "generated_emails": generated_emails,
        "failed_emails": failed_emails,
        "pending_emails": pending_emails,
        "stats": MetadataValue.md(f"""
        ## Job Application Statistics
        
        | Metric | Count | Percentage |
        |--------|-------|------------|
        | Total Jobs | {total_jobs} | 100% |
        | Scraped Successfully | {scraped_jobs} | {scraped_jobs/total_jobs*100:.1f}% |
        | Failed Scrapes | {failed_scrapes} | {failed_scrapes/total_jobs*100:.1f}% |
        | Pending Scrapes | {pending_scrapes} | {pending_scrapes/total_jobs*100:.1f}% |
        | Generated Emails | {generated_emails} | {generated_emails/total_jobs*100:.1f}% |
        | Failed Emails | {failed_emails} | {failed_emails/total_jobs*100:.1f}% |
        | Pending Emails | {pending_emails} | {pending_emails/total_jobs*100:.1f}% |
        """),
    })
    
    # Save to Excel
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    excel_path = project_root / "job_tracking_report.xlsx"
    df.to_excel(str(excel_path), index=False)
    context.log.info(f"Saved tracking report to {excel_path}")
    
    return df
