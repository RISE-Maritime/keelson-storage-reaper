#!/usr/bin/env python3
"""Expire navigation-decision records (encounter, navigation_advice, advice_disposition) from Zenoh
router storage once the router has not stored them for --retention-h hours. See README.md.

Dry run unless --apply. Entities are named one by one; a wildcard is refused."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import zenoh  # noqa: E402

from reaper.service import check_entity, reap  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--realm", default="rise")
    p.add_argument("--entity", action="append", required=True, help="an entity id; repeat for several. No wildcards.")
    p.add_argument("--retention-h", type=float, default=24.0, help="hours since the router last stored a key (default 24)")
    p.add_argument("--interval-s", type=float, default=300.0, help="seconds between passes (default 300)")
    p.add_argument("--once", action="store_true", help="one pass, then exit")
    p.add_argument("--apply", action="store_true", help="delete; without it nothing is deleted")
    p.add_argument("--mode", default="client", choices=["client", "peer"])
    p.add_argument("--connect", action="append", default=[], help="a Zenoh endpoint, e.g. tcp/localhost:7447")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    for entity in args.entity:
        try:
            check_entity(entity)
        except ValueError as exc:
            p.error(str(exc))
    if args.retention_h <= 0:
        p.error("--retention-h must be positive")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    conf = zenoh.Config()
    conf.insert_json5("mode", f'"{args.mode}"')
    if args.connect:
        conf.insert_json5("connect/endpoints", str(list(args.connect)).replace("'", '"'))
    conf.insert_json5("scouting/multicast/enabled", "false")
    retention_s = args.retention_h * 3600
    with zenoh.open(conf) as session:
        while True:
            reap(session, args.realm, args.entity, time.time(), retention_s, args.apply)
            if args.once:
                return 0
            time.sleep(args.interval_s)


if __name__ == "__main__":
    sys.exit(main())
