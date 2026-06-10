#!/usr/bin/env python3
"""Verify amount fields contain actual dollar values, not date text."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from redom import load_schema, extract

schema = load_schema('schemas/chime_transactions.yaml')
html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
records = extract(schema, html)

print('=== AMOUNT FIELD VERIFICATION ===')
print(f'Total records: {len(records)}')
print()

for i, r in enumerate(records):
    amt = r.fields.get('amount', 'MISSING')
    desc = r.fields.get('description', 'MISSING')[:30]  # Truncate long desc
    unresolved = r.unresolved
    ctx = r.context.get('date_header', 'N/A')
    print(f'Record {i}: amount="{amt}" | desc="{desc}..." | date={ctx} | unresolved={unresolved}')

print()
print('=== VALIDATION ===')
amounts_valid = all(
    r.fields.get('amount', '').replace('.', '').replace('-', '').replace('+', '').isdigit()
    or r.fields.get('amount', '') == ''
    for r in records
)
if amounts_valid:
    print('✓ All amount fields contain numeric values (dollar amounts)')
else:
    print('✗ ERROR: Some amount fields contain non-numeric text (dates/labels)')
    sys.exit(1)
