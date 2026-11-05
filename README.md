# keelson-storage-reaper

Expires **navigation-decision records** from Zenoh router storage: `encounter`, `navigation_advice`
and `advice_disposition` (keelson `protocols/navigation_decisions.yaml`). It is a small service that
runs beside the router.

## Why it exists

The router keeps every one of these keys forever. Every encounter and every advice is its own key,
and on 2026-11-05 one simulated vessel's navigator wrote about 880 encounters and 1,950 advice in a
day. Every station that opens its navigation display fetches and decodes them all, to keep the last
few minutes (crowsnest-dev #150).

**Zenoh cannot expire a stored value by itself.**
- The storage manager's `garbage_collection.lifespan` collects only *metadata*: tombstones of
  deleted keys and wildcard updates (Zenoh's `DEFAULT_CONFIG.json5`).
- The rocksdb backend's only options are `dir`, `create_db`, `read_only` and `on_closure`.
- Storages ignore a `?_time=[…]` selector.

So something has to delete the keys, and this does it.

## The rule

Expire by **when the router last stored the key**, never by a time inside the payload. Payload times
come from the vessel's clock, and a replay can set them months back.

The protocol restates an open encounter "in full until it closes", and an advice "while the
manoeuvre holds, and once more when retired". So a key the router has not stored for the retention
is one of two things:
- closed or retired that long ago;
- **left open by a navigator that stopped without closing it.** That case also shows on every
  station as "advisor quiet", indefinitely.

| Subject | Key source | Expires when |
|---|---|---|
| `encounter` | `{producer…}/{voyage_id}/{encounter_id}` | the router last stored it more than the retention ago |
| `navigation_advice` | `{producer…}/{voyage_id}/{advice_id}` | the same |
| `advice_disposition` | `{voyage_id}/{advice_id}` | the same, **and** no unexpired advice with that voyage/advice is stored. A decision never outlives its advice |

An entry with no router timestamp has an unknown age, and it is never deleted. Retention defaults to
**24 h** (Ted, 2026-11-05). An MCAP recording keeps the full history regardless.

## Safeguards

- **Dry run by default.** Nothing is deleted without `--apply`.
- **Entities are named, one by one.** `--entity` is required, may be repeated, and refuses a
  wildcard. A delete on a router bridged to a shared network reaches every storage behind it.
- It reads and deletes only the three subjects above.

## Running

```bash
uv sync --locked --extra dev
uv run python bin/keelson-storage-reaper.py --connect tcp/localhost:7447 \
  --entity slipway-usv-alpha --entity slipway-ted-usv-alpha --once            # dry run: reports only
# ... --apply                                                                  # deletes
```

Beside the router, as a compose service:

```yaml
  storage-reaper:
    image: keelson-storage-reaper
    network_mode: host
    restart: unless-stopped
    command: >
      "keelson-storage-reaper --connect tcp/localhost:7447 --apply
       --entity slipway-usv-alpha --entity slipway-ted-usv-alpha"
```

## Development

```bash
uv run --locked ruff check .
uv run --locked pytest -q      # offline: the rules, and the pass against a fake session
```
