import re
from dataclasses import dataclass, field
from datetime import date, time, timedelta


SZAMSZAVAK = {
    "tizenkettő": 12, "tizenkét": 12, "tizenegy": 11, "tíz": 10,
    "kilenc": 9, "nyolc": 8, "hét": 7, "hat": 6, "öt": 5, "négy": 4,
    "három": 3, "kettő": 2, "két": 2, "egy": 1,
}
# Percekhez (időtartam) további számszavak
PERC_SZAVAK = {
    "kilencven": 90, "hatvan": 60, "negyvenöt": 45, "negyven": 40,
    "harminc": 30, "húsz": 20, "tizenöt": 15, **SZAMSZAVAK,
}

HONAPOK = {
    "január": 1, "február": 2, "március": 3, "április": 4, "május": 5,
    "június": 6, "július": 7, "augusztus": 8, "szeptember": 9,
    "október": 10, "november": 11, "december": 12,
}

# A napnevek tövei (ragozott alakokra is illeszkedjen: kedden, szerdán, ...)
NAPTOVEK = {
    "hétfő": 0, "kedd": 1, "szerd": 2, "csütörtök": 3,
    "péntek": 4, "szombat": 5, "vasárnap": 6,
}


def _alternacio(szavak):
    # A hosszabb szavak előre kerülnek, hogy pl. a "tizenegy" ne "egy"-ként illeszkedjen
    return "|".join(sorted(map(re.escape, szavak), key=len, reverse=True))


SZAM_RE = _alternacio(SZAMSZAVAK)
ORA = rf"(\d{{1,2}}|{SZAM_RE})"          # óra: számjeggyel vagy szóval
PERC_SZAM = rf"(\d{{1,3}}|{_alternacio(PERC_SZAVAK)})"
HONAP_RE = _alternacio(HONAPOK)
NAP_RE = _alternacio(NAPTOVEK)


def _szam(szoveg):
    if szoveg is None:
        return None
    if szoveg.isdigit():
        return int(szoveg)
    return PERC_SZAVAK.get(szoveg)


@dataclass
class Ertelmezes:
    datum: date | None = None
    kezdes: time | None = None
    vege: time | None = None
    idotartam_perc: int | None = None
    megjegyzesek: list[str] = field(default_factory=list)


def _datum_evvel(ev, honap, nap, ma):
    """Ha nincs megadva év, és a dátum már elmúlt, a következő évre tesszük."""
    try:
        if ev:
            return date(int(ev), honap, nap)
        d = date(ma.year, honap, nap)
        if d < ma:
            d = date(ma.year + 1, honap, nap)
        return d
    except ValueError:
        return None


