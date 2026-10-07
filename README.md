# strategy-validation

**Does a stock screen actually select anything, or does it just inherit whatever the day did?**

Two CSV files in, one sheet out. No signals, no recommendations, no price targets.

```
python validate.py --picks picks.csv --universe universe.csv
```

## The one question

The client's screen picked some names each day. Every other name available that
same day is the fair comparison. So take random draws **of the same size, from
the same day**, many times, and see where the observed result lands among them.

Same-day is the whole point. Comparing a screen against "the market" lets it
take credit for whatever the day itself did — a screen can look brilliant
during a week when everything went up, and be worthless on Monday.

## Input

`picks.csv` — what the screen chose:

```csv
date,name
2024-01-02,AAPL
2024-01-02,MSFT
2024-01-03,NVDA
```

`universe.csv` — everything it *could* have chosen, with the outcome:

```csv
date,name,fwd_ret
2024-01-02,AAPL,0.0124
2024-01-02,MSFT,-0.0031
...
```

`fwd_ret` is whatever horizon the client claims to be picking for. This tool
does not care what it is; it compares the client's draw against the other
draws from the same pool. Garbage in still produces a percentile — that is
the client's problem, not something this tool can detect.

## Output

```
VERDICT: SELECTION DETECTED
  observed result sits at the 100.0% mark of same-day random draws...

  random draws        : 2000 (seed 20261007)
  observed mean       : +4.0742%
  control mean        : -0.0371%
  control spread (sd) : ...
  observed percentile : 1.0000
  gate (Bonferroni)   : 0.9500 for 1 variant(s)
```

Plus a cost grid, because a screen that clears 8 bps is a rounding error.

### Verdicts

| Verdict | Meaning |
|---|---|
| `SELECTION DETECTED` | observed result beats the gate for this many variants |
| `NOT SHOWN` | indistinguishable from same-day random draws |
| `NOT ESTABLISHED` | fewer than 20 pick days — too few to say anything |

`NOT ESTABLISHED` exists because below ~20 days the percentile is close to a
coin flip no matter how good the screen is. A validator that always reaches a
conclusion is decoration.

## Reproducing any number

Everything is a function of the two files plus `--draws` and `--seed`, both of
which are printed in the report. Same inputs + same seed = identical output.

```bash
python validate.py --picks d.csv --universe u.csv --draws 2000 --seed 20261007
```

## If you tried thirty variations before settling

Tell it. `--variants 30` widens the gate (Bonferroni: `1 - 0.05/30`) rather
than changing the number. Testing thirty screens and reporting the best one is
how you find performance that isn't there.

```bash
python validate.py --picks d.csv --universe u.csv --variants 30
```

## Cost sensitivity

```bash
python validate.py --picks d.csv --universe u.csv --costs 0,2,5,10,25,50,100
```

Applies once per pick per day, recomputes the mean, tells you the largest
tested cost at which it was still positive. It's a grid, so the true breakeven
lies between steps — the report says so too.

## Demo

```bash
python demos/make_demo.py     # writes 60 days x 120 names into demos/
python validate.py --picks demos/demo_picks_skilled.csv \
                   --universe demos/demo_universe.csv --draws 2000
python validate.py --picks demos/demo_picks_random.csv \
                   --universe demos/demo_universe.csv --draws 2000
```

| Client | Actually has edge? | Verdict | Percentile |
|---|---|---|---|
| `skilled` | yes | SELECTION DETECTED | 1.0000 |
| `random` | no | NOT SHOWN | 0.2495 |
| `thin` | yes, small | SELECTION DETECTED | 1.0000 |

The random client is the one that matters. **The tool has to be able to say
no**, or it isn't measuring anything.

## Sample deliverable

**[SAMPLE.md](SAMPLE.md)** shows a real engagement end to end — a $100k+
SEC Form 4 purchase screen tested on 8 trading days, 197 names, priced, with
the report it produced.

The verdict is `NOT ESTABLISHED`: eight days is too few to conclude anything.
That sample leads the docs on purpose. A validator that only publishes its
successes is an advertisement.

## Demo

```bash
python demos/make_demo.py     # writes 60 days x 120 names into demos/
python validate.py --picks demos/demo_picks_skilled.csv \
                   --universe demos/demo_universe.csv --draws 2000
python validate.py --picks demos/demo_picks_random.csv \
                   --universe demos/demo_universe.csv --draws 2000
```

| Client | Actually has edge? | Verdict | Percentile |
|---|---|---|---|
| `skilled` | yes | SELECTION DETECTED | 1.0000 |
| `random` | no | NOT SHOWN | 0.2495 |
| `thin` | yes, small | SELECTION DETECTED | 1.0000 |

The random client is the one that matters. **The tool has to be able to say
no**, or it isn't measuring anything.

## Tests

```bash
python tests/test_strategy_validation.py
```

47 assertions. They lock down four things worth locking down:

1. **Wrong input raises, never returns empty.** A pipeline that reports zero
   findings while being fed the wrong shape is indistinguishable from a
   genuine negative result.
2. **Same seed reproduces exactly.**
3. **The report contains no banned word** — recommend, advice, guarantee,
   conviction, smart money, worth watching, alpha, outperform, win rate. The
   wording ban is enforced by a test, not by a comment asking nicely.
4. **Per-day detail survives the render.** It once printed a single
   `pool/day` line taken from day one, which on the real Form 4 sample hid
   that the pool moves between 25 and 59 names across eight days.

Every README and SAMPLE.md figure is re-derived from a live run by
`tools/check_readme.py` and `tools/check_sample.py`. Recalled numbers are
wrong numbers.

## What this does not do

- Doesn't check look-ahead, survivorship, or unrealistic fills in how the
  client built *their own* backtest. Those are real failure modes and they're
  upstream of this tool.
- Doesn't detect anything absent from the input files.
- Doesn't say whether to trade anything. It answers one question about one
  screen.

## Why this exists

The author built and published an insider-transaction radar, then measured it
against same-day random draws over four horizons. It didn't beat them. The
measurement cost one afternoon; believing the unmeasured version would have
cost much more.

This is the tool that produced that measurement, generalized to take anyone's
screen instead of just that one.

## Scope note

This compares selection against chance. It does not say whether a strategy
makes money, is tradeable, or should be run. Nothing here is investment
advice, and it is not a recommendation to do anything.
