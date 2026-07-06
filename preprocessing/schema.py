"""
preprocessing/schema.py

Purpose: define ONE consistent shape that every document in the system
gets converted into, regardless of whether it started life as a
CourtListener JSON blob, a scraped PDF, or an email.

Why bother with this file at all? Because every later phase (database,
embeddings, search, RAG) needs to answer questions like "what's the
document's date?" or "give me its clean text" without needing to know
or care where the document originally came from. This schema is the
contract that makes that possible.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class ProcessedDocument:
    """
    @dataclass is a Python shortcut: it auto-generates the boring stuff
    (an __init__ that sets all these fields, a nice __repr__ for printing,
    equality checks) so we just declare the fields and their types.

    Every field below with "Optional[...]" means it's allowed to be None --
    because not every source gives us every piece of metadata. Fields
    WITHOUT Optional are things we insist every document must have.
    """

    # --- identity & provenance ---
    doc_id: str                     # a stable unique ID we generate (see below)
    source_type: str                # e.g. "courtlistener_opinion", "doj_press_release"
    source_url: Optional[str] = None
    original_filename: Optional[str] = None

    # --- the actual content, cleaned ---
    title: Optional[str] = None
    clean_text: str = ""
    raw_text_length: int = 0        # length BEFORE cleaning (for sanity-checking)
    clean_text_length: int = 0      # length AFTER cleaning

    # --- case/document metadata (fill in what's available, leave rest None) ---
    court: Optional[str] = None
    date_filed: Optional[str] = None
    docket_number: Optional[str] = None
    people_mentioned: list[str] = field(default_factory=list)
    # default_factory=list (not "= []") avoids a classic Python bug where
    # a mutable default value gets SHARED across every instance of the
    # class instead of each one getting its own fresh empty list.

    # --- pipeline bookkeeping ---
    processed_at_unix: float = 0.0
    sha256_of_source: Optional[str] = None

    def to_dict(self) -> dict:
        """Converts this object into a plain dictionary, ready for json.dump()."""
        return asdict(self)