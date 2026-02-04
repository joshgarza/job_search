import pytest
import respx
from httpx import Response


@pytest.fixture
def hn_scraper():
    from src.scrapers.hn_hiring import HNHiringScraper

    return HNHiringScraper()


@pytest.fixture
def sample_hn_story():
    return {
        "objectID": "38842977",
        "title": "Ask HN: Who is hiring? (January 2024)",
        "created_at": "2024-01-01T12:00:00.000Z",
    }


@pytest.fixture
def sample_hn_comments():
    return {
        "id": 38842977,
        "children": [
            {
                "id": 38843001,
                "text": "Acme Corp | Backend Engineer | Remote | $150k-200k<p>Python, PostgreSQL, AWS. Email: jobs@acme.com",
                "author": "acme_recruiter",
            },
            {
                "id": 38843002,
                "text": "StartupXYZ | Full Stack | San Francisco | https://startup.xyz<p>React, Node.js, MongoDB",
                "author": "founder",
            },
        ],
    }


class TestHNScraperParsing:
    def test_parse_company_name_from_comment(self, hn_scraper):
        """Should extract company name from first part of comment"""
        text = "Acme Corp | Backend Engineer | Remote"
        result = hn_scraper.parse_company_name(text)
        assert result == "Acme Corp"

    def test_parse_job_title(self, hn_scraper):
        """Should extract job title from comment"""
        text = "Acme Corp | Backend Engineer | Remote"
        result = hn_scraper.parse_job_title(text)
        assert result == "Backend Engineer"

    def test_parse_remote_flag(self, hn_scraper):
        """Should detect remote keyword"""
        assert hn_scraper.is_remote("Acme | Engineer | Remote") == True
        assert hn_scraper.is_remote("Acme | Engineer | San Francisco") == False
        assert hn_scraper.is_remote("Acme | Engineer | REMOTE OK") == True

    def test_parse_tech_stack(self, hn_scraper):
        """Should extract known technologies"""
        text = "Python, PostgreSQL, AWS, React, Node.js"
        result = hn_scraper.parse_tech_stack(text)
        assert "python" in result
        assert "postgresql" in result
        assert "react" in result

    def test_parse_email(self, hn_scraper):
        """Should extract email if present"""
        text = "Contact us at jobs@acme.com for details"
        result = hn_scraper.parse_email(text)
        assert result == "jobs@acme.com"


class TestHNScraperAPI:
    @respx.mock
    def test_fetch_latest_hiring_thread(self, hn_scraper, sample_hn_story):
        """Should find most recent Who is hiring thread, skipping 'Who wants to be hired'"""
        # Simulate whoishiring bot's posts - includes both thread types
        hits = [
            {
                "objectID": "38842978",
                "title": "Ask HN: Who wants to be hired? (January 2024)",
            },
            sample_hn_story,  # "Who is hiring?" thread
        ]
        respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
            return_value=Response(200, json={"hits": hits})
        )
        story_id = hn_scraper.get_latest_thread_id()
        assert story_id == "38842977"

    @respx.mock
    def test_scrape_returns_job_posts(
        self, hn_scraper, sample_hn_story, sample_hn_comments
    ):
        """scrape() should return list of JobPost objects"""
        # Mock search endpoint
        respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
            return_value=Response(200, json={"hits": [sample_hn_story]})
        )
        # Mock items endpoint
        respx.get("https://hn.algolia.com/api/v1/items/38842977").mock(
            return_value=Response(200, json=sample_hn_comments)
        )

        jobs = hn_scraper.scrape()
        assert len(jobs) == 2
        assert jobs[0].company_name == "Acme Corp"
        assert jobs[0].source == "hn_hiring"
