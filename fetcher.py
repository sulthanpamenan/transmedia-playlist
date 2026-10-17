import os
import time
import requests
from playwright.sync_api import sync_playwright

GIST_ID = os.environ.get("GIST_ID", "0489abda2da5420f8f4da73add29b134")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GIST_FILENAME = os.environ.get("GIST_FILENAME", "transmedia.json")
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"

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


def load_gist_tokens():
    try:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.get(GIST_API_URL, headers=headers, timeout=10)
        if res.status_code == 200:
            files = res.json().get("files", {})
            file_data = files.get(GIST_FILENAME, {})
            content = file_data.get("content", "{}")
            import json
            return json.loads(content)
    except Exception as e:
        print(f"[!] Error loading existing Gist tokens: {e}")
    return {}


def save_gist_tokens(tokens):
    import json
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    payload = {
        "files": {
            GIST_FILENAME: {
                "content": json.dumps(tokens, indent=4)
            }
        }
    }
    res = requests.patch(GIST_API_URL, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    print("[✓] Gist tokens successfully updated via GitHub Actions!")


if __name__ == "__main__":
    current_tokens = load_gist_tokens()
    updated = False

    for channel, url in CHANNELS.items():
        token, cookies = get_token_with_retry(channel, url)
        if token:
            current_tokens[channel] = {
                "url": token,
                "cookies": cookies
            }
            updated = True
            print(f"[✓] Token {channel} collected successfully!\n")
        else:
            print(f"[✘] Failed completely to retrieve token {channel}\n")
        time.sleep(3)

    if updated:
        try:
            save_gist_tokens(current_tokens)
        except Exception as e:
            print(f"[!] Failed to save tokens to Gist: {e}")
