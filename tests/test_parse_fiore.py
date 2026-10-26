"""Tests for the Fiore parser, on a miniature copy of the real page.

The grid of tests/fixtures/mini_fiore.html, as rebuild_grid() should return it.
Each position shows which HTML cell occupies it: "1.2" = row 1, third <td> of
that row in the HTML (counting from 0). * = the cell has rowspan="2".

           col 0  col 1  col 2  col 3  col 4  col 5  col 6  col 7
    row 0  0.0    0.1    0.2    0.3    0.4    0.5    0.6    0.7     header (<th>)
    row 1  1.0*   1.1*   1.2*   1.3*   1.4    1.5    1.6    1.7
    row 2  1.0*   1.1*   1.2*   1.3*   2.0    2.1    2.2    2.3     only 4 <td> in the HTML
    row 3  3.0    3.1    3.2    3.3    3.4    3.5    3.6    3.7
    row 4  4.0    4.1    4.2    4.3    4.4    4.5    4.6    4.7

Columns: 0-1 illustrations, 2 Getty translation, 3 Paris translation,
4 Morgan, 5 Getty, 6 Pisani Dossi, 7 Paris.
Row 2 is the trap: its 4 cells belong to columns 4-7, because columns 0-3 are
still taken by the rowspan cells of row 1. So the Getty text of row 2 ("dela
daga...") is cell 2.1 in the HTML, but sits in column 5 of the grid.
"""
from pathlib import Path
from bs4 import BeautifulSoup
from maestro.parse.fiore import rebuild_grid, find_columns, cell_text, normalize_folio, section_title, group_rows, passage_content


FIXTURE = Path(__file__).parent / "fixtures" / "mini_fiore.html"


def load_table():
    return BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "lxml").find("table")


def test_grid_is_rectangular():
    grid = rebuild_grid(load_table())
    assert len(grid) == 5
    assert all((len(row)==8 for row in grid))


def test_rowspan_cell_appears_in_every_row_it_covers():
    grid = rebuild_grid(load_table())
    assert grid[1][2] is grid[2][2]


def test_cells_after_a_rowspan_land_in_the_right_column():
    grid = rebuild_grid(load_table())
    # In the HTML of row 2 this is the second cell, but it belongs to column 5 (Getty)
    assert "dela daga" in grid[2][5].get_text()


def test_rows_not_reached_by_a_rowspan_keep_their_cells():
    grid = rebuild_grid(load_table())
    assert "Morgan text" in grid[3][4].get_text()


def test_columns_are_found_by_header():
    grid = rebuild_grid(load_table())
    assert find_columns(grid[0]) == {"illustrations": [0,1], "text": 5, "translation": 2}


def header(*names):
    """A header row made of <th> cells with the given texts."""
    html = "<table><tr>" + "".join(f"<th>{n}</th>" for n in names) + "</tr></table>"
    return BeautifulSoup(html, "lxml").find("tr").find_all("th")


def test_translation_header_without_the_word_translation():
    # "Seven Swords": the Getty translation header does not say "Translation"
    cols = find_columns(header("Illustrations", "PD by Michael Chidester Getty by Colin Hatcher",
                               "Getty Version (1400s)"))
    assert cols["translation"] == 1
    assert cols["text"] == 2


def test_translation_from_another_manuscript_is_not_the_getty_one():
    # The Latin preface is translated from the Pisani Dossi, not from the Getty
    cols = find_columns(header("Illustrations", "Draft Translation (from the Pisani Dossi)",
                               "Getty Version (1400s)"))
    assert cols["translation"] is None


def test_cell_text_joins_the_initial_and_reads_the_reference():
    grid = rebuild_grid(load_table())
    assert cell_text(grid[1][5]) == ("Queste zinque figure sono le guardie","09r-t")


def test_cell_text_removes_footnotes():
    grid = rebuild_grid(load_table())
    assert cell_text(grid[1][2]) == ("These five figures are the guards of the dagger.", None)


def test_cell_text_turns_line_breaks_into_spaces():
    grid = rebuild_grid(load_table())
    assert cell_text(grid[4][5]) == ("Io son tutta porta di ferro", None)


def test_placeholder_means_empty():
    grid = rebuild_grid(load_table())
    assert cell_text(grid[3][5]) == ("", None)


def test_normalize_folio():
    assert normalize_folio("9r") == "09r"
    assert normalize_folio("32v") == "32v"


def cell(html):
    """A single <td> cell built from an HTML fragment."""
    return BeautifulSoup(f"<table><tr><td>{html}</td></tr></table>", "lxml").find("td")


def test_editorial_marks_are_kept():
    # [!] = "sic", m[e]zi = letter supplied by the transcriber: they stay in the text
    grid = rebuild_grid(load_table())
    assert cell_text(grid[2][5]) == ("dela daga. Voii[!] semo m[e]zi", None)


