import pytest
from unittest.mock import Mock, patch


class TestPipeline:
    def test_dry_run_does_not_sync(self, sample_job_data):
        from src.models import JobPost
        from src.pipeline import run_pipeline

        mock_scraper = Mock()
        mock_scraper.scrape.return_value = [JobPost(**sample_job_data)]

        with patch("src.pipeline.get_scraper", return_value=mock_scraper):
            with patch("src.pipeline.sync_to_crm") as mock_sync:
                with patch("src.pipeline.db"):
                    run_pipeline(["hn_hiring"], dry_run=True)
                    mock_sync.assert_not_called()

    def test_sync_creates_account_and_opportunity(self, sample_job_data):
        from src.models import JobPost
        from src.pipeline import sync_to_crm

        job = JobPost(**sample_job_data)

        with patch("src.pipeline.espo") as mock_espo:
            mock_espo.find_account.return_value = None
            mock_espo.create_account.return_value = "acc123"
            mock_espo.create_opportunity.return_value = "opp456"

            with patch("src.pipeline.db"):
                sync_to_crm(job)

            mock_espo.create_account.assert_called_once()
            mock_espo.create_opportunity.assert_called_once()

    def test_sync_uses_existing_account(self, sample_job_data):
        from src.models import JobPost
        from src.pipeline import sync_to_crm

        job = JobPost(**sample_job_data)

        with patch("src.pipeline.espo") as mock_espo:
            mock_espo.find_account.return_value = {"id": "existing123"}
            mock_espo.create_opportunity.return_value = "opp456"

            with patch("src.pipeline.db"):
                sync_to_crm(job)

            mock_espo.create_account.assert_not_called()
            mock_espo.create_opportunity.assert_called_once()

    def test_pipeline_continues_when_scraper_fails(self, sample_job_data):
        from src.models import JobPost
        from src.pipeline import run_pipeline

        # First scraper fails, second succeeds
        failing_scraper = Mock()
        failing_scraper.scrape.side_effect = RuntimeError("Scraper failed")

        working_scraper = Mock()
        working_scraper.scrape.return_value = [JobPost(**sample_job_data)]

        def mock_get_scraper(source):
            if source == "failing":
                return failing_scraper
            elif source == "working":
                return working_scraper
            return None

        with patch("src.pipeline.get_scraper", side_effect=mock_get_scraper):
            with patch("src.pipeline.db") as mock_db:
                mock_db.is_duplicate.return_value = True  # Skip actual processing
                # Should not raise, pipeline continues
                run_pipeline(["failing", "working"], dry_run=True)

        # Both scrapers should have been called
        failing_scraper.scrape.assert_called_once()
        working_scraper.scrape.assert_called_once()
