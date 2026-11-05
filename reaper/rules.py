"""Which stored navigation-decision keys have expired. Pure: no clock, no Zenoh.

The router keeps every `encounter`, `navigation_advice` and `advice_disposition` key forever, and has
no setting that expires a live value (Zenoh's storage `garbage_collection` collects only tombstones
and wildcard-update metadata; the rocksdb backend exposes no TTL). So this decides what to delete.

THE CLOCK IS THE ROUTER'S. Every stored sample carries the timestamp the router gave it when it was
last written. A payload's own times (`closed_at`, `retired_at`, `valid_to`) are the vessel's clock, and
a replay can set them months back. The protocol (keelson protocols/navigation_decisions.yaml) restates
an open encounter "in full until it closes" and an advice "while the manoeuvre holds, and once more
when retired", so a key the router has not stored for the retention was closed or retired that long
ago -- or abandoned by a navigator that stopped without closing it, which is the case this also clears.

  encounter          `{producer…}/{voyage_id}/{encounter_id}`  expires when last stored > retention ago
  navigation_advice  `{producer…}/{voyage_id}/{advice_id}`     the same
  advice_disposition `{voyage_id}/{advice_id}`                 the same, AND only once no unexpired
                                                               advice with that voyage/advice is stored:
                                                               a decision does not outlive its advice

An entry with no router timestamp has an unknown age and is never expired.
"""

from __future__ import annotations

from dataclasses import dataclass

ENCOUNTER = "encounter"
ADVICE = "navigation_advice"
DISPOSITION = "advice_disposition"
SUBJECTS = (ENCOUNTER, ADVICE, DISPOSITION)


@dataclass(frozen=True)
class Entry:
    subject: str
    key: str
    stored_at_s: float | None  # the router's timestamp for the stored sample, epoch seconds


def _source(key: str, subject: str) -> list[str]:
    """The chunks after `.../pubsub/{subject}/`."""
    marker = f"/pubsub/{subject}/"
    i = key.find(marker)
    return key[i + len(marker):].split("/") if i >= 0 else []


def advice_ref(entry: Entry) -> str | None:
    """`voyage_id/advice_id` an advice or a disposition is about, from its key."""
    parts = _source(entry.key, entry.subject)
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def _old(entry: Entry, now_s: float, retention_s: float) -> bool:
    return entry.stored_at_s is not None and now_s - entry.stored_at_s > retention_s


def expired(entries: list[Entry], now_s: float, retention_s: float) -> list[str]:
    """The keys to delete, in a stable order."""
    out = []
    live_advice = set()
    for e in entries:
        if e.subject == ADVICE and not _old(e, now_s, retention_s):
            ref = advice_ref(e)
            if ref:
                live_advice.add(ref)
    for e in entries:
        if e.subject not in SUBJECTS or not _old(e, now_s, retention_s):
            continue
        if e.subject == DISPOSITION and advice_ref(e) in live_advice:
            continue
        out.append(e.key)
    return sorted(out)
