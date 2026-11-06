"""Curated, citation-backed answers to basic mutual-fund questions.

These are deliberately not model-generated. Each entry is fixed copy with one
official source from ``data/sources.csv``, so a definition question cannot drift
into advice, rankings or performance claims.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

# All URLs below are enabled sources in data/sources.csv.
AMFI_BASICS = "https://www.amfiindia.com/mutual-fund"
AMFI_HOME = "https://www.amfiindia.com/"
SEBI_INVESTOR = "https://investor.sebi.gov.in/"
HDFC_CAS = "https://www.hdfcfund.com/services/consolidated-account-statement"
HDFC_FAQS = "https://www.hdfcfund.com/services/faqs"
HDFC_FLEXI = (
    "https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct"
)

# Fallback only: normally the date comes from the source's fetch metadata.
EDUCATION_REVIEWED_AT = date(2026, 11, 5)


@dataclass(frozen=True)
class EducationEntry:
    key: str
    patterns: tuple[re.Pattern[str], ...]
    answer: str
    url: str


def _entry(key: str, patterns: list[str], answer: str, url: str) -> EducationEntry:
    return EducationEntry(key, tuple(re.compile(p, re.I) for p in patterns), answer, url)


# Order matters: more specific entries must appear before broader ones.
EDUCATION_ENTRIES: tuple[EducationEntry, ...] = (
    _entry(
        "flexi_cap_examples",
        [
            r"\b(example|examples|list|some)\b[^?.!]{0,40}\bflexi\s*cap\b",
            r"\bflexi\s*cap\b[^?.!]{0,40}\b(example|examples|list|some)\b",
        ],
        "Flexi cap funds are equity schemes that invest at least 65% of assets in "
        "equity and equity-related instruments across large-cap, mid-cap and "
        "small-cap companies. In my current scope, HDFC Flexi Cap Fund is an "
        "example of a flexi cap fund.",
        HDFC_FLEXI,
    ),
    _entry(
        "flexi_cap",
        [r"\bflexi\s*cap\b"],
        "A flexi cap fund is an equity scheme that must invest at least 65% of its "
        "assets in equity and equity-related instruments across large-cap, mid-cap "
        "and small-cap companies. The fund manager can shift the allocation between "
        "market capitalisations within the scheme's mandate.",
        AMFI_BASICS,
    ),
    _entry(
        "large_cap",
        [r"\blarge\s*cap\b"],
        "A large cap fund is an equity scheme that invests at least 80% of its "
        "assets in equity and equity-related instruments of large-cap companies. "
        "Large-cap companies are typically the top 100 companies by full market "
        "capitalisation.",
        AMFI_BASICS,
    ),
    _entry(
        "mid_cap",
        [r"\bmid\s*cap\b"],
        "A mid cap fund is an equity scheme that invests at least 65% of its assets "
        "in equity and equity-related instruments of mid-cap companies. Mid-cap "
        "companies are typically ranked 101st to 250th by full market capitalisation.",
        AMFI_BASICS,
    ),
    _entry(
        "small_cap",
        [r"\bsmall\s*cap\b"],
        "A small cap fund is an equity scheme that invests at least 65% of its assets "
        "in equity and equity-related instruments of small-cap companies. Small-cap "
        "companies are typically ranked 251st onwards by full market capitalisation.",
        AMFI_BASICS,
    ),
    _entry(
        "elss",
        [r"\belss\b", r"equity\s+linked\s+savings", r"tax\s+saver"],
        "ELSS (Equity Linked Savings Scheme) is a tax-saving equity mutual fund that "
        "qualifies for deduction under Section 80C of the Income Tax Act, subject to "
        "the applicable limit. It has a mandatory lock-in of three years from the "
        "date of allotment.",
        AMFI_BASICS,
    ),
    _entry(
        "index_fund",
        [r"\bindex\s+funds?\b", r"\bindex\s+schemes?\b"],
        "An index fund is a passive scheme that invests in the securities of a "
        "specified index in the same proportion, with the aim of tracking the index. "
        "It does not try to beat the index and usually has a lower expense ratio.",
        AMFI_BASICS,
    ),
    _entry(
        "etf",
        [r"\betfs?\b", r"exchange\s+traded\s+fund"],
        "An exchange-traded fund (ETF) is a pooled investment product whose units are "
        "listed and traded on a stock exchange like shares. Its market price can "
        "differ slightly from its NAV.",
        AMFI_BASICS,
    ),
    _entry(
        "tracking_error",
        [r"tracking\s+error"],
        "Tracking error measures how closely an index fund follows its benchmark "
        "index over a period. A lower tracking error indicates tighter tracking, and "
        "the figure is disclosed in official fund documents.",
        AMFI_BASICS,
    ),
    _entry(
        "open_closed",
        [r"\bopen[\s-]?ended\b", r"\bclose[\s-]?ended\b"],
        "An open-ended scheme allows investors to buy and redeem units at the "
        "applicable NAV on an ongoing basis. A close-ended scheme has a fixed "
        "maturity and generally does not allow ongoing redemption until maturity.",
        AMFI_BASICS,
    ),
    _entry(
        "swp",
        [r"\bswp\b", r"systematic\s+withdrawal"],
        "A Systematic Withdrawal Plan (SWP) allows an investor to withdraw a fixed "
        "amount from a mutual fund scheme at regular intervals. Units are redeemed at "
        "the prevailing NAV on each withdrawal date.",
        AMFI_BASICS,
    ),
    _entry(
        "stp",
        [r"\bstp\b", r"systematic\s+transfer"],
        "A Systematic Transfer Plan (STP) lets an investor move a fixed amount from "
        "one scheme to another at regular intervals. It is commonly used to transfer "
        "from a liquid or debt scheme into an equity scheme over time.",
        AMFI_BASICS,
    ),
    _entry(
        "nfo",
        [r"\bnfo\b", r"new\s+fund\s+offer"],
        "A New Fund Offer (NFO) is the initial subscription period during which a new "
        "mutual fund scheme accepts investments before it reopens for ongoing "
        "purchase at NAV. Units are allotted after the NFO closes.",
        AMFI_BASICS,
    ),
    _entry(
        "direct_regular",
        [r"\bdirect\s+plans?\b", r"\bregular\s+plans?\b"],
        "A direct plan is bought directly from the AMC or a platform without a "
        "distributor, while a regular plan includes distributor commission in its "
        "expenses. Both plans hold the same portfolio, but their expense ratios and "
        "NAVs can differ.",
        HDFC_FAQS,
    ),
    _entry(
        "growth_idcw",
        [r"\bgrowth\s+(option|plan)\b", r"\bidcw\b", r"dividend\s+option"],
        "Under the growth option, gains remain in the scheme and are reflected in the "
        "NAV. Under the IDCW option, the scheme may distribute a portion of "
        "distributable surplus to unitholders, and the NAV falls by the distribution "
        "amount.",
        AMFI_BASICS,
    ),
    _entry(
        "nav",
        [r"\bnav\b", r"net\s+asset\s+value"],
        "Net Asset Value (NAV) is the per-unit value of a mutual fund scheme's assets "
        "minus its liabilities, calculated at the end of each business day. It is the "
        "price at which units are bought or redeemed, subject to applicable loads and "
        "taxes.",
        AMFI_BASICS,
    ),
    _entry(
        "aum",
        [r"\baum\b", r"assets\s+under\s+management"],
        "Assets Under Management (AUM) is the total market value of the investments "
        "managed by a fund house or scheme. It changes with inflows, outflows and the "
        "market value of the holdings.",
        AMFI_BASICS,
    ),
    _entry(
        "fund_manager",
        [r"fund\s+manager"],
        "A fund manager is the professional responsible for managing a mutual fund "
        "scheme's portfolio and investment decisions within its stated mandate. The "
        "manager's name and tenure are disclosed on the AMC's official scheme page.",
        HDFC_FAQS,
    ),
    _entry(
        "expense_ratio",
        [r"expense\s+ratio", r"total\s+expense\s+ratio", r"\bter\b"],
        "The expense ratio, also called the Total Expense Ratio (TER), is the annual "
        "fee charged by a scheme, expressed as a percentage of its average daily net "
        "assets. It covers fund management and related expenses and is disclosed by "
        "the AMC.",
        AMFI_BASICS,
    ),
    _entry(
        "exit_load",
        [r"exit\s+load", r"entry\s+load"],
        "An exit load is a fee charged when units are redeemed or switched out before "
        "a specified holding period. It is a percentage of the redemption value and is "
        "disclosed in the scheme's load structure.",
        AMFI_BASICS,
    ),
    _entry(
        "min_sip",
        [r"minimum\s+(sip|sip\s+amount)", r"\bmin\.?\s*sip\b"],
        "The minimum SIP amount is the smallest instalment a scheme accepts under a "
        "Systematic Investment Plan. It is set by the AMC for each scheme and can "
        "differ between schemes and plans.",
        AMFI_BASICS,
    ),
    _entry(
        "lock_in",
        [r"lock[\s-]?in"],
        "A lock-in period is the minimum time an investor must stay invested in a "
        "scheme before units can be redeemed. ELSS tax saver funds have a statutory "
        "lock-in of three years from the date of allotment.",
        AMFI_BASICS,
    ),
    _entry(
        "riskometer",
        [r"risk[\s-]?o[\s-]?meter", r"\briskometer\b"],
        "The riskometer is a SEBI-mandated indicator that shows the risk level of a "
        "mutual fund scheme on a scale from Low to Very High. It reflects the scheme's "
        "risk over its stated horizon and is displayed on official scheme documents.",
        SEBI_INVESTOR,
    ),
    _entry(
        "benchmark",
        [r"\bbenchmark\b", r"benchmark\s+index"],
        "A benchmark is the market index against which a mutual fund scheme is "
        "measured. For example, large-cap schemes are often measured against a "
        "large-cap index, and index funds track their stated index.",
        AMFI_BASICS,
    ),
    _entry(
        "sip",
        [r"\bsip\b", r"systematic\s+investment"],
        "A Systematic Investment Plan (SIP) lets an investor buy fund units at fixed "
        "intervals, usually monthly, instead of investing a lump sum at once. Each "
        "instalment buys units at the prevailing NAV, so the number of units varies "
        "with price.",
        AMFI_BASICS,
    ),
    _entry(
        "lumpsum",
        [r"lump[\s-]?sum"],
        "A lump sum investment puts a single amount into a mutual fund scheme at one "
        "time, instead of spreading purchases through a SIP. Units are allotted at "
        "the NAV applicable on the transaction date.",
        AMFI_BASICS,
    ),
    _entry(
        "capital_gains",
        [r"capital\s+gains"],
        "A capital gains statement lists the purchase and redemption details of "
        "mutual fund units and the resulting capital gains or losses for a financial "
        "year. It is used for tax reporting and can be downloaded from the AMC or "
        "registrar.",
        HDFC_CAS,
    ),
    _entry(
        "cas",
        [r"\bcas\b", r"consolidated\s+account\s+statement"],
        "A consolidated account statement (CAS) is a single statement that lists all "
        "mutual fund holdings across AMCs for a folio holder. It is usually generated "
        "using the investor's PAN and can be downloaded from official AMC or registrar "
        "pages.",
        HDFC_CAS,
    ),
    _entry(
        "folio",
        [r"\bfolio\b"],
        "A folio is the account number the AMC uses to record an investor's holdings "
        "in its schemes. It is quoted when you buy, redeem or request a statement.",
        HDFC_FAQS,
    ),
    _entry(
        "mutual_fund",
        [r"\bmutual\s+funds?\b"],
        "A mutual fund pools money from many investors and invests it in a diversified "
        "portfolio of securities such as stocks or bonds, managed by a professional "
        "asset management company. Units represent an investor's share of the fund's "
        "assets, and the fund is regulated by SEBI.",
        AMFI_BASICS,
    ),
)

EDUCATION_BY_KEY: dict[str, EducationEntry] = {e.key: e for e in EDUCATION_ENTRIES}

# Phrasing that turns a topic into a definition/example question. Scheme-specific
# fact questions are routed before this is consulted.
LOOKUP_RE = re.compile(
    r"^\s*(what\s+(is|are|does|do)|what's|define|explain|meaning\s+of"
    r"|tell\s+me\s+about|describe)\b"
    r"|\b(example|examples|difference\s+between|types?\s+of|how\s+does)\b",
    re.I,
)


def match_education(question: str) -> EducationEntry | None:
    """Return the first curated entry matching the question."""
    for entry in EDUCATION_ENTRIES:
        if any(p.search(question) for p in entry.patterns):
            return entry
    return None
