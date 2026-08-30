import time
import requests
from playwright.sync_api import sync_playwright

RAILWAY_URL = "https://transmedia-playlist.up.railway.app/update_token"

CHANNELS = {
    "trans7": "https://20.detik.com/live/trans-7",
    "transtv": "https://20.detik.com/live/trans-tv",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"


def fetch_single_channel(channel_key, page_url):
    m3u8_url = None
    cookies_dict = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--autoplay-policy=no-user-gesture-required",
                ],
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 720},
                extra_http_headers={"Referer": "https://20.detik.com/"},
            )
            page = context.new_page()

            def handle_request(req):
                nonlocal m3u8_url
                url = req.url
                if ".m3u8" in url and "wowzatoken" in url:
                    if "ads" not in url.lower() and "advert" not in url.lower():
                        m3u8_url = url

            page.on("request", handle_request)

            print(f"[+] Opening {channel_key} ({page_url})...")
            page.goto(page_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(3)

            click_targets = [
                "video",
                ".vjs-big-play-button",
                "#player",
                ".video-js",
                ".video-ads-skip-button",
                ".skip-ad-button",
            ]
            for target in click_targets:
                try:
                    if page.is_visible(target):
                        page.click(target, timeout=1500)
                except Exception:
                    pass

            page.mouse.click(640, 360)

            for _ in range(40):
                if m3u8_url:
                    break
                time.sleep(0.5)

            for c in context.cookies():
                cookies_dict[c["name"]] = c["value"]

            browser.close()
    except Exception as e:
        print(f"[!] Error fetching {channel_key}: {e}")

    return m3u8_url, cookies_dict


def get_token_with_retry(channel_key, page_url, max_retries=3):
    for attempt in range(1, max_retries + 1):
        print(f"[*] Retrieving token {channel_key} (Attempt {attempt}/{max_retries})...")
        token, cookies = fetch_single_channel(channel_key, page_url)
        if token:
            return token, cookies
        print(f"[!] Ad failed/blocked on attempt {attempt}. Retrying...")
        time.sleep(3)
    return None, {}


for channel, url in CHANNELS.items():
    token, cookies = get_token_with_retry(channel, url)
    if token:
        payload = {"channel": channel, "url": token, "cookies": cookies}
        try:
            res = requests.post(RAILWAY_URL, json=payload, timeout=10)
            print(f"[✓] Token {channel} successfully sent! Response: {res.status_code}\n")
        except Exception as e:
            print(f"[!] Error sending to Railway ({channel}): {e}\n")
    else:
        print(f"[✘] Failed completely to retrieve token {channel}\n")

    time.sleep(3)
