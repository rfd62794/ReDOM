"""Schema loading and validation."""

import yaml
from typing import Union

from .types import ExtractionSchema, AnchorRule, FieldRule


class SchemaError(Exception):
    """Raised when schema validation fails."""
    pass


# Closed enums per Phase 1 spec
VALID_KINDS = {"string", "currency", "date"}
VALID_RESOLVE = {"literal", "relative_date"}
VALID_ON_UNRESOLVED = {"flag", "skip", "error"}


def load_schema(path_or_str: Union[str, bytes]) -> ExtractionSchema:
    """Load and validate a YAML schema into typed ExtractionSchema.
    
    Args:
        path_or_str: Either a file path (str) or YAML content (str/bytes).
    
    Returns:
        Validated ExtractionSchema instance.
    
    Raises:
        SchemaError: On unknown enum values or malformed YAML.
    """
    # Determine if input is a path or raw YAML
    if isinstance(path_or_str, str) and '\n' not in path_or_str and path_or_str.endswith('.yaml'):
        with open(path_or_str, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    else:
        data = yaml.safe_load(path_or_str)
    
    # Validate source
    source = data.get('source', '')
    if not source:
        raise SchemaError("Schema missing required 'source' field")
    
    # Validate anchors
    anchors_data = data.get('anchors', [])
    anchors = []
    for i, anchor_data in enumerate(anchors_data):
        selector = anchor_data.get('selector', '')
        role = anchor_data.get('role', '')
        resolve = anchor_data.get('resolve', '')
        
        if resolve not in VALID_RESOLVE:
            raise SchemaError(
                f"Unknown 'resolve' value '{resolve}' at anchor[{i}]. "
                f"Valid: {VALID_RESOLVE}"
            )
        
        anchors.append(AnchorRule(
            selector=selector,
            role=role,
            resolve=resolve
        ))
    
    # Validate record_selector
    record_selector = data.get('record_selector', '')
    if not record_selector:
        raise SchemaError("Schema missing required 'record_selector' field")
    
    # Validate inherits
    inherits = data.get('inherits', '')
    if not inherits:
        raise SchemaError("Schema missing required 'inherits' field")
    
    # Validate fields
    fields_data = data.get('fields', [])
    fields = []
    for i, field_data in enumerate(fields_data):
        name = field_data.get('name', '')
        selector = field_data.get('selector', '')
        kind = field_data.get('kind', '')
        
        if kind not in VALID_KINDS:
            raise SchemaError(
                f"Unknown 'kind' value '{kind}' at field[{i}] (name='{name}'). "
                f"Valid: {VALID_KINDS}"
            )
        
        fields.append(FieldRule(
            name=name,
            selector=selector,
            kind=kind
        ))
    
    # Validate on_unresolved
    on_unresolved = data.get('on_unresolved', 'flag')
    if on_unresolved not in VALID_ON_UNRESOLVED:
        raise SchemaError(
            f"Unknown 'on_unresolved' value '{on_unresolved}'. "
            f"Valid: {VALID_ON_UNRESOLVED}"
        )
    
    # Get reference_date (optional, for relative_date resolution)
    reference_date = data.get('reference_date', '')
    
    return ExtractionSchema(
        source=source,
        anchors=tuple(anchors),
        record_selector=record_selector,
        inherits=inherits,
        fields=tuple(fields),
        on_unresolved=on_unresolved,
        reference_date=reference_date
    )
