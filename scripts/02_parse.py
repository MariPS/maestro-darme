"""Parse the downloaded Fiore page into corpus/processed/fiore_getty.jsonl, and print checks."""

from collections import Counter
from maestro import config
from maestro.parse import fiore

html_path = config.CORPUS_RAW / "fiore" / "fiore_de_i_liberi.html"
output = config.CORPUS_PROCESSED / "fiore_getty.jsonl"

passages = fiore.parse(html_path)

output.parent.mkdir(parents=True, exist_ok=True)
with open(output, "w", encoding="utf-8") as f:
    for p in passages:
        f.write(p.model_dump_json() + "\n")     # JSONL: one passage per line


# --- compare these numbers with expected numbers ---
folios = {p.folio for p in passages if p.folio}
print(f"{len(passages)} passages -> {output.relative_to(config.ROOT)}")
print(f"  distinct folios:   {len(folios)} ({min(folios)}..{max(folios)})")
print(f"  without folio:     {sum(1 for p in passages if not p.folio)}")
print(f"  with translation:  {sum(1 for p in passages if p.translation_en)}")
print(f"  with illustrations:{sum(1 for p in passages if p.image_urls)}")
print(f"  unique ids:        {len({p.passage_id for p in passages}) == len(passages)}")
print("  passages per section:")
for section, n in Counter(p.section for p in passages).items():
    print(f"    {n:3}  {section}")