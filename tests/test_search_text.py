"""Tests for the text that represents a passage in search."""
from maestro.index.search_text import search_text, strip_editorial_marks
from maestro.parse.schemas import TreatisePassage


def passage(**changes):
    """A valid passage, with some fields changed for the test."""
    data = dict(
        passage_id="fiore_getty:09r-t", treatise_id="fiore_getty",
        treatise_title="Fior di Battaglia (MS Ludwig XV 13)", author="Fiore de'i Liberi",
        year_circa=1410, section="Dagger, Introduction", folio="09r",
        text="Queste zinque figure sono le guardie dela daga.", language="ita-arc",
        translation_en="These five figures are the guards of the dagger.",
        source_url="https://wiktenauer.com/wiki/Fiore_de'i_Liberi",
        source_license="CC-BY-SA-4.0", source_revision=163576,
    )
    data.update(changes)
    return TreatisePassage(**data)


def test_editorial_marks_are_removed_for_search():
    assert strip_editorial_marks("Voii[!] semo m[e]zi") == "Voii semo mezi"


def test_search_text_has_section_original_and_translation():
    assert search_text(passage()).splitlines() == [
        "Dagger, Introduction",
        "Queste zinque figure sono le guardie dela daga.",
        "These five figures are the guards of the dagger.",
    ]


def test_search_text_without_translation():
    assert search_text(passage(translation_en=None)).splitlines() == [
        "Dagger, Introduction",
        "Queste zinque figure sono le guardie dela daga.",
    ]


def test_translator_insertions_are_kept_for_search():
    p = passage(translation_en="I am the Fourth [Dagger Remedy] Master")
    assert "[Dagger Remedy]" in search_text(p)