"""
Parser for Fiore dei Liberi, "Fior di Battaglia", Getty manuscript (MS Ludwig XV 13).
"""
import re
import copy
from maestro import config

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


def section_title(table):
    """The headings above a table, from h3 down: "Dagger, Introduction".

    The h2 ("Treatise") is the same for every table, so it is left out:
    the h3 is needed because two sections are called "Introduction".
    """
    headings = table.find_previous(["h2","h3","h4"])
    if headings is None:
        return "Untitled"
    parts = [headings.get_text(" ", strip=True)]
    
    if headings.name == "h4":
        parent = headings.find_previous("h3")
        if parent is not None:
            parts.insert(0, parent.get_text(" ", strip=True))
    
    return ", ".join(parts)


def group_rows(grid, text_col, translation_col):
    """Group the data rows into passages: a list of lists of row indexes.

    A row continues the previous passage when it shares with the row above either
    the Getty cell or the translation cell (one cell with rowspan covering both).
    Both cases exist: one translation for two pieces of text, and one text for two
    translations. Grouping by translation only would repeat that text twice.
    """
    groups = []
    for r in range(1, len(grid)):                      # row 0 is the header
        if groups:
            above, here = grid[r - 1], grid[r]
            same_text = here[text_col] is not None and here[text_col] is above[text_col]
            same_translation = (translation_col is not None
                                and here[translation_col] is not None
                                and here[translation_col] is above[translation_col])
            if same_text or same_translation:
                groups[-1].append(r)
                continue
        groups.append([r])
    return groups


def image_urls(cells):
    """Full URLs of the illustrations in the given cells, the Getty's first."""
    urls = []
    for cell in cells:
        if cell is None:
            continue
        for img in cell.find_all("img"):
            src = img.get("src","")
            if not src:     # an <img> without an address
                continue
            if src.startswith("/"): # paths in the HTML are relative
                src = config.WIKTENAUER_BASE + src
            if src not in urls:     # with rowspan the same cell repeats
                urls.append(src)
    
    # The passage's text is the Getty's, so its own illustration comes first.
    urls.sort(key=lambda url: 0 if "MS_Ludwig" in url else 1)
    return urls



def passage_content(grid, rows, columns):
    """Text, manuscript reference, translation and illustrations of one passage."""

    text_col = columns["text"]
    translation_col = columns["translation"]
    illustrations_col = columns["illustrations"]

    # --- text, reference and translation ---
    text, reference = cell_text(grid[rows[0]][text_col])

    translation = None
    if translation_col is not None:
        translation, _ = cell_text(grid[rows[0]][translation_col])
    if len(rows) > 1:
        text_cell_values = [grid[r_idx][text_col] for r_idx in rows]
        if len(set(text_cell_values)) == 1:  # all text cells equal, then translations must be unified
            if translation_col is not None:
                for r_idx in rows[1:]:
                    part = cell_text(grid[r_idx][translation_col])[0]
                    if part != "":
                        translation += f" {part}"
        else:   # else all cell translations equal, text must be unified
            for r_idx in rows[1:]:
                part = cell_text(grid[r_idx][text_col])[0]
                if part:
                    text += f" {part}"
    
    text = text.strip()
    if translation is not None:
        translation = translation.strip()
        if translation == "":
            translation = None
    
    
    # --- illustration ---
    cells = [grid[r][col] for col in illustrations_col for r in rows]
    illustrations = image_urls(cells)


    return {"text": text, "reference": reference,
            "translation": translation, "illustrations": illustrations}