#!/usr/bin/env python3
"""Check what dates records actually have."""

import sys
sys.path.insert(0, 'c:\\Github\\ReDOM')

from pathlib import Path
from redom import load_schema, extract

schema = load_schema('schemas/chime_transactions.yaml')
html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
records = extract(schema, html)

print("=== RECORD DATES ===")
dates = {}
for i, r in enumerate(records):
    date = r.context.get('date_header', 'N/A')
    unresolved = r.unresolved
    key = f"{date} (unresolved={unresolved})"
    if key not in dates:
        dates[key] = []
    dates[key].append(f"Record {i}: {r.fields.get('description', 'N/A')[:20]}")

for date_key, recs in sorted(dates.items()):
    print(f"\n{date_key}:")
    for r in recs:
        print(f"  {r}")
