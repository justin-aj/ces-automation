import os
import json
import re
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import csv
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# Load environment variables
load_dotenv()

class JobScraper:
    def __init__(self, api_key: Optional[str] = None, crawl4ai_api_key: Optional[str] = None):
        """
        Initialize the JobScraper with API keys for Gemini and Crawl4AI.
        
        Args:
            api_key: API key for Gemini (optional if in .env)
            crawl4ai_api_key: API key for Crawl4AI (optional, crawl4ai works without an API key)
        """
        print("[INIT] Initializing JobScraper")
        
        # Configure Gemini API
        gemini_key: Optional[str] = api_key or os.getenv('GEMINI_API_KEY')
        if not gemini_key:
            raise ValueError("Gemini API key not found. Add to .env or provide directly.")
        
        print("[INIT] Configuring Gemini API")
        genai.configure(api_key=gemini_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("[INIT] Successfully initialized Gemini model")
    
    async def scrape_job_page(self, url: str) -> Optional[str]:
        """
        Scrape job page content using Crawl4AI AsyncWebCrawler.
        
        Args:
            url: URL of the job page to scrape
            
        Returns:
            Scraped content as text
        """
        print(f"[SCRAPE] Scraping content from: {url}")
        
        try:    
            async with AsyncWebCrawler() as crawler:
                # Step 5: Run the crawler
                url = url.strip()
                result = await crawler.arun(url=url)
                return result.markdown
        except Exception as e:
            print(f"[ERROR] Error scraping job page: {e}")
            return None
    
    async def extract_job_details(self, job_content: str) -> Optional[Dict[str, str]]:
        """
        Extract structured job information from scraped content using Gemini.
        
        Args:
            job_content: Scraped text content from the job page
            
        Returns:
            Dict containing job_role, role_details, company_name
        """
        if not job_content:
            print("[ERROR] No content to extract from")
            return None
        
        print("[EXTRACT] Extracting job details with Gemini API")
        
        prompt = f"""
        Extract the following information from this job posting content.
        Return ONLY a JSON object with these keys:
        - job_role: The full title of the job position
        - company_name: The name of the company
        - role_details: A comprehensive summary of the job that includes:
          1. Required technical skills and tech stack (programming languages, frameworks, tools)
          2. Required qualifications (education, years of experience)
          3. Key responsibilities
          4. Any domain-specific knowledge required
          5. Any unique or important requirements mentioned
        
        Here's the job posting content:
        {job_content[:10000]}  # Limit content length
        
        Return ONLY the JSON object with the requested fields. No introduction or explanation.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text
            
            # Try to parse as JSON, removing markdown formatting if present
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text.replace("```json", "", 1)
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("```", 1)[0]
            clean_text = clean_text.strip()
            
            job_details = json.loads(clean_text)
            print("[EXTRACT] Successfully extracted job details")
            return job_details
            
        except Exception as e:
            print(f"[ERROR] Error extracting job details: {e}")
            return None
    
    async def process_contacts_csv(self, file_path: str) -> pd.DataFrame:
        """
        Process a contacts CSV file exported from the Chrome extension.
        
        Args:
            file_path: Path to the contacts CSV file
            
        Returns:
            DataFrame with combined job details and contact information
        """
        print(f"[PROCESS] Processing contacts CSV: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Contacts file not found: {file_path}")
        
        # Read contacts CSV
        contacts_df = pd.read_csv(file_path)
        
        if 'job_link' not in contacts_df.columns:
            raise ValueError("CSV file does not contain 'job_link' column")
        
        results = []
        
        # Process each job link
        for i, row in contacts_df.iterrows():
            try:
                print(f"\n[PROCESS] Processing entry {i+1}/{len(contacts_df)}")
                
                # Extract contact info
                contact_info: Dict[str, str] = {
                    'employer_name': row.get('employer_name', ''),
                    'employer_role': row.get('employer_role', ''),
                    'email_id': row.get('email_id', ''),
                    'job_link': row.get('job_link', '')
                }
                
                # Skip if no job link
                if not contact_info['job_link']:
                    print("[WARN] No job link found for this entry, skipping")
                    results.append({**contact_info, 'job_role': '', 'company_name': '', 'role_details': '', 'scraped': False})
                    continue
                
                # Scrape job content
                job_content = await self.scrape_job_page(contact_info['job_link'])
                
                if not job_content:
                    print("[WARN] Failed to scrape content, skipping")
                    results.append({**contact_info, 'job_role': '', 'company_name': '', 'role_details': '', 'scraped': False})
                    continue
                
                # Extract job details
                job_details = await self.extract_job_details(job_content)
                
                if not job_details:
                    print("[WARN] Failed to extract job details, skipping")
                    results.append({**contact_info, 'job_role': '', 'company_name': '', 'role_details': '', 'scraped': False})
                    continue
                
                # Combine information
                combined_info: Dict[str, Any] = {**contact_info, **job_details, 'scraped': True}
                results.append(combined_info)
                
                print(f"[SUCCESS] Processed {contact_info['job_link']}")
                
            except Exception as e:
                print(f"[ERROR] Error processing entry {i+1}: {e}")
                results.append({
                    'employer_name': row.get('employer_name', ''),
                    'employer_role': row.get('employer_role', ''),
                    'email_id': row.get('email_id', ''),
                    'job_link': row.get('job_link', ''),
                    'job_role': '',
                    'company_name': '',
                    'role_details': '',
                    'scraped': False,
                    'error': str(e)
                })
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        print(f"[PROCESS] Completed processing {len(results)} entries")
        
        return results_df
    
    def save_results(self, results_df: pd.DataFrame, output_path: Optional[str] = None) -> Dict[str, Union[str, int]]:
        """
        Save the combined results to CSV and JSON.
        
        Args:
            results_df: DataFrame with combined information
            output_path: Directory to save results (default: current directory)
            
        Returns:
            Dict with paths to saved files
        """
        if output_path:
            output_dir = Path(output_path)
        else:
            output_dir = Path.cwd()
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as CSV
        csv_path = output_dir / "job_details.csv"
        results_df.to_csv(csv_path, index=False)
        
        # Save as JSON
        json_path = output_dir / "job_details.json"
        results_df.to_json(json_path, orient='records', indent=2)
        
        print(f"[SAVE] Results saved to CSV: {csv_path}")
        print(f"[SAVE] Results saved to JSON: {json_path}")
        
        return {
            "csv_path": str(csv_path),
            "json_path": str(json_path),
            "record_count": len(results_df)
        }


async def main() -> None:
    """
    Main function to run the job scraper.
    """
    try:
        # Initialize the scraper
        scraper = JobScraper()
        
        # Input file path
        contacts_csv = "contacts.csv"  # Default name
            
        # Output directory
        output_dir: str = input("Enter output directory (leave empty for current directory): ").strip()
        
        # Process the contacts and job links
        results_df = await scraper.process_contacts_csv(contacts_csv)
        
        # Save the results
        save_info = scraper.save_results(results_df, output_dir)
        
        print("\nJob scraping completed successfully!")
        print(f"Processed {save_info['record_count']} entries")
        print(f"Results saved to:")
        print(f"- CSV: {save_info['csv_path']}")
        print(f"- JSON: {save_info['json_path']}")
        
    except Exception as e:
        print(f"Error in main execution: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
