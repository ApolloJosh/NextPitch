# Next Pitch

A daily baseball guessing game. One pitcher a day; every at-bat is a real plate
appearance pulled from somewhere in his career. Before each pitch you call the
**type** and the **spot**, and the answer is what he actually threw.

Built on MLB's public pitch tracking, so every location, velocity, hot/cold grid
and pitch-type split in the game is real.

---

## How it plays

| | |
|---|---|
| **1 run** | Right pitch type, wrong spot — or the reverse |
| **3 runs** | Both right |
| **×1.5** | Every scoring call multiplies the next one |
| **+2 mult** | Bonus for calling one of the nine squares *inside* the zone rather than one of the four big areas outside it. Caps at ×8 |
| **Strike** | Miss both. The multiplier resets to ×1 |
| **Out** | Three strikes. Three outs ends the day |

Each at-bat starts with **10 EDGE**, and you earn more by being right — 1 for a
partial call, 3 for both. Spend it on the scouting rack:

- **In this count** — what this pitcher goes to on 1-2, on 3-0, and so on
- **Hot & cold zones** — the hitter's batting average by zone, that season, painted on the strike zone
- **His mix that game** — what he'd thrown earlier in the game this at-bat came from
- **Batter vs pitch type** — SLG, wOBA and whiff rate against each pitch in the arsenal

**Unspent EDGE does not carry.** A new hitter means a new budget.

Zones follow MLB's 13-region scheme in the catcher's view, so a right-handed
hitter stands on the left of the graphic.

---

## Running it

```
python3 -m http.server 8000      # then open http://localhost:8000
```

Opening `index.html` straight off disk won't work — it fetches the day's card
and browsers block that over `file://`. For a single file that runs anywhere:

```
python3 tools/bundle.py                    # newest card
python3 tools/bundle.py --date 2026-09-01
```

That writes `dist/next-pitch-<date>.html` with the artwork and the card inlined.

---

## Building a card

```
python3 tools/build_pack.py --date 2026-09-02
python3 tools/build_pack.py --date 2026-09-02 --pitcher 543037    # force a pitcher
```

The pitcher is chosen deterministically from the date, so everyone gets the same
arm on the same day. The builder then samples twelve starts spread across his
career, keeps every plate appearance of five or more pitches, and deals eighteen
of them round-robin by season so the card jumps around rather than sitting in
one year.

**Run this where the network is open.** Both `statsapi.mlb.com` and
`baseballsavant.mlb.com` are refused by the egress proxy inside sandboxed
environments; a normal terminal or a CI runner is fine.

### Where the data comes from

| Source | What it gives |
|---|---|
| `statsapi.mlb.com` GUMBO feed | Every pitch: type, velocity, plate location in feet, the count, the call, the result |
| `statsapi.mlb.com` hotColdZones | The 13-region batting-average grid, per hitter per season |
| `baseballsavant.mlb.com` pitch-arsenal leaderboard | Hitter performance split by pitch type |

No API key, no sign-up. Cache what you pull and don't hammer it.

---

## The pitcher pool

`data/pitchers.json` holds 30 pitchers with their scoring method written into
the file. Three things about it are judgment calls rather than arithmetic:

- **Starters and closers are ranked separately.** No single IP/W/SV formula
  compares them — weight saves enough for closers to qualify and the top eleven
  are all closers; weight them down and none qualify. The pool is 22 and 8 by
  design.
- **Ranking is on best single season**, not career totals. Summing across
  seasons rewards longevity: by career score, Kevin Gausman outranks deGrom and
  Michael Wacha outranks Skubal.
- **Wins are weighted at 0.5.** At full weight Rick Porcello's 22-win 2016
  outranks Skubal's Cy Young year.

2020 is excluded entirely — a 60-game season isn't comparable as a peak in
either rate or counting stats. ERA+ uses real league ERA per season but **no park
factor**, so Coors and Petco arms are slightly mis-rated.

Sixteen starters made it on merit; six more slots are reserved for pitchers whose
best season is 2021 or later, because a pool ranked purely on merit comes out
80% 2015–19 and a game about baseball now shouldn't be all history.

---

## Layout

```
index.html                 the game; fetches a card at runtime
data/pitchers.json         the 30-pitcher pool and how it was built
data/packs/<date>.json     one day's card
data/packs/index.json      which cards exist, and the newest
data/batter.path           batter silhouette, normalised to unit height
tools/build_pack.py        builds a card from MLB's API
tools/bundle.py            inlines artwork + card into one file
dist/                      bundled builds
```

---

## Known gaps

- **Pitch-type splits only exist from 2017.** At-bats from 2015 and 2016 show
  the hitter's season line instead, labelled as such.
- **The count table is a small sample.** It's built from the same dozen games
  the card was drawn from — a few hundred pitches, not a career. It's a
  tendency, not a projection.
- **No park factor** in the ERA+ used to build the pool.
- **Hot/cold zone numbering** follows MLB's own scheme, catcher's view. Worth
  confirming against a Savant chart before anything goes to print.

---

## Data and rights

All data is MLB's, pulled from public endpoints that carry MLB's copyright
notice in every response. This is a personal project and is not affiliated with
or endorsed by MLB. Anything commercial is a conversation with a lawyer, not a
README.
