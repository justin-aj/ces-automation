"""
Models for job status tracking.

This module provides classes for tracking job application status,
managing email generation, and persisting state to JSON.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import json


@dataclass
class JobStatus:
    """Class to track job application status."""
    
    job_id: str
    job_link: str
    employer_name: str
    employer_role: str
    email_id: str
    company_name: Optional[str] = None
    job_role: Optional[str] = None
    
    # Status tracking
    scrape_status: str = "pending"  # pending, success, failed
    email_status: str = "pending"   # pending, success, failed
    gmail_draft_id: Optional[str] = None
    
    # Content
    job_details: Optional[Dict] = None
    email_content: Optional[Dict] = None
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    scraped_at: Optional[str] = None
    email_generated_at: Optional[str] = None
    
    # Error tracking
    scrape_error: Optional[str] = None
    email_error: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)
    
    def mark_scraped(self, success: bool, job_details: Optional[Dict] = None, error: Optional[str] = None):
        """Mark job as scraped with success or failure."""
        self.scraped_at = datetime.now().isoformat()
        self.scrape_status = "success" if success else "failed"
        if job_details:
            self.job_details = job_details
            self.company_name = job_details.get("company_name")
            self.job_role = job_details.get("job_name")
        if error:
            self.scrape_error = error
    
    def mark_email_generated(self, success: bool, email_content: Optional[Dict] = None, 
                           error: Optional[str] = None, draft_id: Optional[str] = None):
        """Mark email as generated with success or failure."""
        self.email_generated_at = datetime.now().isoformat()
        self.email_status = "success" if success else "failed"
        if email_content:
            self.email_content = email_content
        if error:
            self.email_error = error
        if draft_id:
            self.gmail_draft_id = draft_id


class JobStatusTracker:
    """Class to track and persist job application statuses."""
    
    def __init__(self, storage_path: str = "job_status.json"):
        self.storage_path = storage_path
        self.jobs: Dict[str, JobStatus] = {}
        self._load()
    
    def _load(self):
        """Load job statuses from storage."""
        import os
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for job_id, job_dict in data.items():
                        self.jobs[job_id] = JobStatus(**job_dict)
            except Exception as e:
                print(f"Error loading job statuses: {e}")
    
    def save(self):
        """Save job statuses to storage."""
        jobs_dict = {job_id: job.to_dict() for job_id, job in self.jobs.items()}
        with open(self.storage_path, "w") as f:
            json.dump(jobs_dict, f, indent=2)
    
    def add_job(self, job: JobStatus):
        """Add or update job status."""
        self.jobs[job.job_id] = job
        self.save()
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Get job status by ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[JobStatus]:
        """List all job statuses."""
        return list(self.jobs.values())
    
    def update_job(self, job_id: str, **kwargs):
        """Update job status."""
        if job_id in self.jobs:
            for key, value in kwargs.items():
                if hasattr(self.jobs[job_id], key):
                    setattr(self.jobs[job_id], key, value)
            self.save()
    
    def to_dataframe(self):
        """Convert to pandas DataFrame."""
        import pandas as pd
        return pd.DataFrame([job.to_dict() for job in self.jobs.values()])
