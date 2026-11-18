from transcript import atir
from hangfajl_kezeles import hangrogzit

fajlnev = hangrogzit()

if fajlnev is not None:
    atirat = atir(fajlnev)
    print("Átirat:", atirat)