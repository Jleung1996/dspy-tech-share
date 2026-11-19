# peerlens

A peer-labelling and prompt-comparison harness for a benchmark-selection workflow.

It answers one question, as a number rather than an opinion:

> **If I give you `NVDA`, does your system return `AMD` / `TSM`, or does it return `Salesforce`?**

And it lets you answer the follow-up: *did that get better because I rewrote the
prompt, or because I gave the model better context?*

---

## Repository layout

```
peerlens/        the package - catalogue, labels, signals, metric, prompt rules
cases/           regression cases (YAML)
tests/           79 tests covering the metric, gates and regression suite
scripts/         CLIs: run_baseline, run_demo, run_regression, run_teach,
                 run_optimize, score_proposals, verify_notebook, audit_deck
deck/            the HTML deck generator and its content modules
docs/            PROMPT_DECOMPOSITION.md, how-the-deck-was-built.md
out/             generated artefacts - the deck, the baseline, the leaderboard
notebook.ipynb   a 37-cell walkthrough that runs offline
```

Everything is run from the repository root.

---

## The short version

| | |
|---|---|
| **Does the metric need humans?** | Mostly no. Three independent proxies triangulate a label; humans review only the disagreements. |
| **Does it need DSPy?** | No. The labelling and measurement layer is plain Python. DSPy is needed only to run the real programs. |
| **Does it need an API key?** | No, for the harness. Yes, for `--lm`. |
| **Is the demo data real?** | **No.** The return series is a seeded factor model. See [What is real](#what-is-real-and-what-is-not). |

---

## The claim this harness tests

Three prompt qualities are modelled as deterministic runners, so the pipeline can
be validated with no model and no cost:

| System under test | score | peer credit | peer hits | hard neg | dup |
|---|---|---|---|---|---|
| A: naive (description only) | 0.307 | 0.578 | 0.467 | 0.289 | 0.100 |
| B: sector-only | 0.176 | 0.444 | 0.356 | 0.344 | 0.200 |
| C: industry-aware + enriched pack | **0.639** | 0.661 | 0.378 | **0.022** | 0.000 |
| C′: industry-aware, no co-movement | 0.606 | 0.661 | 0.378 | 0.044 | 0.000 |

Read the last two columns, not the first.

**The interesting result is that A finds *more* peers than C and still scores half
as well.** A's peer-hit rate is 0.467 against C's 0.378 — because A spends all
three slots on closest matches, while C deliberately spends one on a reference.
But A also puts an unrelated instrument in the answer 29% of the time, and C does
it 2% of the time.

That asymmetry is the entire argument for scoring tiers instead of similarity:
**a single "how similar is this" number ranks the worst system second.**

And the C vs C′ comparison is the second point: adding measured co-movement to the
catalogue moves hard negatives from 4.4% to 2.2%. Small, but it is a *context*
change — the prompt text is byte-identical. That is the lever you were asking
about.

---

## Which similarity notion actually works?

Same run, each signal scored against hand-curated truth:

| signal | precision | recall | F1 | hard-negative accuracy | false positives on hard negatives |
|---|---|---|---|---|---|
| taxonomy (sector/industry) | 1.00 | 0.77 | 0.87 | 0.87 | 0 / 77 |
| co-movement (market-orthogonalised) | 1.00 | 0.77 | 0.87 | 0.87 | 0 / 77 |
| description (TF-IDF) | 0.44 | 0.50 | 0.47 | 0.68 | 9 / 77 |

Description similarity — i.e. the thing a naive prompt implicitly does — is
**44% precise**. It is also the only signal that confuses industries *within* a
sector: it happily matches a payments network to a bank. Everything else is noise
by comparison.

This is the answer to "how do I tell whether a prompt is doing well at financial
information": build the three signals, and see which one your prompt is
accidentally imitating.

---

## Quick start

```bash
python scripts/run_demo.py                     # synthetic returns, scripted runners
python scripts/run_demo.py --assets EQ_NVDA,EQ_V --quiet
python scripts/run_demo.py --returns prices.csv
python scripts/run_demo.py --lm openai/gpt-4o-mini    # run the real DSPy programs
python -m pytest tests -q
```

Outputs land in `out/`:

| file | contents |
|---|---|
| `comparison.md` | the table above, plus per-case and per-pick detail |
| `per_case.csv` | every case × every runner, with all axes |
| `signals.csv` | every (asset, candidate) pair with all three raw scores and the verdict |
| `conflicts.md` | the human-review queue |

---

## How the labelling works

```
                    ┌──────────────────┐
   (asset, candidate)│ 1. taxonomy      │ sector / industry / breadth
                    │ 2. co-movement   │ correlation of market-orthogonal residuals
                    │ 3. description   │ TF-IDF cosine over business summaries
                    └────────┬─────────┘
                             ▼
                    votes ≥ 2 of 3  ──►  accept
                    votes == 0      ──►  reject
                    otherwise       ──►  conflict  ──► human review
```

Two design points worth defending:

**Co-movement uses residuals, not raw correlation.** Raw correlation would rank
every asset that is simply long the market as a peer of every other. The panel is
regressed on a market proxy first, and the correlation of the *residuals* is the
signal. That is what makes it measure beyond-beta similarity rather than size.

**Broad indices are adjacent, never peers.** An S&P 500 reference is a legitimate
whole-portfolio reference for any equity, so punishing it is wrong. Rewarding it
would let a system score well by returning three broad indices and never doing
the peer analysis. Half credit, scored as a separate tier.

---

## The metric

`peerlens/metric.py`, four tiers:

| pick | credit |
|---|---|
| peer (same industry, substitutable) | 1.0 |
| adjacent (sector proxy, broad index, cross-industry neighbour) | 0.5 |
| hard negative (same sector, clearly wrong) | −1.5 |
| unrelated / unknown id | −1.5 |

```
composite = clamp01(peer_credit − 1.5 × hard_negative_rate) × duplicate_penalty
```

Wrong count, duplicate ids, or an id not in the catalogue → `0.0`, because your
downstream contract requires exactly three.

**Deliberate choice:** three different semiconductor *companies* is a legitimate
peer set — it is what you asked for. Three semiconductor *ETFs* tracking the same
index is the redundancy your review rules forbid. Only the latter is penalised.

Every axis is returned alongside the composite, because "0.64" tells you nothing
about whether the failure was peers, format, or duplication.

---

## What is real and what is not

Being explicit, because this is financial data and the difference matters.

**Real:**
- The 89-instrument catalogue: names, tickers, sectors, industries, regions,
  currencies. Assembled by hand from public, stable facts.
- The 30-asset test bed and every peer / adjacent / hard-negative label.
- All signal logic, the triangulation, the metric, the report.

**Not real:**
- **The return panel.** `synthetic_panel()` generates it from a seeded factor
  model. It is a test fixture. No number derived from it is a finding about
  actual securities.

**Consequence you must know about:** the synthetic generator defines industries as
exact factor loadings, so **co-movement reproduces the taxonomy almost perfectly
in the demo**. The table above shows taxonomy and co-movement with identical
scores — that is circularity, not corroboration. There is a test
(`test_synthetic_panel_encodes_the_taxonomy`) that pins this so the caveat cannot
quietly go stale.

With real return data those two signals stop agreeing, and the agreement between
them becomes genuinely informative. That is the first thing to fix.

```bash
python scripts/run_demo.py --returns my_prices.csv
```

CSV format: a `date` column plus one column per ticker id.

**A second limitation:** cross-sector negatives are derived mechanically from the
taxonomy, so every signal scores well on them by construction. The number that
actually discriminates is `hard-negative accuracy`, computed only on within-sector
confusions like *bank vs payments network*.

---

## What the harness already caught

Not just a demo — the thing found real defects in its own ground truth:

1. **`ASML` is a curated peer of the semiconductor names that all three signals
   miss.** Taxonomy sees "Semiconductor Equipment" vs "Semiconductors" and says
   no. Co-movement agrees. This is supply-chain coupling, and it is invisible to
   every proxy here. `missed_peers()` lists these; they are exactly where a human
   is still required. Kept in deliberately rather than papered over.

2. **The semiconductor indices were tagged `sector=Semiconductors`** instead of
   `Information Technology`, which silently made them cross-sector negatives for
   software names. Caught by `test_hard_negatives_share_the_asset_sector`.

3. **A duplicate-exposure rule was penalising the correct answer.** Three chip
   *companies* is right; the rule was flagging them as redundant until it was
   narrowed to funds only.

---

## The DSPy layer

`peerlens/dspy_program.py` implements the real experiment: three variants where
**B and C share byte-identical instructions** and differ only in whether the
catalogue is enriched with metadata and co-movement. That is what makes it a test
of context rather than wording.

DSPy 3.5.0 is vendored into `.pydeps/`, so `--lm` works without touching your
interpreter:

```bash
python scripts/run_demo.py --lm openai/gpt-4o-mini
```

Notes for editing that file:

- `XMLAdapter` is the default in 3.5. Avoid `Any` and string/container unions in
  signature fields — nested pydantic models are fine.
- `ChainOfThought` adds its own reasoning field, so `output_fields` is a superset
  of what you declared.
- A custom LM must return the canonical `Response` object; returning
  `list[str]` no longer works. `DummyLM` cannot satisfy a nested-output JSON
  adapter, so the free path is the scripted runners, not a fake DSPy LM.

`DspyRunner._to_selections` deliberately does **not** pad or repair a bad answer.
A wrong count or an invented id is a real failure and the metric should see it.

---

## Layout

```
peerlens/
  model.py          Instrument / Case / Pack, GICS-style taxonomy
  pack.py           89-instrument catalogue + 30 curated cases + conflict notes
  marketdata.py     ReturnPanel, synthetic factor model, CSV loader
  signals.py        taxonomy / co-movement / description
  labeling.py       triangulation, agreement report, conflict queue, missed peers
  metric.py         tiered asymmetric scoring + DSPy metric adapter
  runners.py        scripted runners A / B / C / C'
  harness.py        comparison table and reports
  prompt_v2.py      the equity prompt decomposed into schema / python / validator / instruction
  regression.py     reported failure -> permanent test case
  dspy_program.py   the three-variant DSPy experiment (optional)
cases/
  regressions.yaml  six regression cases, addable by operations without Python
scripts/run_demo.py         peer-scoring harness CLI
scripts/run_regression.py   regression gate, exits non-zero on a blocking failure
tests/              76 tests
out/                generated reports
```

---

## The prompt decomposition

`docs/PROMPT_DECOMPOSITION.md` is the shareable write-up. Short version:

**Your 22 prompt rules split 16 mechanical / 6 optimisable.**

| mechanism | count | meaning |
|---|---|---|
| schema | 6 | the field does not exist, so the rule cannot be broken |
| validator | 9 | checked after generation, retried on failure |
| python | 1 | computed, not generated (the rationale prefix) |
| instruction | 6 | genuine judgement — **the only thing DSPy may optimise** |

The three most fragile rules are now structurally impossible to violate: the
rationale prefix is a string concat, the catalogue name is a dictionary lookup
(the model never emits one), and numeric claims are caught by digit detection
with no numeric field to fill.

```bash
python scripts/run_regression.py --replay      # must FAIL - proves the cases catch real bugs
python scripts/run_regression.py --runner C    # the stand-in: 5/6 pass
python scripts/run_regression.py --outputs answers.json   # real model output
```

`--replay` feeds the recorded bad output back in. All six fail, exit code 1.
That is the point: **a regression test that passes on the broken output is
worthless.**

Scope: equities only. The bond-specific rules (currency, issuer domicile,
cash-flow currency, duration) are deliberately excluded — a bond signature needs
different fields entirely.

---

## Where to go next

In priority order, judged by information gained per hour spent:

1. **Replace the synthetic panel with real returns.** Everything downstream gets
   meaningfully more credible, and the taxonomy/co-movement agreement becomes a
   real finding.
2. **Expand the hard-negative set.** It is 77 pairs. The discriminative power of
   the whole harness lives there.
3. **Calibrate the three thresholds against curated data** rather than leaving
   them at hand-chosen values.
4. **Only then** run `--lm` and let GEPA optimise against this metric. If you
   optimise before step 1, you will be optimising against a synthetic world.
