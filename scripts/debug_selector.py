#!/usr/bin/env python3
"""Debug selector matching."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

# Test selector matching
selector = 'a.group.flex.flex-col'
required = [c for c in selector.split('.') if c]
print(f'Required classes: {required}')

# Check if any a tags match
matches = []
for a in soup.find_all('a'):
    classes = a.get('class', [])
    if all(cls in classes for cls in required):
        matches.append(a)
        
print(f'Matches: {len(matches)}')

# Show first few match's classes
for i, m in enumerate(matches[:3]):
    print(f'Match {i} classes: {m.get("class", [])}')
    
# Also try with just a.group
print()
print('Trying a.group only:')
matches2 = soup.find_all('a', class_='group')
print(f'a.group matches: {len(matches2)}')
