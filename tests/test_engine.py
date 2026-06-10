"""8 anchor tests for ReDOM Phase 1."""

import pytest
from pathlib import Path

from redom import load_schema, SchemaError, extract, Record, ExtractionSchema


# Fixtures paths
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "chime_transactions.yaml"
HTML_PATH = Path(__file__).parent / "fixtures" / "chime_sample.html"


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
        assert schema.record_selector == ".transaction"
        assert schema.inherits == "date_header"
        assert schema.on_unresolved == "flag"
        assert schema.reference_date == "2026-04-10"

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
        
        # Fixture has 6 transaction records (1 orphan + 5 with context)
        assert len(records) == 6
        
        # Record 0: orphan (no preceding h2) - tested separately in test_unresolved_header_flags_record
        
        # Records 1-2 under "Yesterday" (reference_date 2026-04-10 - 1 = 2026-04-09)
        assert records[1].context["date_header"] == "2026-04-09"
        assert records[1].fields["description"] == "Starbucks Coffee"
        
        assert records[2].context["date_header"] == "2026-04-09"
        assert records[2].fields["description"] == "Grocery Store"
        
        # Records 3-4 under "Thursday, April 9th" (absolute date 2026-04-09)
        assert records[3].context["date_header"] == "2026-04-09"
        assert records[3].fields["description"] == "Gas Station"
        
        assert records[4].context["date_header"] == "2026-04-09"
        assert records[4].fields["description"] == "Direct Deposit"
        
        # Record 5 under "Tuesday, March 31st" (absolute date 2026-03-31)
        assert records[5].context["date_header"] == "2026-03-31"
        assert records[5].fields["description"] == "Electric Bill"

    def test_relative_date_resolves_against_reference(self, schema, html):
        """"Yesterday" resolves to reference_date − 1, ISO format."""
        records = extract(schema, html)
        
        # "Yesterday" with reference_date 2026-04-10 should resolve to 2026-04-09
        # Records at positions 1 and 2 are under "Yesterday"
        for i in [1, 2]:
            assert records[i].context["date_header"] == "2026-04-09"
            assert not records[i].unresolved

    def test_absolute_header_parses_to_iso(self, schema, html):
        """"Thursday, April 9th" → "2026-04-09"."""
        records = extract(schema, html)
        
        # Records 3 and 4 are under "Thursday, April 9th"
        for i in [3, 4]:
            assert records[i].context["date_header"] == "2026-04-09"
            assert not records[i].unresolved
        
        # Record 5 is under "Tuesday, March 31st"
        assert records[5].context["date_header"] == "2026-03-31"
        assert not records[5].unresolved

    def test_unresolved_header_flags_record(self, schema, html):
        """A record with no resolvable preceding anchor → unresolved=True."""
        records = extract(schema, html)
        
        # First record (orphan-record) has no preceding h2 header
        first_record = records[0]
        
        assert first_record.unresolved is True
        # Context should not have the inherits role (date_header)
        assert "date_header" not in first_record.context
        assert first_record.fields["description"] == "Mystery Charge"

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
