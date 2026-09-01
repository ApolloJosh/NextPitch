#!/usr/bin/env python3
"""
Build one day's card for Next Pitch.

A card is one pitcher and a set of real plate appearances sampled from across
his career — different season, ballpark and hitter every time — plus the
scouting data each at-bat needs.

    python3 tools/build_pack.py --date 2026-09-02
    python3 tools/build_pack.py --date 2026-09-02 --pitcher 543037   # force one

RUN THIS WHERE THE NETWORK IS OPEN. statsapi.mlb.com and baseballsavant.mlb.com
are both refused by the egress proxy inside Cowork containers and inside the
desktop app's sandbox, so this belongs on your Mac's Terminal or a CI runner.

Network lives in the get_* functions; everything below them is pure.
"""

import argparse, hashlib, json, pathlib, random, re, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://statsapi.mlb.com"
SAVANT = "https://baseballsavant.mlb.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

SEASONS = list(range(2015, 2027))          # the Statcast era
MIN_PITCHES = 5                            # an at-bat has to be a real duel
MIN_ARSENAL = 3                            # and offer a real choice
GAMES_SAMPLED = 12
AT_BATS = 18

# Not pitches anyone could call: intentional balls, pitchouts, automatic and
# unknown. MLB codes the sweeper ST; the game shows SW.
JUNK = {"IN", "PO", "AB", "AS", "UN", ""}
ALIAS = {"ST": "SW"}
def code(c): return ALIAS.get(c, c)


# ── network ───────────────────────────────────────────────────────────────
def get(url, timeout=60, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:                          # noqa: BLE001
            last = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last}")

def get_json(url, **kw):
    return json.loads(get(url, **kw))

def get_starts(pid):
    """Every game this pitcher started, across the Statcast era."""
    out = []
    for y in SEASONS:
        d = get_json(f"{API}/api/v1/people/{pid}/stats"
                     f"?stats=gameLog&group=pitching&season={y}")
        for s in (d.get("stats") or [{}])[0].get("splits", []):
            if s["stat"].get("gamesStarted"):
                out.append({"y": y, "pk": s["game"]["gamePk"], "date": s["date"]})
        time.sleep(0.2)
    return out

def get_feed(pk):
    return get_json(f"{API}/api/v1.1/game/{int(pk)}/feed/live", timeout=120)

def get_hot_cold(pid, season):
    """The 13-region grid Gameday paints, for that season."""
    d = get_json(f"{API}/api/v1/people/{pid}/stats"
                 f"?stats=hotColdZones&season={season}&group=hitting")
    splits = (d.get("stats") or [{}])[0].get("splits") or []
    ba = next((s for s in splits if s.get("stat", {}).get("name") == "battingAverage"), None)
    ba = ba or (splits[0] if splits else None)
    if not ba:
        return None
    return {z["zone"]: (z["temp"], z["value"]) for z in ba["stat"]["zones"]}

def get_season_line(pid, season):
    d = get_json(f"{API}/api/v1/people/{pid}/stats"
                 f"?stats=season&group=hitting&season={season}")
    sp = (d.get("stats") or [{}])[0].get("splits") or []
    if not sp:
        return None
    s = sp[0]["stat"]
    return [s.get("avg"), s.get("obp"), s.get("slg"), s.get("ops"),
            s.get("homeRuns"), s.get("strikeOuts"), s.get("baseOnBalls"),
            s.get("plateAppearances")]

_ARSENAL = {}
def get_vs_pitch(season):
    """Savant's batter pitch-arsenal leaderboard. Only exists from 2017 on —
    earlier seasons fall back to the batter's season line in the game."""
    if season in _ARSENAL:
        return _ARSENAL[season]
    text = get(f"{SAVANT}/leaderboard/pitch-arsenal-stats"
               f"?type=batter&year={season}&min=1&csv=true", timeout=180).decode("utf-8", "replace")
    lines = text.strip().split("\n")
    out = {}
    if len(lines) > 5:
        cells = lambda l: [c.strip('"') for c in re.findall(r'"[^"]*"|[^,]+', l)]
        # the header's first field is a quoted "last, first" — split it the same
        # way as the rows or every column index shifts by one
        ix = {h: i for i, h in enumerate(cells(lines[0]))}
        for line in lines[1:]:
            c = cells(line)
            out.setdefault(int(c[ix["player_id"]]), []).append(
                [code(c[ix["pitch_type"]]), int(c[ix["pa"]]), c[ix["ba"]],
                 c[ix["slg"]], c[ix["woba"]], float(c[ix["whiff_percent"]])])
    _ARSENAL[season] = out
    return out


