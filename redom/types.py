"""Pure stdlib dataclasses for ReDOM schema and record types."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class FieldRule:
    """Defines how to extract a single field from a record element."""
    name: str
    selector: str
    kind: str  # "string" | "currency" | "date" — Phase 1 set, closed enum


@dataclass(frozen=True)
class AnchorRule:
    """Defines how to identify and resolve context-carrying elements."""
    selector: str  # e.g. "h2"
    role: str  # e.g. "date_header"
    resolve: str  # "literal" | "relative_date" — Phase 1 set, closed enum


@dataclass(frozen=True)
class ExtractionSchema:
    """Complete schema for extracting flat records from hierarchical HTML."""
    source: str
    anchors: Tuple[AnchorRule, ...]
    record_selector: str
    inherits: str  # role name a record inherits from the nearest preceding anchor
    fields: Tuple[FieldRule, ...]
    on_unresolved: str  # "flag" | "skip" | "error" — Phase 1: only "flag" implemented
    reference_date: str = ""  # ISO date string for relative_date resolution


@dataclass(frozen=True)
class Record:
    """A flat record with reattached parent context."""
    fields: dict  # extracted field values by name
    context: dict  # reattached parent context, e.g. {"date_header": "2026-04-09"}
    unresolved: bool  # True if context could not be resolved
