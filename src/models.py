from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class JobPost(BaseModel):
    """Normalized job posting from any source"""

    source: str
    source_id: str
    source_url: str
    company_name: str
    company_website: Optional[str] = None
    title: str
    location: Optional[str] = None
    remote: bool = False
    description: str = ""
    tech_stack: list[str] = []
    posted_at: Optional[datetime] = None


class Company(BaseModel):
    """Maps to EspoCRM Account"""

    name: str
    website: Optional[str] = None
    industry: str = "Software"
    description: Optional[str] = None


class Person(BaseModel):
    """Maps to EspoCRM Contact"""

    first_name: str
    last_name: str
    title: Optional[str] = None
    email: Optional[str] = None
    account_id: Optional[str] = None
    source_url: str
