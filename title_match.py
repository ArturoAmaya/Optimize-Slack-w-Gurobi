import re
from itertools import chain

control_chars = re.escape(
    "".join(map(chr, chain(range(0x00, 0x20), range(0x7F, 0xA0))))
)
# cribbed from ExploratoryCurricularAnalytics to help match names with the prereq db
def clean_course_title(title: str) -> str:
    """
    Cleans up the course title by removing asterisks and (see note)s.
    """
    title = re.sub(r"[*^~.#+=¹%s]+|<..?>" % control_chars, "", title)
    title = title.strip()
    title = re.sub(r"\s*/\s*(AWPE?|A?ELWR|SDCC)", "", title)
    title = title.upper()
    title = re.sub(r"\s+OR\s+|\s*/\s*", " / ", title)
    title = re.sub(r"-+", " - ", title)
    title = re.sub(r" +", " ", title)
    title = re.sub(
        r" ?\( ?(GE SEE|NOTE|FOR|SEE|REQUIRES|ONLY|OFFERED)[^)]*\)", "", title
    )
    title = re.sub(r"^\d+ ", "", title)
    title = re.sub(r"ELECT?\b", "ELECTIVE", title)
    title = title.replace(" (VIS)", "")
    if title.startswith("NE ELECTIVE "):
        title = re.sub(r"[()]", "", title)
    title = re.sub(r"TECH\b", "TECHNICAL", title)
    title = re.sub(r"REQUIRE\b", "REQUIREMENT", title)
    title = re.sub(r"BIO\b", "BIOLOGY", title)
    title = re.sub(r"BIOPHYS\b", "BIOPHYSICS", title)
    return title
