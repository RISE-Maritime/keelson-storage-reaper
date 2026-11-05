"""The pass, against a fake session: what it reads, and that only --apply deletes."""

from datetime import datetime, timezone

import pytest

from reaper.service import check_entity, reap

NOW = 1_800_000_000.0
DAY = 86_400.0


class Ts:
    def __init__(self, s):
        self._s = s

    def get_time(self):
        return datetime.fromtimestamp(self._s, timezone.utc)


class Sample:
    def __init__(self, key, stored_at):
        self.key_expr = key
        self.timestamp = None if stored_at is None else Ts(stored_at)


class Reply:
    def __init__(self, sample):
        self.ok = sample


class Session:
    def __init__(self, store):
        self.store = store  # key -> stored_at (or None)
        self.deleted = []
        self.queried = []

    def get(self, selector, timeout=None):
        self.queried.append(selector)
        prefix = selector[: -len("**")]
        return [Reply(Sample(k, t)) for k, t in self.store.items() if k.startswith(prefix)]

    def delete(self, key):
        self.deleted.append(key)


STORE = {
    "rise/@v0/a/pubsub/encounter/navigation/0/colreg/v/old": NOW - 2 * DAY,
    "rise/@v0/a/pubsub/encounter/navigation/0/colreg/v/new": NOW - 60,
    "rise/@v0/a/pubsub/encounter/navigation/0/colreg/v/unstamped": None,
    "rise/@v0/b/pubsub/encounter/navigation/0/colreg/v/other-vessel": NOW - 9 * DAY,
}


def test_a_dry_run_deletes_nothing_and_says_what_it_would():
    s = Session(dict(STORE))
    [r] = reap(s, "rise", ["a"], NOW, DAY, apply=False)
    assert s.deleted == []
    assert r.expired == ["rise/@v0/a/pubsub/encounter/navigation/0/colreg/v/old"]
    assert (r.stored, r.deleted) == (3, 0)


def test_apply_deletes_exactly_the_expired_keys_of_the_named_entity():
    s = Session(dict(STORE))
    reap(s, "rise", ["a"], NOW, DAY, apply=True)
    assert s.deleted == ["rise/@v0/a/pubsub/encounter/navigation/0/colreg/v/old"]
    # vessel b was not named, so its week-old record is not touched
    assert all("/@v0/a/" in q for q in s.queried)


def test_it_reads_the_three_subjects_per_entity():
    s = Session({})
    reap(s, "rise", ["a"], NOW, DAY, apply=False)
    assert s.queried == [
        "rise/@v0/a/pubsub/encounter/**",
        "rise/@v0/a/pubsub/navigation_advice/**",
        "rise/@v0/a/pubsub/advice_disposition/**",
    ]


@pytest.mark.parametrize("entity", ["*", "**", "a/b", "", "slipway-*", "$*"])
def test_a_wildcard_or_multi_chunk_entity_is_refused(entity):
    with pytest.raises(ValueError):
        check_entity(entity)
    with pytest.raises(ValueError):
        reap(Session({}), "rise", [entity], NOW, DAY, apply=True)