# ── pure ──────────────────────────────────────────────────────────────────
def is_pitch(ev):
    """playEvents also carries pickoffs, mound visits and substitutions."""
    pd = ev.get("pitchData") or {}
    return bool(ev.get("isPitch")
                and (pd.get("coordinates") or {}).get("pX") is not None
                and (ev.get("details") or {}).get("type"))

def spread_games(starts, n, seed):
    """One game per slot across the career, so a card is not all one season."""
    rnd = random.Random(seed)
    s = sorted(starts, key=lambda g: g["date"])
    out = []
    for i in range(n):
        lo, hi = i * len(s) // n, (i + 1) * len(s) // n
        if hi > lo:
            out.append(s[rnd.randrange(lo, hi)])
    return out

def spread_at_bats(abs_, n):
    """Deal round-robin by season so the card jumps around the career."""
    by = {}
    for a in abs_:
        by.setdefault(a["season"], []).append(a)
    seasons, out, i = sorted(by), [], 0
    while len(out) < n:
        added = False
        for s in seasons:
            if i < len(by[s]):
                out.append(by[s][i]); added = True
                if len(out) >= n:
                    break
        if not added:
            break
        i += 1
    return out

def at_bats_from_game(feed, pid, meta):
    """Every 5+ pitch plate appearance this pitcher worked in this game."""
    gd, plays = feed["gameData"], feed["liveData"]["plays"]["allPlays"]
    mine = [p for p in plays if p["matchup"]["pitcher"]["id"] == pid]

    arsenal = {}
    for p in mine:
        for ev in p.get("playEvents", []):
            if is_pitch(ev):
                c = code(ev["details"]["type"]["code"])
                if c not in JUNK:
                    arsenal[c] = ev["details"]["type"]["description"]
    if len(arsenal) < MIN_ARSENAL:
        return []

    out, mix = [], {}
    for p in mine:
        evs = [e for e in p.get("playEvents", []) if is_pitch(e)
               and code(e["details"]["type"]["code"]) not in JUNK]
        if len(evs) >= MIN_PITCHES:
            pitches = []
            for i, e in enumerate(evs):
                # `count` on a playEvent is the count AFTER the pitch, so the
                # count the player sees is the previous pitch's.
                pre = (0, 0) if i == 0 else (evs[i-1]["count"]["balls"], evs[i-1]["count"]["strikes"])
                d = e["pitchData"]
                pitches.append([pre[0], pre[1], code(e["details"]["type"]["code"]),
                                d["startSpeed"],
                                round(d["coordinates"]["pX"], 3), round(d["coordinates"]["pZ"], 3),
                                round(d["strikeZoneTop"], 2), round(d["strikeZoneBottom"], 2),
                                e["details"]["call"]["code"], e["details"]["description"]])
            out.append({
                "pk": meta["pk"], "date": meta["date"], "season": meta["y"],
                "venue": gd["venue"]["name"],
                "away": gd["teams"]["away"]["abbreviation"], "home": gd["teams"]["home"]["abbreviation"],
                "awayName": gd["teams"]["away"]["teamName"], "homeName": gd["teams"]["home"]["teamName"],
                "inning": p["about"]["inning"], "top": p["about"]["isTopInning"],
                "o": evs[0]["count"]["outs"], "on": p["matchup"]["splits"]["menOnBase"],
                "bt": [p["matchup"]["batter"]["id"], p["matchup"]["batter"]["fullName"],
                       p["matchup"]["batSide"]["code"]],
                "arsenal": dict(arsenal), "mix": dict(mix),
                "res": [p["result"]["event"], p["result"]["description"]],
                "p": pitches,
            })
        for e in evs:
            c = code(e["details"]["type"]["code"])
            mix[c] = mix.get(c, 0) + 1
    return out

ZK = ["01","02","03","04","05","06","07","08","09","11","12","13","14"]
TEMP = {"hot":"h","warm":"w","lukewarm":"l","cool":"o","cold":"c"}

