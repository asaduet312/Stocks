"""PSX endpoint URLs, timeouts, rate limits, and column mappings."""

BASE_URL = "https://dps.psx.com.pk"

ENDPOINTS: dict[str, str] = {
    "trading_board": "/trading-board",
}

REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://dps.psx.com.pk/",
    "X-Requested-With": "XMLHttpRequest",
}

REQUEST_TIMEOUT: int = 30
MAX_RETRIES: int = 3
RETRY_DELAYS: tuple[int, ...] = (1, 2)

if len(RETRY_DELAYS) != MAX_RETRIES - 1:
    raise ValueError(
        f"constants.py misconfigured: len(RETRY_DELAYS)={len(RETRY_DELAYS)} "
        f"must equal MAX_RETRIES-1={MAX_RETRIES - 1}"
    )

MAX_REQUESTS_PER_SECOND: int = 2

BOARDS: tuple[str, ...] = ("main", "gem", "bnb")
MARKETS: tuple[str, ...] = ("REG", "ODL", "DFC", "SQR", "CSF")

# Raw PSX <th> header text -> internal snake_case name.
COLUMN_MAP: dict[str, str] = {
    "SYMBOL": "symbol",
    "Symbol": "symbol",
    "LDCP": "ldcp",
    "CURRENT": "current",
    "Current": "current",
    "CHANGE": "change",
    "CHANGE (%)": "change_pct",
    "% Change": "change_pct",
    "VOLUME": "volume",
    "TURNOVER": "turnover",
    "Turnover": "turnover",
    "BID VOL.": "bid_vol",
    "BID PRICE": "bid_price",
    "OFFER VOL.": "offer_vol",
    "OFFER PRICE": "offer_price",
    "BID YIELD (%)": "bid_yield",
    "OFFER YIELD (%)": "offer_yield",
    "LTP": "ltp",
    "LTY (%)": "lty",
    "LDCY (%)": "ldcy",
}
