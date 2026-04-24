from __future__ import annotations

import csv
import io
import json
import re
from collections import deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from pypdf import PdfReader
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import ScraperConfig


@dataclass
class Record:
    tipo: str
    fonte: str
    url: str
    titulo: str
    trecho: str
    data_identificada: str | None
    score_relevancia: int


class DeepScraper:
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.client = httpx.Client(
            timeout=config.request_timeout_seconds,
            headers={"User-Agent": config.user_agent},
            follow_redirects=True,
        )
        self.visited: set[str] = set()
        self.records: list[Record] = []

    def _domain_allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == d or host.endswith(f".{d}") for d in self.config.domains_allowlist)

    def _is_candidate_file(self, url: str) -> bool:
        path = (urlparse(url).path or "").lower()
        return any(path.endswith(ext.lower()) for ext in self.config.file_extensions)

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    def _get(self, url: str) -> httpx.Response:
        return self.client.get(url)

    def _extract_links(self, base_url: str, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for a in soup.select("a[href]"):
            href = a.get("href", "").strip()
            if not href or href.startswith(("mailto:", "javascript:")):
                continue
            resolved = urljoin(base_url, href)
            if resolved.startswith("http") and self._domain_allowed(resolved):
                links.append(resolved)
        return links

    def _extract_text_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))

    def _extract_text_pdf(self, raw: bytes) -> str:
        pdf = PdfReader(io.BytesIO(raw))
        chunks: list[str] = []
        for page in pdf.pages[:20]:
            chunks.append(page.extract_text() or "")
        return re.sub(r"\s+", " ", " ".join(chunks)).strip()

    def _score(self, text: str) -> tuple[int, str]:
        low = text.lower()
        hits = [k for k in self.config.all_keywords if k in low]
        score = len(hits)
        trecho = text[:700]
        return score, trecho

    def _infer_date(self, text: str) -> str | None:
        patterns = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
        for raw in patterns[:10]:
            try:
                dt = parse_date(raw, dayfirst=True)
                return dt.date().isoformat()
            except Exception:
                continue
        return None

    def _classify(self, text: str) -> str | None:
        low = text.lower()
        is_ata = any(k in low for k in self.config.keywords_atas)
        is_vigencia = any(k in low for k in self.config.keywords_vigencia)
        is_vr = any(k in low for k in self.config.keywords_grupo_vr)
        if is_ata and is_vigencia:
            return "ata_vigente"
        if is_vr:
            return "aditivo_grupo_vr"
        return None

    def crawl(self) -> list[Record]:
        queue = deque((u, 0) for u in self.config.seed_urls)

        while queue and len(self.visited) < self.config.max_pages:
            url, depth = queue.popleft()
            if url in self.visited or depth > self.config.max_depth:
                continue
            self.visited.add(url)

            try:
                resp = self._get(url)
            except Exception:
                continue

            ctype = (resp.headers.get("content-type") or "").lower()
            text = ""
            if "text/html" in ctype:
                text = self._extract_text_html(resp.text)
                for link in self._extract_links(url, resp.text):
                    if link not in self.visited:
                        queue.append((link, depth + 1))
            elif "application/pdf" in ctype or url.lower().endswith(".pdf"):
                try:
                    text = self._extract_text_pdf(resp.content)
                except Exception:
                    text = ""
            elif self._is_candidate_file(url):
                text = resp.text[:5000]

            if not text:
                continue

            tipo = self._classify(text)
            if not tipo:
                continue

            score, trecho = self._score(text)
            title = text[:120]
            self.records.append(
                Record(
                    tipo=tipo,
                    fonte=urlparse(url).netloc,
                    url=url,
                    titulo=title,
                    trecho=trecho,
                    data_identificada=self._infer_date(text),
                    score_relevancia=score,
                )
            )

        return sorted(self.records, key=lambda r: r.score_relevancia, reverse=True)

    def save(self, rows: list[Record]) -> tuple[Path, Path]:
        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

        json_path = out / f"resultados_{ts}.json"
        csv_path = out / f"resultados_{ts}.csv"

        with json_path.open("w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in rows], f, ensure_ascii=False, indent=2)

        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else [
                "tipo", "fonte", "url", "titulo", "trecho", "data_identificada", "score_relevancia"
            ])
            writer.writeheader()
            for r in rows:
                writer.writerow(asdict(r))

        return json_path, csv_path
