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
from maestro.parse.fiore import rebuild_grid

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