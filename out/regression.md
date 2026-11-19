# Regression suite

source: replayed reported_output (should FAIL)

| case | severity | result | picks | notes |
|---|---|---|---|---|
| REG-0001 | high | **FAIL** | EQ_CRM, EQ_ADBE, IDX_NDX | returned forbidden benchmark(s): ['EQ_ADBE', 'EQ_CRM']; only 0 acceptable peer(s), need 2 from ['EQ_AMD', 'EQ_ASML', 'EQ_AVGO', 'EQ_INTC', 'EQ_MU', 'EQ_QCOM', 'EQ_TSM', 'ETF_SMH', 'ETF_SOXX', 'IDX_SOX'] [validator: all three picks share one role - not a three-option comparison; relationship is empty] |
| REG-0002 | high | **FAIL** | IDX_HSI, ETF_EWH, CASH_SGD | returned forbidden benchmark(s): ['CASH_SGD', 'ETF_EWH', 'IDX_HSI']; only 0 acceptable peer(s), need 2 from ['EQ_AMD', 'EQ_ASML', 'EQ_AVGO', 'EQ_INTC', 'EQ_MU', 'EQ_QCOM', 'EQ_TSM', 'ETF_SMH', 'ETF_SOXX', 'IDX_SOX'] [validator: all three picks share one role - not a three-option comparison; relationship is empty] |
| REG-0003 | high | **FAIL** | IDX_SPX, ETF_SPY, ETF_QQQ | only 0 acceptable peer(s), need 1 from ['EQ_ASML', 'ETF_SMH', 'IDX_JP_SEMI', 'IDX_SOX'] [validator: all three picks share one role - not a three-option comparison; relationship is empty] |
| REG-0004 | medium | fail | CASH_SGD, ETF_TLT, IDX_SPX | returned forbidden benchmark(s): ['CASH_SGD', 'ETF_TLT']; only 0 acceptable peer(s), need 1 from ['EQ_PEP', 'EQ_PG', 'ETF_XLP'] [validator: all three picks share one role - not a three-option comparison; relationship is empty] |
| REG-0005 | medium | fail | EQ_JPM, EQ_BAC, ETF_XLF | returned forbidden benchmark(s): ['EQ_BAC', 'EQ_JPM'] [validator: all three picks share one role - not a three-option comparison; relationship is empty] |
| REG-0006 | high | **FAIL** | IDX_SOX, ETF_SMH, ETF_SOXX | only 0 acceptable peer(s), need 1 from ['EQ_AMD', 'EQ_AVGO', 'EQ_MU', 'EQ_QCOM', 'EQ_TSM'] [validator: all three picks share one role - not a three-option comparison; three funds tracking one industry - near-duplicate exposure] |

**FAIL** | 0/6
