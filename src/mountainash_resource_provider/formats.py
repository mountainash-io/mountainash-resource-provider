"""Normalization for provider-published and resource-supplied format tokens."""

from __future__ import annotations

import re

from .errors import ProviderFormatError

_ASCII_WHITESPACE = " \t\r\n\f\v"
_FORMAT_NAME = re.compile(r"[a-z0-9][a-z0-9._+-]*\Z")
_HTTP_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")
_LOCATOR_SCHEME = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*):")


def normalize_format_name(raw: str) -> str:
    """Normalize a physical format identifier."""
    if not isinstance(raw, str):
        raise ProviderFormatError("format name must be a string")
    normalized = raw.strip(_ASCII_WHITESPACE).casefold()
    if not normalized or _FORMAT_NAME.fullmatch(normalized) is None:
        raise ProviderFormatError(f"invalid format name: {raw!r}")
    return normalized


def normalize_suffix(raw: str) -> str:
    """Normalize a filename suffix to one leading dot."""
    if not isinstance(raw, str):
        raise ProviderFormatError("suffix must be a string")
    return f".{normalize_format_name(raw.strip(_ASCII_WHITESPACE).lstrip('.'))}"


def normalize_mediatype(raw: str, *, published: bool = False) -> str:
    """Normalize a media type, rejecting parameters in published declarations."""
    if not isinstance(raw, str):
        raise ProviderFormatError("mediatype must be a string")
    parts = raw.strip(_ASCII_WHITESPACE).split(";")
    if published and len(parts) > 1:
        raise ProviderFormatError("published mediatypes cannot include parameters")
    media = parts[0]
    if media.count("/") != 1:
        raise ProviderFormatError(f"invalid mediatype: {raw!r}")
    type_part, subtype_part = (
        part.strip(_ASCII_WHITESPACE).casefold() for part in media.split("/")
    )
    if not _HTTP_TOKEN.fullmatch(type_part) or not _HTTP_TOKEN.fullmatch(subtype_part):
        raise ProviderFormatError(f"invalid mediatype: {raw!r}")
    return f"{type_part}/{subtype_part}"


def normalize_locator_prefix(raw: str) -> str:
    """Case-fold a locator scheme while preserving its remaining characters."""
    if not isinstance(raw, str):
        raise ProviderFormatError("locator prefix must be a string")
    match = _LOCATOR_SCHEME.match(raw)
    if match is None:
        raise ProviderFormatError(f"invalid locator prefix: {raw!r}")
    return f"{match.group('scheme').casefold()}{raw[match.end() - 1:]}"


__all__ = [
    "normalize_format_name",
    "normalize_locator_prefix",
    "normalize_mediatype",
    "normalize_suffix",
]
