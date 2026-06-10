#!/usr/bin/env python3
"""Find actual dollar amount elements in Chime HTML."""

import re
from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

# Find all text nodes with dollar patterns
dollar_pattern = re.compile(r'\$[\d,]+\.\d{2}')

print('=== ELEMENTS WITH DOLLAR AMOUNTS ===')
print()

count = 0
for elem in soup.find_all(string=dollar_pattern):
    text = elem.strip()
    if not text:
        continue
    parent = elem.parent
    classes = parent.get('class', [])
    class_str = ' '.join(classes) if classes else '(no class)'
    
    print(f'Tag: {parent.name} | Class: {class_str}')
    print(f'Text: "{text[:60]}"')
    print()
    
    count += 1
    if count >= 15:
        print(f'... (showing first 15)')
        break

print(f'Found {count} elements with dollar amounts')
