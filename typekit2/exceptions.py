# this_file: typekit2/exceptions.py
"""Typed errors raised by typekit2."""

from __future__ import annotations

from typing import Any


class TypekitError(Exception):
    """Base class for all package errors."""


class TypekitConfigurationError(TypekitError):
    """The client cannot be configured from explicit arguments or the environment."""


class TypekitAPIError(TypekitError):
    """Adobe Fonts rejected a request or returned an invalid response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        errors: list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []
