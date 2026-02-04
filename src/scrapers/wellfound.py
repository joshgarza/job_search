import time
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from src.scrapers.base import BaseScraper
from src.models import JobPost


class WellfoundScraper(BaseScraper):
    BASE_URL = "https://wellfound.com"

    def __init__(self, role: str = "software-engineer", remote: bool = True):
        self.role = role
        self.remote = remote

    def _build_search_url(self, role: str = None, remote: bool = None, page: int = 1) -> str:
        role = role or self.role
        remote = remote if remote is not None else self.remote

        url = f"{self.BASE_URL}/role/{role}"
        params = []
        if remote:
            params.append("remote=true")
        if page > 1:
            params.append(f"page={page}")
        if params:
            url += "?" + "&".join(params)
        return url

    def _parse_job_card(self, html: str) -> dict:
        """Parse a single job card HTML and extract job data"""
        soup = BeautifulSoup(html, "html.parser")

        # Extract company name
        company_elem = soup.select_one('[class*="name"]')
        company_name = company_elem.get_text(strip=True) if company_elem else "Unknown"

        # Extract job title
        title_elem = soup.select_one('[class*="title"]')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"

        # Extract location
        location_elem = soup.select_one('[class*="location"]')
        location = location_elem.get_text(strip=True) if location_elem else ""

        # Check remote flag
        remote_elem = soup.select_one('[class*="remote"]')
        remote = remote_elem is not None

        # Extract tech stack from tags
        tech_stack = []
        tags_container = soup.select_one('[class*="tags"]')
        if tags_container:
            tech_stack = [
                span.get_text(strip=True) for span in tags_container.find_all("span")
            ]

        # Extract job URL/ID
        job_link = soup.select_one('a[href*="/jobs/"]')
        source_id = ""
        source_url = ""
        if job_link:
            href = job_link.get("href", "")
            source_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
            # Extract ID from URL like /jobs/1234567-software-engineer
            match = re.search(r"/jobs/(\d+)", href)
            if match:
                source_id = match.group(1)

        # Extract company website link
        company_link = soup.select_one('a[href*="/company/"]')
        company_website = ""
        if company_link:
            href = company_link.get("href", "")
            company_website = (
                f"{self.BASE_URL}{href}" if href.startswith("/") else href
            )

        return {
            "source_id": source_id,
            "source_url": source_url,
            "company_name": company_name,
            "company_website": company_website,
            "title": title,
            "location": location,
            "remote": remote,
            "description": "",
            "tech_stack": tech_stack,
        }

    def _fetch_job_description(self, page, url: str) -> str:
        """Navigate to job detail page and fetch description"""
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1)

            desc_elem = page.query_selector('[class*="jobDescription"], [class*="description"]')
            if desc_elem:
                return desc_elem.inner_text()
        except Exception:
            pass
        return ""

    def scrape(self) -> list[JobPost]:
        """Fetch and parse job posts from Wellfound"""
        jobs = []

        try:
            playwright_context = sync_playwright().start()
        except Exception as e:
            raise RuntimeError(f"Failed to start Playwright: {e}")

        # Try Firefox first (fewer system deps), fall back to Chromium
        browser = None
        launch_errors = []
        for browser_type in [playwright_context.firefox, playwright_context.chromium]:
            try:
                browser = browser_type.launch(headless=True)
                break
            except Exception as e:
                launch_errors.append(str(e))
                continue

        if browser is None:
            playwright_context.stop()
            raise RuntimeError(
                f"Failed to launch browser. Install system dependencies with: "
                f"sudo playwright install-deps\n"
                f"Or: sudo apt-get install libasound2t64\n"
                f"Errors: {launch_errors}"
            )

        try:
            page = browser.new_page()

            page_num = 1
            max_pages = 5

            while page_num <= max_pages:
                url = self._build_search_url(page=page_num)
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                # Find job cards
                job_cards = page.query_selector_all('[data-test="StartupResult"], [class*="styles_component"]')

                if not job_cards:
                    break

                for card in job_cards:
                    try:
                        card_html = card.inner_html()
                        job_data = self._parse_job_card(card_html)

                        if not job_data["source_id"]:
                            continue

                        # Optionally fetch full description
                        if job_data["source_url"]:
                            job_data["description"] = self._fetch_job_description(
                                page, job_data["source_url"]
                            )
                            time.sleep(1)  # Rate limit

                        jobs.append(
                            JobPost(
                                source="wellfound",
                                source_id=job_data["source_id"],
                                source_url=job_data["source_url"],
                                company_name=job_data["company_name"],
                                company_website=job_data["company_website"] or None,
                                title=job_data["title"],
                                location=job_data["location"] or None,
                                remote=job_data["remote"],
                                description=job_data["description"],
                                tech_stack=job_data["tech_stack"],
                            )
                        )
                    except Exception as e:
                        print(f"Error parsing job card: {e}")
                        continue

                # Check for next page
                next_btn = page.query_selector('a[aria-label="Next page"], button:has-text("Next")')
                if not next_btn:
                    break

                page_num += 1
                time.sleep(2)  # Rate limit between pages
        finally:
            browser.close()
            playwright_context.stop()

        return jobs
