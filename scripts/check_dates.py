#!/usr/bin/env python3
"""Check actual date headers in fixture."""

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('tests/fixtures/chime_real.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

print("=== DATE HEADERS IN FIXTURE ===")
h2s = soup.find_all('h2')
for h2 in h2s:
    print(f'H2: "{h2.get_text(strip=True)}"')

print()
print("=== REFERENCE DATE CHECK ===")
print(f"File captured: June 10, 2026")
print(f"Schema reference_date: 2026-06-09")
print(f"If 'Yesterday' appears, should resolve to: 2026-06-08 (reference_date - 1)")
