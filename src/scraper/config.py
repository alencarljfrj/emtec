from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    segmento: str
    seed_urls: list[str]
    domains_allowlist: list[str]
    max_depth: int = 4
    max_pages: int = 500
    request_timeout_seconds: int = 30
    concurrency: int = 6
    user_agent: str = "AtasVigentesBot/1.0"
    keywords_atas: list[str] = Field(default_factory=list)
    keywords_vigencia: list[str] = Field(default_factory=list)
    keywords_grupo_vr: list[str] = Field(default_factory=list)
    file_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".html"])
    output_dir: str = "output"

    @property
    def all_keywords(self) -> set[str]:
        return {k.lower().strip() for k in [*self.keywords_atas, *self.keywords_vigencia, *self.keywords_grupo_vr]}


def load_config(path: str | Path) -> ScraperConfig:
    with Path(path).expanduser().open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    return ScraperConfig.model_validate(payload)
