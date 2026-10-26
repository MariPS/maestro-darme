<h1 align="center">
  <img src="docs/images/banner.jpg" alt="Maestro d'Arme" width="100%">
</h1>

<p align="center"><i><a href="README.md">English</a> · Italiano</i></p>

**Maestro d'Arme** è un assistente per interrogare in linguaggio naturale i
**trattati storici di scherma europea** (HEMA), di maestri e tradizioni diverse, con
risposte ancorate ai testi originali e citazioni al foglio del manoscritto.

> *"Come si para un fendente secondo Fiore dei Liberi?"* → il passaggio esatto del
> trattato, in italiano del Quattrocento, con traduzione e riferimento al foglio
> (es. *Fior di Battaglia, MS Ludwig XV 13, f. 23r*).
>
> *"Che differenza c'è fra la posta di donna di Fiore e il vom Tag di Liechtenauer?"*
> → i passaggi dei due maestri affiancati, ciascuno con la sua citazione, senza
> fondere le due tradizioni in una sola.

I trattati si aggiungono uno alla volta: il primo è *Fior di Battaglia* di Fiore dei
Liberi (tradizione italiana, ~1410); seguiranno lo Zettel di Liechtenauer con le sue
glosse e la *Gründtliche Beschreibung* di Joachim Meyer (tradizione tedesca).

**Stato**: in sviluppo. Sono pronti l'acquisizione dei testi e il parser per il primo
trattato: *Fior di Battaglia* diventa 350 passaggi strutturati. Seguiranno
l'indicizzazione e la ricerca; il resto della pipeline è descritto nella
[roadmap](#roadmap).

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

## Cosa funziona oggi

### Acquisizione dei testi

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

### Parsing

Su Wiktenauer *Fior di Battaglia* è un insieme di tabelle che affiancano più
manoscritti. Il modulo `maestro.parse.fiore` ne estrae il **manoscritto Getty**
(MS Ludwig XV 13), un passaggio validato per ogni gioco:

- ricostruisce ogni tabella come una griglia completa, perché le celle che coprono
  più righe (`rowspan`) spostano le altre nell'HTML;
- trova le colonne per nome dell'intestazione e non per posizione, che cambia da
  tabella a tabella;
- pulisce il testo conservando i segni editoriali del trascrittore (`[!]` per *sic*,
  `m[e]zo` per una lettera integrata dall'editore);
- assegna a ogni passaggio il suo foglio e un identificativo stabile basato sul
  riferimento del manoscritto stesso, come `fiore_getty:23r-a` (foglio 23 recto,
  figura a).

Il ragionamento dietro ogni scelta, e ciò che i dati veri hanno rivelato lungo la
strada, è nel [diario di sviluppo](docs/DEVLOG.md).

## Installazione

Requisiti: Python 3.11 o successivo.

```bash
git clone https://github.com/MariPS/maestro-darme.git
cd maestro-darme
conda create -n maestro-darme python=3.11 -y
conda activate maestro-darme
pip install -e .
```

Per lavorare sul codice, installa anche gli strumenti di sviluppo e lancia i test:

```bash
pip install -e ".[dev]"
pytest
```

I test girano su un piccolo file HTML in `tests/fixtures/`: non servono né internet
né il corpus scaricato.

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

Poi analizzala:

```bash
python scripts/02_parse.py
```

I passaggi vengono salvati in `corpus/processed/fiore_getty.jsonl`, uno per riga, e lo
script stampa un riepilogo per controllare il risultato (passaggi, fogli, traduzioni,
illustrazioni, passaggi per sezione). Un passaggio è fatto così (testi accorciati):

```json
{
  "passage_id": "fiore_getty:23r-a",
  "treatise_id": "fiore_getty",
  "treatise_title": "Fior di Battaglia (MS Ludwig XV 13)",
  "author": "Fiore de'i Liberi",
  "year_circa": 1410,
  "section": "Sword in Two Hands, Introduction",
  "folio": "23r",
  "text": "· Colpi Fendenti · ¶ Noii semo fendenti & in l'arte façemo questione d...",
  "language": "ita-arc",
  "translation_en": "Downward Blows We are downward blows and we dispute By cleav...",
  "image_urls": ["https://wiktenauer.com/images/thumb/e/e1/MS_Ludwig_XV_13_23r..."],
  "source_url": "https://wiktenauer.com/wiki/Fiore_de'i_Liberi",
  "source_license": "CC-BY-SA-4.0",
  "source_revision": 163576
}
```

## Struttura del repository

```
maestro-darme/
├── pyproject.toml
├── src/maestro/
│   ├── config.py             # percorsi e impostazioni usati da più moduli
│   ├── acquire/
│   │   └── wiktenauer.py     # client per la MediaWiki API di Wiktenauer
│   └── parse/
│       ├── schemas.py        # TreatisePassage: la forma validata di un passaggio
│       └── fiore.py          # parser per Fiore dei Liberi (manoscritto Getty)
├── scripts/
│   ├── 01_acquire.py         # scarica i trattati in corpus/raw/
│   ├── 02_parse.py           # li analizza in corpus/processed/*.jsonl
│   └── explore_html.py       # riassume le tabelle di una pagina scaricata
├── tests/
│   ├── fixtures/
│   │   ├── mini_fiore.html       # una miniatura della pagina vera, con tutte le sue trappole
│   │   └── mini_fiore.meta.json  # il suo file di provenienza
│   └── test_parse_fiore.py
├── docs/
│   ├── DEVLOG.md             # scoperte e scelte di progetto (in inglese)
│   └── images/               # banner, logo e immagine di anteprima
└── corpus/                   # generato dagli script, non versionato
```

Per vedere com'è organizzato l'HTML scaricato, prima di analizzarlo:

```bash
python scripts/explore_html.py corpus/raw/fiore/fiore_de_i_liberi.html      # tutte le tabelle
python scripts/explore_html.py corpus/raw/fiore/fiore_de_i_liberi.html 1    # una tabella, cella per cella
```

Cosa ha rivelato questa esplorazione, e perché determina il parser, è descritto nel
[diario di sviluppo](docs/DEVLOG.md).

## Roadmap

- [x] Acquisizione dei testi da Wiktenauer, con provenienza e revisione
- [x] Parsing delle trascrizioni in passaggi strutturati (testo originale, traduzione, foglio)
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

## Immagini

Il banner, il logo (`docs/images/logo.png`) e l'immagine di anteprima usano il
*Segno* di Fiore dei Liberi, *Fior di Battaglia*, Los Angeles, J. Paul Getty Museum,
MS Ludwig XV 13, f. 32r: il maestro con le sette spade e i quattro animali delle
virtù (avvedutezza, prestezza, ardimento, fortezza), scelto come emblema del maestro
d'arme in generale, di qualunque tradizione. Immagine digitale per gentile concessione dell'Open Content Program del
Getty, tramite [Wiktenauer](https://wiktenauer.com).

Il motto sotto il titolo, *ex verbis magistrorum*, in latino significa "dalle parole
dei maestri": è il principio del progetto, in cui ogni risposta nasce dai testi dei
maestri stessi.

Il titolo è scritto con il carattere Hershey *Gothic Italian*. I caratteri Hershey
sono stati creati da A. V. Hershey presso lo U. S. National Bureau of Standards; il
formato dei dati è stato creato da James Hurt, Cognition, Inc.
