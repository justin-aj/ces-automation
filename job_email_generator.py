from typing import Dict, Optional, List, AsyncIterator
import google.generativeai as genai
import os
import json
import csv
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class JobEmailGenerator:
    def __init__(self, your_name: str, your_role: Optional[str] = None, your_background: Optional[str] = None, 
                 resume_text: Optional[str] = None, gemini_api_key: Optional[str] = None):
        """
        Initialize the JobEmailGenerator.
        
        Args:
            your_name: Your full name
            your_role: Your current professional role
            your_background: Brief description of your professional background
            resume_text: Full text content of your resume
            gemini_api_key: API key for Gemini (optional if in .env)
        """
        print(f"\n[INIT] Initializing JobEmailGenerator for {your_name}")
        self.your_name = your_name
        self.your_role = your_role or "Professional"
        self.your_background = your_background
        self.resume_text = resume_text
        print(f"[INIT] Role: {self.your_role}")
        print(f"[INIT] Background provided: {'Yes' if your_background else 'No'}")
        print(f"[INIT] Resume text provided: {'Yes' if resume_text else 'No'}")
        
        # Configure Gemini API
        print("[INIT] Setting up Gemini API...")
        api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("[ERROR] No API key found in environment or parameters")
            raise ValueError("Gemini API key not found. Please add it to .env file or provide it directly.")
        
        print("[INIT] Configuring Gemini API...")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("[INIT] Successfully initialized Gemini model")

    def _create_prompt(self, job_details: Dict[str, str]) -> str:
        """Create a detailed prompt for Gemini to generate the email."""
        prompt = f"""You are a professional job application assistant. Generate a compelling cold email for a job application.
        Return ONLY a JSON object with 'subject' and 'body' keys, following this exact format:
        {{
            "subject": "Engaging subject line here",
            "body": "Email content here\\n\\nWith proper paragraphs"
        }}

        Use these details to craft a personalized email:

        About the Sender:
        - Name: {self.your_name}
        - Current Role: {self.your_role}
        - Professional Background: {self.your_background or 'relevant experience'}

        Detailed Resume:
        {self.resume_text if self.resume_text else "No detailed resume provided"}

        About the Job:
        - Company: {job_details.get('company_name', 'the company')}
        - Position: {job_details.get('job_role', 'the position')}
        - Recipient: {job_details.get('employer_name', 'Hiring Manager')}
        - Recipient's Role: {job_details.get('employer_role', 'Hiring Manager')}

        Full Job Description:
        {job_details.get('role_details', 'No specific requirements provided')}

        Key Instructions:
        1. Analyze the job description and identify the most relevant aspects of the sender's background
        2. Create natural connections between the sender's experience and job requirements
        3. Keep the tone professional but conversational
        4. Include a clear call to action
        5. Keep it concise (3-4 paragraphs)
        6. Make the subject line attention-grabbing but professional
        7. Avoid generic phrases like "I am writing to..."
        8. Focus on value proposition and specific relevant experience
        
        Remember: Return ONLY the JSON object with 'subject' and 'body' keys. No additional text or formatting."""
        return prompt

    async def generate_cold_email(self, job_details: Dict[str, str]) -> Dict[str, str]:
        """
        Generate a personalized cold email based on job details using Gemini API.

        Args:
            job_details: Dictionary containing:
            - employer_name: Name of the hiring manager/employer
            - employer_role: Role of the employer (e.g., "Hiring Manager", "CTO")
            - company_name: Name of the company
            - job_role: The position being applied for
            - role_details: Specific details about the job role

        Returns:
            Dict containing 'subject' and 'body' of the email
        """
        try:
            prompt = self._create_prompt(job_details)
            print("Prompt created for Gemini API:")
            print(prompt)

            # Generate email using Gemini
            response = await self.model.generate_content_async(prompt)
            print("Received response from Gemini API.")

            try:
                # Try to parse the response as JSON
                email_content = response.text.strip()
                print("Raw response text:")
                print(email_content)

                # Remove any markdown code block formatting if present
                email_content = email_content.replace('```json\n', '').replace('\n```', '')
                print("Cleaned response text for JSON parsing:")
                print(email_content)

                email_dict = json.loads(email_content)
                print("Parsed JSON response:")
                print(email_dict)

                # Validate the response format
                if not all(k in email_dict for k in ('subject', 'body')):
                    print("Invalid response format: missing 'subject' or 'body'.")
                    raise ValueError("Invalid response format")

                print("Returning generated email content.")
                return email_dict

            except (json.JSONDecodeError, ValueError):
                print("Failed to parse Gemini response as JSON. Using fallback email template.")
                return self._generate_fallback_email(job_details)

        except Exception as e:
            print(f"Error generating email with Gemini: {e}")
            print("Using fallback email template.")
            return self._generate_fallback_email(job_details)

    def _generate_fallback_email(self, job_details: Dict[str, str]) -> Dict[str, str]:
        """Generate a basic email if the AI generation fails."""
        employer_name = job_details.get('employer_name', 'Hiring Manager')
        company_name = job_details.get('company_name', 'your company')
        job_role = job_details.get('job_role', 'the open position')
        
        greeting = 'Dear Hiring Manager' if employer_name.lower() == 'hiring manager' else f'Dear {employer_name}'
        
        body = f'''{greeting},

I hope this email finds you well. I am writing to express my strong interest in the {job_role} position at {company_name}. As a {self.your_role} with {self.your_background or 'relevant experience'}, I was excited to learn about this opportunity.

I believe my background and skills make me an excellent candidate for this role, and I would welcome the opportunity to discuss how I can contribute to your team.

Thank you for considering my application. I look forward to the possibility of connecting soon.

Best regards,
{self.your_name}'''

        subject = f"Experienced {self.your_role} interested in {job_role} position"

        return {
            'subject': subject,
            'body': body
        }

    async def process_csv_file(self, csv_file_path: str) -> List[Dict[str, str]]:
        """
        Process a CSV file containing job application details and generate emails for each entry.

        Args:
            csv_file_path: Path to the CSV file containing job details.
                CSV should have headers: company_name, job_role, employer_name, employer_role, role_details

        Returns:
            List of dictionaries containing generated emails with 'subject' and 'body' keys.
        """
        csv_path = Path(csv_file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        print(f"\n[CSV] Reading job details from: {csv_file_path}")
        generated_emails = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Validate CSV headers
                required_fields = {'company_name', 'job_role', 'employer_name', 'employer_role', 'role_details', 'email_id'}
                missing_fields = required_fields - set(reader.fieldnames)
                if missing_fields:
                    raise ValueError(f"Missing required columns in CSV: {', '.join(missing_fields)}")

                # Process each row
                for row_num, row in enumerate(reader, 1):
                    print(f"\n[CSV] Processing row {row_num}: {row['company_name']} - {row['job_role']}")
                    try:
                        email = await self.generate_cold_email(row)
                        generated_emails.append({
                            'company': row['company_name'],
                            'position': row['job_role'],
                            'email': email,
                            'email_id': row['email_id']  # Include the email ID from CSV
                        })
                        print(f"[CSV] Successfully generated email for {row['company_name']}")
                    except Exception as e:
                        print(f"[ERROR] Failed to generate email for row {row_num}: {e}")
                        continue

        except Exception as e:
            print(f"[ERROR] Error processing CSV file: {e}")
            raise

        print(f"\n[CSV] Completed processing {len(generated_emails)} job applications")
        return generated_emails

    async def save_generated_emails(self, emails: List[Dict[str, str]], output_dir: str) -> None:
        """
        Save generated emails to individual text files.

        Args:
            emails: List of dictionaries containing generated emails and metadata
            output_dir: Directory where email files will be saved
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\n[SAVE] Saving generated emails to: {output_dir}")
        
        for idx, email_data in enumerate(emails, 1):
            company = email_data['company'].replace(' ', '_')
            position = email_data['position'].replace(' ', '_')
            filename = f"{company}_{position}_{idx}.txt"
            file_path = output_path / filename

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"To: {email_data['email_id']}\n")  # Add recipient email
                    f.write(f"Subject: {email_data['email']['subject']}\n\n")
                    f.write(email_data['email']['body'])
                print(f"[SAVE] Saved email for {company} to: {filename}")
            except Exception as e:
                print(f"[ERROR] Failed to save email for {company}: {e}")

        print(f"\n[SAVE] Successfully saved {len(emails)} emails to {output_dir}")


