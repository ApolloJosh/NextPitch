#!/usr/bin/env python3
"""
Inline the batter artwork and one day's pack into a single self-contained
HTML file. The result opens straight from disk (no web server, no CORS)
and is what you hand to a tester or paste into a host that wants one file.

    python3 tools/bundle.py                     # newest pack
    python3 tools/bundle.py --date 2026-09-01
"""

import argparse, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="pack date (defaults to index.latest)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    idx = json.loads((ROOT / "data/packs/index.json").read_text())
    date = args.date or idx["latest"]
    pack_path = ROOT / f"data/packs/{date}.json"
    if not pack_path.exists():
        raise SystemExit(f"no pack at {pack_path}")

    html = (ROOT / "index.html").read_text()
    art = (ROOT / "data/batter.path").read_text().strip()
    pack = pack_path.read_text().strip()

    if "__BATTER_PATH__" not in html:
        raise SystemExit("index.html is missing the __BATTER_PATH__ placeholder")
    html = html.replace("__BATTER_PATH__", art)

    # Inject the pack ahead of the app so boot() finds it and skips the fetch.
    marker = "<script>\n/* ══ Next Pitch ══"
    if marker not in html:
        raise SystemExit("could not find the app script to inject before")
    html = html.replace(
        marker,
        f"<script>window.__PACK={pack};</script>\n{marker}",
        1,
    )

    out = pathlib.Path(args.out) if args.out else ROOT / "dist" / f"next-pitch-{date}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"wrote {out}  ({len(html):,} bytes, pack {date})")


if __name__ == "__main__":
    main()
