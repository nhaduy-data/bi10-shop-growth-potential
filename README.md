# How big can this shop become? – BI Season 10, Final Round

**Champion of Business Intelligence Season 10 (ITB Club, 2026)** · Team *KDL Ú vjp pro 123*

The company sells consumer loans through a network of about 11,700 partner shops. Two shops can sign the same number of contracts per month and still have very different room to grow. The question in the final round: how far can each shop realistically grow, what is holding it back, and which shops should get the sales team's resources first.

Slides: [`slides/BI10_Final_Round_Slides.pdf`](slides/BI10_Final_Round_Slides.pdf)

## Approach

Every shop gets four numbers, each computed in its own step:

1. **Current Actual**: what the shop signs per month now (average of Jul–Sep 2026).
2. **Business-as-Usual (BAU)**: what it will sign from Oct 2026 to Mar 2027 if nothing changes.
3. **Attainable Potential**: what it would sign if it performed like the top quarter of similar shops (same size, goods category, application type and province).
4. **Addressable Market Ceiling**: the most the province's market allows, based on working-age population and a benchmark penetration rate.

The gap between Attainable Potential and BAU is the growth that needs action. Each shop's gap is split across the KPIs that management can act on:

```
direct contracts = sales agents × applications per agent × (1 − reject rate − cancel rate)
Current Actual   = direct contracts + cross-sell contracts
```

No machine learning: every number is a calculation, a peer comparison or a simple statistical test, so a manager can trace any figure back to the raw data. Instead of a complex model, the results are checked with backtests and sensitivity tests.

## Results

- Network total, contracts per month: Current Actual 39,450 · BAU 39,272 · Attainable Potential 55,595 · Market Ceiling 65,959.
- Without intervention the network stays flat. The opportunity gap is **16,324 contracts and 222.9 billion VND in loans per month (41.6% of BAU)**.
- The gap comes mostly from applications per sales agent (42.7%) and number of sales agents (32.1%). Reject and cancel rates add little.
- The market ceiling cuts 20.7% of the gain, concentrated in 8 provinces; Ho Chi Minh City, Hanoi and Dong Nai hold 72.8% of that cut.
- Shops are split into 4 groups: Invest now (184), Pilot (2,915, holding 72% of the gap), Keep as is (8,274), High risk (379). If the first two groups close half their gap, the network signs about 6,175 more contracts per month (+15.7% on BAU).
- The BAU forecast beats a 3-month average in backtests (WAPE 0.460 vs 0.474). Shops that went from 1 to about 2 sales agents signed 2.7–3.4 more contracts per month than shops that stayed at 1. Under different assumptions the total gap ranges from 11,892 to 20,626 contracts per month.

## Files

This is the folder the team submitted to the judges, plus the slides. The notebooks are written in Vietnamese and keep their outputs, so they can be read without running anything.

| Notebook | Step |
|---|---|
| `EDA/BI10_R03_EDA.ipynb` | Data exploration and data quality checks |
| `EDA/BI10_R03_clean.ipynb` | Cleaning, writes the shared `clean_data/` |
| `Bước 0 - Business Understanding/BI10_R03_Buoc0.ipynb` | Business overview: where growth comes from |
| `Bước 1 - Current Actual/BI10_R03_Buoc1.ipynb` | Current Actual, KPI breakdown, lead-to-contract cross-sell matching |
| `Bước 2 - BAU/BI10_R03_Buoc2.ipynb` | BAU forecast |
| `Bước 3/BI10_R03_Buoc3.ipynb` | Attainable Potential, with a second method as a check (section 3.10) |
| `Bước 4/Task4_Addressable_Market_Ceiling.ipynb` | Market ceiling by province, with external data |
| `Bước 5/BI10_R03_Buoc5.ipynb` | Opportunity gap and its causes |
| `Bước 6/BI10_R03_Buoc6.ipynb` | Shop prioritization and rollout plan |
| `Bước 7/BI10_R03_Buoc7.ipynb` | Backtests and sensitivity tests |

Shared code in `File Python/`: `r3_db.py` (opens the clean data in DuckDB), `load_clean.py`, `r3_tiem_nang.py` (Steps 1, 3, 4, 5 as functions so Steps 5–7 can rerun them under other assumptions), `r3_bau.py` (BAU functions from Step 2).

External data (`Bước 4/external_data.xlsx`): 2025 province statistics from the National Statistics Office, mapped from 63 old provinces to the 34 new ones. Sources and method are in `Bước 4/readme.docx` and `README_vi.md`.

`README_vi.md` is the Vietnamese write-up submitted with the analysis, covering each step's method and why it was chosen.

## Running it

The competition dataset is not included; it belongs to the organizer and is about 1.6 GB. Neither are the CSV outputs, which are recreated on the run.

```
pip install duckdb pandas numpy scipy matplotlib openpyxl jupyter
```

The code expects the working layout described in `README_vi.md`: the dataset in `Round3_BI10_dataset/`, step folders named `Bước 1` to `Bước 7`, and the files from `File Python/` at the root. Run the cleaning notebook first, then Steps 0 to 7.

## Team

A five-person team project; I was the team leader and did the EDA, data cleaning, and Steps 0, 1 and 3. Steps 5–7 were built together. I know my own parts in full detail, and my teammates' parts less deeply.

Earlier round of the same competition: [bi10-consumer-financial-health](https://github.com/nhaduy-data/bi10-consumer-financial-health)
