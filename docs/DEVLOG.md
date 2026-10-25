# Development log

Findings and design decisions made while building the project, grouped by topic.
The code shows *what* the project does; this log records *why*, and what turned out
to be different from what I expected.

*Last updated: 2026-10-25*

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

## 5. The shape of a passage

Before writing any parser, I defined what a passage *is*: a Pydantic model,
`TreatisePassage` (`src/maestro/parse/schemas.py`). Every parser, for every treatise,
will have to produce exactly this shape, and the model checks the data as soon as a
passage is created.

**Every field answers a need.** Identity (`passage_id`, `treatise`, `author`, `year`) for
citations; position (`section`, `folio`); content (`text`, `language`,
`translation_en`, `image_urls`); provenance (`source_url`, `source_license`,
`source_revision`, taken from the `.meta.json`). More fields might be added later when needed.

**Stable identifiers.** `passage_id` is built from the manuscript's own reference:
`fiore_getty:09r-t` is folio 9 recto, figure "t". A running counter (1, 2, 3...)
would be simpler, but it shifts whenever the parser changes: drop one passage and
every later id moves by one. Since these ids will be cited by other files, they must
depend on *what* a passage is, not on the order in which it was found.

**Required or optional?** The rule: a field is optional if there is a real passage,
in this or another treatise, where that information is missing.

- `text` is required: a passage without text is not a passage.
- `translation_en` is optional: it is missing in 2 of the 27 transcription tables.
- `folio` is optional. Of the 352 Getty cells with text, **306** contain a marker such
  as `[9r-t]` and **46** (about one in eight) do not: a marker appears at the start of
  a folio, and the paragraphs that continue it do not repeat it. The parser will try
  to recover the folio in other ways (the file name of the Getty illustration,
  `MS_Ludwig_XV_13_09r-a.jpg`, or the folio of the previous passage), but the schema
  describes what *can* happen, not what I hope will happen: with a required `folio`,
  the first passage without one would stop everything with a validation error. Other
  treatises are not even cited by folio: Liechtenauer's Zettel is cited by verse,
  printed books often by chapter.
- Missing values are `None`, not an empty string: `None` says explicitly "unknown",
  while `""` looks like a real value.

**Storage: JSONL**, one passage per line. `model_dump_json()` writes a line;
`model_validate_json()` reads it back and *re-validates* it, so a corrupted or
hand-edited file is caught when it is loaded, not when the data is used.

## 6. Shared configuration

`src/maestro/config.py` was created only when a second module needed the same
information as the downloader. The parser has to know where the pages were saved,
and the site's base address: image paths in the HTML are relative
(`/images/thumb/...`) and become full URLs only with `https://wiktenauer.com`.
Settings used by a single module (the API address, the User-Agent, the rate limit)
stay in that module.

Paths are computed from the location of `config.py` itself
(`Path(__file__).resolve().parents[2]` is the project root), not from the current
folder. With the relative path used before (`corpus/raw/fiore`), launching the
download script from inside `scripts/` would have looked for, and saved, the files
in `scripts/corpus/...`.

## 7. Rebuilding the table grid

`rebuild_grid()` (`src/maestro/parse/fiore.py`) turns an HTML table into a full
matrix, so that "column 5" means column 5 in every row. It keeps a dictionary
`(row, column) -> cell`: for each cell of the HTML it looks for the first free column
in its row, then "stamps" the cell on every position it covers (`rowspan` rows ×
`colspan` columns). The same cell object therefore appears in every row it covers,
which will be useful to group the rows that share a translation.

On the real page, table 1 becomes a 44 × 8 grid with no empty positions, and row 2,
column 5 holds the Getty text (`¶ Anchora volse savere tempere…`) that the raw HTML
had put in cell 4.

**Testing on a miniature.** The real page is 1.8 MB and is not in the repository, so
the parser is tested on `tests/fixtures/mini_fiore.html`: a 5-row table that
reproduces every trap found so far (rowspan, two illustration columns, the
translation in column 2, a decorated initial, footnotes, a folio marker, a play
missing from the Getty, an illustration from another manuscript). The grid the
fixture should produce is drawn at the top of `tests/test_parse_fiore.py`.

**What the "first free column" step does**, checked by removing it:

