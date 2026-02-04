import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command()
def run(
    sources: str = typer.Option("hn_hiring", help="Comma-separated sources"),
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

    table.add_row("Total Jobs", str(total))
    table.add_row("Synced", str(synced))
    table.add_row("Pending", str(pending))

    console.print(table)


if __name__ == "__main__":
    app()
