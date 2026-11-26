import argparse
import json
from datetime import datetime
from pathlib import Path

from datum_ertelmezes import ertelmez
from esemeny_osszeallitas import IDOZONA, osszeallit

FAJL = Path(__file__).resolve().parent.parent / "tests" / "teszt_mondatok.json"


def _hhmm(t):
    return t.strftime("%H:%M") if t else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nincs-llm", action="store_true")
    p.add_argument("--nincs-szandek", action="store_true")
    p.add_argument("--fajl", default=str(FAJL), help="tesztmondatok JSON-fájlja")
    p.add_argument("--mod", default="hibrid", choices=["hibrid", "hibrid3", "modell"])
    args = p.parse_args()

    adat = json.loads(Path(args.fajl).read_text(encoding="utf-8"))
    most = datetime.fromisoformat(adat["referencia_ido"]).replace(tzinfo=IDOZONA)
    mondatok = adat["mondatok"]

    if not args.nincs_szandek:
        from szandek import szandek
    if not args.nincs_llm:
        from adatkinyeres import kinyer

    jo = {k: 0 for k in ["szandek", "llm_datum", "llm_kezdes", "szabaly_datum",
                         "szabaly_kezdes", "vegso_datum", "vegso_kezdes"]}
    naptar_db = 0
    hibak = []

    for m in mondatok:
        szoveg = m["szoveg"]
        sor = f"- {szoveg}"

        if not args.nincs_szandek:
            felismert, val, _ = szandek(szoveg, args.mod)
            if felismert == m["szandek"]:
                jo["szandek"] += 1
            else:
                hibak.append(f"{sor}\n    szándék: {felismert} ({val:.0%}), elvárt: {m['szandek']}")

        if m["szandek"] == "egyeb":
            continue
        naptar_db += 1

        sz = ertelmez(szoveg, most.date())
        jo["szabaly_datum"] += str(sz.datum) == str(m["datum"])
        jo["szabaly_kezdes"] += _hhmm(sz.kezdes) == m["kezdes"]

        llm = {}
        if not args.nincs_llm:
            llm = kinyer(szoveg, most.replace(tzinfo=None), m["szandek"])
            jo["llm_datum"] += llm.get("datum") == m["datum"]
            jo["llm_kezdes"] += (llm.get("kezdes") or None) == m["kezdes"]

        e = osszeallit(szoveg, llm, most, m["szandek"])
        vd = e.kezdes.date() if isinstance(e.kezdes, datetime) else e.kezdes
        vk = None if e.egesz_napos or e.kezdes is None else _hhmm(e.kezdes)
        ok_d, ok_k = str(vd) == str(m["datum"]), vk == m["kezdes"]
        jo["vegso_datum"] += ok_d
        jo["vegso_kezdes"] += ok_k
        if not (ok_d and ok_k):
            hibak.append(f"{sor}\n    végső: {vd} {vk}, elvárt: {m['datum']} {m['kezdes']}"
                         + (f"\n    LLM: {llm.get('datum')} {llm.get('kezdes')}" if llm else ""))

    def sor(nev, kulcs, n):
        print(f"  {nev:<34} {jo[kulcs]:>3}/{n}  ({jo[kulcs] / n:.0%})")

    print(f"\nKiértékelés ({Path(args.fajl).name}, szándék mód: {args.mod}): {len(mondatok)} mondat, ebből {naptar_db} naptárbejegyzés\n")
    if not args.nincs_szandek:
        sor("Szándékfelismerés", "szandek", len(mondatok))
    if not args.nincs_llm:
        sor("Csak LLM - dátum", "llm_datum", naptar_db)
        sor("Csak LLM - kezdés", "llm_kezdes", naptar_db)
    sor("Csak szabályalapú - dátum", "szabaly_datum", naptar_db)
    sor("Csak szabályalapú - kezdés", "szabaly_kezdes", naptar_db)
    sor("Végeredmény - dátum", "vegso_datum", naptar_db)
    sor("Végeredmény - kezdés", "vegso_kezdes", naptar_db)
    if hibak:
        print("\nHibás esetek:")
        print("\n".join(hibak))


if __name__ == "__main__":
    main()
