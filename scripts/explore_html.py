"""Summarise the structure of an HTML file before writing a parser for it.

Usage:
    python scripts/explore_html.py <file.html>        # overview of all tables
    python scripts/explore_html.py <file.html> 1      # detail of table number 1
"""

from bs4 import BeautifulSoup
import sys


def rows(table):
    """The <tr> rows of a table (lxml wraps them in a <tbody>)."""
    body = table.find("tbody") or table
    return body.find_all("tr", recursive=False)


def overview(soup):
    """Print one "identity card" line per table, to spot the ones that hold the text."""

    for i, table in enumerate(soup.find_all("table")):
        table_rows = rows(table)

        # Number of columns = the number of cells in the fullest row.
        # Rows do not all have the same number of cells: a cell with rowspan reaches down
        # into the rows below and takes their place. default=0 avoids an error on a table with no rows.
        columns = max((len(r.find_all(["td", "th"], recursive=False)) for r in table_rows), default=0)

        # How much text the table holds: tells transcriptions (tens of thousands of
        # characters) apart from service tables such as menus and licences.
        characters = len(table.get_text(" ", strip=True))

        # The heading that comes before the table, searched backwards in the document.
        heading = table.find_previous(["h2", "h3", "h4"])
        heading = heading.get_text(" ", strip=True)[:30] if heading else "-"

        print(f"[{i:2}] class={table.get('class')} rows={len(table_rows)} columns={columns} "
              f"characters={characters}  (under heading: {heading})")


def detail(soup, n):
    """Print the header and the first data rows of table number n, cell by cell."""
    tables = soup.find_all("table")
    if n >= len(tables):
        print(f"There are only {len(tables)} tables (0-{len(tables) - 1}).")
        return
    table_rows = rows(tables[n])

    print("=== Header ===")
    for c, cell in enumerate(table_rows[0].find_all(["td", "th"], recursive=False)):
        print(f"  col {c}: {cell.get_text(' ', strip=True)[:70]}")

    for r, row in enumerate(table_rows[1:4], start=1):
        print(f"\n=== Row {r} ===")
        for c, cell in enumerate(row.find_all(["td", "th"], recursive=False)):
            span = f" rowspan={cell.get('rowspan')}" if cell.get("rowspan") else ""
            print(f"  cell {c}{span}: {cell.get_text(' ', strip=True)[:90]}")
            

def main():
    sys.stdout.reconfigure(encoding="utf-8")   # the Windows console is not UTF-8
    # sys.argv holds the command-line arguments: [script name, file name, ...]
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    with open(sys.argv[1], encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")   # the whole document as a tree of elements
    if len(sys.argv) == 2:
        overview(soup)
    else:
        detail(soup, int(sys.argv[2]))


if __name__ == "__main__":
    main()
