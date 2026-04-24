from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config
from .crawler import DeepScraper

app = typer.Typer(help="Scraper profundo para atas vigentes e aditivos do Grupo VR.")
console = Console()


@app.command()
def run(
    config_path: Path = typer.Option(Path("config/sources.yaml"), "--config", "-c", exists=True),
) -> None:
    cfg = load_config(config_path)
    scraper = DeepScraper(cfg)

    console.print(f"[bold cyan]Iniciando scraping[/] para segmento: {cfg.segmento}")
    rows = scraper.crawl()
    json_path, csv_path = scraper.save(rows)

    table = Table(title="Resumo da coleta")
    table.add_column("Tipo")
    table.add_column("Qtd")

    for kind in ("ata_vigente", "aditivo_grupo_vr"):
        table.add_row(kind, str(sum(1 for r in rows if r.tipo == kind)))

    console.print(table)
    console.print(f"Total de registros: [bold]{len(rows)}[/bold]")
    console.print(f"JSON: {json_path}")
    console.print(f"CSV: {csv_path}")


if __name__ == "__main__":
    app()
