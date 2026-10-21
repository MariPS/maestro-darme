# Maestro d'Arme

*[English](README.md) · Italiano*

Assistente per interrogare in linguaggio naturale i **trattati storici di scherma
europea** (HEMA), con risposte ancorate al testo originale e citazioni al foglio
del manoscritto.

> *"Come si para un fendente secondo Fiore dei Liberi?"* → il passaggio esatto del
> trattato, in italiano del Quattrocento, con traduzione e riferimento al foglio
> (es. *Fior di Battaglia, MS Ludwig XV 13, f. 23r*).

**Stato**: in sviluppo. È pronto il modulo di acquisizione dei testi; il resto
della pipeline è descritto nella [roadmap](#roadmap).

---

## Il problema

I trattati di scherma storica sono un dominio difficile, per le persone e per i
modelli linguistici generici:

- **lingua arcaica e specialistica**: italiano del XV secolo, alto tedesco antico,
  latino, con grafie che cambiano anche all'interno dello stesso testo;
- **molte opere autonome**: ogni maestro ha il suo lessico e il suo sistema di guardie;
- **interpretazione contestata**: c'è il testo originale, e ci sono le
  interpretazioni moderne, che vanno tenute distinte.

Un LLM generico risponde in modo plausibile ma senza fonti verificabili, e tende a
mescolare tradizioni diverse. L'obiettivo di questo progetto è il contrario: **il
testo originale è la fonte di verità**, e ogni risposta deve poter essere
ricondotta a un passaggio preciso.

## Architettura prevista

Il sistema è pensato su due livelli:

1. **Biblioteca (RAG sui trattati)**: i testi vengono suddivisi in passaggi,
   indicizzati con una ricerca ibrida (semantica multilingue + lessicale BM25) e
   restituiti con la loro citazione. È la fonte di verità.
2. **Wiki di sintesi**: le sintesi di valore (per esempio il confronto fra due
   guardie) vengono salvate come pagine Markdown che citano i passaggi originali,
   con controlli periodici che le citazioni siano ancora valide.

Tutto gira in locale, con modelli open source.

## Cosa funziona oggi: acquisizione dei testi

I testi provengono da [Wiktenauer](https://wiktenauer.com), la principale
biblioteca digitale di trattati HEMA. Il modulo `maestro.acquire.wiktenauer`:

- usa la **MediaWiki API** (`action=parse`) invece di fare scraping delle pagine:
  restituisce solo il contenuto, senza menu e script;
- registra la **revisione** della pagina scaricata, così è sempre possibile sapere
  quale versione del testo è stata usata;
- invia **al massimo una richiesta al secondo**, con uno User-Agent che identifica
  il progetto: il sito è gestito da volontari;
- **riprova** fino a 3 volte in caso di errori di rete o del server, con attese
  crescenti; non ritenta gli errori dell'API (es. pagina inesistente), perché
  riprovare non cambierebbe il risultato.

## Installazione

Requisiti: Python 3.11 o successivo.

```bash
git clone https://github.com/MariPS/maestro-darme.git
cd maestro-darme
conda create -n maestro-darme python=3.11 -y
conda activate maestro-darme
pip install -e .
```

## Uso

Dalla cartella principale del progetto:

```bash
python scripts/01_acquire.py
```

Lo script scarica la pagina di Fiore dei Liberi (*Fior di Battaglia*, ~1410) in
`corpus/raw/fiore/`. Se il file esiste già, non lo riscarica.

Accanto all'HTML viene salvato un file `.meta.json` con la provenienza:

```json
{
  "title": "Fiore de'i Liberi",
  "revid": 163576,
  "url": "https://wiktenauer.com/wiki/Fiore_de'i_Liberi",
  "downloaded_at": "2026-10-21T18:16:22+00:00"
}
```

## Struttura del repository

```
maestro-darme/
├── pyproject.toml
├── src/maestro/
│   └── acquire/
│       └── wiktenauer.py     # client per la MediaWiki API di Wiktenauer
├── scripts/
│   └── 01_acquire.py         # scarica i trattati in corpus/raw/
└── corpus/                   # generato dagli script, non versionato
```

## Roadmap

- [x] Acquisizione dei testi da Wiktenauer, con provenienza e revisione
- [ ] Parsing delle trascrizioni in passaggi strutturati (testo originale, traduzione, foglio)
- [ ] Indicizzazione con embedding multilingue
- [ ] Ricerca ibrida semantica + BM25, con normalizzazione dell'ortografia antica
- [ ] Valutazione su un insieme di domande con fonti attese (recall@k, MRR)
- [ ] Risposte generate da un LLM locale, con verifica automatica delle citazioni
- [ ] Wiki di sintesi con controlli di manutenzione
- [ ] Interfaccia web

Primo trattato: *Fior di Battaglia* di Fiore dei Liberi (manoscritto Getty).
Previsti in seguito: Joachim Meyer (1570) e lo Zettel di Liechtenauer con le sue glosse.

## Fonti e licenze dei testi

I trattati originali sono di pubblico dominio. Le **trascrizioni** e le
**traduzioni** sono di [Wiktenauer](https://wiktenauer.com) e dei loro autori, e
sono generalmente distribuite con licenza **CC-BY-SA 4.0**.

Il corpus **non è incluso** in questo repository: si scarica con lo script, e ogni
file conserva URL e revisione della fonte.
