"""
Parser for Fiore dei Liberi, "Fior di Battaglia", Getty manuscript (MS Ludwig XV 13).
"""
import re
import copy

# Manuscript reference in the Getty text: "[9r-t]", "[ 22v-d ]", "[1r]"
# group 1 = folio (9r), group 2 = position of the figure on the page (t, d...), optional
MARKER_RE = re.compile(r"\[\s*(\d{1,3}[rv])(?:-([a-z0-9]+))?\s*\]")
# Editors' placeholders such as "[No text]": the cell is actually empty
PLACEHOLDER_RE = re.compile(r"\[\s*No (text|illustration|translation)[^\]]*\]", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
# Translators number their paragraphs: "[10] With the grips...". Only a number at the
# very START is dropped; inside the text numbers belong to lists ("[1] strength, [2] speed").
LEADING_NUMBER_RE = re.compile(r"^\[\d+\]\s*")

def rebuild_grid(table):
    """Turn an HTML table into a full rows x columns matrix of cells.

    A cell with rowspan/colspan appears only once in the HTML, but covers several
    positions: here it is placed in every position it covers, so the same cell can 
    appear in several rows and column numbers are reliable.
    """
    body = table.find("tbody") or table
    html_rows = body.find_all("tr", recursive=False)

    taken = {}  # (row, column) -> the cell that occupies that position
    for r, tr in enumerate(html_rows):
        c = 0   # column where the next cell will be placed, starting from left
        for cell in tr.find_all(["td","th"], recursive=False):
            while (r,c) in taken:   # skip positions already covered from above rows
                c+=1
            height = int(cell.get("rowspan",1))
            width = int(cell.get("colspan",1))
            for dr in range(height):        # 'stamp' the cell on every position it covers
                for dc in range(width):
                    taken[(r + dr, c + dc)] = cell
            c += width

    n_rows = len(html_rows)
    n_cols = max((col for (_,col) in taken), default=-1) + 1
    return [[ taken.get((r,col)) for col in range(n_cols)] for r in range(n_rows)]


def find_columns(header):
    """Find the columns we need by their header text.

    Returns {"illustrations": [indexes], "text": index or None, "translation": index or None}.
    """
    columns = {"illustrations": [], "text": None, "translation": None}
    # Fallback: in "Seven Swords" the Getty translation header is
    # "PD by Michael Chidester Getty by Colin Hatcher", without "Translation".
    fallback = None
    for i, cell in enumerate(header):
        if cell is None:
            continue
        name = cell.get_text(" ", strip=True).lower()
        if "illustration" in name:
            columns["illustrations"].append(i)  # there can be two of them
        elif "getty version" in name:
            columns["text"] = i
        elif "translation" in name and "getty" in name and columns["translation"] is None:
            columns["translation"] = i
        elif "getty" in name and fallback is None:
            fallback = i
    if columns["translation"] is None:
        columns["translation"] = fallback
    return columns


def normalize_folio(folio):
    """'9r' -> '09r', so that '9r' and '09r' are not two different folios."""
    number, side = folio[:-1], folio[-1]    # "9", "r": the side is always the last character
    return f"{int(number):02d}{side}"



def cell_text(cell):
    """Clean text of a cell and its manuscript reference: ("Queste zinque...", "09r-t").

    The reference is None when the cell has no marker such as [9r-t].
    """
    if cell is None:
        return "", None

    c = copy.copy(cell)     # work on a copy: the methods below modify the HTML cell structure directly, without returning a copy
    for note in c.select("sup.reference"):  # footnotes inserted by Wiktenauer, e.g. [2] in 'Queste zinque figure[2] sono le guardie...'
        note.decompose()
    for br in c.find_all("br"):
        br.replace_with("\n")   # real line breaks become "\n"
    for block in c.find_all(["p","div","li"]):
        block.append("\n")    # the end of each paragraph becomes "\n"

    text = c.get_text("")
    reference_folio = None

    m = MARKER_RE.search(text)
    if m:
        reference_folio = normalize_folio(m.group(1)) + (f"-{m.group(2)}" if m.group(2) else '')

    text = MARKER_RE.sub(" ", text)  # once reference_folio is saved, delete it from the text  
    text = SPACE_RE.sub(" ",text).strip()   # \s also matches the non-breaking space &#160;
    text = LEADING_NUMBER_RE.sub("", text)

    if PLACEHOLDER_RE.fullmatch(text):
        text = ""
    return text, reference_folio
