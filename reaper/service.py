"""One reaping pass over router storage: read, judge (rules.py), and delete or report."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .rules import SUBJECTS, Entry, expired

logger = logging.getLogger("reaper")

ENTITY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def check_entity(entity: str) -> str:
    """An entity is one key chunk, never a wildcard: a delete on a router bridged to a shared network
    reaches every storage behind it, so the reaper touches only entities it was told about by name."""
    if not ENTITY_RE.match(entity or ""):
        raise ValueError(f"not a single entity id: {entity!r} (wildcards are refused)")
    return entity


def stored_at_s(sample) -> float | None:
    """The router's timestamp for a stored sample, or None when it carries none."""
    ts = getattr(sample, "timestamp", None)
    if ts is None:
        return None
    return ts.get_time().timestamp()


def collect(session, realm: str, entity: str, timeout_s: float = 10.0) -> list[Entry]:
    entries = []
    for subject in SUBJECTS:
        for reply in session.get(f"{realm}/@v0/{entity}/pubsub/{subject}/**", timeout=timeout_s):
            sample = getattr(reply, "ok", None)
            if sample is None:
                continue
            entries.append(Entry(subject, str(sample.key_expr), stored_at_s(sample)))
    return entries


@dataclass(frozen=True)
class PassResult:
    entity: str
    stored: int
    expired: list[str]
    deleted: int


def reap(session, realm: str, entities: list[str], now_s: float, retention_s: float, apply: bool) -> list[PassResult]:
    """One pass. With `apply` False nothing is deleted; the result says what would be."""
    results = []
    for entity in entities:
        check_entity(entity)
        entries = collect(session, realm, entity)
        keys = expired(entries, now_s, retention_s)
        deleted = 0
        if apply:
            for key in keys:
                session.delete(key)
                deleted += 1
        logger.info(
            "%s: %d stored, %d past %.0f h%s",
            entity, len(entries), len(keys), retention_s / 3600,
            f", {deleted} deleted" if apply else " (dry run: nothing deleted)",
        )
        results.append(PassResult(entity, len(entries), keys, deleted))
    return results
