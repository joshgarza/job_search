import httpx
from typing import Optional
from src.models import Company, Person, JobPost


class EspoClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}/api/v1/{endpoint}"
        response = httpx.request(method, url, auth=self.auth, **kwargs)
        response.raise_for_status()
        return response.json()

    def find_account(self, name: str) -> Optional[dict]:
        """Find account by exact name match"""
        params = {
            "where[0][type]": "equals",
            "where[0][attribute]": "name",
            "where[0][value]": name,
        }
        result = self._request("GET", "Account", params=params)
        if result.get("total", 0) > 0:
            return result["list"][0]
        return None

    def create_account(self, company: Company) -> str:
        """Create account, returns ID"""
        data = {
            "name": company.name,
            "website": company.website,
            "industry": company.industry,
            "description": company.description,
        }
        result = self._request("POST", "Account", json=data)
        return result["id"]

    def find_contact(self, email: str = None, name: str = None) -> Optional[dict]:
        """Find contact by email or name"""
        params = {}
        if email:
            params["where[0][type]"] = "equals"
            params["where[0][attribute]"] = "emailAddress"
            params["where[0][value]"] = email
        result = self._request("GET", "Contact", params=params)
        if result.get("total", 0) > 0:
            return result["list"][0]
        return None

    def create_contact(self, person: Person, account_id: str) -> str:
        """Create contact linked to account with Cold status"""
        data = {
            "firstName": person.first_name,
            "lastName": person.last_name,
            "title": person.title,
            "emailAddress": person.email,
            "accountId": account_id,
            "cStatus": "Cold",
            "cRelationshipStrength": "1/10",
            "description": f"Source: {person.source_url}",
        }
        result = self._request("POST", "Contact", json=data)
        return result["id"]

    def create_opportunity(self, job: JobPost, account_id: str) -> str:
        """Create opportunity (job application) linked to account"""
        from datetime import datetime, timedelta

        # Build description with job details
        description = f"{job.description[:1000]}..." if len(job.description) > 1000 else job.description
        description += f"\n\nSource: {job.source_url}"
        if job.tech_stack:
            description += f"\nTech: {', '.join(job.tech_stack)}"

        # Set close date to 30 days from now
        close_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        data = {
            "name": f"{job.title} at {job.company_name}"[:150],
            "accountId": account_id,
            "stage": "To Apply",
            "amount": 0,
            "closeDate": close_date,
            "description": description,
        }
        result = self._request("POST", "Opportunity", json=data)
        return result["id"]
