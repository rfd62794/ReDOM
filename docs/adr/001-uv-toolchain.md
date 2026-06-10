# ADR 001: UV Toolchain Adoption

## Status
Accepted for ReDOM — June 2026

## Decision
Adopt `uv` as the package and environment manager for ReDOM. Lockfile committed (`uv.lock`) ensures reproducible 8/0/0 floor across machines.

## Deferred
Stack-wide standardization (PrivyBot, other RFD services) remains an open question requiring separate ADR. ReDOM converted now; stack-wide decision pending deliberate evaluation.

## Consequences
- `uv run pytest` now the certified execution path
- Interpreter ambiguity structurally eliminated via `.python-version` + uv
- Dependency resolution locked and reproducible

---
*RFD IT Services Ltd. | ReDOM*
