"""
Downloader per Wiktenauer, tramite la MediaWiki API che:
- restituisce solo il contenuto della pagina (niente menu, script, CSS);
- mi dice il numero di revisione, quindi posso tracciare la versione scaricata per eventuali aggiornamenti alla pagina.

L'endpoint è action=parse che restituisce l'HTML già "renderizzato"
Documentazione: https://www.mediawiki.org/wiki/API:Parsing_wikitext 
"""
from datetime import datetime, timezone
import time
import json
import re
from pathlib import Path
import requests

BASE = "https://wiktenauer.com"
API = "https://wiktenauer.com/api.php"
USER_AGENT = "MaestroDArme/0.1 (progetto di studio HEMA)"
SECONDI_TRA_RICHIESTE = 1.0

_ultima_richiesta = 0.0   # quando è partita l'ultima richiesta (0 = mai)

def chiama_api(params: dict, tentativi: int = 3) -> dict:
    """Manda una richiesta all'API di Wiktenauer e restituisce la risposta come dizionario.
    Chiama l'API rispettando il rate limit, e riprova in caso di errori di rete o del server.
    """

    params = {**params, "format":"json", "formatversion":"2"} # aggiungo i parametri fissi
    for tentativo in range(1, tentativi + 1):   # 1, 2, 3
        _aspetta_turno()
        try:
            r = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
            if r.status_code == 200:
                dati = r.json()
                if "error" in dati:
                    # errore "logico" (es. pagina inesistente): riprovare non serve
                    raise RuntimeError(f"Errore API: {dati['error'].get('info')}")
                return dati     # successo: il return esce dal ciclo
            print(f"    HTTP {r.status_code}, tentativo {tentativo}/{tentativi}")
        except requests.RequestException as e:
            print(f"    errore di rete ({e}), tentativo {tentativo}/{tentativi}")
        if tentativo < tentativi:
            time.sleep(2 ** tentativo)  # 2, 4 secondi (è inutile aspettare gli ultimi 8 secondi se non c'è un altro tentativc dopo)
    
    # se arrivo qui tutti i tentativi sono falliti
    raise RuntimeError(f"Impossibile completare la richiesta dopo {tentativi} tentativi.")



def nome_file(titolo: str) -> str:
    """"Fiore de'i Liberi" -> "fiore_de_i_liberi": tutto ciò che non è lettera o cifra diventa _"""
    return re.sub(r"[^a-z0-9]+", "_", titolo.lower()).strip("_")


def scarica_pagina(titolo: str, cartella: Path):
    """
    Scarica una pagina e la salva come .html insieme al .meta.json.

    Il file .meta.json contiene la provenienza: titolo, URL, revisione,
    data di download.
    """

    cartella.mkdir(parents=True,exist_ok=True)
    print(f"Scarico '{titolo}'...")
    pagina = chiama_api({"action":"parse","page":titolo,"prop":"text|revid"})["parse"]

    base = cartella / nome_file(titolo)            # es. corpus/raw/fiore/fiore_de_i_liberi
    html_path = base.with_suffix(".html")
    html_path.write_text(pagina["text"], encoding="utf-8")

    meta = {
        "title": pagina["title"],
        "revid": pagina["revid"],
        "url": f"{BASE}/wiki/{pagina['title'].replace(' ', '_')}",
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    base.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return html_path
    

def _aspetta_turno():
    """Aspetta quanto basta perché fra due richieste passino almeno SECONDI_TRA_RICHIESTE."""

    global _ultima_richiesta                      # voglio MODIFICARE la variabile del modulo
    trascorso = time.time() - _ultima_richiesta # secondi passati dall'ultima richiesta
    if trascorso < SECONDI_TRA_RICHIESTE:
        time.sleep(SECONDI_TRA_RICHIESTE - trascorso) # aspetto solo la differenza
    _ultima_richiesta = time.time() # segno l'ora di questa richiesta
