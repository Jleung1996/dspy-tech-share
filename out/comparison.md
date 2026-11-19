# Peer-labelling comparison

Catalogue: 89 instruments. Cases: 30.

| system under test | score | peer credit | peer hits | hard neg | format ok | dup exp | mean roles |
|---|---|---|---|---|---|---|---|
| A: naive (description only) | **0.307** | 0.578 | 0.467 | 0.289 | 1.000 | 0.100 | 1.57 |
| B: sector-only | **0.176** | 0.444 | 0.356 | 0.344 | 1.000 | 0.200 | 1.23 |
| C: industry-aware + enriched pack | **0.639** | 0.661 | 0.378 | 0.022 | 1.000 | 0.000 | 2.47 |
| C': industry-aware, no co-movement | **0.606** | 0.661 | 0.378 | 0.044 | 1.000 | 0.000 | 2.47 |

## Per case

| asset | A | B | C | C' |
|---|---|---|---|---|
| NVDA | 1.00 | 0.17 | 0.83 | 0.83 |
| AMD | 1.00 | 0.17 | 0.67 | 0.17 |
| TSM | 1.00 | 0.17 | 0.83 | 0.83 |
| ASML | 0.67 | 0.17 | 0.00 | 0.00 |
| AVGO | 0.00 | 0.17 | 0.17 | 0.17 |
| MU | 1.00 | 0.17 | 0.67 | 0.17 |
| CRM | 1.00 | 0.00 | 1.00 | 1.00 |
| MSFT | 0.17 | 0.00 | 1.00 | 1.00 |
| JPM | 0.67 | 0.00 | 0.67 | 0.67 |
| V | 0.00 | 0.00 | 0.67 | 0.67 |
| GS | 0.53 | 0.00 | 0.67 | 0.67 |
| MA | 0.00 | 0.00 | 0.67 | 0.67 |
| UNH | 0.00 | 0.00 | 0.67 | 0.67 |
| LLY | 0.17 | 0.17 | 0.83 | 0.83 |
| PFE | 0.17 | 0.17 | 0.83 | 0.83 |
| XOM | 0.67 | 0.50 | 0.67 | 0.67 |
| COP | 0.67 | 0.67 | 0.50 | 0.50 |
| KO | 0.00 | 0.67 | 0.67 | 0.67 |
| PEP | 0.00 | 0.67 | 0.67 | 0.67 |
| CAT | 0.00 | 0.33 | 0.50 | 0.50 |
| DE | 0.00 | 0.33 | 0.50 | 0.50 |
| BA | 0.00 | 0.27 | 0.67 | 0.67 |
| HD | 0.50 | 0.50 | 0.67 | 0.67 |
| AMZN | 0.00 | 0.00 | 0.50 | 0.50 |
| GOOGL | 0.00 | 0.00 | 0.67 | 0.67 |
| NFLX | 0.00 | 0.00 | 0.50 | 0.50 |
| T | 0.00 | 0.00 | 0.67 | 0.67 |
| NEE | 0.00 | 0.00 | 0.67 | 0.67 |
| PLD | 0.00 | 0.00 | 0.50 | 0.50 |
| LIN | 0.00 | 0.00 | 0.67 | 0.67 |

## Picks

### A: naive (description only)

