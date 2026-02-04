import re
import httpx
from typing import Optional
from src.scrapers.base import BaseScraper
from src.models import JobPost


class HNHiringScraper(BaseScraper):
    ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
    ALGOLIA_ITEM = "https://hn.algolia.com/api/v1/items"

    TECH_KEYWORDS = [
        "python",
        "javascript",
        "typescript",
        "go",
        "golang",
        "rust",
        "java",
        "ruby",
        "php",
        "c++",
        "c#",
        "swift",
        "kotlin",
        "scala",
        "react",
        "vue",
        "angular",
        "node",
        "django",
        "flask",
        "rails",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "elasticsearch",
        "aws",
        "gcp",
        "azure",
        "docker",
        "kubernetes",
        "terraform",
    ]

    def get_latest_thread_id(self) -> str:
        """Find the most recent 'Who is hiring' thread posted by whoishiring bot"""
        params = {"tags": "story,ask_hn,author_whoishiring", "hitsPerPage": 5}
        response = httpx.get(self.ALGOLIA_SEARCH, params=params)
        response.raise_for_status()
        hits = response.json().get("hits", [])
        # Find the "Who is hiring?" thread (not "Who wants to be hired?")
        for hit in hits:
            title = hit.get("title", "")
            if "Who is hiring?" in title:
                return hit["objectID"]
        raise ValueError("No hiring thread found")

    def parse_company_name(self, text: str) -> str:
        """Extract company name (first segment before |)"""
        parts = text.split("|")
        if parts:
            name = parts[0].strip()
            # Truncate to first line and max 100 chars for CRM compatibility
            name = name.split("\n")[0].split("—")[0].split("-")[0].strip()
            if len(name) > 100:
                name = name[:100].rsplit(" ", 1)[0]  # Don't cut mid-word
            return name if name else "Unknown"
        return "Unknown"

    def parse_job_title(self, text: str) -> str:
        """Extract job title (second segment)"""
        parts = text.split("|")
        if len(parts) >= 2:
            title = parts[1].strip()
            # Truncate for CRM compatibility
            if len(title) > 100:
                title = title[:100].rsplit(" ", 1)[0]
            return title if title else "Software Engineer"
        return "Software Engineer"

    def is_remote(self, text: str) -> bool:
        """Check if position is remote"""
        text_lower = text.lower()
        return "remote" in text_lower

    def parse_tech_stack(self, text: str) -> list[str]:
        """Extract known technologies from text"""
        text_lower = text.lower()
        found = []
        for tech in self.TECH_KEYWORDS:
            if tech in text_lower:
                found.append(tech)
        return found

    def parse_email(self, text: str) -> Optional[str]:
        """Extract email address if present"""
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def parse_comment(self, comment: dict, thread_id: str) -> Optional[JobPost]:
        """Parse a single HN comment into a JobPost"""
        text = comment.get("text", "")
        if not text or len(text) < 50:
            return None

        # Clean HTML
        text_clean = re.sub(r"<[^>]+>", " ", text)

        return JobPost(
            source="hn_hiring",
            source_id=str(comment.get("id")),
            source_url=f"https://news.ycombinator.com/item?id={comment.get('id')}",
            company_name=self.parse_company_name(text_clean),
            title=self.parse_job_title(text_clean),
            location=None,
            remote=self.is_remote(text_clean),
            description=text_clean,
            tech_stack=self.parse_tech_stack(text_clean),
        )

    def scrape(self) -> list[JobPost]:
        """Fetch and parse all jobs from latest hiring thread"""
        thread_id = self.get_latest_thread_id()

        response = httpx.get(f"{self.ALGOLIA_ITEM}/{thread_id}")
        response.raise_for_status()
        data = response.json()

        jobs = []
        for comment in data.get("children", []):
            job = self.parse_comment(comment, thread_id)
            if job:
                jobs.append(job)

        return jobs
