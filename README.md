# Cold Email Automation Project

Last Updated: August 8, 2025

## Latest Updates

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
- Creates personalized email drafts in Gmail
- Supports multiple email templates
- Personalizes recipient names from email addresses
- Maintains OAuth tokens for persistent authentication
- Handles batch processing of recipient lists

### Technical Components
- Uses Google Gmail API
- Implements OAuth2 authentication flow
- Stores credentials in `token.pickle` and `credentials.json`
- Python-based implementation

### Usage
The script currently supports:
1. Creating draft emails for a list of recipients
2. Using randomized templates for content variety
3. Personalizing messages with recipient names
4. Storing drafts in Gmail for review before sending

### Required Files
- `main.py`: Core implementation
- `credentials.json`: Google API credentials (required)
- `token.pickle`: OAuth token storage (auto-generated)

### Required Setup

1. **Install Dependencies**
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client google.generativeai pandas python-dotenv
```

2. **Configure API Credentials**
   - Place your `credentials.json` file (from Google Cloud Console) in the root directory
   - Add your Gemini API key to `.env` file:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

3. **Prepare Data Files**
   - Create `sample_jobs.csv` with required columns:
     - company_name
     - job_role
     - employer_name
     - employer_role
     - role_details
     - email_id
   - Update your resume in `main.py`

### Next Steps
- Add email template customization options
- Implement rate limiting for API calls
- Add email tracking functionality
- Enhance resume parsing capabilities
- Add scheduling features for email sending
- Implement A/B testing for email content

### File Structure
- `main.py`: Main script with resume and execution logic
- `job_email_generator.py`: Core email generation functionality
- `sample_jobs.csv`: Job application details
- `credentials.json`: Google API credentials
- `.env`: Environment variables and API keys

### Usage Instructions
1. Set up all required credentials and files
2. Update your resume in `main.py`
3. Prepare your job applications in `sample_jobs.csv`
4. Run the script:
```bash
python main.py
```

The system will:
- Read and validate your job applications
- Generate personalized emails using AI
- Create drafts in your Gmail account
- Provide detailed feedback on the process
