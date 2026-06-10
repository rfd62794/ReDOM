#!/usr/bin/env python3
"""Find the selector that matches exactly one element per transaction.

Look for data-* attributes, data-index, or specific classes that identify
individual transaction rows (not nested containers).
"""

from pathlib import Path
from bs4 import BeautifulSoup
import re

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

print("=== FINDING PER-TRANSACTION IDENTIFIERS ===")
print()

# Strategy 1: Find elements with data-* attributes that look like row identifiers
data_attrs = {}
for elem in soup.find_all(attrs=True):
    for attr, value in elem.attrs.items():
        if attr.startswith('data-') and isinstance(value, str):
            key = f"{elem.name}[{attr}]"
            if key not in data_attrs:
                data_attrs[key] = set()
            data_attrs[key].add(value)

print("Data attributes found:")
for key, values in sorted(data_attrs.items()):
    print(f"  {key}: {len(values)} unique values")
    # Show first few
    for v in list(values)[:3]:
        print(f"    - {v}")

print()

# Strategy 2: Look for elements containing exactly one emoji + merchant + amount pattern
print("=== ANALYZING ROW CANDIDATES ===")

# Find all divs and check what's inside them
candidates = []
for div in soup.find_all('div'):
    classes = div.get('class', [])
    text = div.get_text(strip=True)
    
    # Must have emoji (common pattern in Chime)
    has_emoji = any(ord(c) > 127000 for c in text)
    
    # Must have dollar amount somewhere inside
    has_amount = bool(re.search(r'\$[\d,]+\.\d{2}', text))
    
    # Must have merchant name (non-emoji text)
    non_emoji_text = re.sub(r'[^\x00-\x7F]', '', text)
    has_merchant = len(non_emoji_text) > 5
    
    if has_emoji and has_amount and has_merchant:
        # This looks like a transaction row
        child_count = len(div.find_all(recursive=False))
        candidates.append({
            'classes': ' '.join(classes),
            'text_preview': text[:60],
            'child_count': child_count,
            'element': div
        })

print(f"Found {len(candidates)} potential transaction containers")
for i, c in enumerate(candidates[:5]):
    print(f"\nCandidate {i}:")
    print(f"  Classes: {c['classes']}")
    print(f"  Text: {c['text_preview']}")
    print(f"  Direct children: {c['child_count']}")

print()

# Strategy 3: Look for the common parent pattern
transaction_rows = soup.select('.flex.flex-row')
print(f"=== .flex.flex-row count: {len(transaction_rows)} ===")

# Look at parents of amount elements
amount_divs = soup.find_all('div', class_=re.compile(r'flex-none.*text-right'))
print(f"Amount divs: {len(amount_divs)}")

if amount_divs:
    # Check parent of first amount
    parent = amount_divs[0].parent
    print(f"\nParent of amount element:")
    print(f"  Tag: {parent.name}")
    print(f"  Classes: {parent.get('class', [])}")
    
    # See if this parent has a more specific selector
    parent_classes = parent.get('class', [])
    if parent_classes:
        selector = '.'.join([''] + parent_classes)
        print(f"  Selector: {selector}")
        
        # Count how many match this exact pattern
        matches = soup.select(selector)
        print(f"  Matches: {len(matches)}")

# Strategy 4: Look for data-index or data-row patterns
print("\n=== LOOKING FOR ROW INDEXES ===")
for attr in ['data-index', 'data-row-index', 'data-key', 'data-id']:
    elems = soup.find_all(attrs={attr: True})
    if elems:
        print(f"{attr}: {len(elems)} elements")
        values = [e[attr] for e in elems[:5]]
        print(f"  Sample values: {values}")
