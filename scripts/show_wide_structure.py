#!/usr/bin/env python3
"""Show wider DOM structure around transactions."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

# Find a row and show its parent and siblings
row = soup.select_one('.flex.flex-row.gap-4')
if row:
    print('=== ROW PARENT ===')
    parent = row.parent
    print(f'Parent tag: {parent.name}')
    print(f'Parent classes: {parent.get("class", [])}')
    print()
    
    print('=== PARENT CHILDREN (first 5) ===')
    for i, child in enumerate(parent.find_all(recursive=False)[:5]):
        classes = child.get('class', [])
        class_str = ' '.join(classes) if classes else '(no class)'
        text = child.get_text(strip=True)[:60]
        print(f'{i}: {child.name}.{class_str} -> "{text}"')
