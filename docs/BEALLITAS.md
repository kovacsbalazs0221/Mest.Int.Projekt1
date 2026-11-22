# Hangból Google Naptár-esemény: a teljes lánc beállítása és futtatása

Ez a leírás a `src/fo_program.py` láncot írja le, amely a meglévő felvételre (`hangfajl_kezeles.py`)
és átírásra (`transcript.py`) épül. A régi `fut.py` változatlanul működik tovább.

## A feldolgozási lánc

```
 mikrofon ──► [1] Whisper medium (faster-whisper)      hang → magyar átirat
                │
                ▼
          [2] mDeBERTa-v3 XNLI (zero-shot)          átirat → esemény / emlékeztető / egyéb
                │   (egyéb → leáll)
                ▼
          [3] LLM: Qwen2.5 7B (Ollama, helyben)       átirat → JSON (cím, dátum, idő, hely…)
                │
                ▼
          [saját] datum_ertelmezes.py                szabályalapú magyar dátum/idő értelmező
          [saját] esemeny_osszeallitas.py            összevetés, ellenőrzés, alapértékek
                │
                ▼
          megerősítés a konzolon ──► Google Calendar API (naptar.py)
```

| Fájl | Szerep |
|---|---|
| `src/fo_program.py` | a teljes lánc, parancssori kapcsolókkal |
| `src/szandek.py` | 2. modell: szándékfelismerés |
| `src/adatkinyeres.py` | 3. modell: LLM-hívás JSON-sémával (Ollama) |
| `src/datum_ertelmezes.py` | saját: „holnapután”, „jövő pénteken”, „fél 4”, „3-tól 5-ig”… |
| `src/esemeny_osszeallitas.py` | saját: LLM és szabály összevetése, hiányzó/hibás adatok kezelése |
| `src/naptar.py` | Google OAuth bejelentkezés + esemény létrehozása |
| `src/ertekeles.py` | lépésenkénti pontosságmérés a tesztmondatokon |
| `tests/` | egységtesztek (pytest) és tesztmondatok |

**Miért van szabályalapú értelmező is?** A helyben futó 7B-s modellek gyakran
elszámolják a naptárt (pl. „jövő pénteken” → rossz dátum). A dátumot és az időt ezért elsősorban
a saját, determinisztikus értelmező adja. Az LLM-re a cím, a helyszín és a leírás kinyeréséhez van
szükség, valamint tartaléknak, ha a szabályok nem találnak semmit. Ha a kettő eltér, a program
figyelmeztet. A `src/ertekeles.py` számokkal is megmutatja, mennyit javít ez a lépés.

## 1. Python-csomagok

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements_naptar.txt
```

Az első futtatáskor a Whisper (~1,5 GB) és az mDeBERTa (~560 MB) modell letöltődik.

## 2. Ollama (helyi LLM)

1. Telepítés: https://ollama.com/download (Windows-telepítő), utána a háttérben fut.
2. Modell letöltése (~4,7 GB):
   ```powershell
   ollama pull qwen2.5:7b
   ```
3. Próba: `ollama run qwen2.5:7b "Szia"`

Gyengébb gépen (8 GB RAM alatt) használjátok a `qwen2.5:3b` modellt:
```powershell
ollama pull qwen2.5:3b
$env:OLLAMA_MODELL = "qwen2.5:3b"
```

## 3. Google Naptár API (egyszer kell)

1. https://console.cloud.google.com → új projekt (pl. „MestInt Naptar”).
2. *APIs & Services → Library* → **Google Calendar API** → *Enable*.
3. *APIs & Services → OAuth consent screen* (Google Auth Platform):
   - User type: **External**, töltsétek ki a nevet és az e-mail-címet.
   - *Audience / Test users*: adjátok hozzá **mindkettőtök Gmail-címét** (tesztüzemmódban csak ők léphetnek be).
4. *Clients / Credentials → Create credentials → OAuth client ID* → típus: **Desktop app**.
5. Töltsétek le a JSON-t, és mentsétek ide: `titkos/credentials.json`.

Az első létrehozáskor megnyílik a böngésző, itt kell engedélyezni a hozzáférést. Ezután a token a
`titkos/token.json` fájlba kerül. A `titkos/` mappa tartalma **nem kerül gitbe**, mert a mappa
saját `.gitignore`-ja kizárja.

## 4. Futtatás

A projekt gyökeréből:

```powershell
# teljes lánc: tartsd nyomva a szóközt és beszélj
.\.venv\Scripts\python.exe .\src\fo_program.py

# próbák a hangfelvétel nélkül / naptárba írás nélkül
.\.venv\Scripts\python.exe .\src\fo_program.py --szoveg "Jövő pénteken fél négykor konzultáció a tanszéken" --proba
.\.venv\Scripts\python.exe .\src\fo_program.py --fajl felvetel.wav --proba
```

Kapcsolók: `--szoveg`, `--fajl`, `--proba` (nem ír a naptárba), `--igen` (nem kér megerősítést),
`--nincs-szandek` (kihagyja a 2. modellt).

## 5. Tesztelés

```powershell
# egységtesztek (nem kell hozzájuk modell, másodpercek alatt lefutnak)
.\.venv\Scripts\python.exe -m pytest

# lépésenkénti pontosság a tests/teszt_mondatok.json mondatain
.\.venv\Scripts\python.exe .\src\ertekeles.py
.\.venv\Scripts\python.exe .\src\ertekeles.py --nincs-llm   # Ollama nélkül
```

A dokumentáció tesztelési fejezetéhez érdemes:
- valódi felvételeket készíteni (több beszélő, zajos környezet), és a Whisper-átiratokat felvenni a
  `teszt_mondatok.json`-ba;
- kitölteni a táblázatot az `ertekeles.py` kimenetével (csak LLM, csak szabály, végeredmény);
- feljegyezni a hibás eseteket. Ezek a korlátok fejezet alapanyagai.

## Ismert korlátok (kiindulópont a dokumentációhoz)

- A szabályalapú értelmező a gyakori kifejezéseket ismeri. Sorszámneveket („huszonötödikén”) és
  ünnepneveket („karácsony előtt”) nem kezel, ezeknél az LLM értéke marad.
- Ha 1 és 6 óra közötti időpont napszak nélkül hangzik el, a program délutánt feltételez, és ezt jelzi is.
- A zero-shot szándékfelismerés nincs magyar adatokon finomhangolva, ezért a rövid, kétértelmű
  mondatokat („holnap?”) várhatóan bizonytalanul sorolja be. Ezt az `ertekeles.py` eredményeivel érdemes ellenőrizni.
- Egy hangutasítás egyetlen eseményt hoz létre. Ismétlődő eseményeket nem kezel.
