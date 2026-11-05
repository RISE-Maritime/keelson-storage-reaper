"""The CLI's safeguards: entities are required and named, and the default is a dry run."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("cli", Path(__file__).resolve().parents[1] / "bin" / "keelson-storage-reaper.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def test_no_entity_is_refused():
    with pytest.raises(SystemExit):
        cli.parse_args([])


def test_a_wildcard_entity_is_refused():
    with pytest.raises(SystemExit):
        cli.parse_args(["--entity", "*"])


def test_the_default_is_a_dry_run_at_24_h():
    args = cli.parse_args(["--entity", "slipway-usv-alpha"])
    assert (args.apply, args.retention_h, args.realm) == (False, 24.0, "rise")


def test_a_non_positive_retention_is_refused():
    with pytest.raises(SystemExit):
        cli.parse_args(["--entity", "a", "--retention-h", "0"])
