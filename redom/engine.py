"""Reattachment engine — pure function over (schema, html) → records."""

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from typing import List, Optional

from .types import ExtractionSchema, Record, AnchorRule


def _resolve_relative_date(text: str, reference_date: str) -> Optional[str]:
    """Resolve relative or absolute date text to ISO date string.
    
    Args:
        text: Date text like "Yesterday", "Today", "Thursday, April 9th"
        reference_date: ISO date string (YYYY-MM-DD) to resolve relatives against
    
    Returns:
        ISO date string or None if unparseable.
    """
    if not reference_date:
        return None
    
    text = text.strip()
    ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
    
    # Relative dates
    lower_text = text.lower()
    if lower_text == "today":
        return reference_date
    elif lower_text == "yesterday":
        yesterday = ref_date - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
    
    # Absolute dates: patterns like "Thursday, April 9th", "April 9th", "Apr 9"
    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', text)
    
    # Try various date formats
    date_formats = [
        "%A, %B %d",      # Thursday, April 9
        "%A, %b %d",      # Thursday, Apr 9
        "%B %d",          # April 9
        "%b %d",          # Apr 9
        "%A, %B %d %Y",   # Thursday, April 9 2026
        "%B %d %Y",       # April 9 2026
        "%b %d %Y",       # Apr 9 2026
        "%Y-%m-%d",       # 2026-04-09 (already ISO)
    ]
    
    current_year = ref_date.year
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            # If year not in format, use reference year
            if "%Y" not in fmt:
                parsed = parsed.replace(year=current_year)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def _coerce_value(value: str, kind: str) -> str:
    """Coerce a raw string value according to its kind.
    
    Args:
        value: Raw extracted text
        kind: One of "string", "currency", "date"
    
    Returns:
        Coerced string value.
    """
    value = value.strip()
    
    if kind == "string":
        return value
    
    elif kind == "currency":
        # Extract numeric portion, preserve sign
        # Remove currency symbols, whitespace, commas
        cleaned = re.sub(r'[$,\s]', '', value)
        return cleaned
    
    elif kind == "date":
        # Assume already in ISO format or pass through
        return value
    
    return value


def _element_matches_selector(element, selector: str) -> bool:
    """Check if a BeautifulSoup element matches a CSS selector.
    
    Supports: element names ("h2"), class selectors (".transaction" or ".flex.flex-row"),
    and multi-class Tailwind-style selectors (".flex.flex-row.gap-4")
    """
    if not selector:
        return False
    
    # Class selector (.class or .class1.class2.class3 for Tailwind)
    if selector.startswith('.'):
        # Split by dots and filter empty strings (first dot creates empty)
        required_classes = [c for c in selector.split('.') if c]
        element_classes = element.get('class', [])
        # All required classes must be present
        return all(cls in element_classes for cls in required_classes)
    
    # ID selector (#id) - not commonly used but handle it
    if selector.startswith('#'):
        return element.get('id') == selector[1:]
    
    # Element name (h2, div, etc.)
    return element.name == selector


def extract(schema: ExtractionSchema, html: str) -> List[Record]:
    """Extract flat records from HTML according to schema.
    
    Pure function: same (schema, html) inputs always produce same outputs.
    No I/O, no clock access, no side effects.
    
    Algorithm:
    1. Parse HTML with BeautifulSoup
    2. Walk elements in document order
    3. When anchor matches: resolve and store in current_context
    4. When record matches: extract fields, attach context copy
    5. If inherits role missing from context: mark unresolved
    
    Args:
        schema: ExtractionSchema defining anchors, records, fields
        html: HTML document string
    
    Returns:
        List of Record objects in document order.
    """
    soup = BeautifulSoup(html, 'html.parser')
    records: List[Record] = []
    
    # Current context accumulates anchor values by role
    current_context: dict = {}
    
    # Build anchor role lookup by selector for quick matching
    anchor_by_selector = {a.selector: a for a in schema.anchors}
    anchor_selectors = list(anchor_by_selector.keys())
    
    # Get all elements in document order
    all_elements = soup.find_all(True)
    
    for element in all_elements:
        # Check if this element matches any anchor selector
        matched_anchor = None
        for selector in anchor_selectors:
            if _element_matches_selector(element, selector):
                matched_anchor = anchor_by_selector[selector]
                break
        
        if matched_anchor:
            # Resolve anchor text and update context
            text = element.get_text(strip=True)
            
            if matched_anchor.resolve == "literal":
                current_context[matched_anchor.role] = text
            elif matched_anchor.resolve == "relative_date":
                resolved = _resolve_relative_date(text, schema.reference_date)
                if resolved:
                    current_context[matched_anchor.role] = resolved
                # If unresolvable, context for this role is not updated
                # Following records will see old value or be unresolved
        
        # Check if this element matches the record selector
        if _element_matches_selector(element, schema.record_selector):
            # Extract fields from this record element
            fields = {}
            for field in schema.fields:
                field_elem = element.select_one(field.selector)
                if field_elem:
                    raw_value = field_elem.get_text(strip=True)
                    fields[field.name] = _coerce_value(raw_value, field.kind)
                else:
                    fields[field.name] = ""
            
            # Check if inherits role is in context
            inherits_role = schema.inherits
            unresolved = False
            context_copy = dict(current_context)
            
            if inherits_role not in current_context:
                unresolved = True
                if schema.on_unresolved == "flag":
                    # Leave context key out, mark unresolved
                    pass
            
            record = Record(
                fields=fields,
                context=context_copy,
                unresolved=unresolved
            )
            records.append(record)
    
    return records
