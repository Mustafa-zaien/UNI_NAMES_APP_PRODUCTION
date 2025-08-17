"""Doctor Cleaner package.

This package provides a structured interface for:
- Loading/updating the golden reference (Repository pattern)
- Running the processing pipeline (Service layer)
- CLI entrypoint to integrate with desktop apps
"""

__all__ = [
    "config",
    "repository",
    "pipeline",
    "cli",
]
