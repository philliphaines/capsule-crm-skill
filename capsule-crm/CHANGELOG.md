# Changelog

The version lives in `SKILL.md`'s frontmatter (`metadata.version`). Bump it with
`python3 scripts/bump_version.py patch|minor|major "what changed"`, which updates `SKILL.md` and
adds an entry here.

- **major**: the skill's rules or the client's command line change in a way that breaks existing use.
- **minor**: new endpoints, behaviour or client features.
- **patch**: corrections and wording.

## 1.1.2 (2026-11-28)

- OAuth apps are registered at https://developer.capsulecrm.com/.

## 1.1.1 (2026-11-20)

- Dropped the note that titles and countries take very long strings; use the values from /titles and /countries.

## 1.1.0 (2026-11-19)

- Text limits per field, counted in code points (opportunity name 100, project name 255, most short fields 250).
- Characters above U+FFFF (most emoji) can't be stored: Capsule saves "��" or fails with a 500. The client refuses to send them and explains a 500 on a write.
- `/titles?includeBuiltinTitles=true` and `/countries`; addresses take the country's English name.
- Markets, product prices (`/products?embed=prices&sideload=true`) and `embed=market` on opportunities.
- Payment terms (`durationBasis`, `duration`) and adding, changing and removing products through `lineItems`.

## 1.0.1 (2026-11-17)

- Removed references to the app the skill was first built from.
- Task categories carry an `id` (checked live).

## 1.0.0 (2026-11-17)

- First version: `SKILL.md`, `scripts/capsule.py`, and references for endpoints, writing, filters, gotchas and OAuth.
