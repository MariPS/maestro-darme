from maestro.acquire.wiktenauer import scarica_pagina, nome_file
from pathlib import Path

titolo = "Fiore de'i Liberi"
cartella = Path("corpus/raw/fiore")        # percorso relativo: vale se lanci dalla radice
destinazione = cartella / (nome_file(titolo) + ".html")

if destinazione.exists():
    print(f"Già presente: {destinazione}")
else:
    print(f"Salvato: {scarica_pagina(titolo, cartella)}")