| asset | picks | roles | score |
|---|---|---|---|
| NVDA | Advanced Micro Devices, Inc., Qualcomm Incorporated, Taiwan Semiconductor Manufacturing Company | dominant_sle, dominant_sle, dominant_sle | 1.00 |
| AMD | NVIDIA Corporation, Qualcomm Incorporated, Taiwan Semiconductor Manufacturing Company | dominant_sle, dominant_sle, dominant_sle | 1.00 |
| TSM | PHLX Semiconductor Index, Intel Corporation, Invesco PHLX Semiconductor ETF | dominant_sle, dominant_sle, dominant_sle | 1.00 |
| ASML | TOPIX Semiconductor Index, PHLX Semiconductor Index, Micron Technology, Inc. | dominant_sle, dominant_sle, dominant_sle | 0.67 |
| AVGO | iShares Expanded Tech-Software ETF, Microsoft Corporation, Qualcomm Incorporated | diversifier, dominant_sle, dominant_sle | 0.00 |
| MU | ASML Holding N.V., Intel Corporation, Broadcom Inc. | dominant_sle, dominant_sle, dominant_sle | 1.00 |
| CRM | iShares Expanded Tech-Software ETF, Microsoft Corporation, Adobe Inc. | diversifier, dominant_sle, dominant_sle | 1.00 |
| MSFT | Oracle Corporation, Salesforce, Inc., Amazon.com, Inc. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| JPM | Bank of America Corporation, Morgan Stanley, The Goldman Sachs Group, Inc. | dominant_sle, dominant_sle, dominant_sle | 0.67 |
| V | Mastercard Incorporated, JPMorgan Chase & Co., Singapore Dollar Cash | dominant_sle, dominant_sle, liquidity_re | 0.00 |
| GS | Morgan Stanley, JPMorgan Chase & Co., Bank of America Corporation | dominant_sle, dominant_sle, dominant_sle | 0.53 |
| MA | Visa Inc., JPMorgan Chase & Co., Singapore Dollar Cash | dominant_sle, dominant_sle, liquidity_re | 0.00 |
| UNH | Elevance Health, Inc., Health Care Select Sector SPDR Fund, Johnson & Johnson | dominant_sle, diversifier, dominant_sle | 0.00 |
| LLY | Pfizer Inc., Johnson & Johnson, PepsiCo, Inc. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| PFE | Eli Lilly and Company, Johnson & Johnson, PepsiCo, Inc. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| XOM | Chevron Corporation, Energy Select Sector SPDR Fund, ConocoPhillips | dominant_sle, diversifier, dominant_sle | 0.67 |
| COP | Exxon Mobil Corporation, Chevron Corporation, Energy Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.67 |
| KO | PepsiCo, Inc., The Procter & Gamble Company, Eli Lilly and Company | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| PEP | The Coca-Cola Company, The Procter & Gamble Company, Eli Lilly and Company | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| CAT | Deere & Company, Industrial Select Sector SPDR Fund, Materials Select Sector SPDR Fund | dominant_sle, diversifier, diversifier | 0.00 |
| DE | Caterpillar Inc., Industrial Select Sector SPDR Fund, The Procter & Gamble Company | dominant_sle, diversifier, dominant_sle | 0.00 |
| BA | Lockheed Martin Corporation, Industrial Select Sector SPDR Fund, Elevance Health, Inc. | dominant_sle, diversifier, dominant_sle | 0.00 |
| HD | Lowe's Companies, Inc., Consumer Discretionary Select Sector SPDR Fund, Amazon.com, Inc. | dominant_sle, diversifier, dominant_sle | 0.50 |
| AMZN | Microsoft Corporation, Alphabet Inc., Consumer Discretionary Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.00 |
| GOOGL | Amazon.com, Inc., Microsoft Corporation, Meta Platforms, Inc. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| NFLX | Communication Services Select Sector SPDR Fund, Adobe Inc., AT&T Inc. | diversifier, dominant_sle, dominant_sle | 0.00 |
| T | Verizon Communications Inc., Communication Services Select Sector SPDR Fund, Qualcomm Incorporated | dominant_sle, diversifier, dominant_sle | 0.00 |
| NEE | Utilities Select Sector SPDR Fund, Duke Energy Corporation, ConocoPhillips | diversifier, dominant_sle, dominant_sle | 0.00 |
| PLD | Real Estate Select Sector SPDR Fund, Linde plc, Air Products and Chemicals, Inc. | diversifier, dominant_sle, dominant_sle | 0.00 |
| LIN | Air Products and Chemicals, Inc., Materials Select Sector SPDR Fund, Industrial Select Sector SPDR Fund | dominant_sle, diversifier, diversifier | 0.00 |

### B: sector-only

