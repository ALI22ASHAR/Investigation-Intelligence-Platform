"""
preprocessing/text_cleaning.py

Purpose: take messy raw text and normalize it into clean, consistent
text. This is intentionally separate from extraction (schema.py) and
from figuring out WHERE text comes from (that's the next file) --
this module only knows how to take a string and make it cleaner.
"""

import re  # Python's regular expressions module -- for pattern-based text find/replace
import unicodedata  # for normalizing unicode characters (smart quotes, accented letters, etc.)


def normalize_whitespace(text: str) -> str:
    """
    Collapses runs of whitespace (multiple spaces, tabs, blank lines)
    down to single spaces/newlines.

    Legal documents extracted from PDFs are FULL of this: PDF text
    extraction often inserts extra spaces where columns/tables were,
    or repeated blank lines from page breaks.
    """
    # \s+ matches one-or-more whitespace characters of ANY kind (space,
    # tab, newline) in a row. Replacing every such run with a single
    # space collapses "word    word" or "word\n\n\nword" into "word word".
    text = re.sub(r"[ \t]+", " ", text)          # collapse repeated spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)       # collapse 3+ newlines to just 2 (keep paragraph breaks)
    return text.strip()  # remove leading/trailing whitespace from the whole string


def normalize_unicode(text: str) -> str:
    """
    Converts "smart quotes" (’ “ ”) and similar typographic characters
    into their plain ASCII equivalents (' " "), and normalizes accented
    characters to a consistent representation.

    Why this matters: without this, searching for the word "don't" might
    fail to match text that actually contains "don’t" (curly apostrophe)
    -- they LOOK the same to a human but are different characters to a
    computer. This bites people constantly in search/NLP pipelines.
    """
    # NFKC normalization: converts visually-equivalent character sequences
    # into one consistent form. This is a standard, well-documented
    # Unicode normalization mode (Normalization Form KC).
    text = unicodedata.normalize("NFKC", text)

    replacements = {
        "\u2018": "'", "\u2019": "'",   # curly single quotes -> straight
        "\u201c": '"', "\u201d": '"',   # curly double quotes -> straight
        "\u2013": "-", "\u2014": "-",   # en-dash / em-dash -> hyphen
        "\xa0": " ",                     # non-breaking space -> normal space
    }
    for bad_char, good_char in replacements.items():
        text = text.replace(bad_char, good_char)
    return text


def remove_page_artifacts(text: str) -> str:
    """
    Strips common PDF-extraction junk: standalone page numbers on their
    own line, and repeated "Page X of Y" style footers.
    """
    # ^\s*\d+\s*$ means: a line that contains ONLY a number (possibly with
    # surrounding whitespace) and nothing else -- a classic lone page number.
    # re.MULTILINE makes ^ and $ match the start/end of EACH line, not just
    # the start/end of the whole string.
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # Matches things like "Page 3 of 10" case-insensitively.
    text = re.sub(r"Page \d+ of \d+", "", text, flags=re.IGNORECASE)

    return text


def clean_text_pipeline(raw_text: str) -> str:
    """
    Runs all cleaning steps in a deliberate ORDER. Order matters here:
    we remove page artifacts BEFORE collapsing whitespace, otherwise the
    blank line left behind by a removed page number wouldn't get
    collapsed away properly.
    """
    text = normalize_unicode(raw_text)
    text = remove_page_artifacts(text)
    text = normalize_whitespace(text)
    return text


if __name__ == "__main__":
    # A tiny self-test you can run directly to sanity-check the functions
    # BEFORE wiring them into the full pipeline. Running a file's own
    # tests like this (python preprocessing/text_cleaning.py) is a cheap,
    # fast way to catch bugs early.
    sample = """
    IN THE MATTER OF SOMETHING

    3

    This    is  a messy   document with “smart quotes” and extra   spaces.


    Page 2 of 5


    It also has multiple    blank lines above.
    """
    print("--- BEFORE ---")
    print(repr(sample))
    print("--- AFTER ---")
    print(repr(clean_text_pipeline(sample)))