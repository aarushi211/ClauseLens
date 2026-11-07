"""
src/RAG/risk_classifier.py

Clause-Level Risk Classification & Unfair Clause Tagging.
Informed by legal research benchmarks including CLAUDETTE and UNFAIR-ToS,
as well as consumer advocacy standards (ToS;DR).

Classifies contract clauses into Risk Levels (HIGH, MEDIUM, LOW)
and identifies specific unfair/concerning contractual categories.
"""

import re
from typing import TypedDict, Optional

class RiskAssessment(TypedDict):
    risk_level: str          # "HIGH" | "MEDIUM" | "LOW"
    risk_reason: str         # Clear consumer-facing explanation
    unfair_category: Optional[str] # e.g. "Arbitration & Class Action Waiver"

# ── Regex patterns for deterministic risk rule checks ──────────────────────────
_RE_ARBITRATION = re.compile(
    r"\b(binding\s+arbitration|arbitrate|class\s+action\s+waiver|waive\s+any\s+right\s+to\s+bring\s+a\s+class\s+action|waive\s+trial\s+by\s+jury|jury\s+trial\s+waiver)\b",
    re.I
)

_RE_UNILATERAL_CHANGE = re.compile(
    r"\b(modify\s+(?:these\s+)?terms\s+(?:at\s+any\s+time|without\s+(?:prior\s+)?notice)|sole\s+discretion\s+(?:to\s+modify|to\s+change|to\s+update)|changes\s+effective\s+immediately\s+upon\s+posting)\b",
    re.I
)

_RE_UNILATERAL_TERMINATION = re.compile(
    r"\b(terminate\s+(?:your\s+)?(?:account|access)\s+(?:at\s+any\s+time|without\s+(?:cause|notice|liability)|in\s+our\s+sole\s+discretion))\b",
    re.I
)

_RE_DATA_SELLING = re.compile(
    r"\b(sell\s+(?:your\s+)?(?:personal\s+)?(?:information|data)|share\s+(?:your\s+)?(?:data|information)\s+with\s+(?:advertisers|third\s+party\s+partners|affiliates\s+for\s+marketing)|monetize\s+user\s+data)\b",
    re.I
)

_RE_BROAD_IP_LICENSE = re.compile(
    r"\b(perpetual,\s+irrevocable,\s+worldwide,\s+royalty-free|exclusive\s+license\s+to\s+(?:use|reproduce|distribute)|transfer\s+all\s+rights|sub-?licensable\s+(?:through\s+multiple\s+tiers\s+)?license)\b",
    re.I
)

_RE_LIABILITY_DISCLAIMER = re.compile(
    r"\b(aggregate\s+liability\s+(?:shall\s+not\s+exceed|capped\s+at)\s+\$?(?:0|100|amount\s+you\s+paid)|as\s+is\s+without\s+warranty\s+of\s+any\s+kind|disclaim\s+all\s+consequential,\s+punitive|hold\s+harmless\s+and\s+indemnify)\b",
    re.I
)

_RE_TRACKING = re.compile(
    r"\b(cross-site\s+tracking|behavioral\s+advertising|third-party\s+trackers|pixel\s+tags\s+to\s+track)\b",
    re.I
)

_RE_NO_INFO = re.compile(
    r"(does not contain information|not addressed in the provided|not explicitly covered|not mentioned)",
    re.I
)


