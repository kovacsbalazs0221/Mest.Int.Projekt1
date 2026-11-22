"""
2. modell: szándékfelismerés (zero-shot szövegosztályozás).

A Whisper átiratáról eldönti, hogy a felhasználó
  - új eseményt/találkozót akar felvenni ("esemeny"),
  - emlékeztetőt kér ("emlekezteto"), vagy
  - a mondat nem naptárral kapcsolatos ("egyeb").

Modell: MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (többnyelvű, magyarul is működik).
Zero-shot: nem tanítjuk, hanem minden címkéhez egy magyar hipotézismondatot
képez ("Ez a mondat ...") és megnézi, mennyire következik a bemenetből (NLI).
Az első futtatáskor a modell letöltődik (~560 MB).
"""

MODELL_NEV = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# címke -> a hipotézisbe illesztett leírás
CIMKEK = {
    "esemeny": "egy időpontra szervezett programról, találkozóról vagy eseményről szól",
    "emlekezteto": "arra kér, hogy emlékeztessenek valamire",
    "egyeb": "általános kérdés vagy beszélgetés, nem időponttal kapcsolatos",
}
HIPOTEZIS_SABLON = "Ez a mondat {}."

# Ha a legjobb címke valószínűsége ez alatt van, bizonytalannak jelöljük
BIZONYTALAN_KUSZOB = 0.5

_osztalyozo = None


def _betolt():
    global _osztalyozo
    if _osztalyozo is None:
        from transformers import pipeline
        print("Szándékfelismerő modell betöltése...")
        _osztalyozo = pipeline("zero-shot-classification", model=MODELL_NEV, device=-1)
    return _osztalyozo


def szandek(atirat):
    """
    Visszaad: (címke, valószínűség, minden címke valószínűsége szótárban)
    """
    osztalyozo = _betolt()
    leirasok = list(CIMKEK.values())
    eredmeny = osztalyozo(atirat, candidate_labels=leirasok,
                          hypothesis_template=HIPOTEZIS_SABLON, multi_label=False)

    vissza = {v: k for k, v in CIMKEK.items()}
    pontok = {vissza[l]: round(float(p), 3) for l, p in zip(eredmeny["labels"], eredmeny["scores"])}
    legjobb = eredmeny["labels"][0]
    return vissza[legjobb], float(eredmeny["scores"][0]), pontok


if __name__ == "__main__":
    import sys
    szoveg = " ".join(sys.argv[1:]) or "Holnap délután háromkor megyek fogorvoshoz."
    print(szandek(szoveg))
