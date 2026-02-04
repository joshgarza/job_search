import pytest
import tempfile
import os


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    os.unlink(db_path)


class TestJobStorage:
    def test_save_and_retrieve_job(self, temp_db, sample_job_data):
        from src.db import JobDatabase
        from src.models import JobPost

        db = JobDatabase(temp_db)
        job = JobPost(**sample_job_data)

        db.save_job(job)
        retrieved = db.get_job(job.source, job.source_id)

        assert retrieved is not None
        assert retrieved["company_name"] == "Acme Corp"

    def test_is_duplicate(self, temp_db, sample_job_data):
        from src.db import JobDatabase
        from src.models import JobPost

        db = JobDatabase(temp_db)
        job = JobPost(**sample_job_data)

        assert db.is_duplicate(job) == False
        db.save_job(job)
        assert db.is_duplicate(job) == True

    def test_mark_synced(self, temp_db, sample_job_data):
        from src.db import JobDatabase
        from src.models import JobPost

        db = JobDatabase(temp_db)
        job = JobPost(**sample_job_data)
        db.save_job(job)

        db.mark_synced(job.source, job.source_id, "acc123", "contact456")
        retrieved = db.get_job(job.source, job.source_id)

        assert retrieved["synced_at"] is not None
        assert retrieved["account_id"] == "acc123"
