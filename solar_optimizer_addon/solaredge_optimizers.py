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
USERNAME = os.getenv("SE_USERNAME", "wurstbrot30@hotmail.com")
PASSWORD = os.getenv("SE_PASSWORD", "x14h&fBQrTn:")
CLIENT_ID = "ugfnsujd3384sshcjehaphlh3"
REDIRECT_URI = "https://monitoring.solaredge.com/mfe/auth/callback"
SITE_ID = "3909779"

LOGIN_URL = "https://login.solaredge.com/login"
TOKEN_URL = "https://login.solaredge.com/oauth2/token"
OPTIMIZERS_URL = f"https://monitoring.solaredge.com/services/cni/ui-api/optimizers?siteId={SITE_ID}&include-optimizers=true"

SESSION = requests.Session()


def _pkce_pair():
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8").rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("utf-8")).digest()
    ).decode("utf-8").rstrip("=")
    return verifier, challenge


def login_and_get_token():
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

    # 1) Login‑Seite holen (Form + Cookies)
    r = SESSION.get(LOGIN_URL, params=params, timeout=20)
    r.raise_for_status()

    # 2) Login‑Formular absenden
    data = {
        "username": USERNAME,
        "password": PASSWORD,
        "rememberMe": "true",
    }
    r2 = SESSION.post(LOGIN_URL, params=params, data=data, allow_redirects=True, timeout=20)
    r2.raise_for_status()

    # 3) Redirect mit Authorization Code abfangen
    #    Der Code steckt in der URL der letzten Weiterleitung
    final_url = r2.url
    parsed = urllib.parse.urlparse(final_url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "code" not in qs:
        raise RuntimeError("Kein Authorization Code in Redirect‑URL gefunden")

    auth_code = qs["code"][0]

    # 4) Code gegen Access Token tauschen
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
        raise RuntimeError("Kein access_token im Token‑Response")

    return token_data["access_token"]


def fetch_optimizers(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    r = SESSION.get(OPTIMIZERS_URL, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def main():
    try:
        token = login_and_get_token()
        data = fetch_optimizers(token)

        # Erwartete Struktur: Liste von Optimierern
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

        out = {
            "timestamp": int(time.time()),
            "optimizers": optimizers,
        }
        print(json.dumps(out))

    except Exception as e:
        # Bei Fehlern ein leeres, aber gültiges JSON ausgeben,
        # damit HA nicht komplett aussteigt
        err = {"error": str(e), "optimizers": []}
        print(json.dumps(err))
        sys.exit(1)


if __name__ == "__main__":
    main()
