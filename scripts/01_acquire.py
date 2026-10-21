from maestro.acquire.wiktenauer import download_page, safe_filename
from pathlib import Path

title = "Fiore de'i Liberi"
folder = Path("corpus/raw/fiore")        # relative path: works when run from the project root
destination = folder / (safe_filename(title) + ".html")

if destination.exists():
    print(f"Already present: {destination}")
else:
    print(f"Saved: {download_page(title, folder)}")
