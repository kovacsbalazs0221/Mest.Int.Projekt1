import argparse
import json
import sys
from datetime import date, datetime

from esemeny_osszeallitas import IDOZONA, osszeallit, osszefoglalo


def atirat_megszerzese(args):
    if args.szoveg:
        return args.szoveg
    from transcript import atir          # csak itt töltjük be a Whispert
    if args.fajl:
        return atir(args.fajl)
    from hangfajl_kezeles import hangrogzit
    fajlnev = hangrogzit()
    return atir(fajlnev) if fajlnev else None


def datum_bekerese():
    while True:
        valasz = input("Nem derült ki a dátum. Add meg (ÉÉÉÉ-HH-NN), vagy Enter = kilépés: ").strip()
        if not valasz:
            return None
        try:
            return date.fromisoformat(valasz)
        except ValueError:
            print("Hibás formátum.")


def main():
    p = argparse.ArgumentParser(description="Hangutasításból Google Naptár-esemény")
    p.add_argument("--szoveg", help="átirat megadása kézzel (kihagyja a felvételt és a Whispert)")
    p.add_argument("--fajl", help="meglévő WAV fájl átírása")
    p.add_argument("--proba", action="store_true", help="nem hoz létre eseményt a naptárban")
    p.add_argument("--igen", action="store_true", help="megerősítés kérése nélkül létrehozza")
    p.add_argument("--nincs-szandek", action="store_true", help="kihagyja a szándékfelismerést")
    args = p.parse_args()

    atirat = atirat_megszerzese(args)
    if not atirat:
        print("Nincs átirat, kilépek.")
        return 1
    print(f"\n[1] Átirat: {atirat}")

    tipus = "esemeny"
    if not args.nincs_szandek:
        from szandek import BIZONYTALAN_KUSZOB, szandek
        tipus, valoszinuseg, pontok = szandek(atirat)
        print(f"[2] Szándék: {tipus} ({valoszinuseg:.0%})  {pontok}")
        if tipus == "egyeb":
            if valoszinuseg >= BIZONYTALAN_KUSZOB:
                print("Ez nem tűnik naptárbejegyzésnek, nem hozok létre eseményt.")
                return 0
            print("Bizonytalan, eseményként folytatom.")
            tipus = "esemeny"

    from adatkinyeres import OLLAMA_MODELL, kinyer
    most = datetime.now(IDOZONA)
    print(f"[3] Adatkinyerés ({OLLAMA_MODELL})...")
    try:
        llm = kinyer(atirat, most.replace(tzinfo=None), tipus)
    except RuntimeError as h:
        print(f"Hiba: {h}")
        return 1
    print("    LLM válasz:", json.dumps(llm, ensure_ascii=False))

    e = osszeallit(atirat, llm, most, tipus)
    if "datum" in e.hianyzik:
        d = datum_bekerese()
        if d is None:
            return 1
        llm["datum"] = d.isoformat()
        e = osszeallit(atirat, llm, most, tipus)

    print("\n[4] A létrehozandó esemény:")
    print(osszefoglalo(e))

    if args.proba:
        from naptar import esemeny_torzs
        print("\n(Próba mód, a naptárba nem írok.) API-törzs:")
        print(json.dumps(esemeny_torzs(e), ensure_ascii=False, indent=2, default=str))
        return 0

    if not args.igen and input("\nLétrehozzam? [i/n]: ").strip().lower() not in ("i", "igen", "y"):
        print("Megszakítva.")
        return 0

    from naptar import letrehoz
    link = letrehoz(e)
    print(f"[5] Kész! {link}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
