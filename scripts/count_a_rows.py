#!/usr/bin/env python3
"""Check if 'a' tags with transaction classes are the right selector."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

# Find 'a' tags with the transaction link classes
a_tags = soup.find_all('a', class_=lambda x: x and 'group' in x and 'flex' in x and 'flex-col' in x)

print(f"Found {len(a_tags)} 'a' tags with transaction classes")
print()

for i, a in enumerate(a_tags[:3]):
    text = a.get_text(strip=True)[:60]
    print(f"a[{i}]: {text}...")
    
    # Check what's inside
    children = a.find_all(recursive=False)
    print(f"  Direct children: {len(children)}")
    for child in children:
        print(f"    - {child.name}: {child.get('class', [])}")
    print()

# Count all a[href] that look like transaction links
print("=== All transaction links ===")
all_links = soup.find_all('a', href=True)
transaction_links = [a for a in all_links if '/transaction/' in a.get('href', '')]
print(f"Links with /transaction/: {len(transaction_links)}")

# Check for specific data-testid pattern
print("\n=== Looking for transaction row data-testid ===")
testid_divs = soup.find_all('div', attrs={'data-testid': True})
for div in testid_divs[:3]:
    print(f"div data-testid={div['data-testid']}, classes={div.get('class', [])}")
