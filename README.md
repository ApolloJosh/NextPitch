# Next Pitch

A daily baseball guessing game. One pitcher a day; every at-bat is a real plate
appearance pulled from somewhere in his career. Before each pitch you call the
**type** and the **spot**, and the answer is what he actually threw.

Built on MLB's public pitch tracking, so every location, velocity, hot/cold grid
and pitch-type split in the game is real.

---

## How it plays

You call two things before every pitch: the **type**, and the **spot**. The spot
isn't a box — it's a point. Click anywhere in the frame, and when the pitch lands,
rings go up around where it actually crossed.

| Distance from the pitch | | Points | Multiplier |
|---|---|---|---|
| within 3″ | **Bullseye** | 4, then **doubled** | ×2 |
| within 6″ | Inside it | 2 | ×1.5 |
| within 10″ | Caught the edge | 1 | ×1.15 |
| beyond | missed the spot | 0 | — |

Plus **+2** for the right pitch type, and **+2** more for getting type and spot
together. A bullseye doubles the whole pitch. Miss on both and the multiplier
resets to ×1 and you take a **miss**; three misses is an out, three outs ends the
day.

The multiplier grows by *how close* you were, not merely that you scored. That
matters: pitches cluster over the middle, so a flat multiplier made clicking the
centre of the zone every time the strongest strategy — a lazy call kept a streak
alive as well as a read one. Graded growth pays the read.

Simulated over a real card, 61 runs each:

| | Points | Pitches survived | Bullseyes |
|---|---|---|---|
| Clicking at random | 7 | 13 | 0 |
| His best pitch, middle of the zone | 123 | 31 | 0 |
| Working the count table | 119 | 31 | 1 |
| Reading him well | 158 | 32 | 2 |

Lazy play and half-attentive play land in the same place, which is the point:
the count table alone doesn't beat the middle of the zone, because pitches
cluster there anyway. What separates them is precision — and precision is what
the bullseye pays.

You start the day with **10 EDGE** and earn more by being right — 1 for a partial
call, 2 for both, 3 for a bullseye. Spend it on the scouting rack:

- **In this count** — what this pitcher goes to on 1-2, on 3-0, and so on
- **Hot & cold zones** — the hitter's batting average by zone, that season, painted on the strike zone
- **His mix that game** — what he'd thrown earlier in the game this at-bat came from
- **Batter vs pitch type** — SLG, wOBA and whiff rate against each pitch in the arsenal

**It is one budget for the whole day.** Nothing refills between hitters, so what
you spend scouting the first man isn't there for the ninth.

### In your ear

Three more sell the answer to the pitch in front of you rather than a tendency,
and they last exactly one pitch:

| | | |
|---|---|---|
| **Bang the Can** | 9 EDGE | The pitch type, this once. |
| **Read the Mitt** | 9 EDGE | Where it will cross, marked on the zone. It shows the spot; landing on it is still your problem. |
| **Sit on Two** | 5 EDGE | Narrows the arsenal to two types, one of which is right. |
| **Upstairs or Down** | 5 EDGE | Which half of the zone it crosses. The other half goes dark. |

Two of them make the other two pointless — Bang the Can settles what Sit on Two
narrows, and Read the Mitt settles what Upstairs or Down narrows — so when the
stronger one is bought the cheaper one is disabled rather than left there to
take five EDGE for nothing.

Simulated over a real card, 61 runs each:

| | Points | Pitches | Median buys (can/mitt/two/half) |
|---|---|---|---|
| Never buy | 41 | 16 | 0 / 0 / 0 / 0 |
| The two cheap narrowers when flush | 34 | 16 | 0 / 0 / 1 / 1 |
| Bank, then cash in at a high multiplier | 80 | 18 | 0 / 1 / 0 / 0 |
| Buy everything you can afford | **96** | 26 | 1 / 1 / 2 / 2 |

The fourth special changed the shape of this. With three, banking to cash in at
a high multiplier was the best play (80 against 75 for buying constantly). Add a
second five-EDGE narrower and spending everything as you earn it wins instead —
not by scoring more per pitch but by **surviving longer**, 26 pitches against
18. Both are coherent: one trades floor for ceiling, the other buys the floor.
Whether two viable strategies is better than one clear one is a design call, not
a bug, and it's easy to tune back by pricing the narrowers apart.

The scouting rack still earns its place: three EDGE of *In this count* covers
every pitch of a six-pitch at-bat, where five EDGE of *Sit on Two* covers one.

Pitches you bought help on are logged separately — counted on the final card and
shown as 🟦 in the shared grid — so a score says how it was got.

