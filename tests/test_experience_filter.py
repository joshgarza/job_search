import pytest


class TestParseExperienceLevel:
    def test_parses_plus_years(self):
        from src.filters import parse_experience_level

        result = parse_experience_level("5+ years experience required")
        assert result["years_min"] == 5
        assert result["years_max"] is None

    def test_parses_range(self):
        from src.filters import parse_experience_level

        result = parse_experience_level("Looking for 3-5 years of experience")
        assert result["years_min"] == 3
        assert result["years_max"] == 5

    def test_detects_junior_level(self):
        from src.filters import parse_experience_level

        result = parse_experience_level("Junior Developer position available")
        assert result["level"] == "junior"

    def test_detects_senior_level(self):
        from src.filters import parse_experience_level

        result = parse_experience_level("Senior Engineer needed")
        assert result["level"] == "senior"

    def test_detects_mid_level(self):
        from src.filters import parse_experience_level

        result = parse_experience_level("Mid-level Software Engineer")
        assert result["level"] == "mid"

    def test_returns_none_when_not_found(self):
        from src.filters import parse_experience_level

        result = parse_experience_level("Software Engineer position")
        assert result["years_min"] is None
        assert result["years_max"] is None
        assert result["level"] is None


class TestExperienceFilter:
    @pytest.fixture
    def sample_job_data(self):
        return {
            "source": "test",
            "source_id": "1",
            "source_url": "https://example.com/1",
            "company_name": "Test Corp",
            "title": "Software Engineer",
            "description": "",
            "tech_stack": [],
        }

    def test_rejects_overqualified_jobs(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_experience_filter

        data = sample_job_data.copy()
        data["description"] = "Requires 10+ years of experience"
        job = JobPost(**data)
        config = {"max_years": 5}
        assert passes_experience_filter(job, config) == False

    def test_accepts_within_years_range(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_experience_filter

        data = sample_job_data.copy()
        data["description"] = "3-5 years of experience"
        job = JobPost(**data)
        config = {"max_years": 5}
        assert passes_experience_filter(job, config) == True

    def test_accepts_matching_level(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_experience_filter

        data = sample_job_data.copy()
        data["title"] = "Mid-level Developer"
        data["description"] = "Looking for a mid-level developer"
        job = JobPost(**data)
        config = {"levels": ["junior", "mid"]}
        assert passes_experience_filter(job, config) == True

    def test_rejects_wrong_level(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_experience_filter

        data = sample_job_data.copy()
        data["title"] = "Senior Engineer"
        data["description"] = "Looking for a senior engineer"
        job = JobPost(**data)
        config = {"levels": ["junior", "mid"]}
        assert passes_experience_filter(job, config) == False

    def test_passes_when_no_config(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_experience_filter

        data = sample_job_data.copy()
        data["description"] = "10+ years required, Senior position"
        job = JobPost(**data)
        config = {}
        assert passes_experience_filter(job, config) == True

    def test_passes_when_no_experience_mentioned(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_experience_filter

        data = sample_job_data.copy()
        data["description"] = "Software Engineer position"
        job = JobPost(**data)
        config = {"max_years": 5, "levels": ["junior", "mid"]}
        assert passes_experience_filter(job, config) == True
