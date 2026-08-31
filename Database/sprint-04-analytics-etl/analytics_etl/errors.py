"""Custom exception types for the analytics ETL pipeline."""


class ClientError(RuntimeError):
    """Raised when a Fauxnance API request cannot be completed."""


class RateLimitError(RuntimeError):
    """Raised when the API daily quota has been reached."""


class SymbolRequestError(RuntimeError):
    """Raised when the API rejects one symbol request."""


class NetworkError(RuntimeError):
    """Raised when a request cannot reach the API after retries."""


class PayloadError(RuntimeError):
    """Raised when the API response is not valid JSON."""


class ServerError(RuntimeError):
    """Raised when the API remains unavailable after server-error retries."""
