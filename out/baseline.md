# Baseline

source: deepseek/deepseek-flash

- peer score: **0.583**
- peer score on parsed cases: 0.603
- parse failures: 1/30
- peer picks: 26/90
- wrong picks: 2
- validator clean: 73.3%
- regression: 2/6 (4 blocking)

| asset | score | peers | adj | wrong | picks | validator |
|---|---|---|---|---|---|---|
| EQ_NVDA | 0.00 | 0 | 0 | 0 | - | expected exactly 3 picks, got 0; all three picks share one role - not a three-option comparison |
| EQ_MU | 0.00 | 1 | 1 | 1 | IDX_SOX, IDX_SPX, CASH_USD | ok |
| EQ_PLD | 0.00 | 0 | 2 | 1 | ETF_XLRE, ETF_SPY, CASH_USD | ok |
| EQ_TSM | 0.50 | 1 | 1 | 0 | IDX_SOX, IDX_ACWI, IDX_JP_SEMI | three funds tracking one industry - near-duplicate exposure |
| EQ_COP | 0.50 | 0 | 3 | 0 | ETF_XLE, EQ_SLB, IDX_SPX | ok |
| EQ_PEP | 0.50 | 0 | 3 | 0 | ETF_XLP, IDX_SPX, IDX_ACWI | limitation uses banned word(s) ['equivalent'] |
| EQ_AMZN | 0.50 | 0 | 3 | 0 | ETF_XLY, IDX_SPX, IDX_NDX | ok |
| EQ_NFLX | 0.50 | 0 | 3 | 0 | ETF_XLC, IDX_SPX, EQ_META | ok |
| EQ_NEE | 0.50 | 0 | 3 | 0 | ETF_XLU, IDX_SPX, ETF_VT | limitation uses banned word(s) ['equivalent'] |
| EQ_ASML | 0.67 | 1 | 2 | 0 | IDX_SX5E, IDX_SOX, ETF_VT | three funds tracking one industry - near-duplicate exposure |
| EQ_AVGO | 0.67 | 1 | 2 | 0 | IDX_SOX, IDX_SPX, IDX_NDX | three funds tracking one industry - near-duplicate exposure |
| EQ_MSFT | 0.67 | 1 | 2 | 0 | ETF_IGV, IDX_SPX, ETF_XLK | ok |
| EQ_JPM | 0.67 | 1 | 2 | 0 | ETF_XLF, EQ_BAC, ETF_SPY | ok |
| EQ_V | 0.67 | 1 | 2 | 0 | EQ_MA, ETF_XLF, IDX_SPX | ok |
| EQ_GS | 0.67 | 1 | 2 | 0 | EQ_MS, ETF_XLF, IDX_SPX | ok |
| EQ_MA | 0.67 | 1 | 2 | 0 | EQ_V, ETF_XLF, IDX_SPX | ok |
| EQ_UNH | 0.67 | 1 | 2 | 0 | ETF_XLV, EQ_ELV, IDX_SPX | ok |
| EQ_LLY | 0.67 | 1 | 2 | 0 | ETF_XLV, IDX_SPX, EQ_JNJ | ok |
| EQ_XOM | 0.67 | 1 | 2 | 0 | ETF_XLE, EQ_CVX, IDX_SPX | ok |
| EQ_KO | 0.67 | 1 | 2 | 0 | EQ_PEP, ETF_XLP, IDX_SPX | ok |
| EQ_CAT | 0.67 | 1 | 2 | 0 | ETF_XLI, EQ_DE, IDX_SPX | ok |
| EQ_DE | 0.67 | 1 | 2 | 0 | ETF_XLI, EQ_CAT, IDX_SPX | ok |
| EQ_BA | 0.67 | 1 | 2 | 0 | EQ_LMT, ETF_XLI, IDX_SPX | ok |
| EQ_HD | 0.67 | 1 | 2 | 0 | EQ_LOW, ETF_XLY, IDX_SPX | ok |
| EQ_GOOGL | 0.67 | 1 | 2 | 0 | ETF_XLC, IDX_SPX, EQ_META | ok |
| EQ_T | 0.67 | 1 | 2 | 0 | EQ_VZ, ETF_XLC, IDX_SPX | ok |
| EQ_LIN | 0.67 | 1 | 2 | 0 | EQ_APD, ETF_XLB, IDX_SPX | ok |
| EQ_AMD | 0.83 | 2 | 1 | 0 | ETF_SMH, IDX_SPX, EQ_ASML | limitation uses banned word(s) ['verified']; limitation uses banned word(s) ['equivalent'] |
| EQ_CRM | 0.83 | 2 | 1 | 0 | ETF_IGV, EQ_MSFT, IDX_SPX | ETF_IGV: rationale body is 147 words (limit 110); EQ_MSFT: rationale body is 131 words (limit 110) |
| EQ_PFE | 0.83 | 2 | 1 | 0 | EQ_JNJ, EQ_LLY, ETF_XLV | ok |
