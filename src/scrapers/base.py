from abc import ABC, abstractmethod
from src.models import JobPost


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self) -> list[JobPost]:
        """Fetch and parse job posts from source"""
        pass
