import re
import time
import os
from datetime import datetime
from typing import Optional
import httpx
from src.scrapers.base import BaseScraper
from src.models import JobPost

# Common tech keywords to extract from descriptions
TECH_KEYWORDS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
    "react", "angular", "vue", "next.js", "nextjs", "node.js", "nodejs", "express",
    "django", "flask", "fastapi", "spring", "rails",
    "aws", "azure", "gcp", "google cloud", "kubernetes", "k8s", "docker",
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "graphql", "rest", "api",
    "machine learning", "ml", "ai", "llm", "gpt", "openai", "langchain",
    "tensorflow", "pytorch", "pandas", "numpy",
]


class IndeedScraper(BaseScraper):
    """
    Scraper that uses JSearch API (via RapidAPI) to fetch job listings.
    JSearch aggregates Indeed, Glassdoor, LinkedIn, and other job boards.
    """

    API_URL = "https://jsearch.p.rapidapi.com/search"

    def __init__(
        self,
        api_key: Optional[str] = None,
        query: str = "remote software engineer",
        remote: bool = True,
        max_pages: int = 5,
    ):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY", "")
        self.query = query
        self.remote = remote
        self.max_pages = max_pages

    def _build_request(
        self, query: str = None, remote: bool = None, page: int = 1
    ) -> tuple[str, dict]:
        """Build API URL and params for JSearch"""
        query = query or self.query
        remote = remote if remote is not None else self.remote

        params = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
        }
        if remote:
            params["remote_jobs_only"] = "true"

        return self.API_URL, params

    def _get_headers(self) -> dict:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

    def _extract_tech_stack(self, text: str) -> list[str]:
        """Extract tech keywords from job description"""
        text_lower = text.lower()
        found = []
        for tech in TECH_KEYWORDS:
            # Use word boundary matching for short terms
            if len(tech) <= 3:
                if re.search(rf"\b{re.escape(tech)}\b", text_lower):
                    found.append(tech)
            elif tech in text_lower:
                found.append(tech)
        return found

    def _is_remote(self, item: dict) -> bool:
        """Check if job is remote from API data and description"""
        if item.get("job_is_remote"):
            return True

        # Check description for remote indicators
        desc = (item.get("job_description") or "").lower()
        title = (item.get("job_title") or "").lower()
        location = (item.get("job_city") or "").lower()

        remote_indicators = ["remote", "work from home", "wfh", "distributed", "anywhere"]
        for indicator in remote_indicators:
            if indicator in desc or indicator in title or indicator in location:
                return True
        return False

    def _parse_response(self, response: dict) -> list[dict]:
        """Parse JSearch API response into job data dicts"""
        jobs = []
        data = response.get("data", [])

        for item in data:
            location_parts = []
            if item.get("job_city"):
                location_parts.append(item["job_city"])
            if item.get("job_state"):
                location_parts.append(item["job_state"])

            location = ", ".join(location_parts) if location_parts else "Remote"

            posted_at = None
            if item.get("job_posted_at_datetime_utc"):
                try:
                    posted_at = datetime.fromisoformat(
                        item["job_posted_at_datetime_utc"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            description = item.get("job_description", "")
            jobs.append(
                {
                    "source_id": item.get("job_id", ""),
                    "source_url": item.get("job_apply_link", ""),
                    "company_name": item.get("employer_name", "Unknown"),
                    "company_website": item.get("employer_website"),
                    "title": item.get("job_title", "Unknown"),
                    "location": location,
                    "remote": self._is_remote(item),
                    "description": description,
                    "tech_stack": self._extract_tech_stack(description),
                    "posted_at": posted_at,
                }
            )

        return jobs

    def scrape(self) -> list[JobPost]:
        """Fetch and parse job posts from JSearch API"""
        if not self.api_key:
            raise RuntimeError(
                "RAPIDAPI_KEY not set. Get a key from rapidapi.com/letscrape-6bRBa3QguO5/"
                "jsearch and set it in config/.env"
            )

        jobs = []
        page = 1
        max_retries = 3

        with httpx.Client(timeout=30.0) as client:
            while page <= self.max_pages:
                url, params = self._build_request(page=page)

                retry_count = 0
                response = None

                while retry_count < max_retries:
                    response = client.get(
                        url, params=params, headers=self._get_headers()
                    )

                    if response.status_code == 429:
                        retry_count += 1
                        wait_time = 2**retry_count
                        time.sleep(wait_time)
                        continue

                    break

                if response is None:
                    break

                if response.status_code == 401 or response.status_code == 403:
                    body = response.text
                    if "not subscribed" in body.lower():
                        raise RuntimeError(
                            "Not subscribed to JSearch API. Subscribe (free tier available) at: "
                            "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
                        )
                    raise RuntimeError(
                        f"API authentication failed (HTTP {response.status_code}). "
                        "Check your RAPIDAPI_KEY is valid."
                    )

                if response.status_code != 200:
                    break

                data = response.json()
                page_jobs = self._parse_response(data)

                if not page_jobs:
                    break

                for job_data in page_jobs:
                    jobs.append(
                        JobPost(
                            source="indeed",
                            source_id=job_data["source_id"],
                            source_url=job_data["source_url"],
                            company_name=job_data["company_name"],
                            company_website=job_data["company_website"],
                            title=job_data["title"],
                            location=job_data["location"],
                            remote=job_data["remote"],
                            description=job_data["description"],
                            posted_at=job_data["posted_at"],
                            tech_stack=job_data["tech_stack"],
                        )
                    )

                page += 1
                time.sleep(1)

        return jobs
