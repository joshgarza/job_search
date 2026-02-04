# SWE Job Lead Pipeline

A Python pipeline that scrapes software engineering job opportunities from web sources, filters them, and syncs to EspoCRM as Accounts (companies) and Contacts (leads with `cStatus=Cold`).

## Architecture

```
[HN Who's Hiring]  ─┐
[Wellfound]        ─┼→ [Normalizer] → [Filter] → [Dedup] → [EspoCRM Sync]
[Indeed/JSearch]   ─┘                                 ↓
                                                 SQLite DB
                                              (cache + state)
```

## Prerequisites

- Python 3.10+
- Access to an EspoCRM instance
- (Optional) RapidAPI key for Indeed/JSearch scraper

## Setup

### 1. Clone and enter the project

```bash
cd job_search
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure credentials

Edit `config/.env` with your credentials:

```bash
# EspoCRM
ESPO_URL=http://192.168.68.68:8080
ESPO_USER=admin
ESPO_PASS=your_password

# Indeed/JSearch (optional)
# 1. Sign up at https://rapidapi.com
# 2. Subscribe to JSearch API (free tier): https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
# 3. Copy your API key from the dashboard
RAPIDAPI_KEY=your_rapidapi_key
```

### 5. Configure filters (optional)

Edit `config/filters.yaml` to customize which jobs are synced:

```yaml
role:
  include:
    - backend
    - full stack
    - software engineer
  exclude:
    - senior staff
    - principal
    - manager

location:
  include:
    - remote
    - seattle
  remote_ok: true

company:
  exclude_keywords:
    - defense
    - gambling

tech:
  require_any:
    - python
    - typescript
    - react
  min_match: 2
  exclude:           # Reject jobs with these technologies
    - cobol
    - fortran
    - .net

experience:          # Filter by experience level
  max_years: 5       # Reject jobs requiring more than 5 years
  levels:
    - junior
    - mid
```

## Usage

### Run a dry run (preview without syncing)

```bash
python cli.py run --dry-run
```

This scrapes jobs and shows what would be synced without actually creating records in EspoCRM.

### Run full sync

```bash
python cli.py run
```

This will:
1. Scrape jobs from the configured sources
2. Filter jobs based on `config/filters.yaml`
3. Skip duplicates already in the database
4. Create Account and Contact records in EspoCRM

### Check pipeline status

```bash
python cli.py status
```

Shows counts of total jobs scraped, synced, and pending.

### Specify different sources

```bash
# Single source
python cli.py run --sources hn_hiring

# Multiple sources
python cli.py run --sources hn_hiring,wellfound,indeed
```

Available sources:
- `hn_hiring` - Hacker News "Who's Hiring" monthly threads
- `indeed` - Indeed/Glassdoor via JSearch API (requires RAPIDAPI_KEY + subscription)
- `wellfound` - Wellfound startup jobs (requires Playwright system deps, may be blocked by bot protection)

## Running Tests

```bash
pytest -v
```

All 67 tests should pass.

## Project Structure

```
job_search/
├── src/
│   ├── models.py           # Pydantic data models
│   ├── scrapers/
│   │   ├── base.py         # Abstract scraper interface
│   │   ├── hn_hiring.py    # HN Who's Hiring scraper
│   │   ├── wellfound.py    # Wellfound scraper (Playwright)
│   │   └── indeed.py       # Indeed/JSearch API scraper
│   ├── filters.py          # Job filtering logic
│   ├── espo_client.py      # EspoCRM API client
│   ├── db.py               # SQLite storage
│   └── pipeline.py         # Main orchestration
├── tests/                  # Test suite (67 tests)
├── config/
│   ├── filters.yaml        # Filter configuration
│   └── .env                # Credentials (not in git)
├── data/                   # SQLite database (not in git)
├── cli.py                  # Command-line interface
└── requirements.txt
```

## EspoCRM Entity Mapping

### Account (Companies)

| Pipeline Field | EspoCRM Field |
|---------------|---------------|
| `company_name` | `name` |
| `company_website` | `website` |
| `tech_stack` | `description` |
| - | `industry` (default: "Software") |

### Contact (Leads)

| Pipeline Field | EspoCRM Field |
|---------------|---------------|
| `company_name` | `firstName` |
| "(Job Posting)" | `lastName` |
| `title` | `title` |
| `source_url` | `description` |
| - | `cStatus` (always "Cold") |
| - | `cRelationshipStrength` (default: "1/10") |
| - | `accountId` (linked to Account) |

## Adding New Scrapers

1. Create a new file in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the `scrape()` method returning a list of `JobPost` objects
3. Register it in `src/pipeline.py` in the `get_scraper()` function
4. Add tests in `tests/`
