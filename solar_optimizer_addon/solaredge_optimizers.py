#!/usr/bin/env python3
import requests
import json
import time
import sys
import urllib.parse
import base64
import hashlib
import os

# --- Konfiguration ---
USERNAME = os.getenv("SE_USERNAME", "")
PASSWORD = os.getenv("SE_PASSWORD", "")
CLIENT_ID = "ugfnsujd3384sshcjehaphlh3"
REDIRECT_URI = "https://monitoring.solaredge.com/mfe/auth/callback"
SITE_ID = "3909779"

LOGIN_URL = "https://login.solaredge.com/login"
TOKEN_URL = "https://login.solaredge.com/oauth2/token"
OPTIMIZERS_URL = (
    f"https://monitoring.solaredge.com/services/cni/ui-api/optimizers"
    f"?siteId={SITE_ID}&include-optimizers=true"
)

SESSION = requests.Session()


def _pkce_pair():
    """Erzeugt Code-Verifier und Code-Challenge für OAuth2 PKCE."""
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8").rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("utf-8")).digest()
    ).decode("utf-8").rstrip("=")
    return verifier, challenge


def login_and_get_token():
    """Führt den SolarEdge OAuth2 Login durch und liefert ein Access Token."""
    verifier, challenge = _pkce_pair()

    params = {
        "lang": "de",
        "response_type": "code",
        "client_id": CLIENT_ID,
        "scope": "email openid",
        "redirect_uri": REDIRECT_URI,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }

    # 1) Login-Seite holen
    r = SESSION.get(LOGIN_URL, params=params, timeout=20)
    r.raise_for_status()

    # 2) Login absenden
    data = {
        "username": USERNAME,
        "password": PASSWORD,
        "rememberMe": "true",
    }
    r2 = SESSION.post(
        LOGIN_URL, params=params, data=data, allow_redirects=True, timeout=20
    )
    r2.raise_for_status()

    # 3) Authorization Code aus Redirect extrahieren
    final_url = r2.url
    parsed = urllib.parse.urlparse(final_url)
    qs = urllib.parse.parse_qs(parsed.query)

    if "code" not in qs:
        raise RuntimeError("Kein Authorization Code in Redirect-URL gefunden")

    auth_code = qs["code"][0]

    # 4) Access Token holen
    data_token = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
    }

    t = SESSION.post(TOKEN_URL, data=data_token, timeout=20)
    t.raise_for_status()
    token_data = t.json()

    if "access_token" not in token_data:
        raise RuntimeError("Kein access_token im Token-Response")

    return token_data["access_token"]


def fetch_optimizers(access_token):
    """Fragt die Optimizer-Daten ab."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    r = SESSION.get(OPTIMIZERS_URL, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def get_optimizers_data():
    """
    Holt die Optimizer-Daten und gibt ein Python-Dict zurück.
    Diese Funktion wird vom HTTP-Server verwendet.
    """
    try:
        token = login_and_get_token()
        data = fetch_optimizers(token)

        optimizers = []
        for opt in data.get("optimizers", []):
            optimizers.append({
                "id": opt.get("id"),
                "serial": opt.get("serialNumber"),
                "model": opt.get("model"),
                "string": opt.get("stringId"),
                "power": opt.get("power"),
                "energy": opt.get("energy"),
                "temperature": opt.get("temperature"),
                "status": opt.get("status"),
            })

        return {
            "timestamp": int(time.time()),
            "optimizers": optimizers,
        }

    except Exception as e:
        return {"error": str(e), "optimizers": []}


def main():
    """CLI-Ausgabe für Debugging oder direkten Aufruf."""
    data = get_optimizers_data()
    print(json.dumps(data))


if __name__ == "__main__":
    main()