- rows below a rowspan cell are corrupted: their cells start again from column 0 and
  overwrite the positions covered from above (`grid[2][2]` becomes an empty cell
  instead of the translation), while columns 4-7 of that row stay empty (`None`);
- rows that no rowspan reaches are unaffected (row 3 keeps its cells).

The tests are split accordingly, one behaviour per test, including a *control* test
on row 3 that passes even without the fix. A test function stops at its first
failing assertion, so two checks in the same function would hide each other.

## 8. Finding the columns by their header

`find_columns()` reads the header row of the grid and returns where the three things
the parser needs are:

| what | recognised by its header |
|---|---|
| Getty text | contains `getty version` |
| translation "from the Getty" | contains `translation` **and** `getty` |
| illustrations | contains `illustration` (one or two columns) |

The order of the checks matters: "Getty Version" also contains "getty", so it must be
recognised as the text column *before* any rule about translations is tried.

**The rule was checked on the real page, not only on the test fixture.** A small
script ran it on all 27 transcription tables and counted the results: the Getty text
was in column 5 in 27 tables, as expected, but the translation was missing in **3**
tables, while the exploration (section 3) had found only 2 without it. Printing the
headers of those three tables showed two different situations:

- **Latin Preface** and **Second Italian Preface**: the translation is made from the
  Pisani Dossi manuscript ("Translation (from the Pisani Dossi)"), and the Getty does
  not contain these prefaces. Here "no Getty translation" is the *right* answer.
- **Seven Swords**: the Getty translation is there, but its header is
  *"PD by Michael Chidester Getty by Colin Hatcher"*, without the word
  "Translation". Here the answer was *wrong*: the parser would have silently lost the
  translations of a whole section.

The fix keeps the precise rule as the main one and adds a **fallback**: only when no
column matches it, the first other column whose header mentions the Getty is taken
as the translation. A single, looser rule ("contains getty") would have given the same
numbers, but it would have hidden the exception: with an explicit fallback, the code
says that an exception exists and why.

After the fix the counts match the exploration: translation in column 2 in 24 tables,
in column 1 in 1, absent in 2.

Two tests pin this down: one for the Seven Swords header, and one checking that a
translation made from another manuscript is *not* taken as the Getty one, so that the
fallback cannot become too generous in the future.

> The fixture tests say whether the function does what I meant; the check on the
> real data says whether what I meant is right. Only the second one found this bug.

## 9. Cleaning the text of a cell

`cell_text()` turns a table cell into two things: the **clean text**, and the
**manuscript reference** found in it, if any (`[9r-t]` becomes `"09r-t"`).

**What is left between square brackets, and why it stays.**

| what | where | example | meaning | decision |
|---|---|---|---|---|
| `[!]` (26 times) | Getty text | `scarmidori[!]` | *sic*: the manuscript really says this, even if it looks wrong | **keep** |
| a letter in brackets | Getty text | `m[e]zo`, `que[ll]` | a letter the 15th-century scribe left out, supplied by the modern transcriber | **keep** |
| words in brackets | translations | `the Fourth [Dagger Remedy] Master` | words added by the translator to make the meaning clear | **keep** |
| a number at the start | translations | `[10] With the grips…` | the translator's numbering of the passages | **remove** |
| a number inside the text | translations | `[1] strength, [2] speed, [3] knowledge` | part of the content | **keep** |

The first two are the transcriber's *critical apparatus*: they tell the reader what
the manuscript says and what has been reconstructed, so the text that the system shows
and quotes keeps them.

The numbers looked like noise at first, but where they appear changes everything. At
the start of a translation they only number the passages, which already have their
own stable id, so they go. Inside the text they are content: the eight qualities a
grappler needs are listed as `[1]`...`[8]`, and `[3]` appears twice to tie an
explanation ("by which I mean...") to its item. Hence the rule: **a number in brackets
is removed only when it opens the text**.

Each decision is pinned down by a test, including the "keep" ones.

## Next steps

The parser for the Getty text, continued:

1. Group rows into passages (rows that share a translation cell), collect the
   illustrations, recover missing folios, build stable ids.
2. A `parse()` function and a script that writes
   `corpus/processed/fiore_getty.jsonl`, with summary statistics to check the result.
