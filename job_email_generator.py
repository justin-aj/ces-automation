import json
from typing import Dict, Optional, List, AsyncIterator
import google.generativeai as genai
import os

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
        prompt = f"""You are a professional email writer crafting a concise, skill-focused cold email. 
        Generate a direct email that clearly presents {self.your_name}'s relevant qualifications for the role. 
        Make sure it is catchy and to the point. Do not invent or assume any qualifications or experiences not explicitly mentioned in the information provided.
        Return ONLY a JSON object with 'subject' and 'body' keys, following this exact format:
        {{
            "subject": "Direct subject line highlighting key skill match (1-min read)",
            "body": "Hi {job_details.get('employer_name', 'Hiring Manager')},\\n\\nConcise email content focusing on relevant skills\\n\\nBrief, clear paragraphs\\n\\nBest regards,\\n{self.your_name}"
        }}

        Candidate Information:
        - Name: {self.your_name}
        - Current Role: {self.your_role}
        - Background: {self.your_background or 'relevant experience'}

        Relevant Experience:
        {self.resume_text if self.resume_text else "No detailed resume provided"}

        Position Details:
        - Role: {job_details.get('job_role', 'the position')}
        - Company: {job_details.get('company_name', 'the company')}
        - Contact: {job_details.get('employer_name', 'Hiring Manager')}
        - Contact Role: {job_details.get('employer_role', 'Hiring Manager')}

        Job Requirements:
        {job_details.get('role_details', 'No specific requirements provided')}

        Email Requirements:
        1. BREVITY - Keep email less than 150 words total
        2. RELEVANCE - Only mention skills and experience EXPLICITLY stated in the candidate information or resume text
        3. SPECIFICS - Use ONLY verifiable numbers and examples provided in the candidate information
        4. DIRECT TONE - Professional and straightforward, no unnecessary praise or flattery
        5. CLEAR FORMAT - Short paragraphs, bullet points for skills if appropriate
        6. READ TIME - Subject line must include "(1-min read)" exactly as written
        7. FORMAT - Must start with "Hi [Name]," and end with either "Best regards," or "Sincerely," followed by name
        8. MANDATORY CLOSING - Every email MUST end with exactly these two sentences:
           - "I'd welcome the opportunity for a brief call to discuss the role in more detail."
           - "If you're not the designated hiring manager for this role, could you please connect me with the appropriate hiring manager or HR?"

        Structure:
        - Greeting: Must start with "Hi [Name]," (use exact name provided in contact information)
        - First Line: State the exact position name and ONE most relevant qualification (must be from provided information)
        - Body: List ONLY 2-3 specific achievements or skills that are EXPLICITLY mentioned in the candidate information
        - Close: Use EXACTLY these two closing sentences without modification:
          * "I'd welcome the opportunity for a brief call to discuss the role in more detail."
          * "If you're not the designated hiring manager for this role, could you please connect me with the appropriate hiring manager or HR?"
        - Signature: Must end with "Best regards," or "Sincerely," followed by the exact candidate name on a new line
        
        Key Points:
        1. DO NOT invent or assume ANY skills, experiences, or achievements not explicitly stated in the provided information
        2. NO company praise or statements about being passionate/excited
        3. ONLY mention skills/achievements that are EXPLICITLY provided in the candidate information or resume text
        4. Use EXACTLY ONE of these closing sentences without modification:
           * "I'd welcome the opportunity for a brief call to discuss the role in more detail."
           * "If you're not the designated hiring manager for this role, could you please connect me with the appropriate hiring manager or HR?"
        5. Subject line MUST include "(1-min read)" exactly as written
        6. Use simple, clear language and avoid technical jargon unless it appears in the job requirements
        7. Limit paragraphs to 1-2 sentences for easy scanning
        8. Do NOT mention or imply any information that isn't explicitly provided

        
        CRITICAL INSTRUCTION: ONLY use information explicitly provided. DO NOT invent qualifications, experiences, or achievements. When in doubt, be general rather than specific.
        
        Return ONLY the JSON object with 'subject' and 'body' keys. No fluff, just relevant qualifications and experience.
        
        General Instructions:
        Write like a confident, clear thinking human speaking to another smart human.
        Avoid robotic phrases like 'in today's fast-paced world', 'leveraging synergies', or 'furthermore'.
        Skip unnecessary dashes (—), quotation marks (“”), and corporate buzzwords like 'cutting-edge', 'robust', or 'seamless experience'.

        No AI tone. No fluff. No filler.
        Use natural transitions like 'here's the thing', 'let's break it down', or 'what this really means is…'
        Keep sentences varied in length and rhythm, like how real people speak or write.
        Prioritize clarity, personality, and usefulness. Every sentence should feel intentional, not generated.
        """
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


