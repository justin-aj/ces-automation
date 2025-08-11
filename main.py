import os
import pickle
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText
from typing import List, Dict, Optional, Union
from job_email_generator import JobEmailGenerator
from job_scraper import JobScraper

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

async def scrape_job_info(contacts_csv_path: str, output_dir: Optional[str] = None) -> str:
    """
    Scrape job information from links in a contacts CSV file.
    
    Args:
        contacts_csv_path: Path to the contacts CSV file with job links
        output_dir: Directory to save results (optional)
        
    Returns:
        Path to the generated job details CSV file
    """
    try:
        print(f"\n[JOB SCRAPER] Starting job scraper for: {contacts_csv_path}")
        
        # Initialize scraper
        scraper = JobScraper()
        
        # Process the contacts CSV to extract job details
        results_df = await scraper.process_contacts_csv(contacts_csv_path)
        
        # Save the results
        save_info = scraper.save_results(results_df, output_dir)
        
        print(f"\n[JOB SCRAPER] Job scraping completed successfully!")
        print(f"[JOB SCRAPER] Processed {save_info['record_count']} entries")
        print(f"[JOB SCRAPER] Results saved to:")
        print(f"- CSV: {save_info['csv_path']}")
        print(f"- JSON: {save_info['json_path']}")
        
        return save_info['csv_path']
    
    except Exception as e:
        print(f"[JOB SCRAPER] Error: {e}")
        raise