def assess_clause_risk(topic_label: str, summary_text: str, excerpts: str = "") -> RiskAssessment:
    """
    Evaluates a topic's summary and source excerpts to assign a risk flag.
    Combines rule-based heuristics inspired by CLAUDETTE categories with topic context.
    """
    combined_text = f"{summary_text} {excerpts}".strip()

    # If the document does not contain information on this topic, mark as LOW / Neutral
    if _RE_NO_INFO.search(summary_text) or len(summary_text.strip()) < 15:
        return {
            "risk_level": "LOW",
            "risk_reason": "No restrictive terms identified in the document.",
            "unfair_category": None
        }

    # 1. Mandatory Arbitration & Class Action Waivers (CLAUDETTE: Dispute Resolution)
    if "Arbitration" in topic_label or _RE_ARBITRATION.search(combined_text):
        if _RE_ARBITRATION.search(combined_text):
            return {
                "risk_level": "HIGH",
                "risk_reason": "Enforces mandatory binding arbitration or waives the constitutional right to join class actions and jury trials.",
                "unfair_category": "Mandatory Arbitration & Class Action Waiver"
            }

    # 2. Unilateral Change of Terms (CLAUDETTE: Unilateral Change)
    if "Policy Changes" in topic_label or _RE_UNILATERAL_CHANGE.search(combined_text):
        if _RE_UNILATERAL_CHANGE.search(combined_text):
            return {
                "risk_level": "HIGH",
                "risk_reason": "Service reserves right to unilaterally modify terms without direct prior notification.",
                "unfair_category": "Unilateral Change of Contract"
            }
        elif "change" in combined_text.lower() or "update" in combined_text.lower():
            return {
                "risk_level": "MEDIUM",
                "risk_reason": "Terms may be modified periodically; check whether advance notice is guaranteed.",
                "unfair_category": "Terms Modification Policy"
            }

    # 3. Data Sharing & Selling (Consumer Privacy Concern)
    if "Data Sharing" in topic_label or _RE_DATA_SELLING.search(combined_text):
        if _RE_DATA_SELLING.search(combined_text):
            return {
                "risk_level": "HIGH",
                "risk_reason": "Discloses that user personal data or activity may be shared or monetized with commercial partners.",
                "unfair_category": "Data Monetization & Third-Party Sharing"
            }
        elif "third part" in combined_text.lower() or "partner" in combined_text.lower():
            return {
                "risk_level": "MEDIUM",
                "risk_reason": "Transfers user data to service providers or affiliated third parties.",
                "unfair_category": "Third-Party Data Transfer"
            }

    # 4. Liability Disclaimers & Indemnification (CLAUDETTE: Limitation of Liability)
    if "Liability" in topic_label or _RE_LIABILITY_DISCLAIMER.search(combined_text):
        if _RE_LIABILITY_DISCLAIMER.search(combined_text):
            return {
                "risk_level": "HIGH",
                "risk_reason": "Significantly disclaims provider liability (e.g. capped damages or broad indemnification clauses).",
                "unfair_category": "Limitation of Liability & Indemnity"
            }
        elif "liability" in combined_text.lower() or "disclaim" in combined_text.lower():
            return {
                "risk_level": "MEDIUM",
                "risk_reason": "Standard liability limitations and service disclaimers apply.",
                "unfair_category": "Liability Disclaimer"
            }

    # 5. IP & User Content Ownership (CLAUDETTE: Content Rights)
    if "IP & Content" in topic_label or _RE_BROAD_IP_LICENSE.search(combined_text):
        if _RE_BROAD_IP_LICENSE.search(combined_text):
            return {
                "risk_level": "HIGH",
                "risk_reason": "Grants provider a broad, perpetual, royalty-free, or transferable license to user-submitted content.",
                "unfair_category": "Broad Intellectual Property License"
            }
        elif "license" in combined_text.lower():
            return {
                "risk_level": "MEDIUM",
                "risk_reason": "Requires granting a license for platform operation and content display.",
                "unfair_category": "Content Display License"
            }

    # 6. Unilateral Account Termination / User Rights (CLAUDETTE: Termination)
    if "User Rights" in topic_label or _RE_UNILATERAL_TERMINATION.search(combined_text):
        if _RE_UNILATERAL_TERMINATION.search(combined_text):
            return {
                "risk_level": "HIGH",
                "risk_reason": "Permits account suspension or deletion at company's sole discretion without mandatory appeal.",
                "unfair_category": "Unilateral Account Termination"
            }

    # 7. Tracking & Cookies
    if "Cookies & Tracking" in topic_label or _RE_TRACKING.search(combined_text):
        if _RE_TRACKING.search(combined_text):
            return {
                "risk_level": "MEDIUM",
                "risk_reason": "Employs tracking technologies across third-party sites for behavioral targeting.",
                "unfair_category": "Cross-Site Behavioral Tracking"
            }

    # Default fallback assessment
    return {
        "risk_level": "LOW",
        "risk_reason": "Standard contractual provision within typical industry norms.",
        "unfair_category": None
    }
