"""
Parser for Fiore dei Liberi, "Fior di Battaglia", Getty manuscript (MS Ludwig XV 13).
"""
from bs4 import BeautifulSoup

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
