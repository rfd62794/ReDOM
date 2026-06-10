# ReDOM — Phase 1 Directive: Schema-Driven Reattachment Engine

*June 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** This is a new repo. No existing test floor.
> Create the repo structure first (§1), then report it before writing any logic.
> Target floor for this phase: **8 passing, 0 failing, 0 skipped.**
> If the structure cannot be created as specified, stop and report — do not improvise an alternative layout.

---

## §0 Context

**The primitive.** Some web UIs encode record context in *layout* rather than in data. A transaction's date is not on the transaction row — it lives in an `<h2>` section header above a group of rows ("Yesterday", "Thursday, April 9th"). The DOM is well-formed; the *relationship* between parent context and child record was never encoded, only implied by document position. Reading the DOM (Playwright, BeautifulSoup) does not solve this. The unsolved operation is **reattachment**: restoring the parent→child relationships the presentation layer flattened, and emitting flat records with that context made explicit.

This pattern has been hand-solved three times across prior work (Chime export, dialer portal extraction, lead-file normalization). Phase 1 formalizes it once: a declarative **extraction schema** (YAML) that describes the reattachment rules for one source, and a generic **engine** that consumes the schema and produces flat records. The schema is data; the engine logic is fixed. New sources become new schema files, never new logic.

**This phase delivers:**
- A documented YAML schema format for declaring reattachment rules.
- A generic engine that consumes a schema + an HTML document and emits flat records.
- A `context_unresolved` flag path for headers the schema cannot resolve (fail loud, never guess).
- One committed real-world fixture (Chime) and a passing test suite against it.

**NOT in scope this phase — explicit deferred list:**
- Live fetching / Playwright / auth of any kind. Engine consumes a *static HTML string only*.
- Any second source. Format generality is earned in Phase 2 by a second schema, not designed speculatively now.
- Golden Columns output transform / dialer formatting. Output is flat records; downstream mapping is later.
- CLI, packaging, PyPI, MCP exposure. Library only.
- Network calls of any kind, in code or in tests.

## §1 Scope Statement

| File | Status | Action |
|---|---|---|
| `pyproject.toml` | New | Minimal package config. Package name `redom`. Deps: `beautifulsoup4`, `pyyaml`. Dev: `pytest`. |
| `redom/__init__.py` | New | Export `extract`, `Record`, `ExtractionSchema`. |
| `redom/schema.py` | New | Load + validate the YAML schema into typed objects. |
| `redom/engine.py` | New | The reattachment engine. Pure function over (schema, html) → records. |
| `redom/types.py` | New | `Record`, `ExtractionSchema`, `FieldRule`, `AnchorRule` dataclasses. |
| `schemas/chime_transactions.yaml` | New | The first real extraction schema. |
| `tests/fixtures/chime_sample.html` | New | One real saved Chime transactions page. Data sanitized (see ⚠️ RULE). |
| `tests/test_engine.py` | New | 8 anchor tests (§3). All run against the static fixture. |
| `docs/SCHEMA_SPEC.md` | New | Human-readable spec for the YAML format. The shareable artifact. |
| `docs/state/current.md` | New | State file. Final completion criterion. |

**Read-only — do not touch:** N/A (new repo). Once `engine.py` passes, it becomes read-only for Phase 2.

## §2 Implementation

### `redom/types.py`
Define dataclasses only. No logic, no imports beyond `dataclasses` and `typing`.

```python
@dataclass(frozen=True)
class FieldRule:
    name: str
    selector: str
    kind: str            # "string" | "currency" | "date" — Phase 1 set, closed enum
@dataclass(frozen=True)
class AnchorRule:
    selector: str        # e.g. "h2"
    role: str            # e.g. "date_header"
    resolve: str         # "literal" | "relative_date"  (Phase 1 set, closed enum)
@dataclass(frozen=True)
class ExtractionSchema:
    source: str
    anchors: tuple[AnchorRule, ...]
    record_selector: str
    inherits: str        # role name a record inherits from the nearest preceding anchor
    fields: tuple[FieldRule, ...]
    on_unresolved: str   # "flag" | "skip" | "error"  (Phase 1: only "flag" implemented)
@dataclass(frozen=True)
class Record:
    fields: dict[str, str]
    context: dict[str, str]      # reattached parent context, e.g. {"date_header": "2026-04-09"}
    unresolved: bool             # True if context could not be resolved
```

> ⚠️ RULE: `types.py` is pure stdlib. No `bs4`, no `yaml`, no network. Any third-party import here is a bug.

### `redom/schema.py`
One function: `load_schema(path_or_str) -> ExtractionSchema`. Parse YAML, validate against the closed enums in `types.py`, raise `SchemaError` with a specific message on any unknown `kind`, `resolve`, or `on_unresolved` value.

> ⚠️ RULE: Validation is strict. An unknown enum value is an error at load time, not a silent fallback. The whole point of the primitive is that it fails loud rather than guessing.

### `redom/engine.py`
One public function:

```python
def extract(schema: ExtractionSchema, html: str) -> list[Record]:
    ...
```

