# Development log

Findings and design decisions made while building the project, grouped by topic.
The code shows *what* the project does; this log records *why*, and what turned out
to be different from what I expected.

*Last updated: 2026-10-21*

---

## 1. The data source: Wiktenauer

- The transcriptions come from [Wiktenauer](https://wiktenauer.com), a MediaWiki
  site. The text of *Fior di Battaglia* is on the **author page** ("Fiore de'i
  Liberi"), not on the page of the manuscript, which only holds an index and an image
  gallery.
- Instead of saving the page from a browser, I use the **MediaWiki API**
  (`api.php?action=parse`): it returns only the rendered content (about 1.8 MB of
  HTML for Fiore), without menus, scripts or styles.
- The API also returns the **revision number** of the page (163576 at the time of
  writing). It is saved with the download, so every piece of text can be traced back
  to the exact version it came from.
- Provenance is stored next to each HTML file in a `.meta.json`: title, revision,
  URL and download time. Provenance has to be recorded *at download time*: later it
  is too late.

## 2. Being a polite API client

**Rate limit.** At most one request per second. Without it, a loop over 100 pages
would send requests back to back as fast as the network allows, and each `parse`
request is expensive for the server, which has to render the page. On a site run by
volunteers that is an unfair load, and the server can defend itself with
`429 Too Many Requests` or by blocking the IP address, which would make the download
fail anyway. With the pause, 100 pages take about 100 seconds: a negligible cost for
a one-off download.

The limit is implemented by remembering when the last request was sent
(a module-level variable) and sleeping only for the time still missing, instead of
always sleeping one full second.

**Retries.** Errors are handled differently depending on their kind:

| what happens | example | what to do |
|---|---|---|
| the network does not answer | no connection, timeout | retry |
| the server answers with an error code | 429, 500 | retry |
| the server answers `200`, but the JSON contains `"error"` | the page does not exist | **stop immediately**: retrying cannot help |

Retries wait longer and longer (2, then 4 seconds: *exponential backoff*), so as not
to hammer a server that is already in trouble. There is no point in waiting after the
**last** attempt: removing that wait brought a total network failure from 14 to
6 seconds.

## 3. The structure of the HTML

Explored with `scripts/explore_html.py` before writing any parsing code.

- The page contains **31 tables**. The transcription is in the **27 tables with
  `class="master"`**, one per section of the treatise (prefaces, grappling, dagger,
  sword, axe, spear, mounted combat...). The others are service tables (author
  infobox, licences, navigation).
- Each `master` table has **8 columns** that place several manuscripts side by side
  (San Daniele, Morgan, Getty, Pisani Dossi, Paris) next to English translations.

**Where things are, across all 27 tables:**

| what | column | in how many tables |
|---|---|---|
| Getty manuscript text ("Getty Version") | 5 | 27 of 27 |
| English translation "from the Getty" | 2 | 24 |
| | 1 | 1 (the first Italian preface) |
| | absent | 2 (Latin and second Italian preface, not in the Getty) |
| "Illustrations" columns | two of them | 23 |
| | one | 4 |

The translation moves from column 1 to column 2 because most tables have **two**
illustration columns. A parser reading "column 1" would silently take an
illustration instead of a translation in 24 tables out of 27.

> **Rule 1: find columns by their header, never by their number.** Even for the
> Getty text, which is always in column 5 today: if a manuscript were added to the
> page, the number would change, the header would not.

**Rows do not all have the same number of cells.** In table 1, the illustration in
the first data row has `rowspan=4`: it covers that row and the three below it. Those
rows therefore have **7 cells instead of 8** in the HTML, and every cell slides one
place to the left:

```
               col 0       col 1     col 2     col 3      col 4    col 5   col 6   col 7
Row 1 (HTML):  cell 0      cell 1    cell 2    cell 3     cell 4   cell 5  cell 6  cell 7
               [illustr.   transl.   transl.   San        Morgan   GETTY   Pisani  Paris
                rowspan=4] Getty     Morgan    Daniele                     Dossi
Row 2 (HTML):  (taken)     cell 0    cell 1    cell 2     cell 3   cell 4  cell 5  cell 6
```

In row 2 the Getty text is in **cell 4**, not cell 5. Reading "cell 5 of every row"
raises no error: in some rows it takes the right text, in others the text of another
manuscript or an empty cell. And it does not happen everywhere (in table 7 the first
rows all have 8 cells), which makes the bug easy to miss.

> **Rule 2: rebuild the full grid first**, placing each cell with `rowspan` in every
> row it covers, and only then read the columns.

## 4. Extracting the text

BeautifulSoup does not see the text of a cell as one sentence, but as a list of
pieces, one for each stretch of text between two tags. The first word of a passage
often starts with a decorated capital in its own tag, `<b>Q</b>ueste zinque figure…`,
so `'Q'` and `'ueste…'` are two separate pieces. `get_text(separator)` joins them
with the separator in between:

| how | result | problem |
|---|---|---|
| `get_text(" ", strip=True)` | `[ 9r-t ] Q ueste zinque…` | the space ends up **inside** the word |
| `get_text("", strip=True)` | `[9r-t]Queste zinque…` | the word is right, but `strip` also deletes real spaces at tag boundaries |
| `get_text("")` | `[9r-t] Queste zinque…` | correct; only extra spaces and line breaks are left to clean |

The plan for the parser: `get_text("")`, then collapse whitespace, and insert a line
break where the HTML really breaks (`<br>`, `<p>`), otherwise two paragraphs would be
glued together.

The same cell shows two more things the parser will have to handle:
- **`[9r-t]`** is the manuscript reference: folio 9 recto, figure "t". This is where
  each passage gets its folio.
- Wiktenauer inserts **footnote markers** (`[132]`) inside the text. They are not part
  of the manuscript and must be removed.

## Next steps

1. Define the shape of a passage (original text, translation, folio, provenance) as
   a validated data model.
2. Write the parser for the Getty text, applying the two rules above and the text
   cleaning plan: rebuild the grid, find columns by header, extract with
   `get_text("")`, read the folio from `[9r-t]`, remove footnote markers.
