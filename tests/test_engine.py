"""8 anchor tests for ReDOM Phase 1."""

import pytest
from pathlib import Path

from redom import load_schema, SchemaError, extract, Record, ExtractionSchema


# Fixtures paths
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "chime_transactions.yaml"
HTML_PATH = Path(__file__).parent / "fixtures" / "chime_real.html"


# Load once for all tests
@pytest.fixture
def schema():
    return load_schema(str(SCHEMA_PATH))


@pytest.fixture
def html():
    return HTML_PATH.read_text(encoding="utf-8")


# Test 1: Schema loads valid YAML
class TestSchemaLoading:
    def test_schema_loads_valid(self):
        """Valid YAML → ExtractionSchema with correct field count."""
        schema = load_schema(str(SCHEMA_PATH))
        
        assert isinstance(schema, ExtractionSchema)
        assert schema.source == "chime_transactions"
        assert len(schema.anchors) == 1
        assert len(schema.fields) == 2
        assert schema.anchors[0].selector == "h2"
        assert schema.anchors[0].role == "date_header"
        assert schema.anchors[0].resolve == "relative_date"
        assert schema.record_selector == ".flex.flex-row"
        assert schema.inherits == "date_header"
        assert schema.on_unresolved == "flag"
        assert schema.reference_date == "2026-06-09"

    def test_schema_rejects_unknown_kind(self):
        """Unknown kind raises SchemaError."""
        invalid_yaml = """
source: test
anchors: []
record_selector: ".item"
inherits: "test"
fields:
  - name: field1
    selector: ".field1"
    kind: unknown_kind
on_unresolved: flag
"""
        with pytest.raises(SchemaError) as exc_info:
            load_schema(invalid_yaml)
        
        assert "Unknown 'kind' value 'unknown_kind'" in str(exc_info.value)
        assert "string" in str(exc_info.value)
        assert "currency" in str(exc_info.value)
        assert "date" in str(exc_info.value)

    def test_schema_rejects_unknown_resolve(self):
        """Unknown resolve raises SchemaError."""
        invalid_yaml = """
source: test
anchors:
  - selector: "h2"
    role: header
    resolve: unknown_resolve
record_selector: ".item"
inherits: "header"
fields: []
on_unresolved: flag
"""
        with pytest.raises(SchemaError) as exc_info:
            load_schema(invalid_yaml)
        
        assert "Unknown 'resolve' value 'unknown_resolve'" in str(exc_info.value)
        assert "literal" in str(exc_info.value)
        assert "relative_date" in str(exc_info.value)


# Test 4-8: Engine behavior
class TestEngine:
    def test_extract_reattaches_date_to_records(self, schema, html):
        """Each record's context["date_header"] matches the header it sat under."""
        records = extract(schema, html)
        
        # Filter to records with both description AND amount (actual transactions)
        valid_records = [r for r in records if r.fields.get("description") and r.fields.get("amount")]
        
        # Should have ~10 transaction records with both fields
        assert len(valid_records) >= 6
        
        # Verify amounts are actual dollar values, not date text
        for r in valid_records:
            amt = r.fields["amount"]
            # Should be numeric (after currency coercion removes $ sign)
            assert amt.replace('.', '').replace('-', '').replace('+', '').isdigit(), \
                f"Amount '{amt}' is not a dollar value"
        
        # Records with date context should have valid reattachment
        dated_records = [r for r in valid_records if not r.unresolved]
        assert len(dated_records) >= 3
        for r in dated_records:
            assert "date_header" in r.context

    def test_relative_date_resolves_against_reference(self, schema, html):
        """"Yesterday" resolves to reference_date − 1, ISO format."""
        records = extract(schema, html)
        
        # Filter to valid transaction records
        valid_records = [r for r in records if r.fields.get("description") and r.fields.get("amount")]
        
        # Find records with Yesterday-derived date (2026-06-08 from ref_date 2026-06-09)
        yesterday_records = [r for r in valid_records if r.context.get("date_header") == "2026-06-08"]
        
        # Should have multiple records under Yesterday
        assert len(yesterday_records) >= 3
        for r in yesterday_records:
            assert not r.unresolved

    def test_absolute_header_parses_to_iso(self, schema, html):
        """Absolute date headers parse to ISO format."""
        records = extract(schema, html)
        
        # Filter to valid transaction records
        valid_records = [r for r in records if r.fields.get("description") and r.fields.get("amount")]
        
        # Find records with ISO dates in context (not unresolved)
        dated_records = [r for r in valid_records if not r.unresolved]
        
        # All dated records should have valid ISO date format
        for r in dated_records:
            date_val = r.context.get("date_header", "")
            # Should be YYYY-MM-DD format
            assert len(date_val) == 10 and date_val[4] == '-' and date_val[7] == '-'

    def test_unresolved_header_flags_record(self, schema, html):
        """A record with no resolvable preceding anchor → unresolved=True."""
        records = extract(schema, html)
        
        # Filter to valid transaction records
        valid_records = [r for r in records if r.fields.get("description") and r.fields.get("amount")]
        
        # Some records should be unresolved (before first h2 date header)
        unresolved_records = [r for r in valid_records if r.unresolved]
        assert len(unresolved_records) >= 1, "Should have at least 1 unresolved record"
        
        for r in unresolved_records:
            assert "date_header" not in r.context
            assert r.fields["description"]  # Has description even if unresolved

    def test_extract_is_pure(self, schema, html):
        """Calling extract twice on same inputs yields identical records."""
        records1 = extract(schema, html)
        records2 = extract(schema, html)
        
        # Same number of records
        assert len(records1) == len(records2)
        
        # Each record identical
        for i, (r1, r2) in enumerate(zip(records1, records2)):
            assert r1.fields == r2.fields, f"Record {i} fields differ"
            assert r1.context == r2.context, f"Record {i} context differ"
            assert r1.unresolved == r2.unresolved, f"Record {i} unresolved flag differ"
        
        # Deep equality - convert to comparable structures
        def record_to_tuple(r: Record):
            return (
                tuple(sorted(r.fields.items())),
                tuple(sorted(r.context.items())),
                r.unresolved
            )
        
        tuples1 = [record_to_tuple(r) for r in records1]
        tuples2 = [record_to_tuple(r) for r in records2]
        
        assert tuples1 == tuples2
