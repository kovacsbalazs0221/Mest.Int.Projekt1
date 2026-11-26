# Mest.Int.Projekt1223

## Hangból Google Naptár-esemény

A projekt célja, hogy magyar nyelvű hangutasításból Google Naptár-eseményt hozzon létre.

## A feldolgozási lánc

```
mikrofon -> [1. Whisper medium: beszédfelismerés]            -> magyar átirat
         -> [2. mDeBERTa zero-shot + szabálykapu: szándék]    -> esemény / emlékeztető / egyéb (egyéb -> leáll)
         -> [3. Qwen2.5 7B (Ollama): adatkinyerés]            -> JSON: cím, dátum, idő, helyszín
         -> [saját: dátumértelmező + ellenőrzés]              -> ellenőrzött esemény
         -> megerősítés a konzolon -> Google Naptár
```

## Telepítés és indítás

- python -m venv .venv
- .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements_naptar.txt
- .\.venv\Scripts\python.exe .\src\fut.py (csak felvétel + átirat)
- .\.venv\Scripts\python.exe .\src\fo_program.py (a teljes lánc)
- Az első futtatáskor a program letölti a beszédfelismeréshez szükséges Whisper Medium modellfájljait (~1,5 GB), és a szándékfelismerő modellt (~560 MB)

Kell még hozzá:

