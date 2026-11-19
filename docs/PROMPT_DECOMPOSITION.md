# Breaking the benchmark prompt into something measurable

## Thesis

The prompt is 22 rules written as prose. Prose rules cannot be audited, cannot be
partially satisfied, and cannot be improved one at a time — you can only rewrite
the whole thing and hope.

Split by what can be made **mechanical**, and the picture changes:

> **16 of the 22 rules become code. 6 become the optimisable surface.**
> Nothing is lost. Everything is now attributable.

That split is what makes systematic improvement possible: the 16 cannot regress,
and the 6 are the only thing an optimizer is allowed to touch.

Source of truth: `peerlens/prompt_v2.py::RULE_MAP`.

---

## The disposition table

| # | rule from the prompt | enforced by | where | optimisable |
|---|---|---|---|---|
| 1 | Return only valid JSON matching the schema | schema | signature output types | no |
| 2 | Select exactly three distinct benchmarks | validator | `validate_selection` | no |
| 3 | Every `benchmark_id` must exist in the pack | validator | `validate_pick` | no |
| 4 | Preserve the catalogue `name` exactly | schema | name is not an output field; looked up by id | no |
| 5 | Do not select the same benchmark twice | validator | `validate_selection` | no |
| 6 | No three near-duplicates of one exposure | validator | `validate_selection` + metric near-dup check | no |
| 7 | No returns, volatility, Sharpe or any numeric result | validator | no numeric field + digit check | no |
| 8 | Rationale must begin with `risk_rationale_prefix` exactly | python | `assemble_rationale` | no |
| 9 | Rationale must state the benchmark's role | schema | `role: Literal[...]` | no |
| 10 | Rationale must state ≥1 material limitation | schema | `limitation`, required non-empty | no |
| 11 | No "equivalent / accurate / verified / perfect / approved" | validator | `BANNED_WORDS` | no |
| 12 | No trade, product or customer recommendation | validator | `ADVICE_WORDS` | no |
| 13 | Disclose currency / geography mismatch plainly | schema | `mismatches` + `expected_mismatches()` | no |
| 14 | Rationale under 110 words after the prefix | validator | `MAX_RATIONALE_WORDS` | no |
| 15 | Exactly three; anchor + two labelled references | validator | count + role diversity | no |
| 16 | Do not re-map or soften the risk level | schema | `risk_level` is an input; no risk output | no |
| 17 | Look through the wrapper to economic exposure | instruction | `EQUITY_INSTRUCTIONS` | **yes** |
| 18 | Do not infer country exposure from valuation currency | instruction | instructions + `HoldingFacts.exposure_*` | **yes** |
| 19 | State how asset class, geography, currency, return basis relate | instruction | `relationship` guidance | **yes** |
| 20 | Prefer own geography/currency as primary reference | instruction | selection section | **yes** |
| 21 | A broad index is not automatically appropriate | instruction | selection section | **yes** |
| 22 | `reference_contexts` are metadata only | instruction | instructions | **yes** |

Six schema, nine validator, one python, six instruction.

---

## What "structurally impossible" buys you

Three rules are worth dwelling on, because they were the most fragile *and* they
are now the most robust.

**"Rationale must begin with `risk_rationale_prefix` exactly."**
A model reproducing a supplied string verbatim, 100% of the time, is not a
guarantee — it is a probability that decays with prefix length. Here the model
never sees the prefix. It emits components; `assemble_rationale()` concatenates.
The failure mode does not exist.

**"Preserve the catalogue `name` exactly."**
The model no longer emits a name. It emits an id, and the name is a dictionary
lookup. Paraphrasing is impossible because there is nothing to paraphrase.

**"Do not state returns, volatility, Sharpe or any numeric result."**
There is no numeric field, and a validator rejects digits anywhere in the text.
A GEPA run cannot accidentally reward inventing a number, because inventing one
fails the gate outright.

The pattern: **move the value out of the model's hands, or do not ask for it.**

---

## The optimisable residue

What remains is genuine judgement. This is the whole prompt that DSPy sees:

