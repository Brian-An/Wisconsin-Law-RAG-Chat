"""Colloquialism and synonym mappings for legal terminology.

Maps informal language officers might use to the formal legal terms
that appear in Wisconsin statutes and case law.
"""

# Informal phrase -> list of formal equivalents
COLLOQUIAL_TO_LEGAL: dict[str, list[str]] = {
    "pulled over": ["traffic stop", "Terry stop", "investigatory stop"],
    "drunk driving": ["operating while intoxicated", "OWI", "OMVWI"],
    "speeding": ["exceeding speed limit", "speed violation"],
    "running a red light": ["failure to obey traffic signal"],
    "hit and run": ["duty upon striking", "failure to report accident"],
    "road rage": ["aggressive driving", "reckless driving"],
    "resisting arrest": ["resisting or obstructing an officer"],
    "shoplifting": ["retail theft", "theft"],
    "breaking and entering": ["burglary", "unlawful entry"],
    "assault": ["battery", "substantial battery", "aggravated battery"],
    "murder": ["first degree intentional homicide", "homicide"],
    "manslaughter": ["second degree reckless homicide", "homicide by negligent operation"],
    "drug possession": ["possession of controlled substance", "controlled substance"],
    "car theft": ["operating vehicle without consent", "theft of motor vehicle"],
    "trespassing": ["criminal trespass", "trespass to land"],
    "domestic abuse": ["domestic violence", "domestic abuse"],
    "restraining order": ["temporary restraining order", "TRO", "injunction"],
    "bail": ["bond", "bail jumping", "conditions of release"],
    "jaywalking": ["pedestrian violation", "failure to yield"],
    "fleeing": ["fleeing or eluding an officer", "vehicle pursuit"],
    "terry stop": ["Terry stop", "investigatory stop", "investigative detention", "reasonable suspicion stop"],
    "stop and frisk": ["Terry frisk", "protective search", "pat down search"],
    "owi": ["operating while intoxicated", "OWI", "OMVWI", "drunk driving"],
    "field sobriety": ["standardized field sobriety test", "SFST", "field sobriety"],
    "pat down": ["Terry frisk", "protective search"],
    "miranda": ["Miranda warning", "custodial interrogation rights"],
    "search warrant": ["search warrant", "warrant execution"],
    "no knock": ["no-knock warrant", "forced entry warrant"],
    "use of force": ["use of force", "reasonable force", "deadly force"],
    "taser": ["electronic control device", "conducted energy weapon"],
    "pepper spray": ["oleoresin capsicum", "OC spray", "chemical agent"],
    "high speed chase": ["vehicle pursuit", "fleeing or eluding"],
    "dwi": ["operating while intoxicated", "OWI"],
    "dui": ["operating while intoxicated", "OWI"],
}

# Maps general topics to Wisconsin statute chapter numbers
TOPIC_TO_CHAPTERS: dict[str, list[str]] = {
    "traffic": ["346"],
    "criminal": ["939", "940", "941", "942", "943", "944", "945", "946", "947", "948"],
    "homicide": ["940"],
    "theft": ["943"],
    "drugs": ["961"],
    "alcohol": ["125", "346"],
    "weapons": ["941"],
    "domestic": ["813", "968"],
    "juvenile": ["938"],
    "police powers": ["175", "968"],
    "terry stop": ["968"],
    "stop and frisk": ["968"],
    "use of force": ["939"],
    "field sobriety": ["343", "346"],
    "owi": ["346"],
    "sexual": ["940", "944", "948"],
    "burglary": ["943"],
    "fraud": ["943"],
}


def get_legal_synonyms(query: str) -> list[str]:
    """Return formal legal synonyms for informal terms found in the query.

    Scans the query (case-insensitive) for known colloquial phrases and
    returns all formal equivalents, deduplicated and in discovery order.
    """
    query_lower = query.lower()
    synonyms: list[str] = []
    for informal, formals in COLLOQUIAL_TO_LEGAL.items():
        if informal in query_lower:
            synonyms.extend(formals)
    return list(dict.fromkeys(synonyms))  # deduplicate, preserve order


def get_chapter_hints(query: str) -> list[str]:
    """Return statute chapter numbers relevant to topics mentioned in the query."""
    query_lower = query.lower()
    chapters: list[str] = []
    for topic, nums in TOPIC_TO_CHAPTERS.items():
        if topic in query_lower:
            chapters.extend(nums)
    return list(dict.fromkeys(chapters))
