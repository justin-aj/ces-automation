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
                message['to'] = job.get('email_id', job.get('email'))  # Use email_id from CSV if available, fallback to old email field
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

async def read_jobs_from_csv(csv_path: str) -> List[Dict[str, str]]:
    """
    Read job applications from a CSV file using pandas.
    
    Args:
        csv_path: Path to the CSV file containing job details
    Returns:
        List of dictionaries containing job application details
    """
    import pandas as pd
    from pathlib import Path
    
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    try:
        # Try reading with different encodings
        for encoding in ['utf-8', 'cp1252', 'latin1', 'iso-8859-1']:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                print(f"Successfully read CSV using {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Could not read the CSV file with any of the attempted encodings")
        
        # Check for required columns
        required_fields = {'company_name', 'job_role', 'employer_name', 'employer_role', 'role_details', 'email_id'}
        missing_fields = required_fields - set(df.columns)
        if missing_fields:
            raise ValueError(f"Missing required columns in CSV: {', '.join(missing_fields)}")
        
        # Clean the data
        # Remove any leading/trailing whitespace and replace empty strings with None
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        df = df.replace(r'^\s*$', None, regex=True)
        
        # Convert DataFrame to list of dictionaries
        jobs = df.to_dict('records')
        
        if not jobs:
            raise ValueError("No jobs found in the CSV file")
            
        print(f"Successfully loaded {len(jobs)} jobs from CSV")
        return jobs
        
    except pd.errors.EmptyDataError:
        raise ValueError("The CSV file is empty")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {str(e)}")

async def main():
    # Create an email generator instance with resume
    resume_text = """Ajin Frank Justin
857-356-5917 | ajinfrankj@gmail.com | linkedin.com/in/ajin-frank-j | portfolio | github/justin-aj | huggingface
Education
Northeastern University Sep 2024 - May 2026 (Expected)
Master of Science in Data Science GPA: 4.0/4.0
• Coursework: Data Mining, Machine Learning, Deep Learning, MLOps, Natural Language Processing
REVA University Jun 2019 - Jul 2023
Bachelor of Technology, Computer Engineering GPA: 9.11/10
Technical Skills
ML/AI: Transformers, PyTorch, sklearn, OpenCV, AI Agents, LSTM, LangChain, Diffusion, LangGraph, Hugging Face
Languages: Python (Advanced - 5yrs), SQL (Advanced - 3yrs), C#/C/C++ (Intermediate), GoLang
Data Processing: pandas, NumPy, PySpark, MapReduce, Excel, EventHubs, Airflow, Kafka, Snowflake, Databricks, dbt
Cloud/MLOps: Azure, AWS, GCP, VertexAI, Docker, Kubernetes, MLFlow, Terraform, GitHub Actions, BitBucket
Visualization/Web Frameworks: Matplotlib, PowerBI, Tableau, Django, FastAPI, Flask, ASP.Net, Streamlit
Databases: PostgreSQL, MongoDB, MySQL, SparkSQL, Azure SQL, Pinecone, OLAP, OLTP, DuckDB, BigQuery
Experience
Data Science Intern - Summer 2025 Jun 2025 – Present
AARP Washington DC, USA
• Developed ML model performance monitoring dashboard in Databricks using PySpark, SQL for scalable data
processing, tracking 10+ performance indicators across 25 production models.
• Conducted research of historical model scores across Logistic Regression, Random Forest, Boosting models for 20+
production use cases, focusing on residual diagnostics, probability calibration, temporal performance drift.
• Integrated statistical-threshold for data/model drift detection, triggering alerts, reducing drift incidents by 40%.
• Enabled informed model selection, improved model stability, achieving a 20% reduction in prediction error.
Graduate Research Assistant Jan 2025 – Apr 2025
D’Amore-Mckim School of Business, Northeastern University Boston, USA
• Built an NLP ETL pipeline (RegEx, NLTK, spaCy) to preprocess 2000+ financial filings, for downstream ML.
• Created a robust PDF/TXT parser (PyMuPDF, RegEx) to extract entities and structure financial text.
• Benchmarked LLMs (Gemini, Claude, GPT-4) achieving 0.86+ F1 in 10-class financial classification.
Data Engineer Jun 2023 – Jun 2024
Dynapac, Fayat Group [Manager Recommendations] Bangalore, India
• Restructured Dyn@Lyzer multi-join PostgreSQL telemetry database into partitioned, normalized schema.
• Conducted time series forecasting on fuel data using ARIMA models, improving operational ROI by 20%.
• Architected a ETL pipeline orchestrator to handle 300M+ records from 1000+ nodes, transform raw data into
structured JSON via batch processing with Azure Durable Functions and load to Azure Blob Storage.
Projects
AskNEU RAG System | RAG, LangChain, Docker, Pinecone, GCP [link] Jan 2025 – Apr 2025
• Architected RAG system with Cohere reranking, direct and Complex Retrieval Framework of documents with
query decomposition, context unification using GPT-4.1, Gemini 2.0 APIs and LangGraph for workflow.
• Engineered automated data pipeline to scrape 50,000+ NEU sites using Selenium, chunking, ingest embeddings
into Pinecone vector database with LangChain wrappers to support semantic search enabled knowledge base.
• Ensured scalability with Docker containers, orchestrating ETL data pipeline(Airflow DAGs), GitHub Actions for
CI/CD, leveraging Kubernetes clusters with terraform for automated deployment, Grafana for monitoring.
AI Banking Assistant | transformers, peft, huggingface, pytorch [link] Dec 2024 – Jan 2025
• Architected question answering and conditional generation tasks, processing 25000+ QA pairs.
• Fine-tuned T5-small, GPT2-small, DistilBERT using PEFT(QLoRA) with 4-bit quantization.
• Achieved a BLEU score of 0.25 and ROUGE-1 F1 score of 0.54 indicating strong model performance in text
generation tasks by fine-tuning and benchmarking a Falcon-7B-based model on NVIDIA v100 GPU CUDA.
Food Categorization using Machine Learning | sklearn, Random Forest [link] Oct 2024 – Dec 2024
• Developed an automated machine learning system to categorize food products using data from the USDA.
• Applied Logistic Regression and Random Forest, achieving 91.98% accuracy, 91.87% F1-Score on 1.7M entries.
Enhanced performance through TF-IDF vectorization, PCA dimensionality reduction, A/B testing.
• Derived statistical insights for nutrition, inventory management, leveraging hypothesis testing, ANOVA.
"""  # Replace with your actual resume text

    email_generator = JobEmailGenerator(
        your_name="Ajin Frank Justin",
        your_role="Data Scientist",
        resume_text=resume_text  # Now passing the full resume text
    )
    
    # Read jobs from CSV file
    try:
        jobs = await read_jobs_from_csv('sample_jobs.csv')
        print(f"Found {len(jobs)} job applications in CSV file")
        
        # Generate and save email drafts for all jobs
        drafts = await save_email_drafts(jobs, email_generator)
        print(f'Successfully created {len(drafts)} email drafts')
        
        # Print details of created drafts
        for i, (job, draft) in enumerate(zip(jobs, drafts), 1):
            print(f"\nDraft {i}:")
            print(f"Company: {job['company_name']}")
            print(f"Position: {job['job_role']}")
            print(f"Draft ID: {draft['id']}")
            
    except FileNotFoundError:
        print("Error: sample_jobs.csv file not found. Please create it with the required columns:")
        print("company_name, job_role, employer_name, employer_role, role_details, email_id")
    except ValueError as e:
        print(f"Error with CSV file: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    asyncio.run(main())
