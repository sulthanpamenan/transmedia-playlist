import time
import requests
from playwright.sync_api import sync_playwright

RAILWAY_URL = "https://transmedia-playlist.up.railway.app/update_token"

CHANNELS = {
    "trans7": "https://20.detik.com/live/trans-7",
    "transtv": "https://20.detik.com/live/trans-tv",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"


def fetch_channel_token(channel_key, page_url):
    m3u8_url = None
    cookies_dict = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = browser.new_context(
                user_agent=USER_AGENT, viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()

            def handle_request(req):
                nonlocal m3u8_url
                if ".m3u8" in req.url and "wowzatoken" in req.url:
                    if not m3u8_url:
                        m3u8_url = req.url

            page.on("request", handle_request)

            print(f"[+] Opening page {channel_key}: {page_url}")
            page.goto(page_url, timeout=35000, wait_until="domcontentloaded")
            time.sleep(2)

            try:
                page.click("video", timeout=2500)
            except Exception:
                page.mouse.click(500, 300)

            for _ in range(15):
                if m3u8_url:
                    break
                time.sleep(0.5)

            for c in context.cookies():
                cookies_dict[c["name"]] = c["value"]

            browser.close()
    except Exception as e:
        print(f"[!] Error fetching {channel_key}: {e}")

    return m3u8_url, cookies_dict


for channel, url in CHANNELS.items():
    token, cookies = fetch_channel_token(channel, url)
    if token:
        payload = {"channel": channel, "url": token, "cookies": cookies}
        res = requests.post(RAILWAY_URL, json=payload, timeout=10)
        print(f"[✓] {channel} token sent to Railway! Status: {res.status_code}")
    else:
        print(f"[!] Failed to get token for {channel}")

    time.sleep(3)
