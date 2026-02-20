"""Law enforcement abbreviation mappings for Wisconsin.

Maps common abbreviations used by officers to their full legal terms
so that query expansion can match against statute/policy text.
"""

import re

# Abbreviation (upper-cased key) -> full expansion
ABBREVIATIONS: dict[str, str] = {
    "OWI": "Operating While Intoxicated",
    "OMVWI": "Operating a Motor Vehicle While Intoxicated",
    "OAR": "Operating After Revocation",
    "OAS": "Operating After Suspension",
    "BOLO": "Be On the Lookout",
    "EDP": "Emotionally Disturbed Person",
    "DV": "Domestic Violence",
    "DUI": "Driving Under the Influence",
    "BAC": "Blood Alcohol Concentration",
    "FTA": "Failure to Appear",
    "LESB": "Law Enforcement Standards Board",
    "DOJ": "Department of Justice",
    "DA": "District Attorney",
    "ADA": "Assistant District Attorney",
    "OIS": "Officer Involved Shooting",
    "SRO": "School Resource Officer",
    "K9": "Canine Unit",
    "SWAT": "Special Weapons and Tactics",
    "FTO": "Field Training Officer",
    "MVA": "Motor Vehicle Accident",
    "PBT": "Preliminary Breath Test",
    "SFSTs": "Standardized Field Sobriety Tests",
    "CCW": "Carrying a Concealed Weapon",
    "PC": "Probable Cause",
    "RS": "Reasonable Suspicion",
    "MOU": "Memorandum of Understanding",
    "SOP": "Standard Operating Procedure",
    "UOF": "Use of Force",
    "CIT": "Crisis Intervention Team",
    "AODA": "Alcohol and Other Drug Abuse",
    "TRO": "Temporary Restraining Order",
    "OC": "Oleoresin Capsicum",
    "ECD": "Electronic Control Device",
    "LEO": "Law Enforcement Officer",
    "PAT": "Pre-trial Assessment Tool",
}


def expand_abbreviations(text: str) -> str:
    """Replace known abbreviations in text with their full expansions.

    Matches whole words only (case-insensitive). Returns the text with
    abbreviations replaced by ``ABBREV (Full Expansion)`` so both forms
    are searchable.
    """
    result = text
    for abbr, full in ABBREVIATIONS.items():
        pattern = re.compile(r"\b" + re.escape(abbr) + r"\b", re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(f"{abbr} ({full})", result)
    return result
