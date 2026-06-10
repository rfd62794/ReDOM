# ReDOM Schema Specification

*Phase 1 — June 2026*

## Overview

The ReDOM extraction schema is a declarative YAML format that describes how to extract flat records from hierarchical HTML where parent context is encoded in document position rather than data attributes. The schema separates **what to extract** (selectors, fields) from **how to extract it** (the generic engine).

## Core Concept: Reattachment

Some web UIs (banking, admin panels, dialers) encode record context in layout:

```html
<h2>Thursday, April 9th</h2>
<div class="transaction">...</div>
<div class="transaction">...</div>
```

The date is not on the transaction rows—it lives in a preceding header. Reading the DOM doesn't solve this. The unsolved operation is **reattachment**: restoring the parent→child relationships the presentation flattened, emitting flat records with that context made explicit.

## Schema Structure

```yaml
source: string                    # Identifier for this source
reference_date: "YYYY-MM-DD"     # Required for relative_date resolution
anchors:                          # Context-carrying elements
  - selector: string              # CSS selector (element name or .class)
    role: string                  # Context key name (e.g., "date_header")
    resolve: string               # "literal" | "relative_date" (closed enum)
record_selector: string          # CSS selector for record elements
inherits: string                 # Which anchor role records inherit from
fields:                          # Field extraction rules
  - name: string                  # Field key in output
    selector: string              # CSS selector within record element
    kind: string                 # "string" | "currency" | "date" (closed enum)
on_unresolved: string           # "flag" | "skip" | "error" (closed enum)
```

## Field Reference

### source
Identifier string. Used for logging, debugging, and future multi-source pipelines.

### reference_date
ISO date string (YYYY-MM-DD). Required when using `resolve: relative_date`. Never read from the system clock—passed in through the schema to keep the engine deterministic and testable.

### anchors
List of anchor rules. Anchors set context values as the engine walks the DOM. When an element matches an anchor's selector, its text is resolved and stored under the anchor's role.

**AnchorRule fields:**
- **selector**: CSS selector. Phase 1 supports element names (`h2`, `div`) and class selectors (`.header`).
- **role**: String key. Records inherit context by role name.
- **resolve**: How to transform the element's text into a context value.
  - `literal`: Use text as-is
  - `relative_date`: Resolve relative terms ("Yesterday", "Today") or absolute dates ("Thursday, April 9th") against `reference_date`, output ISO format

### record_selector
CSS selector matching the elements that become records. Each matching element produces one Record in the output.

### inherits
String matching an anchor's `role`. Records capture a copy of the current context at their document position, specifically looking for this role. If the role is absent from current context, the record is marked `unresolved=True`.

### fields
List of field extraction rules. Each field is extracted from within the record element.

**FieldRule fields:**
- **name**: Output key for this field
- **selector**: CSS selector within the record element
- **kind**: Coercion type (closed enum)
  - `string`: Text as-is
  - `currency`: Remove `$`, `,`, whitespace; preserve sign
  - `date`: Pass through (assumes ISO or pre-processed)

### on_unresolved
Behavior when a record has no resolvable anchor in context.
- `flag` (Phase 1): Set `unresolved=True`, omit the inherits role from context
- `skip`: Skip the record entirely (Phase 2+)
- `error`: Raise exception (Phase 2+)

## Document Order Contract

The engine walks elements in **document order** (depth-first traversal). Context accumulates as anchors are encountered and persists until overwritten by a new anchor of the same role. This is the entire mechanism—no XPath, no parent pointers, no DOM traversal beyond `find_all(True)`.

```html
<h2>Yesterday</h2>           <!-- context.date_header = "2026-04-09" -->
<div class="tx">...</div>   <!-- record with date_header -->
<div class="tx">...</div>   <!-- record with date_header -->
<h2>Today</h2>             <!-- context.date_header = "2026-04-10" -->
<div class="tx">...</div>   <!-- record with new date_header -->
```

## Unresolved Records

When `on_unresolved: flag` and a record appears without a preceding anchor matching the `inherits` role:

- `record.unresolved = True`
- `record.context` contains all resolved anchors except the missing one
- No date guessing, no fallback to "today"

This is the stop condition: fail loud rather than emit bad data.

## Worked Example: Chime Transactions

```yaml
source: chime_transactions
reference_date: "2026-04-10"
anchors:
  - selector: "h2"
    role: date_header
    resolve: relative_date
record_selector: ".transaction"
inherits: date_header
fields:
  - name: description
    selector: ".desc"
    kind: string
  - name: amount
    selector: ".amount"
    kind: currency
on_unresolved: flag
```

**Input HTML:**
```html
<h2>Yesterday</h2>
<div class="transaction">
  <span class="desc">Starbucks</span>
  <span class="amount">-$5.67</span>
</div>
<div class="transaction">
  <span class="desc">Grocery</span>
  <span class="amount">-$42.13</span>
</div>
<h2>Thursday, April 9th</h2>
<div class="transaction">...</div>
```

**Output Records:**
```python
[
  Record(
    fields={"description": "Starbucks", "amount": "-5.67"},
    context={"date_header": "2026-04-09"},
    unresolved=False
  ),
  Record(
    fields={"description": "Grocery", "amount": "-42.13"},
    context={"date_header": "2026-04-09"},
    unresolved=False
  ),
  Record(
    fields={...},
    context={"date_header": "2026-04-09"},  # "Thursday, April 9th" parsed
    unresolved=False
  ),
]
```

## Purity Guarantee

The `extract(schema, html)` function is **pure**:
- Same inputs → same outputs, always
- No I/O inside the engine
- No `datetime.now()` or system clock access
- Reference date is injected via schema

This makes tests deterministic: a saved HTML fixture + fixed reference date produces the same records on every run.

## Phase 1 Constraints (Explicit)

| Feature | Status |
|---------|--------|
| Element/class selectors | ✅ Implemented |
| `literal` resolve | ✅ Implemented |
| `relative_date` resolve | ✅ Implemented |
| `string` kind | ✅ Implemented |
| `currency` kind | ✅ Implemented |
| `date` kind | ✅ Implemented |
| `flag` on_unresolved | ✅ Implemented |
| Live fetching / Playwright | ❌ Deferred to Phase 2+ |
| Multiple sources | ❌ Deferred to Phase 2+ |
| Golden Columns transform | ❌ Deferred to Phase 2+ |
| CLI / packaging | ❌ Deferred to Phase 2+ |
| `skip` / `error` on_unresolved | ❌ Deferred to Phase 2+ |

## Version

Spec version: Phase 1 (June 2026)
