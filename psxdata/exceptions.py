"""Custom exception hierarchy for psxdata."""


class PSXDataError(Exception):
    """Base exception for all psxdata library errors."""


class PSXUnavailableError(PSXDataError):
    """PSX server is unreachable or returned a 5xx response."""


class PSXConnectionError(PSXUnavailableError):
    """Network-level failure — DNS, connection refused, or timeout."""


class PSXServerError(PSXUnavailableError):
    """PSX server was reached but returned a 5xx HTTP response."""


class PSXAuthError(PSXDataError):
    """PSX returned 401 or 403."""


class PSXRateLimitError(PSXDataError):
    """PSX returned 429 — rate limit exceeded."""


class PSXParseError(PSXDataError):
    """HTML structure changed or response could not be parsed."""
