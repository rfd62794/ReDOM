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
        assert schema.record_selector == "a.group.flex.flex-col"
        assert schema.inherits == "date_header"
        assert schema.on_unresolved == "flag"
        assert schema.reference_date == "2026-06-10"

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


# Test 4: Engine selector parsing
class TestSelectorParsing:
    def test_tag_plus_class_selector_parses_correctly(self):
        """Selector 'a.group.flex.flex-col' parses to tag 'a' + classes ['group', 'flex', 'flex-col']."""
        from redom.engine import _element_matches_selector
        from bs4 import BeautifulSoup
        
        # Create test HTML with matching and non-matching elements
        html = '''
        <a class="group flex flex-col">Match</a>
        <a class="group flex">Partial</a>
        <div class="group flex flex-col">Wrong tag</div>
        <span class="group flex flex-col">Also wrong tag</span>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        # Should match the anchor with all three classes
        match = soup.find(string="Match").parent
        assert _element_matches_selector(match, "a.group.flex.flex-col") is True
        
        # Should NOT match partial class match
        partial = soup.find(string="Partial").parent
        assert _element_matches_selector(partial, "a.group.flex.flex-col") is False
        
        # Should NOT match wrong tag
        wrong_tag = soup.find(string="Wrong tag").parent
        assert _element_matches_selector(wrong_tag, "a.group.flex.flex-col") is False
        
        # Should NOT match different tag
        also_wrong = soup.find(string="Also wrong tag").parent
        assert _element_matches_selector(also_wrong, "a.group.flex.flex-col") is False


# Test 5-8: Engine behavior with real fixture
class TestEngine:
    def test_extract_reattaches_date_to_records(self, schema, html):
        """Each record's context["date_header"] matches the header it sat under."""
        records = extract(schema, html)
        
        # Exactly 9 transactions (no duplicates, no noise)
        assert len(records) == 9, f"Expected 9 records, got {len(records)}"
        
        # Every record must have description and amount fields
        for r in records:
            assert "description" in r.fields
            assert "amount" in r.fields
        
        # Amounts must be actual dollar values (coerced to numeric strings)
        for r in records:
            amt = r.fields["amount"]
            # After currency coercion: "-$99.99" -> "-99.99"
            assert amt.replace('.', '').replace('-', '').replace('+', '').isdigit(), \
                f"Amount '{amt}' is not a dollar value"
        
        # Records with date context have valid reattachment
        dated_records = [r for r in records if not r.unresolved]
        assert len(dated_records) >= 6, f"Expected >=6 dated records, got {len(dated_records)}"
        for r in dated_records:
            assert "date_header" in r.context
            assert r.context["date_header"]  # Non-empty date

    def test_relative_date_resolves_against_reference(self, schema, html):
        """"Yesterday" resolves to reference_date − 1, ISO format."""
        records = extract(schema, html)
        
        # Find records with Yesterday-derived date (2026-06-09 from ref_date 2026-06-10)
        yesterday_records = [r for r in records if r.context.get("date_header") == "2026-06-09"]
        
        # Should have exactly 6 records under Yesterday (the dated transactions)
        assert len(yesterday_records) == 6, f"Expected 6 Yesterday records, got {len(yesterday_records)}"
        for r in yesterday_records:
            assert not r.unresolved, "Yesterday records should be resolved"

    def test_absolute_header_parses_to_iso(self, schema, html):
        """Absolute date headers parse to ISO format."""
        records = extract(schema, html)
        
        # Dated records should have valid ISO date format
        dated_records = [r for r in records if not r.unresolved]
        
        for r in dated_records:
            date_val = r.context.get("date_header", "")
            # YYYY-MM-DD format: 10 chars, dashes at positions 4 and 7
            assert len(date_val) == 10 and date_val[4] == '-' and date_val[7] == '-', \
                f"Date '{date_val}' is not ISO format"

    def test_unresolved_header_flags_record(self, schema, html):
        """A record with no resolvable preceding anchor → unresolved=True."""
        records = extract(schema, html)
        
        # Exactly 3 records before first h2 (Available section) should be unresolved
        unresolved_records = [r for r in records if r.unresolved]
        assert len(unresolved_records) == 3, f"Expected 3 unresolved records, got {len(unresolved_records)}"
        
        for r in unresolved_records:
            assert "date_header" not in r.context, "Unresolved records should have no date_header"
            assert r.fields["description"], "Unresolved records should still have description"
            assert r.fields["amount"], "Unresolved records should still have amount"

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
