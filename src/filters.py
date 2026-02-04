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

    required = config.get("require_any", [])
    min_match = config.get("min_match", 1)

    if not required:
        return True

    # Check both parsed tech_stack and raw description
    job_tech = set(t.lower() for t in job.tech_stack)
    desc_lower = job.description.lower()

    matches = 0
    for tech in required:
        tech_lower = tech.lower()
        if tech_lower in job_tech or tech_lower in desc_lower:
            matches += 1

    return matches >= min_match


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
    return True
