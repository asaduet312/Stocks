"""Dynamic HTML table parser for PSX trading-board pages."""
from __future__ import annotations

import logging

from bs4 import BeautifulSoup, Tag

from psxdata.constants import COLUMN_MAP
from psxdata.parsers.normalizers import normalize_column_name

logger = logging.getLogger(__name__)


def extract_table_headers(table: Tag) -> list[str]:
    """Extract and normalise column headers from a single table element."""
    th_tags = table.find_all("th")
    if not th_tags:
        return []
    headers: list[str] = []
    for th in th_tags:
        raw = th.get_text(strip=True)
        if raw in COLUMN_MAP:
            headers.append(COLUMN_MAP[raw])
        else:
            normalised = normalize_column_name(raw)
            if raw:
                logger.warning(
                    "Unknown PSX column header %r — using fallback name %r.",
                    raw,
                    normalised,
                )
            headers.append(normalised)
    return headers


def parse_table_rows(table: Tag, headers: list[str]) -> list[dict[str, str]]:
    """Map <tr><td> rows to dicts keyed by normalised header name."""
    rows: list[dict[str, str]] = []
    tbody = table.find("tbody")
    tr_tags = tbody.find_all("tr") if tbody else table.find_all("tr")

    for tr in tr_tags:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cells:
            continue
        if len(cells) != len(headers):
            logger.warning(
                "Row has %d cells but expected %d — partial mapping applied",
                len(cells),
                len(headers),
            )
        row = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        rows.append(row)
    return rows


def parse_html_table(html: str) -> list[dict[str, str]]:
    """Parse the first HTML table in html, returning rows as normalised dicts."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        logger.warning("No table found in HTML — returning empty result")
        return []
    headers = extract_table_headers(table)
    if not headers:
        logger.warning("No table headers found in HTML — returning empty result")
        return []
    return parse_table_rows(table, headers)
