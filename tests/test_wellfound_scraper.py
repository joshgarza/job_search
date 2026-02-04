import pytest
from unittest.mock import Mock, patch, MagicMock


SAMPLE_JOB_CARD_HTML = """
<div class="styles_component__zVJv9" data-test="StartupResult">
    <a href="/company/acme-corp" class="styles_component__Bj0Yt">
        <span class="styles_name__UfkKR">Acme Corp</span>
    </a>
    <a href="/jobs/1234567-software-engineer" class="styles_component__f7e8a">
        <span class="styles_title__fy9kX">Software Engineer</span>
    </a>
    <span class="styles_location__D2hvm">San Francisco, CA</span>
    <span class="styles_remote__cEZAH">Remote friendly</span>
    <div class="styles_tags__J5k2Z">
        <span>Python</span>
        <span>React</span>
        <span>AWS</span>
    </div>
</div>
"""

SAMPLE_JOB_DETAIL_HTML = """
<div class="styles_jobDescription__Xw9R7">
    <h1>Software Engineer</h1>
    <p>We're looking for a talented software engineer to join our team.</p>
    <p>Requirements: 3+ years experience with Python, React, and AWS.</p>
</div>
"""


class TestWellfoundScraper:
    def test_parses_job_card_html(self):
        from src.scrapers.wellfound import WellfoundScraper

        scraper = WellfoundScraper()
        # Test the HTML parsing method
        job_data = scraper._parse_job_card(SAMPLE_JOB_CARD_HTML)

        assert job_data["company_name"] == "Acme Corp"
        assert job_data["title"] == "Software Engineer"
        assert job_data["location"] == "San Francisco, CA"

    def test_extracts_tech_tags(self):
        from src.scrapers.wellfound import WellfoundScraper

        scraper = WellfoundScraper()
        job_data = scraper._parse_job_card(SAMPLE_JOB_CARD_HTML)

        assert "Python" in job_data["tech_stack"]
        assert "React" in job_data["tech_stack"]
        assert "AWS" in job_data["tech_stack"]

    def test_handles_remote_flag(self):
        from src.scrapers.wellfound import WellfoundScraper

        scraper = WellfoundScraper()
        job_data = scraper._parse_job_card(SAMPLE_JOB_CARD_HTML)

        assert job_data["remote"] == True

    def test_handles_non_remote_job(self):
        from src.scrapers.wellfound import WellfoundScraper

        non_remote_html = SAMPLE_JOB_CARD_HTML.replace(
            '<span class="styles_remote__cEZAH">Remote friendly</span>', ""
        )
        scraper = WellfoundScraper()
        job_data = scraper._parse_job_card(non_remote_html)

        assert job_data["remote"] == False

    @patch("src.scrapers.wellfound.sync_playwright")
    def test_scrape_returns_jobpost_list(self, mock_playwright):
        from src.scrapers.wellfound import WellfoundScraper
        from src.models import JobPost

        # Mock playwright browser
        mock_page = MagicMock()
        mock_page.content.return_value = f"""
        <html><body>
            {SAMPLE_JOB_CARD_HTML}
        </body></html>
        """
        mock_page.query_selector_all.return_value = [MagicMock()]
        mock_page.query_selector.return_value = None  # No next page

        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser

        mock_playwright.return_value.__enter__.return_value = mock_pw_instance

        scraper = WellfoundScraper()
        # Mock internal parsing to return valid data
        with patch.object(
            scraper,
            "_parse_job_card",
            return_value={
                "source_id": "1234567",
                "source_url": "https://wellfound.com/jobs/1234567",
                "company_name": "Acme Corp",
                "company_website": "https://wellfound.com/company/acme-corp",
                "title": "Software Engineer",
                "location": "San Francisco, CA",
                "remote": True,
                "description": "Test description",
                "tech_stack": ["Python", "React"],
            },
        ):
            jobs = scraper.scrape()

        assert isinstance(jobs, list)
        if len(jobs) > 0:
            assert isinstance(jobs[0], JobPost)

    @patch("src.scrapers.wellfound.sync_playwright")
    def test_handles_empty_results(self, mock_playwright):
        from src.scrapers.wellfound import WellfoundScraper

        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body></body></html>"
        mock_page.query_selector_all.return_value = []

        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch.return_value = mock_browser

        mock_playwright.return_value.__enter__.return_value = mock_pw_instance

        scraper = WellfoundScraper()
        jobs = scraper.scrape()

        assert jobs == []

    def test_builds_search_url(self):
        from src.scrapers.wellfound import WellfoundScraper

        scraper = WellfoundScraper()
        url = scraper._build_search_url(role="software-engineer", remote=True)

        assert "wellfound.com" in url
        assert "software-engineer" in url or "role" in url

    @patch("src.scrapers.wellfound.sync_playwright")
    def test_raises_error_on_browser_launch_failure(self, mock_playwright):
        from src.scrapers.wellfound import WellfoundScraper

        mock_pw_instance = MagicMock()
        # Both Firefox and Chromium fail
        mock_pw_instance.firefox.launch.side_effect = Exception("Firefox launch failed")
        mock_pw_instance.chromium.launch.side_effect = Exception("Chromium launch failed")

        mock_playwright.return_value.start.return_value = mock_pw_instance

        scraper = WellfoundScraper()
        with pytest.raises(RuntimeError) as exc_info:
            scraper.scrape()

        assert "Failed to launch browser" in str(exc_info.value)
        assert "playwright install-deps" in str(exc_info.value)
