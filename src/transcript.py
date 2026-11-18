from faster_whisper import WhisperModel
import soundfile as sf


def atir(fajlnev):
    hang, _ = sf.read(fajlnev, dtype="float32")
    modell = WhisperModel("medium", device="cpu", compute_type="int8")
    reszek, _ = modell.transcribe(hang, language="hu")

    atirat = ""
    for resz in reszek:
        atirat += resz.text

    return atirat.strip()
