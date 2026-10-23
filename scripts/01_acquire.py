from maestro.acquire.wiktenauer import download_page, safe_filename
from maestro import config
from pathlib import Path

title = "Fiore de'i Liberi"
folder = Path(config.CORPUS_RAW / "fiore")
destination = folder / (safe_filename(title) + ".html")

if destination.exists():
    print(f"Already present: {destination}")
else:
    print(f"Saved: {download_page(title, folder)}")