def datum_keresese(szoveg, ma):
    s = szoveg.lower()

    # 1) ISO: 2026-11-25
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        return _datum_evvel(m.group(1), int(m.group(2)), int(m.group(3)), ma)

    # 2) Hónapnévvel: (2026.) november 25-én
    m = re.search(rf"\b(?:(\d{{4}})\.?\s*)?({HONAP_RE})\w*\s+(\d{{1,2}})", s)
    if m:
        return _datum_evvel(m.group(1), HONAPOK[m.group(2)], int(m.group(3)), ma)

    # 3) Számokkal: (2026.) 11. 25.
    m = re.search(r"\b(?:(\d{4})\.\s*)?(\d{1,2})\.\s*(\d{1,2})\.", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return _datum_evvel(m.group(1), int(m.group(2)), int(m.group(3)), ma)

    # 4) Relatív szavak
    if re.search(r"\bholnapután", s):
        return ma + timedelta(days=2)
    if re.search(r"\bholnap", s):
        return ma + timedelta(days=1)
    m = re.search(rf"\b{PERC_SZAM}\s+(nap|hét|hónap)\s+múlva", s)
    if m:
        n = _szam(m.group(1))
        if n:
            if m.group(2) == "nap":
                return ma + timedelta(days=n)
            if m.group(2) == "hét":
                return ma + timedelta(weeks=n)
            # hónap: ugyanaz a nap n hónappal később (ha létezik)
            ho = (ma.month - 1 + n) % 12 + 1
            ev = ma.year + (ma.month - 1 + n) // 12
            try:
                return date(ev, ho, ma.day)
            except ValueError:
                return None

    # 5) Napnevek: kedden, jövő pénteken, ezen a héten szerdán
    m = re.search(rf"\b(?:(jövő|következő)\s+)?({NAP_RE})\w*", s)
    if m:
        cel = NAPTOVEK[m.group(2)]
        het_eleje = ma - timedelta(days=ma.weekday())
        if m.group(1) or re.search(r"\b(jövő|következő)\s+hét", s):
            return het_eleje + timedelta(weeks=1, days=cel)
        if re.search(r"\b(ezen a|e)\s+hét", s):
            return het_eleje + timedelta(days=cel)
        kulonbseg = (cel - ma.weekday()) % 7
        return ma + timedelta(days=kulonbseg or 7)

    # 6) Csak nap: 25-én / 25-ére
    m = re.search(r"\b(\d{1,2})-(?:án|én|ára|ére)\b", s)
    if m:
        nap = int(m.group(1))
        try:
            d = date(ma.year, ma.month, nap)
        except ValueError:
            return None
        if d < ma:
            ho = ma.month % 12 + 1
            ev = ma.year + (1 if ma.month == 12 else 0)
            try:
                d = date(ev, ho, nap)
            except ValueError:
                return None
        return d

    # 7) Ma
    if re.search(r"\bm(a|ára)\b", s):
        return ma

    return None


def _napszak(s):
    if re.search(r"\bdélután", s):
        return "délután"
    if re.search(r"\beste\b|\besti\b", s):
        return "este"
    if re.search(r"\béjjel", s):
        return "éjjel"
    if re.search(r"\breggel|\bdélelőtt", s):
        return "délelőtt"
    return None


def _igazit(ora, napszak, megjegyzesek):
    """12 órás alakból 24 órásba a napszak alapján."""
    if ora >= 12:
        return ora
    if napszak in ("délután", "este"):
        return ora + 12
    if napszak == "éjjel":
        return ora + 12 if ora >= 8 else ora
    if napszak is None and 1 <= ora <= 6:
        megjegyzesek.append(f"{ora} óra napszak nélkül: délutánt feltételeztem ({ora + 12} óra)")
        return ora + 12
    return ora


def ido_keresese(szoveg):
    """Visszaad: (kezdes, vege, megtalált szövegrészek, megjegyzések)."""
    s = szoveg.lower()
    napszak = _napszak(s)
    megj = []

    def ido(o, p=0):
        o = _igazit(o, napszak, megj)
        if 0 <= o <= 23 and 0 <= p <= 59:
            return time(o, p)
        return None

    # 1) Sáv: 3-tól 5-ig, 14:00-tól 15:30-ig, háromtól ötig
    m = re.search(rf"\b{ORA}(?:[:.](\d{{2}}))?\s*-?\s*(?:tól|től)\s+{ORA}(?:[:.](\d{{2}}))?\s*-?\s*ig\b", s)
    if m:
        k = ido(_szam(m.group(1)), int(m.group(2) or 0))
        v = ido(_szam(m.group(3)), int(m.group(4) or 0))
        if k and v and v <= k and v.hour < 12:
            v = time(v.hour + 12, v.minute)
        return k, v, [m.span()], megj

    # 2) fél / negyed / háromnegyed + óra
    m = re.search(rf"\b(háromnegyed|negyed|fél)\s*{ORA}(?!\d)(?!\s*ór)", s)
    if m:
        alap = _szam(m.group(2)) - 1
        alap = 12 if alap == 0 else alap
        perc = {"negyed": 15, "fél": 30, "háromnegyed": 45}[m.group(1)]
        return ido(alap, perc), None, [m.span()], megj

    # 3) óó:pp vagy óó.pp-kor
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", s) or \
        re.search(r"\b(\d{1,2})\.(\d{2})\s*-?\s*(?:kor|órakor)\b", s)
    if m:
        return ido(int(m.group(1)), int(m.group(2))), None, [m.span()], megj

    # 4) 15 óra 30 perckor
    m = re.search(rf"\b{ORA}\s*órakor\b|\b{ORA}\s*óra\s+(\d{{1,2}})\s*perc", s)
    if m:
        if m.group(1):
            return ido(_szam(m.group(1))), None, [m.span()], megj
        return ido(_szam(m.group(2)), int(m.group(3))), None, [m.span()], megj

    # 5) 3-kor, háromkor
    m = re.search(rf"\b{ORA}\s*-?\s*kor\b", s)
    if m:
        return ido(_szam(m.group(1))), None, [m.span()], megj

    # 6) délután 3, este 7
    m = re.search(rf"\b(?:reggel|délelőtt|délután|este|éjjel)\s+{ORA}\b(?!\s*(?:nap|hét|perc))", s)
    if m:
        return ido(_szam(m.group(1))), None, [m.span()], megj

    # 7) délben
    m = re.search(r"\bdélben\b", s)
    if m:
        return time(12, 0), None, [m.span()], megj

    return None, None, [], megj


def idotartam_keresese(szoveg):
    s = szoveg.lower()
    m = re.search(r"\b(másfél|háromnegyed|negyed|fél)\s*(órás|órán|órát|óra hossz|óráig)", s)
    if m:
        return {"másfél": 90, "háromnegyed": 45, "negyed": 15, "fél": 30}[m.group(1)]
    m = re.search(rf"\b{PERC_SZAM}\s*(órás|órán át|órán keresztül|órát|óra hossz|óráig)", s)
    if m and _szam(m.group(1)):
        return _szam(m.group(1)) * 60
    m = re.search(rf"\b{PERC_SZAM}\s*perc(es|ig|re|et)?\b", s)
    if m and _szam(m.group(1)):
        return _szam(m.group(1))
    return None


def ertelmez(szoveg, ma):
    e = Ertelmezes()
    e.datum = datum_keresese(szoveg, ma)
    e.kezdes, e.vege, talalatok, e.megjegyzesek = ido_keresese(szoveg)

    # Az időtartamot az időpont nélküli szövegben keressük,
    # hogy a "15 óra 30 perc" ne legyen 30 perces időtartam.
    maradek = szoveg.lower()
    for eleje, vege in sorted(talalatok, reverse=True):
        maradek = maradek[:eleje] + " " + maradek[vege:]
    e.idotartam_perc = idotartam_keresese(maradek)
    return e