| asset | picks | roles | score |
|---|---|---|---|
| NVDA | Adobe Inc., Advanced Micro Devices, Inc., ASML Holding N.V. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| AMD | Adobe Inc., ASML Holding N.V., Broadcom Inc. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| TSM | Adobe Inc., Advanced Micro Devices, Inc., ASML Holding N.V. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| ASML | Adobe Inc., Advanced Micro Devices, Inc., Broadcom Inc. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| AVGO | Adobe Inc., Advanced Micro Devices, Inc., ASML Holding N.V. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| MU | Adobe Inc., Advanced Micro Devices, Inc., ASML Holding N.V. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| CRM | Adobe Inc., Advanced Micro Devices, Inc., ASML Holding N.V. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| MSFT | Adobe Inc., Advanced Micro Devices, Inc., ASML Holding N.V. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| JPM | Bank of America Corporation, The Goldman Sachs Group, Inc., Mastercard Incorporated | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| V | Bank of America Corporation, The Goldman Sachs Group, Inc., JPMorgan Chase & Co. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| GS | Bank of America Corporation, JPMorgan Chase & Co., Mastercard Incorporated | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| MA | Bank of America Corporation, The Goldman Sachs Group, Inc., JPMorgan Chase & Co. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| UNH | Elevance Health, Inc., Johnson & Johnson, Eli Lilly and Company | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| LLY | Elevance Health, Inc., Johnson & Johnson, Pfizer Inc. | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| PFE | Elevance Health, Inc., Johnson & Johnson, Eli Lilly and Company | dominant_sle, dominant_sle, dominant_sle | 0.17 |
| XOM | ConocoPhillips, Chevron Corporation, SLB | dominant_sle, dominant_sle, dominant_sle | 0.50 |
| COP | Chevron Corporation, SLB, Exxon Mobil Corporation | dominant_sle, dominant_sle, dominant_sle | 0.67 |
| KO | PepsiCo, Inc., The Procter & Gamble Company, Consumer Staples Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.67 |
| PEP | The Coca-Cola Company, The Procter & Gamble Company, Consumer Staples Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.67 |
| CAT | The Boeing Company, Deere & Company, Lockheed Martin Corporation | dominant_sle, dominant_sle, dominant_sle | 0.33 |
| DE | The Boeing Company, Caterpillar Inc., Lockheed Martin Corporation | dominant_sle, dominant_sle, dominant_sle | 0.33 |
| BA | Caterpillar Inc., Deere & Company, Lockheed Martin Corporation | dominant_sle, dominant_sle, dominant_sle | 0.27 |
| HD | Amazon.com, Inc., Lowe's Companies, Inc., Consumer Discretionary Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.50 |
| AMZN | The Home Depot, Inc., Lowe's Companies, Inc., Consumer Discretionary Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.00 |
| GOOGL | Meta Platforms, Inc., Netflix, Inc., AT&T Inc. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| NFLX | Alphabet Inc., Meta Platforms, Inc., AT&T Inc. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| T | Alphabet Inc., Meta Platforms, Inc., Netflix, Inc. | dominant_sle, dominant_sle, dominant_sle | 0.00 |
| NEE | Duke Energy Corporation, Utilities Select Sector SPDR Fund, Adobe Inc. | dominant_sle, diversifier, dominant_sle | 0.00 |
| PLD | Real Estate Select Sector SPDR Fund, Adobe Inc., Advanced Micro Devices, Inc. | diversifier, dominant_sle, dominant_sle | 0.00 |
| LIN | Air Products and Chemicals, Inc., Freeport-McMoRan Inc., Materials Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.00 |

### C: industry-aware + enriched pack

| asset | picks | roles | score |
|---|---|---|---|
| NVDA | Advanced Micro Devices, Inc., Qualcomm Incorporated, Technology Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| AMD | NVIDIA Corporation, Qualcomm Incorporated, Hang Seng TECH Index | dominant_sle, dominant_sle, diversifier | 0.67 |
| TSM | PHLX Semiconductor Index, Intel Corporation, Technology Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| ASML | Technology Select Sector SPDR Fund, iShares Expanded Tech-Software ETF, Hang Seng TECH Index | diversifier, diversifier, diversifier | 0.00 |
| AVGO | Qualcomm Incorporated, Micron Technology, Inc., iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 0.17 |
| MU | Intel Corporation, Broadcom Inc., Hang Seng TECH Index | dominant_sle, dominant_sle, diversifier | 0.67 |
| CRM | Microsoft Corporation, Adobe Inc., iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 1.00 |
| MSFT | Oracle Corporation, Salesforce, Inc., iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 1.00 |
| JPM | Bank of America Corporation, Financial Select Sector SPDR Fund, Vanguard Total World Stock ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| V | Mastercard Incorporated, Financial Select Sector SPDR Fund, TOPIX Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| GS | Morgan Stanley, Financial Select Sector SPDR Fund, Invesco QQQ Trust | dominant_sle, diversifier, whole_portfo | 0.67 |
| MA | Visa Inc., Financial Select Sector SPDR Fund, Nasdaq-100 Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| UNH | Elevance Health, Inc., Health Care Select Sector SPDR Fund, MSCI World Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| LLY | Pfizer Inc., Johnson & Johnson, Health Care Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| PFE | Eli Lilly and Company, Johnson & Johnson, Health Care Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| XOM | Chevron Corporation, Energy Select Sector SPDR Fund, Russell 2000 Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| COP | SLB, Energy Select Sector SPDR Fund, MSCI ACWI Index | dominant_sle, diversifier, whole_portfo | 0.50 |
| KO | PepsiCo, Inc., Consumer Staples Select Sector SPDR Fund, S&P 500 Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| PEP | The Coca-Cola Company, Consumer Staples Select Sector SPDR Fund, S&P 500 Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| CAT | Industrial Select Sector SPDR Fund, TOPIX Index, iShares MSCI Japan ETF | diversifier, whole_portfo, whole_portfo | 0.50 |
| DE | Industrial Select Sector SPDR Fund, Straits Times Index, S&P 500 Index | diversifier, whole_portfo, whole_portfo | 0.50 |
| BA | Lockheed Martin Corporation, Industrial Select Sector SPDR Fund, STOXX Europe 600 Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| HD | Lowe's Companies, Inc., Consumer Discretionary Select Sector SPDR Fund, MSCI ACWI Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| AMZN | Consumer Discretionary Select Sector SPDR Fund, Hang Seng Index, STOXX Europe 600 Index | diversifier, whole_portfo, whole_portfo | 0.50 |
| GOOGL | Meta Platforms, Inc., Communication Services Select Sector SPDR Fund, Russell 2000 Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| NFLX | Communication Services Select Sector SPDR Fund, iShares MSCI Japan ETF, Hang Seng Index | diversifier, whole_portfo, whole_portfo | 0.50 |
| T | Verizon Communications Inc., Communication Services Select Sector SPDR Fund, Invesco QQQ Trust | dominant_sle, diversifier, whole_portfo | 0.67 |
| NEE | Duke Energy Corporation, Utilities Select Sector SPDR Fund, MSCI World Index | dominant_sle, diversifier, whole_portfo | 0.67 |
| PLD | Real Estate Select Sector SPDR Fund, Nasdaq-100 Index, Hang Seng Index | diversifier, whole_portfo, whole_portfo | 0.50 |
| LIN | Air Products and Chemicals, Inc., Materials Select Sector SPDR Fund, Nasdaq-100 Index | dominant_sle, diversifier, whole_portfo | 0.67 |

