"""Fixed compliance copy. Tested verbatim so refusals cannot drift."""
from __future__ import annotations

from mf_facts.guardrails.intent import Intent

EDUCATION_LINK = "https://investor.sebi.gov.in/"
AMFI_LEARN = "https://www.amfiindia.com/mutual-fund"
AMC_HOME = "https://www.hdfcfund.com/"

REFUSALS: dict[Intent, str] = {
    Intent.ADVICE: (
        "I can only share factual scheme information, not investment advice. "
        "You can verify scheme facts on the official AMC or SEBI/AMFI pages."
    ),
    Intent.PERFORMANCE: (
        "I don't provide or compare returns. The official factsheet on the AMC website "
        "has the performance data."
    ),
    Intent.PORTFOLIO: (
        "I can't help with portfolio decisions or allocations. "
        "I can share specific scheme facts such as expense ratio or exit load."
    ),
    Intent.PREDICTION: (
        "I can't predict NAV movements. I only report facts published by the AMC."
    ),
    Intent.OUT_OF_SCOPE: (
        "That scheme isn't in my current scope. I cover a small set of HDFC Mutual Fund "
        "schemes: Flexi Cap, Large Cap, ELSS Tax Saver and Nifty 50 Index."
    ),
}

DEFLECTION_LINK: dict[Intent, str] = {
    Intent.ADVICE: EDUCATION_LINK,
    Intent.PERFORMANCE: AMC_HOME,
    Intent.PORTFOLIO: AMFI_LEARN,
    Intent.PREDICTION: EDUCATION_LINK,
    Intent.OUT_OF_SCOPE: AMFI_LEARN,
}

PII_MESSAGE = (
    "I can't accept personal identifiers like PAN, Aadhaar, account numbers, OTPs, "
    "email addresses or phone numbers. Please ask a general scheme question."
)

NOT_FOUND_MESSAGE = (
    "I could not find that fact in my sources. Try asking about expense ratio, exit load, "
    "minimum SIP, lock-in, riskometer, benchmark, or statement download."
)

STATEMENT_ANSWER = (
    "You can download your consolidated account statement from the HDFC Mutual Fund "
    "Download Statement page using your PAN or folio details."
)
