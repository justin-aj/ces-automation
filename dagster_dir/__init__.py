from dagster import Definitions, load_assets_from_modules, define_asset_job
from dagster import AssetSelection
from dagster import ScheduleDefinition

import sys
from pathlib import Path

# Add parent directory to sys.path to find modules
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import local modules - fixed to avoid circular imports
from dagster_dir import assets  # This needs to be done after sys.path is updated
from dagster_dir.resources import GeminiResource, CrawlAIResource, ResumeResource


# Define asset jobs
scrape_job = define_asset_job(
    name="scrape_jobs",
    selection=AssetSelection.groups("input_data", "tracking", "job_scraping"),
    description="Scrape job details from links",
)

email_job = define_asset_job(
    name="generate_emails",
    selection=AssetSelection.groups("email_generation"),
    description="Generate cold emails for job applications and create Gmail drafts",
)

report_job = define_asset_job(
    name="generate_report",
    selection=AssetSelection.groups("reporting"),
    description="Generate job tracking report",
)

full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Run the full cold email automation pipeline",
)

# Define schedules (commented out as user prefers on-demand)
# daily_schedule = ScheduleDefinition(
#     name="daily_scrape",
#     cron_schedule="0 9 * * *",  # 9 AM daily
#     job=scrape_job,
#     execution_timezone="America/New_York",
# )

# Define the Dagster repository
defs = Definitions(
    assets=load_assets_from_modules([assets]),
    jobs=[scrape_job, email_job, report_job, full_pipeline_job],
    # schedules=[daily_schedule],  # Uncomment to enable scheduling
    resources={
        "gemini": GeminiResource(),
        "crawl4ai": CrawlAIResource(),
        "resume": ResumeResource(),
    },
)
