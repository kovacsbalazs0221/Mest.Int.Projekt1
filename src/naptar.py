from pathlib import Path

GYOKER = Path(__file__).resolve().parent.parent
TITKOS = GYOKER / "titkos"
CREDENTIALS = TITKOS / "credentials.json"
TOKEN = TITKOS / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
IDOZONA_NEV = "Europe/Budapest"


def esemeny_torzs(e):
    torzs = {"summary": e.cim}
    if e.helyszin:
        torzs["location"] = e.helyszin
    if e.leiras:
        torzs["description"] = e.leiras

    if e.egesz_napos:
        torzs["start"] = {"date": e.kezdes.isoformat()}
        torzs["end"] = {"date": e.vege.isoformat()}
    else:
        torzs["start"] = {"dateTime": e.kezdes.isoformat(), "timeZone": IDOZONA_NEV}
        torzs["end"] = {"dateTime": e.vege.isoformat(), "timeZone": IDOZONA_NEV}
        if e.emlekezteto_perc is not None:
            torzs["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": e.emlekezteto_perc}],
            }
    return torzs


def _szolgaltatas():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    hitel = None
    if TOKEN.exists():
        hitel = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not hitel or not hitel.valid:
        if hitel and hitel.expired and hitel.refresh_token:
            hitel.refresh(Request())
        else:
            if not CREDENTIALS.exists():
                raise FileNotFoundError(
                    f"Hiányzik: {CREDENTIALS}\nLásd: docs/BEALLITAS.md (Google Naptár beállítása)")
            folyamat = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            hitel = folyamat.run_local_server(port=0)
        TITKOS.mkdir(exist_ok=True)
        TOKEN.write_text(hitel.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=hitel)


def letrehoz(e, naptar_id="primary"):
    """Létrehozza az eseményt, és visszaadja a Google Naptár linkjét."""
    szolg = _szolgaltatas()
    eredmeny = szolg.events().insert(calendarId=naptar_id, body=esemeny_torzs(e)).execute()
    return eredmeny.get("htmlLink")
