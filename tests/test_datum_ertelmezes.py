"""Egységtesztek a szabályalapú dátum/idő értelmezőhöz. Futtatás: python -m pytest"""

from datetime import date, time

import pytest

from datum_ertelmezes import ertelmez

MA = date(2026, 11, 23)  # hétfő


@pytest.mark.parametrize("szoveg, datum", [
    ("ma este", date(2026, 11, 23)),
    ("holnap", date(2026, 11, 24)),
    ("holnapután", date(2026, 11, 25)),
    ("3 nap múlva", date(2026, 11, 26)),
    ("két hét múlva", date(2026, 12, 7)),
    ("kedden", date(2026, 11, 24)),
    ("hétfőn", date(2026, 11, 30)),            # ma hétfő van -> a következő hétfő
    ("jövő pénteken", date(2026, 12, 4)),
    ("jövő héten szerdán", date(2026, 12, 2)),
    ("ezen a héten csütörtökön", date(2026, 11, 26)),
    ("november 25-én", date(2026, 11, 25)),
    ("január 5-én", date(2027, 1, 5)),        # elmúlt -> jövő év
    ("2026. december 3.", date(2026, 12, 3)),
    ("12. 3.", date(2026, 12, 3)),
    ("2026-12-24", date(2026, 12, 24)),
    ("30-án", date(2026, 11, 30)),
    ("20-án", date(2026, 12, 20)),            # ebben a hónapban elmúlt -> jövő hónap
])
def test_datum(szoveg, datum):
    assert ertelmez(szoveg, MA).datum == datum


@pytest.mark.parametrize("szoveg, kezdes", [
    ("15:30-kor", time(15, 30)),
    ("15.30-kor", time(15, 30)),
    ("délután 3-kor", time(15, 0)),
    ("délután háromkor", time(15, 0)),
    ("este hétkor", time(19, 0)),
    ("reggel 8-kor", time(8, 0)),
    ("10 órakor", time(10, 0)),
    ("14 óra 30 perckor", time(14, 30)),
    ("fél négykor", time(15, 30)),
    ("reggel fél 8-kor", time(7, 30)),
    ("negyed 5-kor", time(16, 15)),
    ("háromnegyed 8-kor", time(7, 45)),
    ("fél egykor", time(12, 30)),
    ("délben", time(12, 0)),
    ("délután 4", time(16, 0)),
    ("3-kor", time(15, 0)),                   # napszak nélkül 1-6 óra -> délután
])
def test_kezdes(szoveg, kezdes):
    assert ertelmez(szoveg, MA).kezdes == kezdes


def test_idosav():
    e = ertelmez("szerdán 3-tól 5-ig labor", MA)
    assert (e.kezdes, e.vege) == (time(15, 0), time(17, 0))
    e = ertelmez("14:00-tól 15:30-ig", MA)
    assert (e.kezdes, e.vege) == (time(14, 0), time(15, 30))
    e = ertelmez("háromtól ötig", MA)
    assert (e.kezdes, e.vege) == (time(15, 0), time(17, 0))


@pytest.mark.parametrize("szoveg, perc", [
    ("két órás megbeszélés", 120),
    ("másfél órás", 90),
    ("fél órás hívás", 30),
    ("45 percig", 45),
    ("2 órán át", 120),
    ("15 óra 30 perckor", None),              # ez időpont, nem időtartam
])
def test_idotartam(szoveg, perc):
    assert ertelmez(szoveg, MA).idotartam_perc == perc


def test_nincs_adat():
    e = ertelmez("vegyél tejet", MA)
    assert e.datum is None and e.kezdes is None and e.idotartam_perc is None
