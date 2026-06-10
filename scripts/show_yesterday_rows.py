#!/usr/bin/env python3
"""Show rows under Yesterday section."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

# Find all h2 elements to locate Yesterday
h2s = soup.find_all('h2')
for i, h2 in enumerate(h2s):
    print(f'H2 {i}: "{h2.get_text(strip=True)}"')

print()

# Get the element after Yesterday h2
yesterday_h2 = None
for h2 in h2s:
    if 'Yesterday' in h2.get_text():
        yesterday_h2 = h2
        break

if yesterday_h2:
    # Find next sibling transaction rows
    next_elem = yesterday_h2.find_next_sibling()
    count = 0
    while next_elem and count < 3:
        classes = next_elem.get('class', [])
        if 'flex' in classes and 'flex-row' in classes and 'gap-4' in classes:
            print(f'Row {count} after Yesterday:')
            print(next_elem.prettify()[:1500])
            print()
            count += 1
        next_elem = next_elem.find_next_sibling()
