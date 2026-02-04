import pytest
import os


@pytest.fixture
def sample_job_data():
    return {
        "source": "hn_hiring",
        "source_id": "12345",
        "source_url": "https://news.ycombinator.com/item?id=12345",
        "company_name": "Acme Corp",
        "company_website": "https://acme.com",
        "title": "Backend Engineer",
        "location": "Remote",
        "remote": True,
        "description": "Python, PostgreSQL, AWS",
        "tech_stack": ["python", "postgresql", "aws"],
        "posted_at": None,
    }


@pytest.fixture
def espo_config():
    return {
        "base_url": os.getenv("ESPO_URL", "http://192.168.68.68:8080"),
        "username": os.getenv("ESPO_USER", "admin"),
        "password": os.getenv("ESPO_PASS", "password"),
    }
