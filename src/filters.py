import re
from src.models import JobPost


def passes_role_filter(job: JobPost, config: dict) -> bool:
    title_lower = job.title.lower()
    desc_lower = job.description.lower()

    # Check excludes first (in title or description)
    for exclude in config.get("exclude", []):
        if exclude.lower() in title_lower:
            return False

    # Check includes
    includes = config.get("include", [])
    if not includes:
        return True

    for include in includes:
        if include.lower() in title_lower or include.lower() in desc_lower:
            return True
    return False


def passes_location_filter(job: JobPost, config: dict) -> bool:
    text = f"{job.location or ''} {job.description}".lower()

    # Check excludes first - reject if requires relocation/onsite elsewhere
    for exclude in config.get("exclude", []):
        if exclude.lower() in text:
            return False

    # Remote is always OK if enabled
    if config.get("remote_ok") and job.remote:
        return True

    # Check location includes
    includes = config.get("include", [])
    if not includes:
        return True

    for loc in includes:
        if loc.lower() in text:
            return True
    return False


def passes_company_filter(job: JobPost, config: dict) -> bool:
    text = f"{job.company_name} {job.description}".lower()
    for keyword in config.get("exclude_keywords", []):
        if keyword.lower() in text:
            return False
    return True


def passes_tech_filter(job: JobPost, config: dict) -> bool:
    """Check if job matches required tech stack"""
    if not config:
        return True

    # Check both parsed tech_stack and raw description
    job_tech = set(t.lower() for t in job.tech_stack)
    desc_lower = job.description.lower()

    # Check exclusions first - reject if excluded tech appears
    for excluded in config.get("exclude", []):
        excluded_lower = excluded.lower()
        if excluded_lower in job_tech or excluded_lower in desc_lower:
            return False

    required = config.get("require_any", [])
    min_match = config.get("min_match", 1)

    if not required:
        return True

    matches = 0
    for tech in required:
        tech_lower = tech.lower()
        if tech_lower in job_tech or tech_lower in desc_lower:
            matches += 1

    return matches >= min_match


def parse_experience_level(text: str) -> dict:
    """Extract experience requirements from job description/title"""
    result = {"years_min": None, "years_max": None, "level": None}
    text_lower = text.lower()

    # Parse "X+ years" pattern
    plus_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", text_lower)
    if plus_match:
        result["years_min"] = int(plus_match.group(1))

    # Parse "X-Y years" range pattern (must check before plus pattern overwrites)
    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)", text_lower)
    if range_match:
        result["years_min"] = int(range_match.group(1))
        result["years_max"] = int(range_match.group(2))

    # Detect experience level keywords
    if re.search(r"\b(?:junior|jr\.?|entry[- ]?level)\b", text_lower):
        result["level"] = "junior"
    elif re.search(r"\b(?:senior|sr\.?)\b", text_lower):
        result["level"] = "senior"
    elif re.search(r"\b(?:mid[- ]?level|intermediate)\b", text_lower):
        result["level"] = "mid"

    return result


def passes_experience_filter(job: JobPost, config: dict) -> bool:
    """Check if job matches experience requirements"""
    if not config:
        return True

    max_years = config.get("max_years")
    allowed_levels = config.get("levels", [])

    # Parse experience from both title and description
    title_exp = parse_experience_level(job.title)
    desc_exp = parse_experience_level(job.description)

    # Use title experience if available, else description
    years_min = title_exp["years_min"] or desc_exp["years_min"]
    level = title_exp["level"] or desc_exp["level"]

    # If no experience mentioned, pass the filter
    if years_min is None and level is None:
        return True

    # Check max years requirement
    if max_years is not None and years_min is not None:
        if years_min > max_years:
            return False

    # Check level requirement
    if allowed_levels and level is not None:
        if level not in allowed_levels:
            return False

    return True


def filter_job(job: JobPost, config: dict) -> bool:
    """Returns True if job passes all filters"""
    if not passes_role_filter(job, config.get("role", {})):
        return False
    if not passes_location_filter(job, config.get("location", {})):
        return False
    if not passes_company_filter(job, config.get("company", {})):
        return False
    if not passes_tech_filter(job, config.get("tech", {})):
        return False
    if not passes_experience_filter(job, config.get("experience", {})):
        return False
    return True
