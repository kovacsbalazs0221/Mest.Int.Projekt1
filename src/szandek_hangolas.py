import json
from pathlib import Path

from transformers import pipeline

from szandek import MODELL_NEV

FAJL = Path(__file__).resolve().parent.parent / "tests" / "teszt_mondatok.json"

VALTOZATOK = {
    "A_magyar_hosszu": ("Ez a mondat {}.", {
        "esemeny": "egy időpontra szervezett programról, találkozóról vagy eseményről szól",
        "emlekezteto": "arra kér, hogy emlékeztessenek valamire",
        "egyeb": "általános kérdés vagy beszélgetés, nem időponttal kapcsolatos",
    }),
    "B_magyar_rovid": ("Ez a szöveg {}.", {
        "esemeny": "egy naptárba beírandó program",
        "emlekezteto": "egy emlékeztető kérése",
        "egyeb": "egy kérdés vagy utasítás",
    }),
    "C_angol": ("This text is {}.", {
        "esemeny": "about a scheduled appointment, meeting or event",
        "emlekezteto": "a request to be reminded to do something",
        "egyeb": "a general question or command, not about the calendar",
    }),
    "D_angol_rovid": ("This example is {}.", {
        "esemeny": "an appointment",
        "emlekezteto": "a reminder",
        "egyeb": "a question",
    }),
    "E_vegyes": ("{}", {
        "esemeny": "Ez egy találkozó vagy program időpontja.",
        "emlekezteto": "Ez egy emlékeztető kérése.",
        "egyeb": "Ez egy kérdés, amire választ várnak.",
    }),
}


def main():
    mondatok = json.loads(FAJL.read_text(encoding="utf-8"))["mondatok"]
    osztalyozo = pipeline("zero-shot-classification", model=MODELL_NEV, device=-1)

    eredmenyek = []
    for nev, (sablon, cimkek) in VALTOZATOK.items():
        vissza = {v: k for k, v in cimkek.items()}
        jo, naptar_jo, hibak = 0, 0, []
        for m in mondatok:
            e = osztalyozo(m["szoveg"], candidate_labels=list(cimkek.values()),
                           hypothesis_template=sablon, multi_label=False)
            tipp = vissza[e["labels"][0]]
            jo += tipp == m["szandek"]
            # a lánc szempontjából az számít, hogy naptárügy-e vagy sem
            naptar_jo += (tipp == "egyeb") == (m["szandek"] == "egyeb")
            if tipp != m["szandek"]:
                hibak.append(f"{m['szoveg']}  ->  {tipp} ({e['scores'][0]:.0%}), elvárt: {m['szandek']}")
        eredmenyek.append((jo, naptar_jo, nev, hibak))
        print(f"\n{nev}: 3 címke {jo}/{len(mondatok)}, naptár/egyéb {naptar_jo}/{len(mondatok)}")
        for h in hibak:
            print("   ", h)

    print("\nÖsszesítés (legjobb elöl):")
    for jo, naptar_jo, nev, _ in sorted(eredmenyek, key=lambda r: (r[1], r[0]), reverse=True):
        print(f"  {nev:<18} 3 címke: {jo:>2}/{len(mondatok)}   naptár/egyéb: {naptar_jo:>2}/{len(mondatok)}")


if __name__ == "__main__":
    main()
