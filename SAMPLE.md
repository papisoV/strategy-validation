# Sample deliverable

This is what you receive. Real SEC Form 4 data, real prices, real result.

- **Input:** [`sample_picks.csv`](sample_picks.csv) · [`sample_universe.csv`](sample_universe.csv)
- **Output:** [`sample-report.txt`](sample-report.txt)

Reproduce it exactly:

```bash
python validate.py --picks demos/sample_picks.csv \
                   --universe demos/sample_universe.csv \
                   --draws 2000 --costs 0,2,5,10,25,50,100
```

The two CSVs are checked in, so that command works on a fresh clone.
`make_sample.py` — which regenerates them from the original Form 4 filings and
cached prices — needs `backtest_buys.json` and `pricecache.json` (1.7 MB, not
shipped). Drop them next to it and it rebuilds the pair identically.

## The screen being tested

The author had a screen that watched SEC Form 4 insider purchases and flagged
any filing above **$100,000 notional**. The question: does that threshold
select anything, or does it just flag whichever insiders happened to file?

| | |
|---|---|
| Trading days | 8 |
| Unique names priced | 197 |
| Purchases above $100k | 99 (varying 6–22 per day) |
| Available names per day | 25–59 |
| Forward window | T+5 trading days |
| Universe rows written | 293 |

Note that last row of the inputs table. The available pool is **not** constant
— it swings from 25 to 59 names across eight days. A report that printed a
single "pool per day: 59" line would have hidden that. The sheet prints the
per-day table instead.

## The answer

```
VERDICT: NOT ESTABLISHED
  8 pick day(s) is too few to separate selection from chance; this is a
  statement about sample size, not about the strategy.

  observed mean       : -0.4961%
  control mean        : -0.4096%
  observed percentile : 0.4775
```

Read that carefully, because **NOT ESTABLISHED is the honest answer and it is
the one most tools won't give you.**

Eight days is not enough to tell selection apart from luck, so this report
declines to conclude. What it *can* say is that over these eight days the
screen's picks finished at −0.4961% against −0.4096% for same-day random
draws — i.e. slightly *behind* random, nowhere near the 0.95 gate.

Had the tool been willing to overclaim, it could have reported the number
anyway and let you read the percentile as a result. It doesn't. Below 20 pick
days the conclusion section says so and stops.

## Why lead with a failed screen

Because a validator's value is not that it finds edge. It's that it can say
**no** to something you already believe in.

This screen was the author's own. The NO-GO here is what stopped a product
built on it. That is the whole reason this package exists — see the README.

## What this does not check

The gap between "this screen doesn't select" and "this screen doesn't select
*and here's why*" is large. This report only covers the first half. It does
not audit:

- look-ahead in how the original backtest was built
- survivorship in the symbol universe
- whether assumed fills were achievable
- corporate actions in the price series

Those are real failure modes and they need a different tool. If your question
is "why doesn't it work" rather than "does it work", say so up front.

## Also available: the synthetic cases

The real sample above is honest but inconclusive by construction. If you want
to see the tool separate signal from noise on data long enough to support a
verdict, the `demos/` directory has three 60-day clients — one with genuine
edge, one with none, one with a thin edge that survives 2bps but not 25bps:

| Client | Has edge | Verdict | Percentile |
|---|---|---|---|
| `skilled` | yes | SELECTION DETECTED | 1.0000 |
| `random` | no | NOT SHOWN | 0.2495 |
| `thin` | yes, small | SELECTION DETECTED | 1.0000 |

The `random` row is the one worth reading.
