#!/usr/bin/env python3
"""Sanitize real Chime HTML fixture for testing.

Reads: samples/Chime/Chime _ Accounts_Spending.html (gitignored, never committed)
Writes: tests/fixtures/chime_real.html (sanitized, tracked)

Usage:
    uv run python scripts/sanitize_chime.py --report    # Structure report only
    uv run python scripts/sanitize_chime.py --write     # Generate sanitized fixture

⚠️  CRITICAL: Never commit the raw file. Never echo real transaction values to stdout.
"""

import argparse
import re
from pathlib import Path
from bs4 import BeautifulSoup

# Paths
RAW_FILE = Path("samples/Chime/Chime _ Accounts_Spending.html")
SANITIZED_FILE = Path("tests/fixtures/chime_real.html")


def analyze_structure(soup: BeautifulSoup) -> dict:
    """Extract structure report without echoing values."""
    report = {
        "title": soup.title.string if soup.title else "No title",
        "h2_count": 0,
        "h2_samples": [],  # First 3 h2 text patterns only (dates, not values)
        "transaction_containers": [],
        "amount_elements": [],
        "description_elements": [],
        "data_attrs_found": [],
        "script_count": 0,
    }
    
    # Find h2 elements (date headers)
    h2s = soup.find_all("h2")
    report["h2_count"] = len(h2s)
    for i, h2 in enumerate(h2s[:3]):  # Sample first 3 only
        text = h2.get_text(strip=True)
        # Only capture if it looks like a date header, truncate long strings
        if len(text) < 100:
            report["h2_samples"].append(text)
        else:
            report["h2_samples"].append(text[:50] + "...")
    
    # Find potential transaction containers (divs, sections, articles with transaction-like classes)
    candidates = []
    for elem in soup.find_all(["div", "section", "article", "li"]):
        classes = elem.get("class", [])
        if classes:
            candidates.append(" ".join(classes))
    
    # Report unique class patterns that look like rows/containers
    unique_classes = set()
    for cls_str in candidates:
        if any(keyword in cls_str.lower() for keyword in ["row", "item", "transaction", "list", "entry"]):
            unique_classes.add(cls_str)
    report["transaction_containers"] = sorted(unique_classes)[:10]  # Top 10 patterns
    
    # Find elements that might contain amounts (search by text patterns, report tags/classes)
    amount_patterns = re.compile(r'[\$\-]?[\d,]+\.\d{2}|\$[\d,]+')
    potential_amounts = []
    for elem in soup.find_all(text=amount_patterns):
        parent = elem.parent
        if parent.name in ["span", "div", "p", "td"]:
            classes = " ".join(parent.get("class", []))
            tag_class = f"{parent.name}.{classes}" if classes else parent.name
            if tag_class not in potential_amounts:
                potential_amounts.append(tag_class)
                if len(potential_amounts) >= 10:
                    break
    report["amount_elements"] = potential_amounts
    
    # Find data-* attributes present
    data_attrs = set()
    for elem in soup.find_all(attrs=True):
        for attr in elem.attrs:
            if attr.startswith("data-"):
                data_attrs.add(attr)
    report["data_attrs_found"] = sorted(data_attrs)
    
    # Count scripts
    report["script_count"] = len(soup.find_all("script"))
    
    return report


def print_structure_report(report: dict):
    """Print structure report without echoing real values."""
    print("=" * 60)
    print("CHIME HTML STRUCTURE REPORT")
    print("=" * 60)
    print(f"\nTitle: {report['title']}")
    print(f"\nH2 Elements (date headers): {report['h2_count']} total")
    print("Sample H2 text patterns:")
    for i, sample in enumerate(report['h2_samples'], 1):
        print(f"  {i}. {sample}")
    
    print(f"\nTransaction Container Candidates:")
    for cls in report['transaction_containers']:
        print(f"  - {cls}")
    
    print(f"\nAmount Element Patterns (tag.class):")
    for elem in report['amount_elements']:
        print(f"  - {elem}")
    
    print(f"\nData Attributes Found: {len(report['data_attrs_found'])}")
    for attr in report['data_attrs_found'][:5]:  # Show first 5
        print(f"  - {attr}")
    if len(report['data_attrs_found']) > 5:
        print(f"  ... and {len(report['data_attrs_found']) - 5} more")
    
    print(f"\nScript Elements: {report['script_count']}")
    print("=" * 60)
    print("\nThis report shows SELECTOR TARGETS, not your data.")
    print("Use these classes to update schemas/chime_transactions.yaml")