def test_leading_paragraph_number_is_removed():
    assert cell_text(cell("[10] With the grips that I have on you")) == ("With the grips that I have on you", None)


def test_numbers_inside_the_text_are_kept():
    text = "as follows: [1] strength, [2] speed, [3] knowledge"
    assert cell_text(cell(text)) == (text, None)


def test_translator_insertions_are_kept():
    text = "I am the Fourth [Dagger Remedy] Master"
    assert cell_text(cell(text)) == (text, None)


def table(rows_html):
    """A small <table> built from <tr> rows."""
    return BeautifulSoup(f"<table>{rows_html}</table>", "lxml").find("table")


def test_section_title_is_the_path_of_headings():
    assert section_title(load_table()) == "Dagger, Introduction"


def test_rows_sharing_the_translation_form_one_passage():
    grid = rebuild_grid(load_table())
    assert group_rows(grid, text_col=5, translation_col=2) == [[1, 2], [3], [4]]


def test_rows_sharing_the_getty_text_form_one_passage():
    # one Getty cell covering two rows, each with its own translation
    t = table("<tr><th>Getty Translation</th><th>Getty Version</th></tr>"
              "<tr><td>first part</td><td rowspan='2'>one Getty text</td></tr>"
              "<tr><td>second part</td></tr>")
    assert group_rows(rebuild_grid(t), text_col=1, translation_col=0) == [[1, 2]]


def test_getty_text_without_a_translation_column_is_kept():
    t = table("<tr><th>Illustrations</th><th>Getty Version</th></tr>"
              "<tr><td></td><td>un testo del Getty</td></tr>")
    grid = rebuild_grid(t)
    content = passage_content(grid, [1], find_columns(grid[0]))
    assert content["text"] == "un testo del Getty"
    assert content["translation"] is None


def test_passage_content_with_one_translation_for_two_texts():
    grid = rebuild_grid(load_table())
    content = passage_content(grid, [1, 2], find_columns(grid[0]))
    assert content["text"] == "Queste zinque figure sono le guardie dela daga. Voii[!] semo m[e]zi"
    assert content["reference"] == "09r-t"
    assert content["translation"] == "These five figures are the guards of the dagger."


def test_passage_content_with_one_text_for_two_translations():
    t = table("<tr><th>Getty Translation</th><th>Getty Version</th></tr>"
              "<tr><td>first part</td><td rowspan='2'>one Getty text</td></tr>"
              "<tr><td>second part</td></tr>")
    grid = rebuild_grid(t)
    content = passage_content(grid, [1, 2], find_columns(grid[0]))
    assert content["text"] == "one Getty text"
    assert content["translation"] == "first part second part"


def test_empty_first_translation_leaves_no_space():
    t = table("<tr><th>Getty Translation</th><th>Getty Version</th></tr>"
              "<tr><td></td><td rowspan='2'>one Getty text</td></tr>"
              "<tr><td>second part</td></tr>")
    grid = rebuild_grid(t)
    assert passage_content(grid, [1, 2], find_columns(grid[0]))["translation"] == "second part"


def test_empty_translation_cell_means_no_translation():
    t = table("<tr><th>Getty Translation</th><th>Getty Version</th></tr>"
              "<tr><td></td><td>un testo del Getty</td></tr>")
    grid = rebuild_grid(t)
    assert passage_content(grid, [1], find_columns(grid[0]))["translation"] is None


def test_illustrations_are_listed_once():
    # rows 1-2 share an illustration cell (rowspan=2): its image must appear once
    grid = rebuild_grid(load_table())
    urls = passage_content(grid, [1, 2], find_columns(grid[0]))["illustrations"]
    assert urls == ["https://wiktenauer.com/images/thumb/a/ab/MS_Ludwig_XV_13_09r-a.jpg"
                    "/400px-MS_Ludwig_XV_13_09r-a.jpg"]


def test_getty_illustration_comes_first():
    # row 4 has a Getty image and a Paris one (MS_Latin_11269)
    grid = rebuild_grid(load_table())
    urls = passage_content(grid, [4], find_columns(grid[0]))["illustrations"]
    assert "MS_Ludwig" in urls[0] and "MS_Latin" in urls[1]


def test_getty_illustration_is_moved_first():
    # the Paris image comes first in the table: sorting must move the Getty one ahead
    t = table("<tr><th>Illustrations</th><th>Illustrations</th><th>Getty Version</th></tr>"
              "<tr><td><img src='/images/MS_Latin_11269_31v-c.png'></td>"
              "<td><img src='/images/MS_Ludwig_XV_13_09v-b.jpg'></td><td>testo</td></tr>")
    grid = rebuild_grid(t)
    urls = passage_content(grid, [1], find_columns(grid[0]))["illustrations"]
    assert "MS_Ludwig" in urls[0] and "MS_Latin" in urls[1]