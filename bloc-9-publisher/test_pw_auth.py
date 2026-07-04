"""Test non destructif : session portée par Chromium headless + appel API interne
depuis la page (fetch). Vérifie l'auth sans rien publier."""
import asyncio
import httpx
from playwright.async_api import async_playwright
from cookies import to_playwright


async def main():
    sess = httpx.get("http://localhost:8000/api/v1/sessions/linkedin/cookies", timeout=20).json()
    cookies = to_playwright(sess["cookies"])
    ua = sess.get("user_agent")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=ua or None, locale="fr-FR")
        await context.add_cookies(cookies)
        page = await context.new_page()
        resp = await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=45_000)
        print("goto /feed/ -> HTTP", resp.status if resp else "?", "| url finale:", page.url[:70])

        # Appel API interne DEPUIS la page : hérite des cookies + csrf du navigateur
        result = await page.evaluate("""async () => {
            const csrf = (document.cookie.match(/JSESSIONID="?([^;"]+)"?/) || [])[1] || '';
            const r = await fetch('/voyager/api/me', {
                headers: { 'csrf-token': csrf, 'accept': 'application/vnd.linkedin.normalized+json+2.1',
                           'x-restli-protocol-version': '2.0.0' },
                credentials: 'include'
            });
            const t = await r.text();
            return { status: r.status, body: t.slice(0, 200) };
        }""")
        print("fetch /voyager/api/me ->", result["status"])
        print("corps:", result["body"])
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
