"""Bank-supplied file contracts, safe Excel ingestion, and data-quality controls (WP1)."""

from lrm_data.loader import LoadResult, LoadedSource, load_xlsx
from lrm_data.validation import BatchResult, validate_batch

__all__ = ["BatchResult", "LoadResult", "LoadedSource", "load_xlsx", "validate_batch"]
