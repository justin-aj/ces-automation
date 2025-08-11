from dagster import (
    ConfigurableResource,
    resource,
)
from typing import Optional
import os
import google.generativeai as genai
from pathlib import Path
import asyncio


class GeminiResource(ConfigurableResource):
    """Resource for interacting with Google's Gemini API."""
    
    api_key: Optional[str] = None
    model_name: str = "gemini-2.5-flash"
    
    def setup_context(self):
        """Set up Gemini API with the provided key."""
        api_key = self.api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Set it in .env file or provide directly.")
        
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self.model_name)


class CrawlAIResource(ConfigurableResource):
    """Resource for interacting with Crawl4AI."""
    
    api_key: Optional[str] = None
    
    async def setup_crawler(self):
        """Set up the crawler with the API key."""
        from crawl4ai import AsyncWebCrawler
        
        # Crawl4AI works without an API key as well
        return AsyncWebCrawler()


class ResumeResource(ConfigurableResource):
    """Resource for loading and managing resume content."""
    
    resume_path: str = "resume.txt"
    
    def setup_context(self):
        """Load resume text from file."""
        path = Path(self.resume_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume file not found at {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            resume_text = f.read()
            
        return resume_text
