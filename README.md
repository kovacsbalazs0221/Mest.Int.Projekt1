# Mest.Int.Projekt1223

## Hangból Google Naptár-esemény

A projekt célja, hogy magyar nyelvű hangutasításból Google Naptár-eseményt hozzon létre.

## Telepítés és indítás

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\src\fut.py
Az első futtatáskor a program letölti a beszédfelismeréshez szükséges Whisper Medium modellfájljait

## A kód felépítése jelenleg

- `src/hangfajl_kezeles.py` rögzíti a mikrofon hangját és WAV-fájlba menti. TLG
- `src/transcript.py` a `Systran/faster-whisper-medium` modellel elkészíti az átiratot. TLG
- `src/fut.py` elindítja a felvételt, majd a mentett fájl nevét átadja az átírónak. TLG
- `requirements.txt` rögzíti a telepítendő Python-csomagok verzióit.