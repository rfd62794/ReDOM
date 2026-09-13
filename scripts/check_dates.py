#!/usr/bin/env python3
"""Check actual date headers in fixture."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/sample_statement.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

print("=== DATE HEADERS IN FIXTURE ===")
h2s = soup.find_all('h2')
for h2 in h2s:
    print(f'H2: "{h2.get_text(strip=True)}"')

print()
print("=== REFERENCE DATE CHECK ===")
print(f"Synthetic fixture reference date: March 15, 2026")
print(f"Schema reference_date: 2026-03-15")
print(f"If 'Yesterday' appears, should resolve to: 2026-03-14 (reference_date - 1)")