- **Ollama** (https://ollama.com/download), majd `ollama pull qwen2.5:7b` (~4,7 GB). Gyengébb gépen `qwen2.5:3b`, ekkor az `OLLAMA_MODELL` környezeti változóban kell megadni. Az `OLLAMA_URL` változóval másik címen futó Ollama is megadható (alapból `http://localhost:11434`).
- **Google Naptár hozzáférés**: Google Cloud projektben a Google Calendar API engedélyezése, OAuth kliens (Asztali alkalmazás) létrehozása, és a letöltött JSON mentése `titkos/credentials.json` néven. Részletes lépések: `docs/BEALLITAS.md`.
- Az első naptárba íráskor böngészőben kell bejelentkezni. A token a `titkos/token.json` fájlba kerül. A `titkos/` mappa saját `.gitignore`-ja miatt ezek **nem kerülnek gitbe**, és ne is küldjétek el őket nyilvános helyre.

## Használat

A `fo_program.py` kapcsolói:

| Kapcsoló | Mit csinál |
| --- | --- |
| (nincs) | felvétel a mikrofonról: a szóközt nyomva kell tartani, amíg beszélsz |
| `--szoveg "..."` | kézzel megadott átirat, kihagyja a felvételt és a Whispert |
| `--fajl felvetel.wav` | meglévő WAV fájl átírása |
| `--proba` | nem ír a naptárba, csak kiírja a Calendar API-nak küldendő adatot |
| `--igen` | nem kér megerősítést a létrehozás előtt |
| `--nincs-szandek` | kihagyja a szándékfelismerést |

Példa: `.\.venv\Scripts\python.exe .\src\fo_program.py --szoveg "Jövő pénteken fél négykor konzultáció a tanszéken" --proba`

## Tesztelés

- `.\.venv\Scripts\python.exe -m pytest`: egységtesztek, modell nélkül futnak, pár másodperc alatt.
- `.\.venv\Scripts\python.exe .\src\ertekeles.py`: lépésenkénti pontosság a `tests/teszt_mondatok.json` mondatain (szándék, csak LLM, csak szabályalapú, végeredmény). Kapcsolók:
  - `--fajl tests\teszt_mondatok_fuggetlen.json`: a független ellenőrző készlet (ezt a hangolásnál nem használtuk)
  - `--mod modell` / `hibrid3` / `hibrid`: a szándékfelismerés módja (alapból `hibrid`)
  - `--nincs-llm`, `--nincs-szandek`: az adott modell kihagyása (pl. Ollama nélkül)
- `.\.venv\Scripts\python.exe .\src\szandek_hangolas.py`: öt hipotézis-megfogalmazást mér össze a szándékfelismeréshez. A tesztmondatokhoz tartozó elvárt dátumok egy rögzített referencia-időponthoz (hétfő 10:00) képest értendők, ez a JSON-fájlokban szerepel.

## A kód felépítése

- `src/hangfajl_kezeles.py` rögzíti a mikrofon hangját és WAV-fájlba menti. TLG
- `src/transcript.py` a `Systran/faster-whisper-medium` modellel elkészíti az átiratot. TLG
- `src/fut.py` elindítja a felvételt, majd a mentett fájl nevét átadja az átírónak. TLG
- `src/fo_program.py` a teljes lánc belépési pontja (felvétel, átirat, szándék, LLM, ellenőrzés, naptár).
- `src/szandek.py` 2. modell: szándékfelismerés (`MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, zero-shot) szabályalapú kapuval.
- `src/adatkinyeres.py` 3. modell: adatkinyerés helyi LLM-mel az Ollamán keresztül, JSON-sémával.
- `src/datum_ertelmezes.py` saját, szabályalapú magyar dátum- és időértelmező.
- `src/esemeny_osszeallitas.py` összeveti az LLM és a szabályalapú értelmező eredményét, és ellenőrzi az eseményt.
- `src/naptar.py` Google OAuth bejelentkezés és az esemény létrehozása a Calendar API-val.
- `src/ertekeles.py`, `src/szandek_hangolas.py` kiértékelő és hangoló szkriptek; `tests/` egységtesztek és tesztmondatok.
- `requirements.txt` rögzíti a telepítendő Python-csomagok verzióit, a `requirements_naptar.txt` a lánc további csomagjait.

## Fontos tudnivalók a működésről

### Szándékfelismerés (`szandek.py`)

- A modell zero-shot: nincs tanítva, minden címkéhez egy hipotézismondatot képez, és azt méri, mennyire következik az átiratból. A modell többnyelvű, és a hangolásnál az **angol** hipotézisek bizonyultak pontosabbnak a magyaroknál, ezért azokat használjuk.
- A modell önmagában nem ismeri fel megbízhatóan, ha egy mondat nem naptárügy. Ezért az alapértelmezett **`hibrid`** módban két szabály szűr előtte:
  1. ha az átiratban nincs se dátum, se időpont: egyéb;
  2. ha a mondat kérdés, és nem emlékeztetőt kér (nincs benne pl. „emlékeztess”, „ne felejtsem”, „szólj”): egyéb.

  Ezután a modell már csak az esemény és az emlékeztető között dönt.
- Módok: `modell` (csak a modell, 3 címkével), `hibrid3` (csak a dátum/idő-kapu, utána a modell 3 címkével), `hibrid` (mindkét kapu, utána a modell 2 címkével).
- A `szandek()` visszatérési értéke: `(címke, valószínűség, pontok)`. Ha egy szabály döntött, a pontok között az `ok` kulcs mondja meg, melyik.

### Adatkinyerés LLM-mel (`adatkinyeres.py`)

- A promptba a következő 14 nap naptárát is beletesszük, mert a kis modellek rosszul számolják ki, melyik dátum például a „jövő kedd”.
- A válasz szerkezetét JSON-séma kényszeríti ki (Ollama „structured outputs”), `temperature = 0` mellett.

### Dátum- és időértelmezés (`datum_ertelmezes.py`)

A dátumot és az időpontot elsősorban ez a determinisztikus modul számolja ki, mert az LLM ebben gyakran hibázik. Kezelt kifejezések:

| Típus | Példák |
| --- | --- |
| dátum | ma, holnap, holnapután, 3 nap múlva, egy hét múlva, kedden, jövő pénteken, ezen a héten szerdán, november 25-én, 2026. november 25., 11. 25., 2026-11-25, 25-én |
| időpont | 15:30, 15.30-kor, 3-kor, háromkor, 15 órakor, 15 óra 30 perckor, délután 3, este hétkor, fél 4, negyed 5, háromnegyed 8, délben |
| idősáv | 3-tól 5-ig, 14:00-tól 15:30-ig, háromtól ötig |
| időtartam | két órás, másfél órás, 2 órán át, 45 perces, fél órás |

Szabályok, amiket érdemes tudni:

- A „fél 4” 3:30, a „negyed 5” 4:15, a „háromnegyed 8” 7:45, mert az előző órához számolunk.
- Ha 1 és 6 óra közötti időpont napszak nélkül hangzik el, délutánt feltételez, és ezt figyelmeztetésként ki is írja.
- Napnév (pl. „hétfőn”) a következő ilyen napot jelenti; ha ma van az a nap, akkor a jövő hetit.
- Ha egy hónap és nap év nélkül már elmúlt, a következő évre kerül.
- Az időtartamot a már felismert időpont nélküli szövegben keresi, hogy a „15 óra 30 perc” ne 30 perces időtartam legyen.
- Nem kezeli a sorszámneveket („huszonötödikén”), az ünnepneveket és a „tegnap” szót; ilyenkor az LLM értéke marad.

### Ellenőrzés és összevetés (`esemeny_osszeallitas.py`)

1. A dátumot és az időpontot elsősorban a szabályalapú értelmező adja; ha ott nincs találat, az LLM értéke jön (ha érvényes formátumú).
2. Ha a kettő eltér, figyelmeztetést ad, és a szabályalapút használja.
3. Ha nincs vége-időpont: időtartam (szabály, majd LLM), végül alapértelmezés: esemény 60 perc, emlékeztető 15 perc.
4. Ha nincs időpont: egész napos esemény.
5. Ha nincs dátum, de van időpont: ma, ha még nem múlt el, különben holnap.
6. Ha semmilyen dátum nem derül ki, a program rákérdez. Múltbeli időpontra figyelmeztet.

Értesítés: eseménynél 30 perccel előtte, emlékeztetőnél a kezdéskor. Időzóna: Europe/Budapest.

## Ismert korlátok

- A szándékfelismerő hajlamos az eseményeket emlékeztetőnek sorolni (ez csak az esemény hosszát és az értesítést befolyásolja).
- Ha a szabályok nem találnak időpontot, az LLM néha kitalál egyet, ami el sem hangzott.
- A 7B-s modell címei néha pontatlanok, ezért fontos a létrehozás előtti megerősítés.
- A Google OAuth-alkalmazás tesztüzemmódban van: csak a Google Cloudban felvett tesztfelhasználók jelentkezhetnek be.

Részletes mérési eredmények és a teljes leírás a projektdokumentációban vannak.
