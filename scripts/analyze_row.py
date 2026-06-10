#!/usr/bin/env python3
"""Analyze a single transaction row structure."""

import re
from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

# Find transaction rows
rows = soup.select('.flex.flex-row.gap-4')

print(f'Found {len(rows)} transaction rows')
print()

# Analyze first row
if rows:
    row = rows[0]
    print('=== FIRST ROW STRUCTURE ===')
    print(f'Row classes: {row.get("class", [])}')
    print()
    
    # Look at all children
    for i, child in enumerate(row.find_all(recursive=False)):
        print(f'Child {i}: {child.name} classes={child.get("class", [])}')
        
        # Look for text content
        text = child.get_text(strip=True)
        if text:
            print(f'  Text: "{text[:80]}"')
        print()

print()
print('=== LOOKING FOR AMOUNT WITHIN ROW ===')
for row in rows[:1]:
    # Find the amount div
    amount_elem = row.select_one('.flex-none.text-right.text-label')
    if amount_elem:
        print(f'Amount element found: {amount_elem}')
        print(f'Text: "{amount_elem.get_text(strip=True)}"')
