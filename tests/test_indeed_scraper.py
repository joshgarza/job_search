import pytest
from unittest.mock import patch, MagicMock


SAMPLE_JSEARCH_RESPONSE = {
    "status": "OK",
    "data": [
        {
            "job_id": "abc123",
            "job_title": "Software Engineer",
            "employer_name": "Tech Corp",
            "employer_website": "https://techcorp.com",
            "job_city": "San Francisco",
            "job_state": "CA",
            "job_country": "US",
            "job_description": "We are looking for a Python developer with experience in AWS and Kubernetes.",
            "job_is_remote": True,
            "job_apply_link": "https://example.com/apply/abc123",
            "job_posted_at_datetime_utc": "2024-01-15T10:00:00.000Z",
        },
        {
            "job_id": "def456",
            "job_title": "Backend Developer",
            "employer_name": "Startup Inc",
            "employer_website": None,
            "job_city": "Remote",
            "job_state": None,
            "job_country": "US",
            "job_description": "React and Node.js position. Work from home available.",
            "job_is_remote": False,  # Not marked remote, but description says WFH
            "job_apply_link": "https://example.com/apply/def456",
            "job_posted_at_datetime_utc": None,
        },
    ],
}


class TestIndeedScraper:
    def test_parses_search_results(self):
        from src.scrapers.indeed import IndeedScraper

        scraper = IndeedScraper(api_key="test_key")
        jobs = scraper._parse_response(SAMPLE_JSEARCH_RESPONSE)

        assert len(jobs) == 2
        assert jobs[0]["source_id"] == "abc123"
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[0]["company_name"] == "Tech Corp"
        assert jobs[0]["remote"] == True

    def test_builds_search_url(self):
        from src.scrapers.indeed import IndeedScraper

        scraper = IndeedScraper(api_key="test_key")
        url, params = scraper._build_request(query="python developer", remote=True)

        assert "jsearch" in url.lower() or "rapidapi" in url.lower()
        assert "python developer" in params.get("query", "")

    def test_extracts_location(self):
        from src.scrapers.indeed import IndeedScraper

        scraper = IndeedScraper(api_key="test_key")
        jobs = scraper._parse_response(SAMPLE_JSEARCH_RESPONSE)

        assert jobs[0]["location"] == "San Francisco, CA"
        assert jobs[1]["location"] == "Remote"

    def test_extracts_tech_stack_from_description(self):
        from src.scrapers.indeed import IndeedScraper

        scraper = IndeedScraper(api_key="test_key")
        jobs = scraper._parse_response(SAMPLE_JSEARCH_RESPONSE)

        # First job mentions Python, AWS, Kubernetes
        assert "python" in jobs[0]["tech_stack"]
        assert "aws" in jobs[0]["tech_stack"]
        assert "kubernetes" in jobs[0]["tech_stack"]

        # Second job mentions React, Node.js
        assert "react" in jobs[1]["tech_stack"]
        assert "node.js" in jobs[1]["tech_stack"]

    def test_detects_remote_from_description(self):
        from src.scrapers.indeed import IndeedScraper

        scraper = IndeedScraper(api_key="test_key")
        jobs = scraper._parse_response(SAMPLE_JSEARCH_RESPONSE)

        # First job is marked remote
        assert jobs[0]["remote"] == True

        # Second job not marked remote but says "work from home"
        assert jobs[1]["remote"] == True

    @pytest.fixture
    def mock_httpx_client(self):
        with patch("src.scrapers.indeed.httpx.Client") as mock:
            yield mock

    def test_scrape_returns_jobpost_list(self, mock_httpx_client):
        from src.scrapers.indeed import IndeedScraper
        from src.models import JobPost

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JSEARCH_RESPONSE

        mock_empty = MagicMock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = {"status": "OK", "data": []}

        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = [mock_response, mock_empty]
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        scraper = IndeedScraper(api_key="test_key", max_pages=2)
        jobs = scraper.scrape()

        assert isinstance(jobs, list)
        assert len(jobs) == 2
        assert all(isinstance(j, JobPost) for j in jobs)

    def test_handles_rate_limiting(self, mock_httpx_client):
        from src.scrapers.indeed import IndeedScraper

        # First call returns 429, second returns success, third returns empty
        mock_429 = MagicMock()
        mock_429.status_code = 429

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = SAMPLE_JSEARCH_RESPONSE

        mock_empty = MagicMock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = {"status": "OK", "data": []}

        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = [mock_429, mock_success, mock_empty]
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        scraper = IndeedScraper(api_key="test_key", max_pages=2)
        jobs = scraper.scrape()

        assert len(jobs) == 2
        assert mock_client_instance.get.call_count >= 2

    def test_handles_pagination(self, mock_httpx_client):
        from src.scrapers.indeed import IndeedScraper

        page1_response = {"status": "OK", "data": SAMPLE_JSEARCH_RESPONSE["data"][:1]}
        page2_response = {"status": "OK", "data": SAMPLE_JSEARCH_RESPONSE["data"][1:]}
        empty_response = {"status": "OK", "data": []}

        mock_page1 = MagicMock()
        mock_page1.status_code = 200
        mock_page1.json.return_value = page1_response

        mock_page2 = MagicMock()
        mock_page2.status_code = 200
        mock_page2.json.return_value = page2_response

        mock_empty = MagicMock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = empty_response

        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = [mock_page1, mock_page2, mock_empty]
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        scraper = IndeedScraper(api_key="test_key", max_pages=3)
        jobs = scraper.scrape()

        assert len(jobs) == 2

    def test_handles_empty_results(self, mock_httpx_client):
        from src.scrapers.indeed import IndeedScraper

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "OK", "data": []}

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        scraper = IndeedScraper(api_key="test_key")
        jobs = scraper.scrape()

        assert jobs == []

    def test_raises_error_without_api_key(self):
        from src.scrapers.indeed import IndeedScraper

        scraper = IndeedScraper(api_key="")
        with pytest.raises(RuntimeError) as exc_info:
            scraper.scrape()

        assert "RAPIDAPI_KEY not set" in str(exc_info.value)

    def test_raises_error_on_auth_failure(self, mock_httpx_client):
        from src.scrapers.indeed import IndeedScraper

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "forbidden"

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        scraper = IndeedScraper(api_key="invalid_key")
        with pytest.raises(RuntimeError) as exc_info:
            scraper.scrape()

        assert "authentication failed" in str(exc_info.value)

    def test_raises_error_when_not_subscribed(self, mock_httpx_client):
        from src.scrapers.indeed import IndeedScraper

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = '{"message":"You are not subscribed to this API."}'

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        scraper = IndeedScraper(api_key="valid_key_but_not_subscribed")
        with pytest.raises(RuntimeError) as exc_info:
            scraper.scrape()

        assert "not subscribed" in str(exc_info.value).lower()
        assert "rapidapi.com" in str(exc_info.value)
