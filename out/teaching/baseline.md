# Baseline (v0)

```
You are a benchmark research analyst supporting a private-banking investment
review.

Select three benchmarks for the security provided that would serve as useful
reference points for comparing its performance. Choose only from the supplied
reference pack; do not invent an index.

When choosing, consider the security's asset class, sector and geography, and
whether a broad market index or a more targeted index makes the better
comparison.

For each benchmark give its id and a short rationale explaining why it is a
reasonable comparison.
```

**Score: 0.635** over 10 held-out cases, temperature 0.

| asset | score | peers | adj | wrong | picks | issues |
|---|---|---|---|---|---|---|
| EQ_NVDA | 0.55 | 1 | 2 | 0 | IDX_SOX, ETF_XLK, IDX_SPX | three funds tracking one industry - near-duplicate exposure |
| EQ_ASML | 0.43 | 1 | 2 | 0 | IDX_SOX, IDX_SX5E, IDX_MSCI_WORLD | three funds tracking one industry - near-duplicate exposure; relationship contains a numeric claim |
| EQ_CRM | 0.83 | 2 | 1 | 0 | ETF_IGV, EQ_ORCL, IDX_SPX | ok |
| EQ_V | 0.67 | 1 | 2 | 0 | EQ_MA, ETF_XLF, IDX_SPX | ok |
| EQ_UNH | 0.67 | 1 | 2 | 0 | EQ_ELV, ETF_XLV, IDX_SPX | ok |
| EQ_XOM | 0.67 | 1 | 2 | 0 | EQ_CVX, ETF_XLE, IDX_SPX | ok |
| EQ_PEP | 0.67 | 1 | 2 | 0 | ETF_XLP, EQ_KO, IDX_SPX | ok |
| EQ_BA | 0.67 | 1 | 2 | 0 | EQ_LMT, ETF_XLI, IDX_SPX | ok |
| EQ_GOOGL | 0.67 | 1 | 2 | 0 | ETF_XLC, IDX_SPX, EQ_META | ok |
| EQ_NEE | 0.55 | 1 | 2 | 0 | ETF_XLU, EQ_DUK, IDX_SPX | limitation contains a numeric claim |
