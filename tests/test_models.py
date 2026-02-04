import pytest
from datetime import datetime


def test_job_post_creation(sample_job_data):
    """JobPost model should accept all required fields"""
    from src.models import JobPost

    job = JobPost(**sample_job_data)
    assert job.company_name == "Acme Corp"
    assert job.remote == True
    assert "python" in job.tech_stack


def test_job_post_requires_company_name():
    """JobPost should require company_name"""
    from src.models import JobPost

    with pytest.raises(Exception):
        JobPost(source="test", source_id="1", source_url="http://test", title="Test")


def test_company_model():
    """Company model should map to EspoCRM Account fields"""
    from src.models import Company

    company = Company(name="Test Inc", website="https://test.com")
    assert company.name == "Test Inc"
    assert company.industry == "Software"  # default


def test_person_model():
    """Person model should map to EspoCRM Contact fields"""
    from src.models import Person

    person = Person(
        first_name="John",
        last_name="Doe",
        title="Engineer",
        source_url="https://example.com",
    )
    assert person.first_name == "John"
    assert person.account_id is None  # optional
