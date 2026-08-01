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

    # 1) Login-Seite abrufen
    headers_browser = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    r = SESSION.get(LOGIN_URL, params=params, headers=headers_browser, timeout=20)
    r.raise_for_status()

    # 2) JS-Datei extrahieren
    import re
    js_match = re.search(r'src="(/assets/login[^"]+\.js)"', r.text)
    if not js_match:
        raise RuntimeError("Login-JS nicht gefunden")

    js_url = "https://login.solaredge.com" + js_match.group(1)

    r_js = SESSION.get(js_url, headers=headers_browser, timeout=20)
    r_js.raise_for_status()

    # 3) API-Endpoint extrahieren
    api_match = re.search(r'"/api/[^"]+"', r_js.text)
    if not api_match:
        raise RuntimeError("Login-API nicht gefunden")

    api_endpoint = "https://login.solaredge.com" + api_match.group(0).strip('"')

    # 4) CSRF-Token aus API holen
    r_api = SESSION.get(api_endpoint, headers=headers_browser, timeout=20)
    r_api.raise_for_status()

    csrf_token = r_api.json().get("csrf")
    if not csrf_token:
        raise RuntimeError("CSRF-Token nicht im API-JSON gefunden")

    # 5) Login absenden
    data = {
        "username": USERNAME,
        "password": PASSWORD,
        "_csrf": csrf_token,
        "rememberMe": "true",
    }

    headers_post = {
        "User-Agent": headers_browser["User-Agent"],
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": r.url,
    }

    r2 = SESSION.post(
        LOGIN_URL,
        params=params,
        data=data,
        headers=headers_post,
        allow_redirects=True,
        timeout=20
    )
    r2.raise_for_status()

    # 6) Authorization Code extrahieren
    final_url = r2.url
    parsed = urllib.parse.urlparse(final_url)
    qs = urllib.parse.parse_qs(parsed.query)

    if "code" not in qs:
        raise RuntimeError("Kein Authorization Code in Redirect-URL gefunden")

    auth_code = qs["code"][0]

    # 7) Access Token holen
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
