#!/usr/bin/env python3
"""Show HTML structure of first transaction row."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

# Get first transaction row
row = soup.select_one('.flex.flex-row.gap-4')
if row:
    print('=== FIRST TRANSACTION ROW HTML ===')
    print(row.prettify()[:3000])
    print()
    
    # Look for amount element
    amount = row.select_one('.flex-none.text-right.text-label')
    print('Amount select_one result:', amount)
else:
    print('No row found')
