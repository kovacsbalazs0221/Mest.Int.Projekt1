"""Az ellenőrző/összevető lépés tesztjei, kitalált LLM-válaszokkal (nem kell hozzá modell)."""

from datetime import date, datetime

from esemeny_osszeallitas import IDOZONA, osszeallit
from naptar import esemeny_torzs

MOST = datetime(2026, 11, 23, 10, 0, tzinfo=IDOZONA)  # hétfő 10:00


def llm(**kw):
    alap = {"cim": "Teszt", "datum": None, "kezdes": None, "vege": None,
            "idotartam_perc": None, "egesz_napos": False, "helyszin": None, "leiras": None}
    alap.update(kw)
    return alap


def test_szabaly_felulirja_a_hibas_llm_datumot():
    e = osszeallit("Jövő pénteken délután 4-kor megbeszélés",
                   llm(cim="Megbeszélés", datum="2026-11-27", kezdes="16:00"), MOST)
    assert e.kezdes == datetime(2026, 12, 4, 16, 0, tzinfo=IDOZONA)
    assert any("Eltérő dátum" in f for f in e.figyelmeztetesek)


def test_llm_ertek_ha_a_szabaly_nem_talal():
    e = osszeallit("Karácsony előtti napon tízkor", llm(datum="2026-12-23", kezdes="10:00"), MOST)
    assert e.kezdes == datetime(2026, 12, 23, 10, 0, tzinfo=IDOZONA)


def test_alapertelmezett_idotartam():
    e = osszeallit("holnap 10-kor fogorvos", llm(cim="Fogorvos"), MOST)
    assert (e.vege - e.kezdes).total_seconds() == 3600
    e = osszeallit("holnap 10-kor fogorvos", llm(cim="Fogorvos"), MOST, szandek="emlekezteto")
    assert (e.vege - e.kezdes).total_seconds() == 15 * 60


def test_idotartam_szovegbol():
    e = osszeallit("holnap 10-kor két órás vizsga", llm(), MOST)
    assert (e.vege - e.kezdes).total_seconds() == 2 * 3600


def test_egesz_napos():
    e = osszeallit("december 5-én Anna születésnapja", llm(cim="Anna születésnapja", egesz_napos=True), MOST)
    assert e.egesz_napos and e.kezdes == date(2026, 12, 5) and e.vege == date(2026, 12, 6)
    t = esemeny_torzs(e)
    assert t["start"] == {"date": "2026-12-05"} and t["end"] == {"date": "2026-12-06"}


def test_datum_nelkul_ido_ma_vagy_holnap():
    e = osszeallit("15:00-kor hívjam fel Pétert", llm(), MOST)
    assert e.kezdes.date() == date(2026, 11, 23)
    e = osszeallit("8:00-kor hívjam fel Pétert", llm(), MOST)
    assert e.kezdes.date() == date(2026, 11, 24)


def test_hianyzo_datum():
    e = osszeallit("vegyél tejet", llm(cim="Tejvásárlás"), MOST)
    assert "datum" in e.hianyzik


def test_ervenytelen_llm_ertekek():
    e = osszeallit("holnap valamikor", llm(cim="", datum="jövő hét", kezdes="délután"), MOST)
    assert e.egesz_napos and e.kezdes == date(2026, 11, 24)
    assert any("érvénytelen dátum" in f for f in e.figyelmeztetesek)


def test_mult_figyelmeztetes():
    e = osszeallit("ma reggel 8-kor", llm(), MOST)
    assert any("múltban" in f for f in e.figyelmeztetesek)


def test_api_torzs():
    e = osszeallit("holnap 10-kor fogorvos", llm(cim="Fogorvos", helyszin="Rendelő"), MOST)
    t = esemeny_torzs(e)
    assert t["summary"] == "Fogorvos" and t["location"] == "Rendelő"
    assert t["start"]["dateTime"] == "2026-11-24T10:00:00+01:00"
    assert t["start"]["timeZone"] == "Europe/Budapest"
    assert t["reminders"]["overrides"][0]["minutes"] == 30