def sanitize_html(soup: BeautifulSoup) -> BeautifulSoup:
    """Sanitize HTML: preserve structure, transform values."""
    
    # Track what we've sanitized for reporting
    sanitized_count = {"amounts": 0, "descriptions": 0, "data_attrs": 0, "scripts_removed": 0}
    
    # 1. Remove all script tags (may contain account data)
    for script in soup.find_all("script"):
        script.decompose()
        sanitized_count["scripts_removed"] += 1
    
    # 2. Remove all style tags (cleaner output)
    for style in soup.find_all("style"):
        style.decompose()
    
    # 3. Sanitize data-* attributes
    for elem in soup.find_all(attrs=True):
        for attr in list(elem.attrs.keys()):
            if attr.startswith("data-"):
                # Replace with fake data or remove
                elem[attr] = "SANITIZED"
                sanitized_count["data_attrs"] += 1
    
    # 4. Find and sanitize amounts (dollar patterns)
    amount_pattern = re.compile(r'[\$\-]?[\d,]+\.\d{2}')
    for text_elem in soup.find_all(text=amount_pattern):
        parent = text_elem.parent
        # Replace with fake amount, preserving sign if negative
        original = str(text_elem)
        if "-" in original or "(" in original:
            fake = "-$99.99"
        else:
            fake = "$99.99"
        text_elem.replace_with(fake)
        sanitized_count["amounts"] += 1
    
    # 5. Sanitize merchant descriptions (heuristic: text in transaction rows)
    # Look for elements that are siblings to amounts or in transaction containers
    for elem in soup.find_all(["span", "div", "p"]):
        text = elem.get_text(strip=True)
        # Skip if already sanitized amount
        if re.match(r'[\$\-]?\d', text):
            continue
        # Skip if very short (likely not a merchant name)
        if len(text) < 3:
            continue
        # Skip if it's a date pattern
        if re.match(r'\w+day|\d{1,2}/\d{1,2}|\w+ \d{1,2}', text):
            continue
        # Heuristic: if parent has transaction-like class, this is probably a description
        parent_classes = " ".join(elem.parent.get("class", []) if elem.parent else "")
        if any(kw in parent_classes.lower() for kw in ["transaction", "merchant", "description", "name"]):
            elem.string = "MERCHANT SANITIZED"
            sanitized_count["descriptions"] += 1
    
    # 6. Sanitize any remaining long text that looks like personal data
    for elem in soup.find_all(text=True):
        text = str(elem)
        if len(text) > 50 and not text.strip().startswith("<"):
            # Likely contains personal info
            elem.replace_with("[LONG TEXT SANITIZED]")
    
    # 7. Update title
    if soup.title:
        soup.title.string = "Chime Transactions (Sanitized)"
    
    return soup, sanitized_count


def main():
    parser = argparse.ArgumentParser(description="Sanitize Chime HTML fixture")
    parser.add_argument("--report", action="store_true", help="Show structure report only")
    parser.add_argument("--write", action="store_true", help="Generate sanitized fixture")
    args = parser.parse_args()
    
    if not args.report and not args.write:
        parser.print_help()
        return
    
    # Verify raw file exists
    if not RAW_FILE.exists():
        print(f"ERROR: Raw file not found: {RAW_FILE}")
        print("Capture Chime page first and save to samples/Chime/")
        return
    
    print(f"Reading raw file: {RAW_FILE} ({RAW_FILE.stat().st_size} bytes)")
    
    # Parse
    html = RAW_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    
    if args.report:
        report = analyze_structure(soup)
        print_structure_report(report)
    
    if args.write:
        print(f"\nGenerating sanitized fixture...")
        sanitized_soup, counts = sanitize_html(soup)
        
        # Write output
        SANITIZED_FILE.parent.mkdir(parents=True, exist_ok=True)
        SANITIZED_FILE.write_text(str(sanitized_soup), encoding="utf-8")
        
        print(f"✓ Written: {SANITIZED_FILE} ({SANITIZED_FILE.stat().st_size} bytes)")
        print(f"\nSanitization summary:")
        print(f"  - Scripts removed: {counts['scripts_removed']}")
        print(f"  - Data attributes sanitized: {counts['data_attrs']}")
        print(f"  - Amounts faked: {counts['amounts']}")
        print(f"  - Descriptions faked: {counts['descriptions']}")
        print(f"\n⚠️  VERIFY: Open {SANITIZED_FILE} and confirm no real values appear")
        print(f"   before committing to git.")


if __name__ == "__main__":
    main()
