"""
3. modell: az esemény adatainak kinyerése nagy nyelvi modellel (LLM).

A helyben futó Ollama szerverhez fordul (http://localhost:11434), és
JSON-sémával kényszeríti, hogy a válasz pontosan a várt mezőket tartalmazza.

Alapértelmezett modell: qwen2.5:7b (jól kezeli a magyar szöveget, ~4,7 GB).
Másik modell: OLLAMA_MODELL környezeti változóval, pl. "llama3.1:8b" vagy
gyengébb gépen "qwen2.5:3b".

A dátum/idő mezőket az esemeny_osszeallitas.py ellenőrzi, és a saját
szabályalapú értelmezőnk (datum_ertelmezes.py) eredményét előnyben részesíti.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODELL = os.environ.get("OLLAMA_MODELL", "qwen2.5:7b")

NAPNEVEK = ["hétfő", "kedd", "szerda", "csütörtök", "péntek", "szombat", "vasárnap"]

# A válasz szerkezete (Ollama "structured outputs")
SEMA = {
    "type": "object",
    "properties": {
        "cim": {"type": "string"},
        "datum": {"type": ["string", "null"]},          # ÉÉÉÉ-HH-NN
        "kezdes": {"type": ["string", "null"]},         # ÓÓ:PP
        "vege": {"type": ["string", "null"]},           # ÓÓ:PP
        "idotartam_perc": {"type": ["integer", "null"]},
        "egesz_napos": {"type": "boolean"},
        "helyszin": {"type": ["string", "null"]},
        "leiras": {"type": ["string", "null"]},
    },
    "required": ["cim", "datum", "kezdes", "vege", "idotartam_perc",
                 "egesz_napos", "helyszin", "leiras"],
}


def _rendszer_prompt(most, szandek):
    # Segítségként megadjuk a következő 14 nap naptárát, mert a kis modellek
    # rosszul számolják ki, melyik dátum a "jövő kedd".
    napok = "\n".join(
        f"  {(most + timedelta(days=i)).date().isoformat()} {NAPNEVEK[(most + timedelta(days=i)).weekday()]}"
        for i in range(14)
    )
    tipus = "emlékeztető" if szandek == "emlekezteto" else "naptáresemény"
    return f"""Magyar nyelvű hangutasítás átiratából {tipus} adatait nyered ki.
Mai dátum és idő: {most.strftime('%Y-%m-%d %H:%M')} ({NAPNEVEK[most.weekday()]}).
A következő napok:
{napok}

Szabályok:
- cim: rövid, tömör esemény-cím magyarul (2-6 szó), nagybetűvel kezdve, pl. "Fogorvos", "Megbeszélés Péterrel".
- datum: ÉÉÉÉ-HH-NN formátum, vagy null, ha nem derül ki.
- kezdes / vege: 24 órás ÓÓ:PP formátum, vagy null. "délután 3" = 15:00, "fél 4" = 03:30 vagy 15:30 a napszaktól függően.
- idotartam_perc: ha az időtartam elhangzik (pl. "két órás" = 120), egyébként null.
- egesz_napos: true, ha nincs időpont és egész napos dologról van szó (pl. születésnap, szabadság).
- helyszin: ha elhangzik hely, egyébként null.
- leiras: minden további hasznos részlet, egyébként null.
Ne találj ki adatot, ami nem hangzott el. Csak a JSON-t add vissza."""


def kinyer(atirat, most=None, szandek="esemeny", idokorlat=120):
    """Az átiratból szótárat ad vissza a SEMA mezőivel."""
    most = most or datetime.now()
    keres = {
        "model": OLLAMA_MODELL,
        "messages": [
            {"role": "system", "content": _rendszer_prompt(most, szandek)},
            {"role": "user", "content": atirat},
        ],
        "format": SEMA,
        "stream": False,
        "options": {"temperature": 0},
    }
    adat = json.dumps(keres).encode("utf-8")
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=adat,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=idokorlat) as valasz:
            test = json.loads(valasz.read().decode("utf-8"))
    except urllib.error.HTTPError as h:
        if h.code == 404:
            raise RuntimeError(f"Az Ollama-ban nincs meg a '{OLLAMA_MODELL}' modell. "
                               f"Töltsd le: ollama pull {OLLAMA_MODELL}") from h
        raise
    except urllib.error.URLError as h:
        raise RuntimeError("Nem érem el az Ollama szervert. Fut az Ollama? "
                           f"({OLLAMA_URL})") from h

    tartalom = test["message"]["content"]
    try:
        return json.loads(tartalom)
    except json.JSONDecodeError as h:
        raise RuntimeError(f"Az LLM nem érvényes JSON-t adott vissza: {tartalom!r}") from h


if __name__ == "__main__":
    import sys
    szoveg = " ".join(sys.argv[1:]) or "Jövő pénteken délután négykor megbeszélés Péterrel a könyvtárban."
    print(json.dumps(kinyer(szoveg), ensure_ascii=False, indent=2))
