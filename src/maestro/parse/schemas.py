"""
Data models shared by the whole pipeline.

TreatisePassage is the shape of one passage of a treatise. Every parser, for every
treatise, produces passages of this shape, and Pydantic validates them as soon as
they are created:
- required fields must be present and of the right type;
- optional fields (folio, translation) default to None, meaning "unknown";
- unknown fields are rejected (extra="forbid"), so a misspelled field fails loudly
  instead of being silently dropped.

Passages are stored as JSONL, one per line: model_dump_json() writes a line,
model_validate_json() reads it back and validates it again.
"""
from pydantic import BaseModel, ConfigDict, Field


class TreatisePassage(BaseModel):
    """One passage of a treatise, as produced by a parser."""

    # Unknown fields are an error. By default Pydantic silently drops them,
    # so a typo such as "trasnlation_en" would go unnoticed.
    model_config = ConfigDict(extra="forbid")

    # --- identity ---
    passage_id: str     # "fiore_getty:09r-t": treatise + manuscript reference
    treatise_id: str    # "fiore_getty"
    treatise_title: str # "Fior di Battaglia (MS Ludwig XV 13)"
    author: str         # "Fiore de'i Liberi"
    year_circa: int     # 1410

    # --- position in the treatise ---
    section: str                # heading above the table: "Dagger, Introduction"
    folio: str | None = None    # "09r" (r = recto, v = verso), from markers like [9r-t]

    # --- content ---
    text: str                               # the ORIGINAL text, cleaned but not modernised
    language: str                           # "ita-arc" = archaic Italian (my own convention)
    translation_en: str | None = None       # missing in some tables
    image_urls: list[str] = Field(default_factory=list)     # if missing, a new empty list

    # --- provenance (from the .meta.json) ---
    source_url: str
    source_license: str     # "CC-BY-SA-4.0"
    source_revision: int    # Wiktenauer revision, e.g. 163576
