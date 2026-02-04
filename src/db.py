import sqlite_utils
from datetime import datetime
from typing import Optional
from src.models import JobPost


class JobDatabase:
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db = sqlite_utils.Database(db_path)
        self._init_tables()

    def _init_tables(self):
        if "jobs" not in self.db.table_names():
            self.db["jobs"].create(
                {
                    "source": str,
                    "source_id": str,
                    "source_url": str,
                    "company_name": str,
                    "title": str,
                    "data": str,  # JSON
                    "scraped_at": str,
                    "synced_at": str,
                    "account_id": str,
                    "contact_id": str,
                },
                pk=["source", "source_id"],
            )

    def save_job(self, job: JobPost):
        self.db["jobs"].insert(
            {
                "source": job.source,
                "source_id": job.source_id,
                "source_url": job.source_url,
                "company_name": job.company_name,
                "title": job.title,
                "data": job.model_dump_json(),
                "scraped_at": datetime.now().isoformat(),
                "synced_at": None,
                "account_id": None,
                "contact_id": None,
            },
            replace=True,
        )

    def get_job(self, source: str, source_id: str) -> Optional[dict]:
        try:
            return self.db["jobs"].get((source, source_id))
        except:
            return None

    def is_duplicate(self, job: JobPost) -> bool:
        return self.get_job(job.source, job.source_id) is not None

    def mark_synced(self, source: str, source_id: str, account_id: str, contact_id: str):
        self.db["jobs"].update(
            (source, source_id),
            {
                "synced_at": datetime.now().isoformat(),
                "account_id": account_id,
                "contact_id": contact_id,
            },
        )

    def get_unsynced_jobs(self) -> list[dict]:
        return list(self.db["jobs"].rows_where("synced_at is null"))
