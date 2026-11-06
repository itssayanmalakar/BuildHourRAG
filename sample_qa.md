# Sample Q&A

Verified against the built index on 2026-11-05. Every factual answer contains
one official source link, at most three sentences, and a "last updated" date.
Refusals and PII rejections are fixed copy and never call the model.

Captured with Groq (`qwen/qwen3.8-27b`) enabled. With the key absent or the
API unreachable, the same pipeline serves the grounded extractive fallback:
shorter wording, but the citation, sentence limit and date contract stay
identical.

---

## Factual answers

### Expense ratio

**Q:** What is the expense ratio of HDFC Flexi Cap Fund?

> The total expense ratio of HDFC Flexi Cap Fund is 0.75%.
> Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct
> Last updated from sources: 2026-11-05

### Exit load

**Q:** What is the exit load for HDFC Flexi Cap Fund?

> An exit load of 1.00% is payable if units are redeemed or switched-out within 1 year from the date of allotment. No exit load is payable if units are redeemed or switched-out after 1 year from the date of allotment.
> Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct
> Last updated from sources: 2026-11-05

### Minimum SIP

**Q:** Minimum SIP for HDFC ELSS Tax Saver Fund?

> The minimum SIP amount for the HDFC ELSS Tax Saver Fund is ₹500.
> Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct
> Last updated from sources: 2026-11-05

### ELSS lock-in

**Q:** What is the lock-in period for HDFC ELSS Tax Saver Fund?

> The lock-in period for the HDFC ELSS Tax Saver Fund is 3 years.
> Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct
> Last updated from sources: 2026-11-05

### Riskometer

**Q:** What is the riskometer level of HDFC Large Cap Fund?

> The riskometer level of HDFC Large Cap Fund is Very High.
> Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct
> Last updated from sources: 2026-11-05

### Benchmark

**Q:** What is the benchmark of HDFC Nifty 50 Index Fund?

> The benchmark for the HDFC Nifty 50 Index Fund is the NIFTY 50 Index (Total Returns Index). This index represents the performance of the 50 largest and most liquid companies listed on the National Stock Exchange.
> Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-nifty-50-index-fund/direct
> Last updated from sources: 2026-11-05

### Statement download

**Q:** How do I download my consolidated account statement?

> You can download your consolidated account statement from the HDFC Mutual Fund Download Statement page using your PAN or folio details.
> Source: https://www.hdfcfund.com/services/consolidated-account-statement
> Last updated from sources: 2026-11-05

---

## Basic mutual-fund education (curated, not model-generated)

These answers come from fixed copy in
[`src/mf_facts/guardrails/education.py`](src/mf_facts/guardrails/education.py).
Each one still carries exactly one official source and a fetch date.

### What is a mutual fund?

**Q:** What is a mutual fund?

> A mutual fund pools money from many investors and invests it in a diversified portfolio of securities such as stocks or bonds, managed by a professional asset management company. Units represent an investor's share of the fund's assets, and the fund is regulated by SEBI.
> Source: https://www.amfiindia.com/mutual-fund
> Last updated from sources: 2026-11-05

### What is a flexi cap fund?

**Q:** What is a flexi cap fund?

> A flexi cap fund is an equity scheme that must invest at least 65% of its assets in equity and equity-related instruments across large-cap, mid-cap and small-cap companies. The fund manager can shift the allocation between market capitalisations within the scheme's mandate.
> Source: https://www.amfiindia.com/mutual-fund
> Last updated from sources: 2026-11-05

### Example of a flexi cap fund

**Q:** Can you give me some example of flexi cap funds?

> Flexi cap funds are equity schemes that invest at least 65% of assets in equity and equity-related instruments across large-cap, mid-cap and small-cap companies. In my current scope, HDFC Flexi Cap Fund is an example of a flexi cap fund.
> Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct
> Last updated from sources: 2026-11-05

### SIP and NAV

**Q:** What is SIP?

> A Systematic Investment Plan (SIP) lets an investor buy fund units at fixed intervals, usually monthly, instead of investing a lump sum at once. Each instalment buys units at the prevailing NAV, so the number of units varies with price.
> Source: https://www.amfiindia.com/mutual-fund
> Last updated from sources: 2026-11-05

**Q:** What is NAV?

> Net Asset Value (NAV) is the per-unit value of a mutual fund scheme's assets minus its liabilities, calculated at the end of each business day. It is the price at which units are bought or redeemed, subject to applicable loads and taxes.
> Source: https://www.amfiindia.com/mutual-fund
> Last updated from sources: 2026-11-05

### Direct vs regular plan

**Q:** What is the difference between direct and regular plan?

> A direct plan is bought directly from the AMC or a platform without a distributor, while a regular plan includes distributor commission in its expenses. Both plans hold the same portfolio, but their expense ratios and NAVs can differ.
> Source: https://www.hdfcfund.com/services/faqs
> Last updated from sources: 2026-11-05

Other curated topics include large/mid/small cap, ELSS, index funds, ETFs,
riskometer, benchmark, expense ratio, exit load, lock-in, AUM, folio, CAS,
capital-gains statement, SWP, STP, NFO and tracking error.

---

## Refusals (pre-LLM, fixed copy)

### Investment advice

**Q:** Should I buy HDFC Flexi Cap Fund?

> I can only share factual scheme information, not investment advice. You can verify scheme facts on the official AMC or SEBI/AMFI pages.
> Source: https://investor.sebi.gov.in/
> Last updated from sources: 2026-11-05

### Performance / comparison

**Q:** Which fund gave the best 3-year returns?

> I don't provide or compare returns. The official factsheet on the AMC website has the performance data.
> Source: https://www.hdfcfund.com/
> Last updated from sources: 2026-11-05

### Out of scope AMC

**Q:** What is the expense ratio of SBI Bluechip Fund?

> That scheme isn't in my current scope. I cover a small set of HDFC Mutual Fund schemes: Flexi Cap, Large Cap, ELSS Tax Saver and Nifty 50 Index.
> Source: https://www.amfiindia.com/mutual-fund
> Last updated from sources: 2026-11-05

---

## Personal data rejected before generation

**Q:** My PAN is ABCDE1234F, what is the exit load?

> I can't accept personal identifiers like PAN, Aadhaar, account numbers, OTPs, email addresses or phone numbers. Please ask a general scheme question.

The same message is returned for Aadhaar, account/folio numbers, OTPs, email
addresses and phone numbers. The raw value is never logged or stored; traces
record only the PII category.

---

## Unknown / non-factual

**Q:** hello there

> I could not find that fact in my sources. Try asking about expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, or statement download.

---

## Auto-generated evaluation

`make eval` runs [`tests/golden/golden_set.yaml`](tests/golden/golden_set.yaml),
48 cases covering all seven fact intents, basic education, scheme detection,
refusals, PII and unknown questions.

Latest run:

```text
48/48 passed
```

---

## Disclaimer snippet

> **Facts-only. No investment advice.** This assistant reports publicly
> available scheme facts and links to the official source. It does not
> recommend, rank, or predict returns. Mutual fund investments are subject to
> market risks; read all scheme-related documents carefully. Always verify on
> the AMC/SEBI/AMFI page before acting.
