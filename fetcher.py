import time
import requests
from playwright.sync_api import sync_playwright

RAILWAY_URL = "https://transmedia-playlist.up.railway.app/update_token"

CHANNELS = {
    "trans7": "https://20.detik.com/live/trans-7",
    "transtv": "https://20.detik.com/live/trans-tv",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

def fetch_token(page_url):
    m3u8_url = None
    cookies_dict = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1280, "height": 720})
            page = context.new_page()
            
            def handle_request(req):
                nonlocal m3u8_url
                if ".m3u8" in req.url and "wowzatoken" in req.url:
                    if not m3u8_url:
                        m3u8_url = req.url

            page.on("request", handle_request)
            page.goto(page_url, timeout=30000)
            time.sleep(2)
            try:
                page.click("video", timeout=2000)
            except Exception:
                page.mouse.click(500, 300)
            
            for _ in range(15):
                if m3u8_url: break
                time.sleep(0.5)

            for c in context.cookies():
                cookies_dict[c["name"]] = c["value"]
                
            browser.close()
    except Exception as e:
        print(f"Error fetching {page_url}: {e}")
        
    return m3u8_url, cookies_dict

for channel, url in CHANNELS.items():
    print(f"Retrieving token for {channel}...")
    token, cookies = fetch_token(url)
    if token:
        res = requests.post(RAILWAY_URL, json={"channel": channel, "url": token, "cookies": cookies})
        print(f"Send to Railway ({channel}): {res.status_code}")
    else:
        print(f"Failed to get token for {channel}")