async def main():
    print("\n===== COLD EMAIL AUTOMATION SYSTEM =====\n")
    
    # Create resume text - you can also load this from a file
    resume_text = """Ajin Frank Justin
857-356-5917 | ajinfrankj@gmail.com | linkedin.com/in/ajin-frank-j | portfolio | github.com/justin-aj | HuggingFace | Open to Relocation

Education
Northeastern University – Boston, MA
Master of Science in Data Science | GPA: 4.0/4.0 | Sep 2024 – May 2026 (Expected)

Coursework: Data Mining, Machine Learning, Deep Learning, MLOps, Natural Language Processing, Data Analytics & Engineering, Data Management & Processing, Artificial General Intelligence

REVA University – Bangalore, India
Bachelor of Technology, Computer Engineering | GPA: 9.11/10 | Jun 2019 – Jul 2023

Technical Skills
Languages & Databases: Python (5 yrs, Advanced), SQL (3 yrs, Advanced), C++, C#, GoLang, PostgreSQL, MySQL, MongoDB, SparkSQL, Azure SQL, Pinecone, DuckDB, OLAP, OLTP, BigQuery
Data Processing & Engineering: pandas, NumPy, PySpark, Spark, MapReduce, Hadoop, Hive, Kafka, Airflow, EventHubs, dbt, Delta Lake, Databricks, Apache Flink
ML/AI & Analytics: Transformers, PyTorch, scikit-learn, TensorFlow, OpenCV, AI Agents, LSTM, LangChain, LangGraph, Diffusion Models, Hugging Face, NLP, PEFT, QLoRA, ARIMA, Prophet
Visualization & BI Tools: Matplotlib, Seaborn, Plotly, Power BI, Tableau, Excel
Cloud & MLOps: AWS (S3, Redshift), Azure (Data Factory, Blob Storage), GCP (BigQuery, VertexAI), Docker, Kubernetes, MLFlow, Terraform, GitHub Actions, BitBucket, Grafana
Web Frameworks: Flask, Django, FastAPI, Streamlit, ASP.NET
Big Data Formats: Parquet, Avro
Methodologies: Data Modeling, Data Warehousing, Data Lakes, Scrum, Agile

Experience
Machine Learning / Data Science / Data Analytics Intern – Summer 2025
AARP – Washington DC, USA | Jun 2025 – Present

Developed scalable ML model performance monitoring dashboard in Databricks (PySpark, SQL) to process large volumes of prediction logs, tracking 10+ KPIs across 25+ production models (Logistic Regression, Random Forest, Boosting).

Automated ETL workflows to ingest and aggregate model outputs, enabling real-time diagnostics and improved model governance.

Conducted residual diagnostics, probability calibration, temporal performance drift analysis for 20+ production use cases.

Integrated statistical thresholds for data/model drift detection, triggering automated alerts and reducing drift incidents by 40%.

Delivered insights for model selection and retraining cycles, improving model stability and reducing prediction error by 20%.

Graduate Research Assistant
D’Amore-McKim School of Business, Northeastern University – Boston, USA | Jan 2025 – Apr 2025

Built an NLP ETL pipeline (Airflow, RegEx, NLTK, spaCy) to preprocess 2000+ financial filings for ML and analytics workflows.

Created a robust PDF/TXT parser (PyMuPDF, RegEx) to extract entities and structure financial text for compliance tracking.

Benchmarked LLMs (Gemini, Claude, GPT-4) on 10-class financial classification, achieving 0.86+ F1-scores.

Automated feature extraction, integrating outputs into analytics pipelines for trend analysis and reporting.

Data Engineer / Data Analytics Engineer
Dynapac, Fayat Group – Bangalore, India | Jun 2023 – Jun 2024

Restructured Dyn@Lyzer’s multi-join PostgreSQL telemetry GIS database into a partitioned, normalized schema.

Conducted ARIMA-based time series forecasting on fuel efficiency data, improving operational ROI by 20%.

Designed ETL orchestrator to process 300M+ telemetry records from 1000+ nodes, transforming raw data into JSON via Azure Durable Functions and loading into Azure Blob Storage.

Built interactive Tableau & Power BI dashboards to visualize GIS patterns, operational KPIs, and fuel trends for executive decision-making.

Data Analytics Intern – Mar 2023 – May 2023

Developed data ingestion pipeline to transform JSON into Azure Event Hubs, implementing partition keys for parallel streaming.

Projects
AskNEU – Retrieval-Augmented Generation System | LangChain, LangGraph, Docker, Pinecone, GCP, Cohere | [link] | Jan 2025 – Apr 2025

Architected RAG system with Cohere reranking and Complex Retrieval Framework (query decomposition, context unification) using GPT-4.1 and Gemini APIs.

Scraped 50,000+ NEU web pages via Selenium, chunked data, embedded using LangChain, and stored in Pinecone vector DB for semantic search.

Scaled with Docker, Kubernetes, Airflow DAGs, Terraform, CI/CD via GitHub Actions; monitored with Grafana.

AI Banking Assistant | Transformers, PEFT, Hugging Face, PyTorch | [link] | Dec 2024 – Jan 2025

Built QA and conditional text generation tasks with 25,000+ QA pairs.

Fine-tuned T5-small, GPT2-small, DistilBERT via QLoRA (4-bit quantization) and benchmarked Falcon-7B.

Achieved BLEU 0.25, ROUGE-1 F1 0.54 on NVIDIA V100 GPU, indicating strong text generation performance.

Amazon Product Sales Analysis – Tableau Dashboard | pandas, NumPy, Tableau | Dec 2024 – Jan 2025

Preprocessed and transformed 2M+ rows for KPI tracking and visualization.

Forecasted sales with ARIMA & Prophet, improving accuracy by 22%; implemented customer segmentation, boosting campaign response by 20%.

Identified underperforming SKUs, improving stock turnover by 15%.

Food Categorization using Machine Learning | sklearn, Random Forest, TF-IDF, PCA | [link] | Oct 2024 – Dec 2024

Classified USDA food products into 70+ categories with 91.98% accuracy and 91.87% F1-score on 1.7M entries.

Optimized with TF-IDF vectorization, PCA, and A/B testing; derived insights for nutrition and inventory management using hypothesis testing & ANOVA.
"""  # Replace with your actual resume text

    email_generator = JobEmailGenerator(
        your_name="Ajin Frank Justin",
        your_role="Data Scientist",
        resume_text=resume_text  # Now passing the full resume text
    )
    
    # Main menu
    while True:
        print("\nChoose an option:")
        print("1. Scrape job information from contacts CSV")
        print("2. Generate email drafts from job details CSV")
        print("3. Do both (Scrape jobs and generate emails)")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            # Scrape job information
            contacts_csv = "contacts.csv"  # Default name
                
            output_dir = input("Enter output directory (leave empty for current directory): ").strip()
            
            try:
                job_details_csv = await scrape_job_info(contacts_csv, output_dir)
                print(f"\nJob details saved to: {job_details_csv}")
            except Exception as e:
                print(f"\nError during job scraping: {e}")
            
        elif choice == '2':
            # Generate email drafts
            job_details_csv = input("\nEnter path to job details CSV file: ").strip()
            if not job_details_csv:
                job_details_csv = "job_details.csv"  # Default name
            
            try:
                jobs = await read_jobs_from_csv(job_details_csv)
                print(f"\nFound {len(jobs)} job applications in CSV file")
                
                # Generate and save email drafts
                drafts = await save_email_drafts(jobs, email_generator)
                print(f'\nSuccessfully created {len(drafts)} email drafts')
                
                # Print details of created drafts
                for i, (job, draft) in enumerate(zip(jobs, drafts), 1):
                    print(f"\nDraft {i}:")
                    print(f"Company: {job.get('company_name', 'Unknown')}")
                    print(f"Position: {job.get('job_name', job.get('job_role', 'Unknown'))}")
                    print(f"Draft ID: {draft['id']}")
                    
            except FileNotFoundError:
                print(f"\nError: {job_details_csv} file not found.")
            except ValueError as e:
                print(f"\nError with CSV file: {e}")
            except Exception as e:
                print(f"\nAn error occurred: {e}")
        
        elif choice == '3':
            # Do both: scrape and generate emails
            contacts_csv = "contacts.csv"  # Default name
                
            output_dir = input("Enter output directory (leave empty for current directory): ").strip()
            
            try:
                # First scrape job information
                job_details_csv = await scrape_job_info(contacts_csv, output_dir)
                print(f"\nJob details saved to: {job_details_csv}")
                
                # Then generate emails
                jobs = await read_jobs_from_csv(job_details_csv)
                print(f"\nFound {len(jobs)} job applications in CSV file")
                
                # Generate and save email drafts
                drafts = await save_email_drafts(jobs, email_generator)
                print(f'\nSuccessfully created {len(drafts)} email drafts')
                
                # Print details of created drafts
                for i, (job, draft) in enumerate(zip(jobs, drafts), 1):
                    print(f"\nDraft {i}:")
                    print(f"Company: {job.get('company_name', 'Unknown')}")
                    print(f"Position: {job.get('job_name', job.get('job_role', 'Unknown'))}")
                    print(f"Draft ID: {draft['id']}")
                    
            except Exception as e:
                print(f"\nError during processing: {e}")
        
        elif choice == '4':
            print("\nExiting the Cold Email Automation System. Goodbye!")
            break
        
        else:
            print("\nInvalid choice. Please select a number between 1 and 4.")
            


if __name__ == '__main__':
    asyncio.run(main())
