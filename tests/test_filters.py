import pytest


@pytest.fixture
def filter_config():
    return {
        "role": {
            "include": ["backend", "full stack", "software engineer"],
            "exclude": ["senior staff", "principal", "manager"],
        },
        "location": {"include": ["remote", "seattle"], "remote_ok": True},
        "company": {"exclude_keywords": ["defense", "gambling"]},
    }


class TestRoleFilter:
    def test_includes_matching_title(self, sample_job_data, filter_config):
        from src.models import JobPost
        from src.filters import passes_role_filter

        job = JobPost(**sample_job_data)
        assert passes_role_filter(job, filter_config["role"]) == True

    def test_excludes_senior_staff(self, sample_job_data, filter_config):
        from src.models import JobPost
        from src.filters import passes_role_filter

        data = sample_job_data.copy()
        data["title"] = "Senior Staff Engineer"
        job = JobPost(**data)
        assert passes_role_filter(job, filter_config["role"]) == False


class TestLocationFilter:
    def test_accepts_remote(self, sample_job_data, filter_config):
        from src.models import JobPost
        from src.filters import passes_location_filter

        job = JobPost(**sample_job_data)
        job = JobPost(**{**sample_job_data, "remote": True})
        assert passes_location_filter(job, filter_config["location"]) == True


class TestCompanyFilter:
    def test_excludes_defense(self, sample_job_data, filter_config):
        from src.models import JobPost
        from src.filters import passes_company_filter

        data = sample_job_data.copy()
        data["description"] = "Defense contractor seeking engineers"
        job = JobPost(**data)
        assert passes_company_filter(job, filter_config["company"]) == False


class TestTechFilter:
    def test_passes_with_matching_tech(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_tech_filter

        job = JobPost(**sample_job_data)  # has python, postgresql, aws in tech_stack
        config = {"require_any": ["python", "react", "go"], "min_match": 1}
        assert passes_tech_filter(job, config) == True

    def test_fails_without_enough_matches(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_tech_filter

        data = sample_job_data.copy()
        data["tech_stack"] = ["python"]
        data["description"] = "We use Python"
        job = JobPost(**data)
        config = {"require_any": ["python", "react", "go"], "min_match": 2}
        assert passes_tech_filter(job, config) == False

    def test_checks_description_for_tech(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_tech_filter

        data = sample_job_data.copy()
        data["tech_stack"] = []
        data["description"] = "We use React and TypeScript"
        job = JobPost(**data)
        config = {"require_any": ["react", "typescript"], "min_match": 2}
        assert passes_tech_filter(job, config) == True


class TestTechExclusionFilter:
    def test_excludes_tech_in_stack(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_tech_filter

        data = sample_job_data.copy()
        data["tech_stack"] = ["python", "cobol", "aws"]
        job = JobPost(**data)
        config = {"require_any": ["python", "aws"], "min_match": 1, "exclude": ["cobol"]}
        assert passes_tech_filter(job, config) == False

    def test_excludes_tech_in_description(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_tech_filter

        data = sample_job_data.copy()
        data["tech_stack"] = ["python"]
        data["description"] = "We use Python and .NET framework"
        job = JobPost(**data)
        config = {"require_any": ["python"], "min_match": 1, "exclude": [".net"]}
        assert passes_tech_filter(job, config) == False

    def test_passes_without_excluded_tech(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_tech_filter

        data = sample_job_data.copy()
        data["tech_stack"] = ["python", "react", "aws"]
        data["description"] = "Modern web stack"
        job = JobPost(**data)
        config = {"require_any": ["python", "react"], "min_match": 1, "exclude": ["cobol", "fortran"]}
        assert passes_tech_filter(job, config) == True

    def test_exclude_is_case_insensitive(self, sample_job_data):
        from src.models import JobPost
        from src.filters import passes_tech_filter

        data = sample_job_data.copy()
        data["tech_stack"] = ["COBOL", "python"]
        job = JobPost(**data)
        config = {"require_any": ["python"], "min_match": 1, "exclude": ["cobol"]}
        assert passes_tech_filter(job, config) == False


class TestFullFilter:
    def test_filter_job_all_pass(self, sample_job_data, filter_config):
        from src.models import JobPost
        from src.filters import filter_job

        job = JobPost(**sample_job_data)
        assert filter_job(job, filter_config) == True