def pack_zones(zones):
    """One string per hitter: a temp letter and an average, in fixed zone order."""
    if not zones:
        return None
    return "|".join(TEMP.get(zones[z][0], "l") + zones[z][1] if z in zones else "" for z in ZK)

def count_table(all_abs):
    """What he goes to in each count, over every 5+ pitch at-bat pulled — the
    same population the game draws from, so the book matches the test."""
    tab, n = {}, 0
    for a in all_abs:
        for p in a["p"]:
            k = f"{p[0]}-{p[1]}"
            tab.setdefault(k, {})[p[2]] = tab.setdefault(k, {}).get(p[2], 0) + 1
            n += 1
    out = {}
    for k, v in tab.items():
        tot = sum(v.values())
        out[k] = [tot, [[c, round(x / tot * 100)] for c, x in
                        sorted(v.items(), key=lambda kv: -kv[1])]]
    return out, n


# ── entry ─────────────────────────────────────────────────────────────────
def pick_pitcher(pool, date):
    """Deterministic by date, so everyone gets the same arm on the same day."""
    h = int(hashlib.sha256(date.encode()).hexdigest(), 16)
    return pool[h % len(pool)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--pitcher", type=int, help="MLBAM id, overriding the daily pick")
    ap.add_argument("--out", help="defaults to data/packs/<date>.json")
    args = ap.parse_args()

    pool = json.loads((ROOT / "data/pitchers.json").read_text())["pitchers"]
    who = next((p for p in pool if p["id"] == args.pitcher), None) if args.pitcher \
          else pick_pitcher(pool, args.date)
    if who is None:
        raise SystemExit(f"{args.pitcher} is not in the pool")
    print(f"{args.date}: {who['name']} ({who['role']}, {who['hand']}HP)")

    starts = get_starts(who["id"])
    if len(starts) < 4:
        raise SystemExit(f"{who['name']} has too few starts on file ({len(starts)})")
    picks = spread_games(starts, GAMES_SAMPLED, args.date)
    print(f"  {len(starts)} starts on file; sampling {len(picks)}")

    found = []
    for g in picks:
        try:
            found += at_bats_from_game(get_feed(g["pk"]), who["id"], g)
        except Exception as e:                          # noqa: BLE001
            print(f"  ! {g['date']} {g['pk']}: {e}", file=sys.stderr)
        time.sleep(0.4)
    print(f"  {len(found)} at-bats of {MIN_PITCHES}+ pitches")
    if len(found) < AT_BATS:
        raise SystemExit("not enough usable at-bats; raise GAMES_SAMPLED")

    counts, n_counts = count_table(found)
    card = spread_at_bats(found, AT_BATS)

    for a in card:
        bid, season = a["bt"][0], a["season"]
        a["z"] = pack_zones(get_hot_cold(bid, season)); time.sleep(0.25)
        vp = get_vs_pitch(season).get(bid) or []
        vp = [v for v in vp if v[0] in a["arsenal"]]        # only pitches he'd see here
        a["vp"] = vp or None
        a["sl"] = None if vp else get_season_line(bid, season)
        if not vp:
            time.sleep(0.25)

    pack = {
        "v": 1, "date": args.date,
        "src": "MLB StatsAPI GUMBO + hotColdZones; Savant batter pitch-arsenal splits (2017+ only)",
        "pitcher": {"id": who["id"], "name": who["name"], "hand": who["hand"],
                    "peak": who["peak"], "car": who["car"]},
        "abs": card,
        "counts": counts, "countsN": n_counts,
        "zk": ",".join(ZK), "tk": "h=hot,w=warm,l=lukewarm,o=cool,c=cold",
    }

    out = pathlib.Path(args.out) if args.out else ROOT / f"data/packs/{args.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, separators=(",", ":"), ensure_ascii=False))

    idx_path = ROOT / "data/packs/index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else {"packs": []}
    if args.date not in idx["packs"]:
        idx["packs"].append(args.date)
    idx["packs"].sort()
    idx["latest"] = idx["packs"][-1]
    idx_path.write_text(json.dumps(idx, indent=2))

    print(f"  wrote {out}  ({out.stat().st_size:,} bytes)")
    print(f"  {len(card)} at-bats, {sum(len(a['p']) for a in card)} pitches, "
          f"seasons {sorted({a['season'] for a in card})}")


if __name__ == "__main__":
    main()