The view is the catcher's, so a right-handed hitter stands on the left.

---

## The home screen, and the daily turnover

The landing page names the day's arm with his peak line and a **Face today's
pitcher** button, and lists every earlier card underneath, with a countdown to
the next one. `#YYYY-MM-DD` on the URL drops you straight into that day.

Cards are built a week ahead so there is always a queue, but everything the app
routes and renders is filtered to `date <= today` in the **player's own local
time**. A card dated tomorrow does not exist as far as the UI is concerned: it
isn't listed, and a deep link to it goes to the home screen instead. At local
midnight the countdown hits zero and the page redraws itself with the new arm —
no reload needed.

If the queue ever runs dry the newest card stays playable, but it stops calling
itself "today's pitcher" and says so.

**This hides the next card; it does not secure it.** The packs are static files
in a public repo, so anyone who guesses `data/packs/2026-09-09.json` can read
tomorrow's pitcher. That is fine for a game where the answer is a name, and it
is the price of a site with no server. The fix, if it ever matters, is to stop
publishing ahead: `.github/workflows/daily-card.yml` builds each day's card on a
schedule, so the queue depth is a setting rather than a design.

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

The pitcher comes from a **rotation**, not a hash of the date. Hashing each date
independently looked fine and wasn't: sha256 over the seven days from 2026-09-02
lands on the same pitcher four times. The rotation shuffles the pool with a seed
derived from the cycle number and walks it, so every arm appears once per cycle
and the order changes each time round. It then steps over anyone who has been on
the card in the last fourteen days, and anyone marked `eligible: false`. The builder then samples outings spread across his career —
fourteen starts for a starter, fifty appearances for a reliever, who faces four
hitters a night instead of twenty-five — and deals eighteen plate appearances
round-robin by season so the card jumps around rather than sitting in one year.

Three filters decide what's usable:

- **Five pitches or more.** An at-bat has to be a real duel.
- **Never the first inning.** "His mix that game" is worth nothing before he's
  thrown anything, so the card starts in the second.
- **2017 and later.** Savant's batter pitch-type splits begin there.
- **A hitter with a real book.** At least 150 plate appearances on file that
  season, covering at least two pitches in the arsenal, and a hot/cold grid that
  isn't placeholders. Without this the card fills up with September call-ups,
  2020 part-timers and pitchers batting, whose scouting panels read ".000 on 4
  PA" — worse than no panel, because it looks like information.

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
.github/workflows/         daily card build, so the queue refills itself
data/pitchers.json         the 30-pitcher pool and how it was built
data/packs/<date>.json     one day's card
data/packs/index.json      which cards exist, and the newest
data/batter.path           batter silhouette, normalised to unit height
tools/build_pack.py        builds a card from MLB's API
tools/bundle.py            inlines artwork + card into one file
dist/                      bundled builds
```

---

## Arms that can't carry a card

A card needs at least three pitch types on offer (`MIN_ARSENAL`), or calling the
pitch is a coin flip. Measured against the builder, two arms in the pool can't
clear it and are marked `eligible: false` in `data/pitchers.json`, which the
rotation reads:

| | Usable at-bats from 50 games sampled | Needs |
|---|---|---|
| Craig Kimbrel | 14 | 18 |
| Edwin Díaz | 6 | 18 |

Closers in general are fine — **Aroldis Chapman** yields 64 usable at-bats and
makes a good card, and a distinctive one: every plate appearance is the seventh
inning or later, which plays nothing like a starter's card. It's the two-pitch
arms specifically that fail.

---

## Known gaps

- **Nothing before 2017.** Savant's batter pitch-type splits start there, and a
  card without them is missing a whole scouting panel. It costs the pool its
  2015–16 seasons — Kershaw's 2015 and Arrieta's Cy Young year are out of reach.
- **The count table is a small sample.** It's built from the same dozen games
  the card was drawn from — a few hundred pitches, not a career. It's a
  tendency, not a projection.
- **No park factor** in the ERA+ used to build the pool.
- **Hot/cold zone numbering** follows MLB's own scheme, catcher's view. Worth
  confirming against a Savant chart before anything goes to print.
- **The ring radii are tuned against one card.** 3/6/10 inches came from
  simulating deGrom's; a pitcher who lives on the corners may play differently.

---

## Data and rights

All data is MLB's, pulled from public endpoints that carry MLB's copyright
notice in every response. This is a personal project and is not affiliated with
or endorsed by MLB. Anything commercial is a conversation with a lawyer, not a
README.
