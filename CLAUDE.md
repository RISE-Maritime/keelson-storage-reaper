# CLAUDE.md

Expires navigation-decision records from Zenoh router storage (README).

## Rules that must not be broken

- **The clock is the router's.** Expire by the stored sample's router timestamp, never by a payload
  time; a replay can carry vessel times months old. No timestamp means unknown age, which is never
  expired.
- **Dry run unless `--apply`.** A run without it must delete nothing.
- **Named entities only.** `--entity` is required and refuses wildcards: a delete on a bridged router
  reaches every storage behind it.
- **Three subjects only:** `encounter`, `navigation_advice`, `advice_disposition`. A disposition goes
  only once no unexpired advice with the same `voyage_id/advice_id` is stored.
- **Pure rules.** `reaper/rules.py` has no clock and no Zenoh; every decision is tested there.
- **Tests never touch a router or a network.**

## Commands

```bash
uv run --locked pytest -q
uv run --locked ruff check .
```