Algorithm (document order is the entire mechanism):
1. Parse `html` with BeautifulSoup.
2. Walk elements in document order. Maintain a `current_context: dict[str, str]`.
3. When an element matches an `AnchorRule.selector`: resolve its text per `resolve` (`literal` = raw text; `relative_date` = resolve "Yesterday"/"Thursday, April 9th"/etc. against `schema` reference date — see rule below). Store under `current_context[role]`.
4. When an element matches `record_selector`: extract each `FieldRule` (by selector, coerced per `kind`). Attach a copy of `current_context`. If the `inherits` role is absent from `current_context`, set `unresolved=True` and leave that context key out.
5. Return records in document order.

> ⚠️ RULE: The engine is a **pure function**. Same (schema, html) in → same records out, always. No I/O, no clock read inside `extract`. The reference date for `relative_date` is passed *in* via the schema or an explicit argument — never `datetime.now()` inside the engine. (This is what makes the test deterministic and is non-negotiable.)

> ⚠️ RULE: `relative_date` resolution lives in a small helper with its own unit test. "Yesterday"/"Today" resolve against the passed reference date; absolute headers ("Thursday, April 9th") parse to ISO. An unparseable header → that record is `unresolved=True`. Never emit a guessed date.

### `schemas/chime_transactions.yaml`
The first real schema. Mirrors the actual Chime DOM. Example shape (adjust selectors to the real fixture):

```yaml
source: chime_transactions
reference_date: "2026-04-12"
anchors:
  - selector: "h2"
    role: date_header
    resolve: relative_date
record_selector: ".transaction"
inherits: date_header
fields:
  - { name: amount, selector: ".amount", kind: currency }
  - { name: description, selector: ".desc", kind: string }
on_unresolved: flag
```

### `docs/SCHEMA_SPEC.md`
The shareable artifact. Document every field, every closed enum, the document-order contract, and the unresolved behaviour. Include the Chime schema as the worked example. This is the file another person (or another tool) reads to write a new schema without reading the engine.

## §3 Test Anchors

All tests run against `tests/fixtures/chime_sample.html` + `schemas/chime_transactions.yaml`. No network. No live fetch. Reference date is fixed in the schema.

| # | Test name | Target file | Behaviour |
|---|---|---|---|
| 1 | `test_schema_loads_valid` | schema.py | Valid YAML → `ExtractionSchema` with correct field count. |
| 2 | `test_schema_rejects_unknown_kind` | schema.py | Unknown `kind` raises `SchemaError`. |
| 3 | `test_schema_rejects_unknown_resolve` | schema.py | Unknown `resolve` raises `SchemaError`. |
| 4 | `test_extract_reattaches_date_to_records` | engine.py | Each record's `context["date_header"]` matches the header it sat under in the fixture. |
| 5 | `test_relative_date_resolves_against_reference` | engine.py | "Yesterday" resolves to reference_date − 1, ISO format. |
| 6 | `test_absolute_header_parses_to_iso` | engine.py | "Thursday, April 9th" → "2026-04-09". |
| 7 | `test_unresolved_header_flags_record` | engine.py | A record with no resolvable preceding anchor → `unresolved=True`, no guessed date. |
| 8 | `test_extract_is_pure` | engine.py | Calling `extract` twice on same inputs yields identical records (no clock/IO leakage). |

**Target: 8 passing, 0 failing, 0 skipped.**

> ⚠️ RULE: Mock nothing by faking the DOM in code — use the committed HTML fixture. The fixture *is* the test contract. If the real Chime DOM differs from the schema selectors, fix the schema or the fixture, never hardcode expected records to dodge a selector mismatch.

## §4 Completion Criteria

- [ ] Repo structure created exactly per §1; structure reported before any logic written.
- [ ] `redom/types.py` is pure stdlib (verified: no third-party imports).
- [ ] `extract` is a pure function — reference date injected, never read from `datetime.now()` inside the engine.
- [ ] One real Chime page saved, sanitized, committed as `tests/fixtures/chime_sample.html`.
- [ ] `schemas/chime_transactions.yaml` resolves every record in the fixture (0 unintended unresolved).
- [ ] `docs/SCHEMA_SPEC.md` documents the format completely, with the Chime schema as worked example.
- [ ] **Raw pytest output shows `8 passed, 0 failed, 0 skipped`** — pasted, read by you, not summarized by the agent.
- [ ] `docs/state/current.md` updated as the final action.

## §5 Quick Reference

| Fact | Value |
|---|---|
| Package name | `redom` |
| Phase 1 floor | 8/0/0 |
| Core deps | `beautifulsoup4`, `pyyaml` |
| Engine contract | `extract(schema, html) -> list[Record]`, pure function |
| The mechanism | document-order walk; anchors set context, records inherit it |
| Stop condition (data) | unresolvable context → `unresolved=True`, never guess |
| First source | Chime transactions (static HTML fixture only) |
| Shareable artifact | `docs/SCHEMA_SPEC.md` + the YAML schema |
| Explicitly deferred | live fetch, auth, 2nd source, Golden Columns transform, CLI, packaging |
| Phase 2 (not now) | second real source validates format generality; live-fetch adapter feeds HTML to the proven engine |

---

*RFD IT Services Ltd. | ReDOM Phase 1 | Director → Pipeline → Agent*
*Spec first. Engine is pure. Fixture is the contract. Floor is real.*
