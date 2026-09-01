#!/usr/bin/env python3
"""
Inline the batter artwork and the day cards into a single self-contained
HTML file. The result opens straight from disk (no web server, no CORS)
and is what you hand to a tester or paste into a host that wants one file.

    python3 tools/bundle.py                     # every card
    python3 tools/bundle.py --date 2026-09-01   # one card only
"""

import argparse, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="bundle only this card (default: all of them)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    idx = json.loads((ROOT / "data/packs/index.json").read_text())
    entries = [e if isinstance(e, dict) else {"date": e} for e in idx["packs"]]
    if args.date:
        entries = [e for e in entries if e["date"] == args.date]
        if not entries:
            raise SystemExit(f"no card dated {args.date} in the index")

    packs = {}
    for e in entries:
        path = ROOT / f"data/packs/{e['date']}.json"
        if not path.exists():
            raise SystemExit(f"index lists {e['date']} but {path} is missing")
        packs[e["date"]] = json.loads(path.read_text())

    entries.sort(key=lambda e: e["date"])
    inline_idx = {"latest": entries[-1]["date"], "packs": entries}

    html = (ROOT / "index.html").read_text()
    art = (ROOT / "data/batter.path").read_text().strip()

    if "__BATTER_PATH__" not in html:
        raise SystemExit("index.html is missing the __BATTER_PATH__ placeholder")
    html = html.replace("__BATTER_PATH__", art)

    # Inject ahead of the app so boot() finds both and skips every fetch.
    marker = "<script>\n/* ══ Next Pitch ══"
    if marker not in html:
        raise SystemExit("could not find the app script to inject before")
    blob = (
        "<script>"
        f"window.__PACKS={json.dumps(packs, separators=(',', ':'), ensure_ascii=False)};"
        f"window.__INDEX={json.dumps(inline_idx, separators=(',', ':'), ensure_ascii=False)};"
        "</script>\n"
    )
    html = html.replace(marker, blob + marker, 1)

    stem = f"next-pitch-{args.date}" if args.date else "next-pitch"
    out = pathlib.Path(args.out) if args.out else ROOT / "dist" / f"{stem}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"wrote {out}  ({len(html):,} bytes, {len(packs)} card(s): "
          f"{', '.join(sorted(packs))})")


if __name__ == "__main__":
    main()
