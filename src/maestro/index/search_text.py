"""
The text that represents a passage for search.

The system SHOWS and QUOTES the original text exactly as trascribed, editorial 
marks included (e.g. m[e]zo). It SEARCHES a different copy, built to match questions 
written in modern language:
- the section title , for the context (which weapon, which master)
- the original text without editorial marks ("m[e]zo" -> "mezo")
- the English translation, which carries the meaning in modern language
"""
import re

SIC_RE = re.compile(r"\[!\]")       # "scarmidori[!]": sic, the manuscript says so
SUPPLIED_RE = re.compile(r"\[([a-z]{1,4})\]")    # "m[e]zo": a letter supplied by the editor

def strip_editorial_marks(text):
    """'que[ll]' -> 'quell', 'scarmidori[!]' -> 'scarmidori'. For searching only."""
    text = SIC_RE.sub("", text)
    return SUPPLIED_RE.sub(r"\1", text)


def search_text(passage):
    """Section, original without editorial marks and translation, one per line."""
    parts = [passage.section, strip_editorial_marks(passage.text)]
    if passage.translation_en:
        parts.append(passage.translation_en)
    return "\n".join(parts)