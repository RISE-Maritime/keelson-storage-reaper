"""The expiry rules on literal entries. 24 h retention; times are epoch seconds."""

from reaper.rules import ADVICE, DISPOSITION, ENCOUNTER, Entry, advice_ref, expired

NOW = 1_800_000_000.0
DAY = 86_400.0
BASE = "rise/@v0/slipway-usv-alpha/pubsub"


def enc(eid, age_s, voyage="voy-1"):
    return Entry(ENCOUNTER, f"{BASE}/encounter/navigation/0/colreg/{voyage}/{eid}", NOW - age_s)


def adv(aid, age_s, voyage="voy-1"):
    return Entry(ADVICE, f"{BASE}/navigation_advice/navigation/0/colreg/{voyage}/{aid}", NOW - age_s)


def disp(aid, age_s, voyage="voy-1"):
    return Entry(DISPOSITION, f"{BASE}/advice_disposition/{voyage}/{aid}", NOW - age_s)


def test_a_record_not_stored_for_a_day_expires_and_a_fresh_one_does_not():
    assert expired([enc("old", DAY + 1), enc("new", 60)], NOW, DAY) == [f"{BASE}/encounter/navigation/0/colreg/voy-1/old"]


def test_the_boundary_is_strict():
    assert expired([enc("edge", DAY)], NOW, DAY) == []
    assert expired([enc("edge", DAY + 0.001)], NOW, DAY) != []


def test_an_open_encounter_abandoned_by_a_dead_navigator_expires_too():
    # Nothing in the key says open or closed: an open encounter is restated while it stays open, so
    # one not stored for a day was abandoned. That is the "advisor quiet forever" case.
    assert expired([enc("abandoned", 3 * DAY)], NOW, DAY) == [f"{BASE}/encounter/navigation/0/colreg/voy-1/abandoned"]


def test_old_advice_expires():
    assert expired([adv("a1", DAY + 5)], NOW, DAY) == [f"{BASE}/navigation_advice/navigation/0/colreg/voy-1/a1"]


def test_a_disposition_never_outlives_its_advice():
    # The decision is old but its advice is still being restated: keep the decision.
    entries = [adv("a1", 60), disp("a1", 2 * DAY)]
    assert expired(entries, NOW, DAY) == []


def test_a_disposition_goes_with_its_expired_advice_and_alone_when_none_is_stored():
    entries = [adv("a1", 2 * DAY), disp("a1", 2 * DAY), disp("orphan", 2 * DAY)]
    assert expired(entries, NOW, DAY) == sorted([
        f"{BASE}/navigation_advice/navigation/0/colreg/voy-1/a1",
        f"{BASE}/advice_disposition/voy-1/a1",
        f"{BASE}/advice_disposition/voy-1/orphan",
    ])


def test_a_disposition_for_another_voyages_advice_is_not_kept_by_it():
    assert expired([adv("a1", 60, voyage="voy-2"), disp("a1", 2 * DAY, voyage="voy-1")], NOW, DAY) == [
        f"{BASE}/advice_disposition/voy-1/a1"
    ]


def test_a_fresh_disposition_stays_even_with_no_advice():
    assert expired([disp("a1", 60)], NOW, DAY) == []


def test_an_entry_with_no_router_timestamp_is_never_expired():
    assert expired([Entry(ENCOUNTER, f"{BASE}/encounter/p/voy-1/e", None)], NOW, DAY) == []


def test_a_subject_it_does_not_reap_is_left_alone():
    assert expired([Entry("route", f"{BASE}/route/r/latest", NOW - 10 * DAY)], NOW, DAY) == []


def test_advice_ref_is_the_last_two_chunks():
    assert advice_ref(adv("a1", 0)) == "voy-1/a1"
    assert advice_ref(disp("a1", 0)) == "voy-1/a1"
