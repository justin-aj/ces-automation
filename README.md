# Cold Email Automation Project

Last Updated: August 10, 2025

## Latest Updates

### Major Enhancements (August 10, 2025)
1. **Enhanced Job Detail Extraction**
   - Improved AI prompt for job detail extraction
   - Now extracting comprehensive technical requirements from job postings
   - Added extraction of tech stack, qualifications, and key responsibilities
   - Enhanced extraction of domain-specific knowledge requirements

### Major Enhancements (August 9, 2025)
1. **Job Scraping and Information Extraction**
   - Added `job_scraper.py` to extract job details from URLs
   - Integrated Crawl4AI AsyncWebCrawler for efficient web scraping
   - Implemented markdown-based content extraction
   - Used Gemini 2.5 Flash API to extract structured job data

### Major Enhancements (August 8, 2025)
1. **AI-Powered Email Generation**
   - Integrated Gemini API for intelligent email generation
   - Added sophisticated prompt engineering for better context understanding
   - Implemented personalized email content based on job requirements

2. **Resume Integration**
   - Added support for full resume text input
   - Enhanced matching between resume skills and job requirements
   - Improved context utilization in email generation

3. **Robust CSV Processing**
   - Implemented pandas-based CSV handling
   - Added support for multiple file encodings (UTF-8, CP1252, Latin1, ISO-8859-1)
   - Enhanced data validation and cleaning
   - Added comprehensive error handling

4. **Improved Structure**
   - Separated email generation logic into `job_email_generator.py`
   - Enhanced error handling and user feedback
   - Added detailed logging for debugging

## Current Progress

### Implemented Features
- Gmail API integration with OAuth2 authentication
- Email draft creation functionality
- Template-based email personalization
- Batch processing for multiple recipients
- Random template selection for variety
- Error handling for API interactions

### Current Capabilities
- Scrapes job details from job posting URLs using advanced web crawling techniques
- Extracts comprehensive job information including:
  - Job title and company name
  - Technical skills and tech stack requirements
  - Required qualifications (education, experience)
  - Key responsibilities and duties
  - Domain-specific knowledge requirements
  - Any unique or important requirements
- Creates highly personalized email drafts in Gmail based on extracted job details
- Matches resume skills to job requirements for relevant personalization
- Supports multiple email templates
- Personalizes recipient names from email addresses
- Maintains OAuth tokens for persistent authentication
- Handles batch processing of recipient lists
- Provides interactive CLI for user workflow

### Technical Components
- Uses Google Gmail API for email integration
- Implements OAuth2 authentication flow
- Utilizes Crawl4AI AsyncWebCrawler for efficient web scraping
- Leverages Gemini 2.5 Flash AI for content generation and information extraction
- Implements advanced prompt engineering for detailed job information extraction
- Stores credentials in `token.pickle` and `credentials.json`
- Python-based implementation with pandas for data processing
- Fully asynchronous operation for improved performance
- Robust error handling and fallback mechanisms

### Usage
The script currently supports:
1. Scraping job details from job posting URLs collected by Chrome extension
2. Extracting structured job information using AI
3. Creating personalized draft emails based on job details and your resume
4. Storing drafts in Gmail for review before sending
5. Processing jobs individually or in batches
6. Interactive command-line interface for different workflows

### Required Files
- `main.py`: Core implementation and CLI interface
- `job_email_generator.py`: Email generation functionality
- `job_scraper.py`: Job information extraction
- `credentials.json`: Google API credentials (required)
- `token.pickle`: OAuth token storage (auto-generated)
- `.env`: Environment variables including API keys

### Required Setup

1. **Install Dependencies**
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client google.generativeai pandas python-dotenv crawl4ai
```

2. **Install Playwright Browsers** (required for Crawl4AI)
```bash
playwright install
```

2. **Configure API Credentials**
   - Place your `credentials.json` file (from Google Cloud Console) in the root directory
   - Add your API keys to `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   CRAWL4AI_API_KEY=your_crawl4ai_api_key_here
   ```

3. **Prepare Data Files**
   - Option 1: Use Chrome extension to create `contacts.csv` with:
     - employer_name
     - employer_role
     - email_id
     - job_link
   
   - Option 2: Create `job_details.csv` directly with:
     - company_name
     - job_name or job_role
     - employer_name
     - employer_role
     - email_id
     - job_description
   
   - Update your resume in `main.py`

### Next Steps
- Add email template customization options
- Implement rate limiting for API calls
- Add email tracking functionality
- Enhance resume parsing capabilities
- Add scheduling features for email sending
- Implement A/B testing for email content
- Improve web scraping robustness for more job sites
- Add follow-up email scheduling

### File Structure
- `main.py`: Main script with interactive CLI and integration
- `job_email_generator.py`: Email generation functionality
- `job_scraper.py`: Job information extraction
- `contacts.csv`: Job links and contact information
- `job_details.csv`: Extracted job details
- `credentials.json`: Google API credentials
- `.env`: Environment variables and API keys

### Usage Instructions
1. Set up all required credentials and files
2. Update your resume in `main.py`
3. Prepare your data files (either `contacts.csv` or `job_details.csv`)
4. Run the script:
```bash
python main.py
```

5. Choose an option from the interactive menu:
   - Option 1: Scrape job information from contacts CSV
   - Option 2: Generate email drafts from job details CSV
   - Option 3: Do both (scrape and generate emails)
   - Option 4: Exit

The system will:
- Scrape job details from URLs in your contacts file (if selected)
- Extract structured information using AI
- Generate personalized emails using AI
- Create drafts in your Gmail account
- Provide detailed feedback on the process