### C': industry-aware, no co-movement

| asset | picks | roles | score |
|---|---|---|---|
| NVDA | Advanced Micro Devices, Inc., Qualcomm Incorporated, Technology Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| AMD | NVIDIA Corporation, Qualcomm Incorporated, iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 0.17 |
| TSM | PHLX Semiconductor Index, Intel Corporation, Technology Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| ASML | Technology Select Sector SPDR Fund, iShares Expanded Tech-Software ETF, Hang Seng TECH Index | diversifier, diversifier, diversifier | 0.00 |
| AVGO | Qualcomm Incorporated, Micron Technology, Inc., iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 0.17 |
| MU | Intel Corporation, Broadcom Inc., iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 0.17 |
| CRM | Microsoft Corporation, Adobe Inc., iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 1.00 |
| MSFT | Oracle Corporation, Salesforce, Inc., iShares Expanded Tech-Software ETF | dominant_sle, dominant_sle, diversifier | 1.00 |
| JPM | Bank of America Corporation, Financial Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| V | Mastercard Incorporated, Financial Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| GS | Morgan Stanley, Financial Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| MA | Visa Inc., Financial Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| UNH | Elevance Health, Inc., Health Care Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| LLY | Pfizer Inc., Johnson & Johnson, Health Care Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| PFE | Eli Lilly and Company, Johnson & Johnson, Health Care Select Sector SPDR Fund | dominant_sle, dominant_sle, diversifier | 0.83 |
| XOM | Chevron Corporation, Energy Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| COP | SLB, Energy Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.50 |
| KO | PepsiCo, Inc., Consumer Staples Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| PEP | The Coca-Cola Company, Consumer Staples Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| CAT | Industrial Select Sector SPDR Fund, iShares MSCI Hong Kong ETF, iShares MSCI Japan ETF | diversifier, whole_portfo, whole_portfo | 0.50 |
| DE | Industrial Select Sector SPDR Fund, iShares MSCI Hong Kong ETF, iShares MSCI Japan ETF | diversifier, whole_portfo, whole_portfo | 0.50 |
| BA | Lockheed Martin Corporation, Industrial Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| HD | Lowe's Companies, Inc., Consumer Discretionary Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| AMZN | Consumer Discretionary Select Sector SPDR Fund, iShares MSCI Hong Kong ETF, iShares MSCI Japan ETF | diversifier, whole_portfo, whole_portfo | 0.50 |
| GOOGL | Meta Platforms, Inc., Communication Services Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| NFLX | Communication Services Select Sector SPDR Fund, iShares MSCI Hong Kong ETF, iShares MSCI Japan ETF | diversifier, whole_portfo, whole_portfo | 0.50 |
| T | Verizon Communications Inc., Communication Services Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| NEE | Duke Energy Corporation, Utilities Select Sector SPDR Fund, iShares MSCI Hong Kong ETF | dominant_sle, diversifier, whole_portfo | 0.67 |
| PLD | Real Estate Select Sector SPDR Fund, iShares MSCI Hong Kong ETF, iShares MSCI Japan ETF | diversifier, whole_portfo, whole_portfo | 0.50 |
| LIN | Air Products and Chemicals, Inc., Materials Select Sector SPDR Fund, Nasdaq-100 Index | dominant_sle, diversifier, whole_portfo | 0.67 |
