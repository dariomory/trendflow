"""Console script for trendflow."""

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main() -> None:
    """Console script for trendflow."""
    console.print("trendflow.cli.main")


if __name__ == "__main__":
    app()
