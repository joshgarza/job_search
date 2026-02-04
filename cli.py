import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command()
def run(
    sources: str = typer.Option("hn_hiring,indeed", help="Comma-separated sources (hn_hiring,indeed,wellfound)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without syncing"),
):
    """Scrape and sync job leads"""
    from src.pipeline import run_pipeline

    source_list = [s.strip() for s in sources.split(",")]
    run_pipeline(source_list, dry_run=dry_run)


@app.command()
def status():
    """Show pipeline statistics"""
    from src.db import JobDatabase

    db = JobDatabase()

    table = Table(title="Pipeline Status")
    table.add_column("Metric")
    table.add_column("Value")

    total = len(list(db.db["jobs"].rows))
    synced = len(list(db.db["jobs"].rows_where("synced_at is not null")))
    pending = total - synced

    # Count by source
    by_source = {}
    for job in db.db["jobs"].rows:
        src = job.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    table.add_row("Total Jobs", str(total))
    table.add_row("Synced", str(synced))
    table.add_row("Pending", str(pending))
    for src, count in sorted(by_source.items()):
        table.add_row(f"  {src}", str(count))

    console.print(table)


@app.command()
def clear_cache(
    source: str = typer.Option(None, help="Only clear jobs from this source"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear the job cache database"""
    from src.db import JobDatabase

    db = JobDatabase()

    if source:
        jobs = list(db.db["jobs"].rows_where("source = ?", [source]))
        count = len(jobs)
        target = f"{count} jobs from '{source}'"
    else:
        count = len(list(db.db["jobs"].rows))
        target = f"all {count} jobs"

    if count == 0:
        console.print("No jobs to clear.")
        return

    if not confirm:
        if not typer.confirm(f"Clear {target}?"):
            console.print("Aborted.")
            return

    if source:
        db.db.execute("DELETE FROM jobs WHERE source = ?", [source])
    else:
        db.db.execute("DELETE FROM jobs")

    console.print(f"Cleared {target}.")


if __name__ == "__main__":
    app()
