import sounddevice as sd
import soundfile as sf
import numpy as np
import keyboard
import time

M_frek = 16000
Fajlnev = "felvetel.wav"

print("A program elindult...")
print("Kezdődhet a beszéd! Tartsd lenyomva a spacet, ameddig beszélni kívánsz...")

while not keyboard.is_pressed('space'):
    time.sleep(0.05)

print("A rögzítés elindult!")

hangadat = []                      # ide gyűjtjük a blokkokat
blokkmeret = int(M_frek * 0.1)     # 0,1 mp-es blokk

with sd.InputStream(samplerate=M_frek,
                    channels=1, # ez a mono-t jelöli
                    dtype='float32') as adatfolyam:
    while keyboard.is_pressed('space'):
        blokk, _ = adatfolyam.read(blokkmeret)
        hangadat.append(blokk)

print("Felvétel vége, mentés...")

if len(hangadat) > 0:
    felvett_audio = np.concatenate(hangadat, axis=0)
    sf.write(Fajlnev, felvett_audio, M_frek)
    print(f"Mentve ide: {Fajlnev} (Hossz: {len(felvett_audio) / M_frek:.1f} másodperc)")
else:
    print("Túl rövid volt a gombnyomás.")