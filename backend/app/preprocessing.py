import re

import ftfy

"""
Strip the following for any RAG pipeline

1) Rule based processing - common formatting issues -> Using regex
control characters while unicode can stay
white spaces
Tabs
new lines 
header, footer, page numbers
word split 
bullet point artifacts

2) llm assisted cleaning
"""

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]") #unwanted control characters
_REPEATED_SPACES = re.compile(r"[ \t]+") #tabs and white spaces
_REPEATED_BLANK_LINES = re.compile(r"\n{3,}") #3+ new lines to two new lines

# Rejoins a word wrapped across a line break, e.g. "hyphen-\nated" ->
# "hyphenated". Heuristic, not perfect: a real hyphenated word that happens
# to break at that exact point (e.g. "well-\nknown") gets squashed too
# ("wellknown") — there's no reliable way to tell the two apart with regex
# alone. Only fires on a single line break (not blank-line paragraph breaks).
_HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")


def clean_text(text: str | None) -> str | None:
    """Repair encoding corruption (mojibake) and normalize whitespace.
    Deliberately does not strip accented/non-Latin/symbol characters."""
    if not text:
        return text

    text = ftfy.fix_text(text)
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)
    text = _CONTROL_CHARS.sub("", text)
    text = _REPEATED_SPACES.sub(" ", text)
    text = _REPEATED_BLANK_LINES.sub("\n\n", text)

    return text.strip() or None
