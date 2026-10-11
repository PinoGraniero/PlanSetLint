# PlanSetLint 0.2 · Prima prova

Questa versione offre una finestra in italiano. Selezioni i PDF e avvii il controllo; i documenti vengono letti sul tuo computer. Non vengono caricati su Internet né modificati.

È ancora un prototipo: la prima prova serve a verificare l'utilità dei controlli nel tuo studio. Non sostituisce la verifica tecnica degli elaborati.

## 1. Preparare il computer

Scarica il repository da GitHub con **Code → Download ZIP** ed estrai l'intera cartella. Non avviare il programma dall'interno dello ZIP. Mantieni la cartella in una posizione in cui puoi scrivere.

Serve **Python 3.10 o successivo con Tkinter**. Se Python non è installato, usa l'installer ufficiale da [python.org](https://www.python.org/downloads/). Su Windows abilita l'opzione per aggiungere Python al PATH; il launcher `py` può già essere disponibile. Su macOS usa una distribuzione con Tkinter: gli installer ufficiali di Python lo includono normalmente.

- **Windows:** fai doppio clic su `Avvia-PlanSetLint.bat`.
- **macOS:** fai doppio clic su `Avvia-PlanSetLint.command`.
- **Linux:** installa Python, venv e Tkinter con il gestore di pacchetti della tua distribuzione, poi esegui `python3 launch.py`.

Il primo avvio crea una cartella `.venv` e installa il programma e le dipendenze da PyPI: serve Internet. Gli avvii successivi e i controlli dei PDF funzionano senza connessione.

Se su macOS il file `.command` non è eseguibile, apri Terminale nella cartella estratta ed esegui `python3 launch.py`. Puoi rendere il launcher eseguibile con `chmod +x Avvia-PlanSetLint.command`. Se macOS blocca un file scaricato, valuta il messaggio nelle impostazioni di sistema e segui il normale percorso di apertura previsto da macOS; non occorre disattivare le protezioni.

Questa versione non contiene ancora un'app `.app` o un eseguibile Windows autonomo. L'installazione sul tuo specifico Mac o PC va verificata nella prima prova.

## 2. Provare senza documenti reali

1. Premi **Crea fascicolo dimostrativo** e scegli dove creare la nuova cartella `PlanSetLint-demo`.
2. Il programma seleziona il fascicolo `da_verificare` e il relativo `elenco.csv`.
3. Premi **Avvia controllo**: devono comparire **5 anomalie** (duplicato, revisione diversa, formato diverso, tavola non prevista e tavola mancante).
4. Per una prova senza anomalie scegli la cartella `corretto` e il suo `elenco.csv`. Avvia nuovamente il controllo: sono attesi **2 PDF e nessuna anomalia**.

I PDF dimostrativi sono fogli vuoti sintetici: servono a provare nomi, revisioni, dimensioni e inventario, non il contenuto grafico. La demo non sovrascrive una cartella già esistente.

## 3. Provare un tuo fascicolo

Seleziona una cartella con un piccolo gruppo di tavole PDF. Lo schema iniziale è:

```
A-001_Pianta_R01.pdf
A-002_Prospetto_R02.pdf
```

Puoi scegliere o scrivere uno schema diverso, usando una sola volta ciascuno dei tre campi:

| Campo | Significato |
|---|---|
| `{drawing}` | Numero o codice della tavola |
| `{title}` | Titolo dell'elaborato |
| `{revision}` | Revisione, numerica o alfabetica |

Esempi di schemi:

```
Tavola_{drawing}_{title}_Rev{revision}.pdf
{drawing} - {title} - rev{revision}.pdf
```

I campi devono essere separati da caratteri riconoscibili, coerenti con i nomi reali. Se un separatore compare anche dentro un codice, controlla la lettura nella scheda **PDF esaminati**: il programma non può ricostruire con certezza una convenzione ambigua. Ad esempio non usare underscore per separare i campi se anche il codice tavola ne contiene.

Il titolo non viene confrontato con il cartiglio; numero e revisione sono letti dal nome del file. Maiuscole e minuscole non distinguono i codici. `A-1` e `A-001` restano codici diversi; revisioni `1` e `01` sono equivalenti. Revisioni alfabetiche come `A` e `B` sono ammesse.

Salva le impostazioni con **Salva profilo** e riutilizzale con **Carica profilo**. Il profilo non contiene i documenti né i percorsi della cartella.

## 4. Elenco atteso delle tavole

Senza elenco il programma controlla nomi, duplicati, leggibilità e numero di pagine. Per stabilire cosa manca e quale revisione o formato è previsto, carica un CSV con queste intestazioni esatte:

```csv
drawing,revision,paper
A-001,01,A3
A-002,02,420x900
A-003,A,
```

- `drawing`: codice atteso della tavola.
- `revision`: revisione attesa.
- `paper`: A0, A1, A2, A3, A4 oppure dimensioni in millimetri, ad esempio `420x900`.
- Un campo `paper` vuoto salta il confronto del formato per quella tavola.

Sono accettati CSV UTF-8 con virgole o punto e virgola. Per dimensioni decimali usa il punto, ad esempio `420.5x900`. Puoi creare il CSV con un editor di testo o esportarlo da un foglio di calcolo, preservando gli zeri nei codici e nelle revisioni. L'elenco deve essere corretto e completo per il fascicolo che vuoi verificare.

La dimensione è letta dal **MediaBox del PDF**, con UserUnit se presente. Il controllo accetta indifferentemente orientamento verticale o orizzontale; non verifica scala di stampa o area visibile dopo un ritaglio. La tolleranza iniziale è 3 mm per lato.

Disattiva **Una pagina per PDF** se nel tuo fascicolo sono ammessi file con più pagine. Tutte le pagine saranno confrontate con lo stesso formato atteso del file. **Includi sottocartelle** estende la ricerca; codici uguali in cartelle diverse vengono segnalati come duplicati.

## 5. Leggere e condividere il rapporto

La scheda **Anomalie** mostra i controlli da verificare. Seleziona una riga per leggerne il dettaglio completo. La scheda **PDF esaminati** mostra codici, revisioni, pagine e dimensioni rilevati.

Con **Esporta rapporto** puoi salvare:

- **HTML:** rapporto completo da aprire nel browser; puoi stamparlo in PDF dal comando di stampa del browser.
- **CSV:** tabella delle anomalie, separata da punto e virgola, per il foglio di calcolo.
- **JSON:** rapporto strutturato completo per integrazioni.

I rapporti contengono nomi dei file e percorsi locali: verifica questi dati prima di condividere il rapporto. Nessuna anomalia significa che sono passati i controlli disponibili e attivati, non che il fascicolo sia tecnicamente corretto.

## Cosa verificare nella prima prova

1. Che la finestra si apra sul tuo computer.
2. Che la demo dia i due risultati attesi.
3. Che lo schema legga correttamente 5–10 tue tavole.
4. Che le anomalie siano utili, senza falsi allarmi dovuti alle convenzioni dello studio.

Per segnalare un problema bastano sistema operativo, messaggio di errore e alcuni nomi di file anonimizzati. Non serve inviare documenti riservati.
