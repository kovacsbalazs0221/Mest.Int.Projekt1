"""A szándékfelismerés szabályalapú kapujának tesztjei (a modell nem töltődik be)."""

import pytest

from szandek import szabaly_kapu


@pytest.mark.parametrize("szoveg", [
    "Mesélj egy viccet.",
    "Kapcsold fel a villanyt a nappaliban.",
    "Milyen idő lesz holnap?",
    "Mit főzzek ma vacsorára?",
])
def test_nem_naptarugy(szoveg):
    assert szabaly_kapu(szoveg) is not None


@pytest.mark.parametrize("szoveg", [
    "Holnap délután háromkor fogorvos.",
    "December 5-én Anna születésnapja.",
    "Emlékeztetnél holnap 8-kor, hogy hívjam fel Pétert?",   # kérdés, de emlékeztető-kérés
])
def test_naptarugy(szoveg):
    assert szabaly_kapu(szoveg) is None
