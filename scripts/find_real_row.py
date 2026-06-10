#!/usr/bin/env python3
"""Find the actual transaction row container (parent of description + amount)."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

print("=== FINDING TRANSACTION ROW PARENTS ===")
print()

# Find amount elements and go up to find common row parent
amount_divs = soup.find_all('div', class_=lambda x: x and 'flex-none' in x and 'text-right' in x)
print(f"Found {len(amount_divs)} amount elements")
print()

# Check parent of each amount
for i, amt in enumerate(amount_divs[:3]):
    print(f"Amount {i}:")
    
    # Immediate parent (the amount column)
    parent = amt.parent
    print(f"  Parent tag: {parent.name}, classes: {parent.get('class', [])}")
    
    # Grandparent (potential row)
    grandparent = parent.parent if parent.parent else None
    if grandparent:
        print(f"  Grandparent tag: {grandparent.name}, classes: {grandparent.get('class', [])}")
        
        # Great-grandparent
        if grandparent.parent:
            print(f"  Great-grandparent tag: {grandparent.parent.name}, classes: {grandparent.parent.get('class', [])}")
    print()

# Look at the full row structure
print("=== FULL ROW HTML (first amount) ===")
if amount_divs:
    amt = amount_divs[0]
    row = amt.parent.parent if amt.parent else None
    if row:
        print(row.prettify()[:1500])

print()
print("=== CHECKING FOR data-index ON ROWS ===")

# See if data-index appears on row elements
data_index_elems = soup.find_all(attrs={'data-index': True})
print(f"Elements with data-index: {len(data_index_elems)}")
for elem in data_index_elems:
    print(f"  {elem.name} data-index={elem['data-index']}, classes={elem.get('class', [])}")
