"""Conversion des cookies capturés par l'extension Chrome vers le format Playwright."""

_SAMESITE = {
    "no_restriction": "None",
    "unspecified": "Lax",
    "lax": "Lax",
    "strict": "Strict",
    "none": "None",
}


def to_playwright(chrome_cookies: list[dict]) -> list[dict]:
    out = []
    for c in chrome_cookies:
        name = c.get("name")
        value = c.get("value")
        domain = c.get("domain")
        if not name or value is None or not domain:
            continue
        cookie = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": c.get("path", "/"),
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", False)),
            "sameSite": _SAMESITE.get(str(c.get("sameSite", "")).lower(), "Lax"),
        }
        # expirationDate (float epoch) → expires ; sinon cookie de session
        exp = c.get("expirationDate")
        if exp and not c.get("session"):
            cookie["expires"] = float(exp)
        out.append(cookie)
    return out
