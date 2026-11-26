import re
from datetime import date

from datum_ertelmezes import ertelmez

MODELL_NEV = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

HIPOTEZIS_SABLON = "This text is {}."
CIMKEK = {
    "esemeny": "about a scheduled appointment, meeting or event",
    "emlekezteto": "a request to be reminded to do something",
    "egyeb": "a general question or command, not about the calendar",
}

# Ha a "modell" módban az "egyéb" valószínűsége ez alatt van, bizonytalannak számít
BIZONYTALAN_KUSZOB = 0.5

EMLEKEZTETO_SZAVAK = re.compile(r"eml[ée]keztet|ne felejt|eszembe|sz[óo]lj", re.IGNORECASE)

_osztalyozo = None


def _betolt():
    global _osztalyozo
    if _osztalyozo is None:
        from transformers import pipeline
        print("Szándékfelismerő modell betöltése...")
        _osztalyozo = pipeline("zero-shot-classification", model=MODELL_NEV, device=-1)
    return _osztalyozo


def szabaly_kapu(atirat, kerdes_szabaly=True):
    """Ha a szabályok szerint a mondat nem naptárügy, az okát adja vissza, különben None-t."""
    e = ertelmez(atirat, date.today())
    if e.datum is None and e.kezdes is None:
        return "nem hangzik el dátum vagy időpont"
    if kerdes_szabaly and atirat.strip().endswith("?") and not EMLEKEZTETO_SZAVAK.search(atirat):
        return "kérdés, nem emlékeztető-kérés"
    return None


def _nli(atirat, cimkek):
    osztalyozo = _betolt()
    leirasok = [CIMKEK[c] for c in cimkek]
    eredmeny = osztalyozo(atirat, candidate_labels=leirasok,
                          hypothesis_template=HIPOTEZIS_SABLON, multi_label=False)
    vissza = {CIMKEK[c]: c for c in cimkek}
    pontok = {vissza[l]: round(float(p), 3) for l, p in zip(eredmeny["labels"], eredmeny["scores"])}
    return vissza[eredmeny["labels"][0]], float(eredmeny["scores"][0]), pontok


def szandek(atirat, mod="hibrid"):
    if mod in ("hibrid", "hibrid3"):
        ok = szabaly_kapu(atirat, kerdes_szabaly=(mod == "hibrid"))
        if ok:
            return "egyeb", 1.0, {"ok": ok}
    if mod == "hibrid":
        return _nli(atirat, ["esemeny", "emlekezteto"])
    return _nli(atirat, ["esemeny", "emlekezteto", "egyeb"])


if __name__ == "__main__":
    import sys
    szoveg = " ".join(sys.argv[1:]) or "Holnap délután háromkor megyek fogorvoshoz."
    print(szandek(szoveg))
