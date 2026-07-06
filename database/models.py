"""
database/models.py

Purpose: define the actual database TABLE structure using SQLAlchemy's
ORM. Each class attribute below becomes a real column in Postgres.

This mirrors preprocessing/schema.py (ProcessedDocument) closely on
purpose -- that dataclass was our "in-memory" shape; this is the same
shape, but as a real, permanent, queryable database table.
"""

from sqlalchemy import Column, String, Integer, Float, Text, JSON
from sqlalchemy.orm import declarative_base

# declarative_base() gives us a base class that SQLAlchemy uses to track
# every table we define. Every table class below inherits from this.
Base = declarative_base()


class Document(Base):
    """
    Maps to a table called "documents" in Postgres.

    Column(...) definitions describe both the DATA TYPE and constraints
    (primary_key, nullable, etc.) -- SQLAlchemy uses this to generate the
    actual "CREATE TABLE" SQL for us, so we never hand-write that SQL.
    """
    __tablename__ = "documents"

    # primary_key=True means: this column uniquely identifies each row,
    # and Postgres will enforce that no two rows can share the same value.
    doc_id = Column(String(32), primary_key=True)

    source_type = Column(String(64), nullable=False)  # nullable=False = this field is REQUIRED
    source_url = Column(Text, nullable=True)            # nullable=True = this field is OPTIONAL (can be empty)
    original_filename = Column(String(255), nullable=True)

    title = Column(Text, nullable=True)
    clean_text = Column(Text, nullable=False)  # Text = unlimited-length string (vs String, which needs a max length)
    raw_text_length = Column(Integer, default=0)
    clean_text_length = Column(Integer, default=0)

    court = Column(String(255), nullable=True)
    date_filed = Column(String(32), nullable=True)  # stored as string for now; we'll discuss real Date types below
    docket_number = Column(String(64), nullable=True)

    # JSON column type: lets us store a Python list directly (SQLAlchemy
    # handles converting it to/from Postgres's native JSON storage).
    # Useful for fields like "people_mentioned" which are variable-length
    # lists that don't need their own separate table (yet).
    people_mentioned = Column(JSON, default=list)

    processed_at_unix = Column(Float, nullable=True)
    sha256_of_source = Column(String(128), nullable=True)

    def __repr__(self) -> str:
        # This controls how a Document object prints when you e.g. do
        # print(some_document) -- purely for readable debugging output.
        return f"<Document doc_id={self.doc_id} title={self.title!r}>"