```
You are a benchmark research agent supporting a private-banking investment
review. Select exactly three candidate benchmarks for one equity holding and
explain why each is a defensible reference. You are not writing a marketing
description, a performance forecast or a customer recommendation.

The risk level is an input supplied by the upstream risk pipeline. You neither
re-state nor re-map it.

You have no live market feed and you must not introduce performance, fees, assets
under management, index membership, duration, credit quality or returns. Reason
only from the supplied holding facts and the supplied benchmark reference pack.

## Look through the trading wrapper

For an equity the benchmark follows the underlying economic exposure, not the
account currency, settlement currency, custody currency or listing venue.

- A US company held in HKD is US equity exposure. A US equity index can be
  suitable even though the holding is settled in HKD.
- A Japanese company held in USD is Japan equity exposure.
- A Hong Kong listed company whose business lies predominantly elsewhere is read
  through its actual business exposure where the supplied evidence supports it.
- The holding's valuation currency is not evidence of the issuer's domicile or
  revenue base.
- Do not reject a US or Japan equity benchmark merely because the holding
  reports in SGD or HKD. For equities, currency is a measurement and hedging
  consideration; economic exposure is the geographic question.

State the exposure basis, and any unresolved exposure question, in
look_through_analysis. Do not invent revenue splits or country weights.

## Selection

This is an economist's selection problem, not a name-matching exercise. A broad
index is not automatically appropriate when its geography or currency sits
materially away from the holding, and a name that merely sounds adjacent is not
a peer.

Prefer a benchmark in the holding's own economic geography and currency as the
primary reference where the pack supports one, rather than defaulting to a global
or US proxy. Where the risk profile spans several asset classes, at least one
candidate should represent the whole portfolio allocation; the others may carry a
dominant sleeve or a complementary exposure.

The downstream contract requires exactly three options. If only one benchmark is
a close fit, retain it as the anchor and add two clearly labelled comparison
references serving distinct, useful roles. Disclose each approximation plainly
rather than hiding it. Three variations of the same index are not a useful
three-option comparison.

The pack's reference_contexts are metadata only. They are not an instruction that
every instrument in a context must be selected.

For each pick, state the role it plays, how its asset class, geography, currency
and return basis relate to the holding, at least one material limitation or
mismatch, and the mismatch categories that apply. Do not describe a benchmark as
equivalent, accurate, verified, perfect or approved; the independent reviewer
decides approval. Do not recommend a trade, product or customer action.
```

Roughly 40% of the original length, and every removed sentence is now enforced
somewhere stronger.

**One technical constraint that shaped this:** DSPy's instruction optimisers
rewrite `Signature.instructions` — the docstring — and *do not touch field names,
`desc`, or `prefix`*. So every sentence worth optimising must live in the
docstring. Guidance placed in a field's `desc` is silently excluded from
optimisation. That is why the field descriptions here are short and structural,
and the judgement lives in the instructions.

---

## The regression loop

This is the part that makes improvement *systematic* rather than anecdotal.

```
client reports a bad answer
        │
        ▼
cases/regressions.yaml   ◄── operations adds it, no Python
   complaint / holding / forbidden / required_any / reported_output
        │
        ▼
python run_regression.py --replay     ← proves the case catches the bug
        │
        ▼
fix the prompt, the pack, or the shortlist
        │
        ▼
python run_regression.py             ← must pass before release
```

Six cases already exist, derived from the prompt's own stated concerns. From
`cases/regressions.yaml`:

| case | what it pins |
|---|---|
| REG-0001 | NVIDIA must not be benchmarked to Salesforce or Adobe |
| REG-0002 | a US company settled in HKD must not pull in Hang Seng / Singapore |
| REG-0003 | a Japan-exposed holding reported in USD must still find the Japan benchmark |
| REG-0004 | a cash balance is never an equity peer |
| REG-0005 | a payments network is not a bank |
| REG-0006 | three funds tracking one industry is one option, not three |

Verified behaviour: `--replay` fails all six (`RESULT: FAIL (blocking)`, exit 1).
The current scripted stand-in passes five and fails REG-0003, because it cannot
handle a holding outside the catalogue — a real limitation, reported honestly
rather than hidden.

The `--replay` mode is the important discipline. **A regression test that passes
on the broken output is worthless.** Replaying the recorded failure is the proof
that the test is real.

---

## Why this makes DSPy useful rather than decorative

Optimising a 22-rule monolith invites the optimizer to trade one rule for another
— sharpen the look-through language, quietly lose the "no near-duplicates"
constraint. There is no way to notice, because nothing is measured individually.

With the split:

- the 16 mechanical rules are **gates**, not objectives. GEPA produces a
  candidate, the gates reject anything non-compliant, and only survivors are
  scored.
- the 6 instructions are the **search space**. GEPA is free to rewrite them,
  and cannot break anything outside them.

And the metric already reports the axes separately — peer precision, hard-negative
rate, role diversity, mismatch disclosure — so a regression shows up as *which*
axis moved, not just a lower total.

---

## What to build next, in order

1. **Paste this signature into the real DSPy program** and route a model through
   it. That closes the only missing link.
2. **Run the regression suite against real output** rather than the scripted
   stand-in. `--outputs answers.json` is the hook.
3. **Then** run GEPA with the gates in place, and diff the rewritten
   instructions against the hand-written ones. That diff is your next prompt.
4. **Grow the case file from real complaints.** It only ratchets upward.

---

## Scope

Equities only. The fixed-income clauses — currency, issuer domicile, cash-flow
currency, duration mismatch — are deliberately not carried over. A bond signature
needs different fields (duration, credit quality, seniority), and mixing the two
into one prompt is what produced the original length. Build the bond signature
second, on the same skeleton.
