import os
from dotenv import load_dotenv
from src.models import JobPost, Company
from src.espo_client import EspoClient
from src.db import JobDatabase
from src.filters import filter_job
from src.scrapers.hn_hiring import HNHiringScraper

load_dotenv("config/.env")

espo = EspoClient(
    base_url=os.getenv("ESPO_URL", "http://192.168.68.68:8080"),
    username=os.getenv("ESPO_USER", "admin"),
    password=os.getenv("ESPO_PASS", "password"),
)
db = JobDatabase()


def get_scraper(source: str):
    scrapers = {"hn_hiring": HNHiringScraper()}
    return scrapers.get(source)


def load_filter_config() -> dict:
    import yaml

    try:
        with open("config/filters.yaml") as f:
            return yaml.safe_load(f) or {}
    except:
        return {}


def sync_to_crm(job: JobPost) -> bool:
    """Sync job to CRM as Opportunity. Returns True on success, False on failure."""
    try:
        # Find or create Account (company)
        account = espo.find_account(job.company_name)
        if account:
            account_id = account["id"]
        else:
            company = Company(
                name=job.company_name,
                website=job.company_website,
                description=f"Tech: {', '.join(job.tech_stack)}",
            )
            account_id = espo.create_account(company)

        # Create Opportunity (job application)
        opportunity_id = espo.create_opportunity(job, account_id)

        # Log sync
        db.mark_synced(job.source, job.source_id, account_id, opportunity_id)
        return True
    except Exception as e:
        print(f"  Error syncing {job.company_name}: {e}")
        return False


def run_pipeline(sources: list[str], dry_run: bool = False):
    filter_config = load_filter_config()
    synced = 0
    failed = 0

    for source in sources:
        scraper = get_scraper(source)
        if not scraper:
            print(f"Unknown source: {source}")
            continue

        print(f"Scraping {source}...")
        jobs = scraper.scrape()
        print(f"Found {len(jobs)} jobs")

        for job in jobs:
            if not filter_job(job, filter_config):
                continue
            if db.is_duplicate(job):
                continue

            db.save_job(job)

            if dry_run:
                print(f"[DRY RUN] Would sync: {job.company_name} - {job.title}")
                synced += 1
            else:
                if sync_to_crm(job):
                    print(f"Synced: {job.company_name} - {job.title}")
                    synced += 1
                else:
                    failed += 1

    if not dry_run:
        print(f"\nDone: {synced} synced, {failed} failed")
