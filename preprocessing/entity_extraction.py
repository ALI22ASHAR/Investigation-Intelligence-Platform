"""
preprocessing/entity_extraction.py

Purpose: use spaCy's pretrained NLP model to pull out named entities
(people, organizations, locations, dates) from a document's clean text.

This is what finally populates the "people_mentioned" field that's
been sitting unused in ProcessedDocument since Phase 3.
"""

import spacy

# Loading a spaCy model is slow-ish (~1 second) -- same principle as
# Phase 5's embedding model: load ONCE at module level, reuse everywhere.
print("Loading spaCy NLP model...")
nlp = spacy.load("en_core_web_sm")
print("spaCy model loaded.")


def extract_entities(text: str) -> dict:
    """
    Runs the text through spaCy's NLP pipeline and pulls out entities,
    grouped by type. spaCy tags each detected entity with a label like
    PERSON, ORG, GPE (geopolitical entity -- countries/cities/states),
    or DATE -- these labels come from the model's training data, not
    something we define ourselves.
    """
    # spaCy has a hard limit on how much text it processes in one call
    # (default ~1 million characters) -- fine for our chunk/document
    # sizes, but worth knowing about if you ever feed it something huge.
    doc = nlp(text)

    people = set()
    organizations = set()
    locations = set()

    # doc.ents is spaCy's list of every entity it found in the text,
    # each with a .text (the actual words) and .label_ (the category).
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            people.add(ent.text.strip())
        elif ent.label_ == "ORG":
            organizations.add(ent.text.strip())
        elif ent.label_ == "GPE":
            locations.add(ent.text.strip())

    # Using a set() while collecting avoids duplicate mentions of the
    # same name within one document; we convert to sorted lists at the
    # end since JSON/our schema expects plain lists, and sorting makes
    # output stable/predictable between runs.
    return {
        "people": sorted(people),
        "organizations": sorted(organizations),
        "locations": sorted(locations),
    }


if __name__ == "__main__":
    sample = (
        "In the matter of Epstein v. Soler-Epstein, filed in the Supreme "
        "Court of New York, Judge Maria Rodriguez presided over the case. "
        "The defendant, James Epstein, was represented by attorneys from "
        "Goldstein & Associates. The plaintiff resides in Brooklyn."
    )
    result = extract_entities(sample)
    print("People:       ", result["people"])
    print("Organizations:", result["organizations"])
    print("Locations:    ", result["locations"])