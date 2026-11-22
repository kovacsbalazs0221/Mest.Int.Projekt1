"""
Ellenőrzés és összevetés: az LLM kimenetéből és a szabályalapú
dátumértelmezésből egy ellenőrzött, naptárba írható esemény lesz.

Döntési szabályok:
  1. A dátumot és az időpontot elsősorban a datum_ertelmezes.py adja
     (determinisztikus, nem "hallucinál"); ha ott nincs találat, az LLM értéke jön.
  2. Ha a kettő eltér, figyelmeztetést adunk, és a szabályalapút használjuk.
  3. Ha nincs vége-időpont: időtartam (szabály -> LLM -> alapértelmezés).
  4. Ha nincs időpont: egész napos esemény.
  5. Ha nincs dátum, de van időpont: ma (ha még nem múlt el), különben holnap.
  6. Múltbeli időpontra figyelmeztetünk.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from datum_ertelmezes import ertelmez

IDOZONA = ZoneInfo("Europe/Budapest")
ALAP_IDOTARTAM = {"esemeny": 60, "emlekezteto": 15}
EMLEKEZTETO_PERC = {"esemeny": 30, "emlekezteto": 0}


@dataclass
class Esemeny:
    cim: str
    kezdes: datetime | date | None
    vege: datetime | date | None
    egesz_napos: bool = False
    helyszin: str | None = None
    leiras: str | None = None
    emlekezteto_perc: int = 30
    figyelmeztetesek: list[str] = field(default_factory=list)
    hianyzik: list[str] = field(default_factory=list)


def _iso_datum(s):
    try:
        return date.fromisoformat(s) if s else None
    except (TypeError, ValueError):
        return None


def _ora_perc(s):
    if not s:
        return None
    m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})(?::\d{2})?\s*", str(s))
    if not m:
        return None
    o, p = int(m.group(1)), int(m.group(2))
    return time(o, p) if o < 24 and p < 60 else None


def _ures(s):
    return s is None or not str(s).strip() or str(s).strip().lower() in ("null", "none")


def osszeallit(atirat, llm, most=None, szandek="esemeny"):
    most = most or datetime.now(IDOZONA)
    if most.tzinfo is None:
        most = most.replace(tzinfo=IDOZONA)
    llm = llm or {}
    szabaly = ertelmez(atirat, most.date())
    figy = list(szabaly.megjegyzesek)

    # --- dátum ---
    llm_datum = _iso_datum(llm.get("datum"))
    if llm.get("datum") and llm_datum is None:
        figy.append(f"Az LLM érvénytelen dátumot adott: {llm.get('datum')!r}")
    datum = szabaly.datum or llm_datum
    if szabaly.datum and llm_datum and szabaly.datum != llm_datum:
        figy.append(f"Eltérő dátum: szabály {szabaly.datum}, LLM {llm_datum}, a szabályalapút használom")

    # --- időpont ---
    llm_kezdes, llm_vege = _ora_perc(llm.get("kezdes")), _ora_perc(llm.get("vege"))
    kezdes = szabaly.kezdes or llm_kezdes
    if szabaly.kezdes and llm_kezdes and szabaly.kezdes != llm_kezdes:
        figy.append(f"Eltérő kezdés: szabály {szabaly.kezdes:%H:%M}, LLM {llm_kezdes:%H:%M}, a szabályalapút használom")
    vege = szabaly.vege or llm_vege
    if kezdes and vege and vege <= kezdes:
        figy.append(f"A vége ({vege:%H:%M}) nem a kezdés után van, figyelmen kívül hagyom")
        vege = None

    # --- időtartam ---
    llm_hossz = llm.get("idotartam_perc")
    llm_hossz = llm_hossz if isinstance(llm_hossz, int) and 0 < llm_hossz <= 24 * 60 else None
    hossz = szabaly.idotartam_perc or llm_hossz or ALAP_IDOTARTAM.get(szandek, 60)

    hianyzik = []
    if datum is None:
        if kezdes:
            datum = most.date() if kezdes > most.time().replace(tzinfo=None) else most.date() + timedelta(days=1)
            figy.append(f"Nem hangzott el dátum, ezt feltételeztem: {datum}")
        else:
            hianyzik.append("datum")

    # --- cím, helyszín, leírás ---
    cim = (llm.get("cim") or "").strip()
    if _ures(cim):
        cim = atirat.strip()[:50] or "Esemény"
        figy.append("Az LLM nem adott címet, az átirat elejét használom")
    helyszin = None if _ures(llm.get("helyszin")) else llm["helyszin"].strip()
    leiras = None if _ures(llm.get("leiras")) else llm["leiras"].strip()
    leiras = (leiras + "\n\n" if leiras else "") + f"Hangutasítás: \"{atirat.strip()}\""

    e = Esemeny(cim=cim, kezdes=None, vege=None, helyszin=helyszin, leiras=leiras,
                emlekezteto_perc=EMLEKEZTETO_PERC.get(szandek, 30),
                figyelmeztetesek=figy, hianyzik=hianyzik)

    if datum is None:
        return e

    if kezdes is None:
        e.egesz_napos = True
        e.kezdes, e.vege = datum, datum + timedelta(days=1)
        if not llm.get("egesz_napos"):
            figy.append("Nem hangzott el időpont, egész napos eseményként veszem fel")
    else:
        e.kezdes = datetime.combine(datum, kezdes, tzinfo=IDOZONA)
        e.vege = (datetime.combine(datum, vege, tzinfo=IDOZONA) if vege
                  else e.kezdes + timedelta(minutes=hossz))
        if e.kezdes < most:
            figy.append("Figyelem: az időpont a múltban van!")

    return e


def osszefoglalo(e):
    sorok = [f"  Cím:       {e.cim}"]
    if e.kezdes is None:
        sorok.append("  Időpont:   (hiányzik)")
    elif e.egesz_napos:
        sorok.append(f"  Dátum:     {e.kezdes:%Y-%m-%d} (egész napos)")
    else:
        sorok.append(f"  Kezdés:    {e.kezdes:%Y-%m-%d %H:%M}")
        sorok.append(f"  Vége:      {e.vege:%Y-%m-%d %H:%M}")
    if e.helyszin:
        sorok.append(f"  Helyszín:  {e.helyszin}")
    if e.emlekezteto_perc is not None and not e.egesz_napos:
        sorok.append(f"  Értesítés: {e.emlekezteto_perc} perccel előtte")
    for f in e.figyelmeztetesek:
        sorok.append(f"  ! {f}")
    return "\n".join(sorok)
