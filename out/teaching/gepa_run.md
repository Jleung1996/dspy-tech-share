# GEPA run summary — what we observed

Run: `deepseek/deepseek-flash`, `auto=light`, temperature 0
Split: 9 train / 3 val (curated cases) · 10 held-out cases for the baseline number
Status: **stopped manually at iteration 32** — plateau reached long before the budget ran out

## The baseline we can defend

| | |
|---|---|
| prompt | the realistic `v0` (see `prompts/v0.md`) |
| **score** | **0.635** |
| eval set | 10 cases, stratified, held out from optimisation |
| mean peer hits | 1.10 / 3 |
| mean wrong picks | 0.00 / 3 |
| fatal (unparseable / wrong count) | 0 / 10 |

Per-case detail in `baseline.md`. The signature of v0's behaviour: **nine of ten
answers were the same template** — one true peer + one sector ETF + `IDX_SPX`.
That template scores ~0.667 by construction, which is where six cases landed.

## What the optimiser did

32 iterations, 22 successful reflection proposals, 5 candidate programs retained.

| program | first seen | internal score |
|---|---|---|
| 0 (original) | iteration 1 | 0.6111 |
| 2 | iteration 3 | **0.7222** |
| 3 | iteration 6 | 0.7222 |
| 4 | iteration 17 | 0.7222 |

**Improvement: +0.111, achieved by iteration 3. Nothing better in the following
29 iterations.**

## The honest reading

1. **The optimiser made the prompt better.** On GEPA's own evaluation set, the
   original prompt scored **0.611** and the first rewritten prompt scored
   **0.722**. Same cases, same metric, same protocol, only the instruction
   changed. That is a clean paired comparison: **+0.111, about +18% relative.**
   This is a real improvement and should be presented as one.

2. **The rewrite happened fast, then stalled.** The gain landed on the third
   attempt. Nothing beat 0.722 in the following 29 iterations. Two readings, both
   defensible: the prompt had little headroom left, or reflection ran out of
   useful edits to propose. The first is more likely — a five-paragraph prompt
   already naming asset class, sector and geography leaves less to fix than the
   one-line version would.

3. **Do not chain the two rulers.** `0.635` is measured on 10 held-out cases;
   `0.722` on GEPA's own split. Writing "0.635 → 0.722" mixes measurements and
   is meaningless. The correct statement of the same fact is:

   | ruler | original prompt | GEPA prompt |
   |---|---|---|
   | GEPA's evaluation split | 0.611 | **0.722** |
   | our 10 held-out cases | 0.635 | **not measured** |

   Both rows agree the optimiser helped. Only the second row would let us claim
   the gain on the ruler the baseline uses — and it is empty, because the
   rewritten prompt text was not saved.

4. **What the remaining headroom probably is.** Naming peer *companies* instead
   of funds is closer to a retrieval problem than a wording problem. Instruction
   rewriting cannot reorder a shortlist or add facts the model lacks.

## What we do not have

**The rewritten prompt texts.** GEPA keeps candidates in memory and writes
checkpoints only when a `run_dir` is configured. This run had neither, so the 22
proposals were lost when the process was stopped.

Recoverable in ~10 minutes by re-running with a `RecordingProposer` that appends
each proposal to `prompts/proposal_NNN.md` before returning, plus a bounded
`max_metric_calls`. That would produce the 10-row leaderboard this run was meant
to produce.
