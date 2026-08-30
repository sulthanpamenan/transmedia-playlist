import os
import threading
import time
from urllib.parse import unquote, urljoin
from flask import Flask, Response, request
from playwright.sync_api import sync_playwright
import requests

app = Flask(__name__)

CHANNELS = {
    "trans7": "https://20.detik.com/live/trans-7",
    "transtv": "https://20.detik.com/live/trans-tv",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)

STREAM_CACHE = {}


def fetch_token_and_cookies(page_url):
    m3u8_url = None
    cookies_dict = {}

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

        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        def handle_request(req):
            nonlocal m3u8_url
            url = req.url
            if ".m3u8" in url and "wowzatoken" in url:
                if not m3u8_url:
                    m3u8_url = url

        page.on("request", handle_request)

        try:
            page.goto(page_url, timeout=25000, wait_until="domcontentloaded")
            time.sleep(2)

            try:
                page.click("video", timeout=2000)
            except Exception:
                page.mouse.click(500, 300)

            for _ in range(15):
                if m3u8_url:
                    break
                time.sleep(0.5)

            raw_cookies = context.cookies()
            for c in raw_cookies:
                cookies_dict[c["name"]] = c["value"]

        except Exception as e:
            print(f"[!] Playwright Fetch Error: {e}")
        finally:
            browser.close()

    return m3u8_url, cookies_dict


def background_token_worker():
    while True:
        print("\n[+] Background Worker: Updating M3U8 tokens & cookies...")
        for key, url in CHANNELS.items():
            token_url, cookies = fetch_token_and_cookies(url)
            if token_url:
                STREAM_CACHE[key] = {"url": token_url, "cookies": cookies}
                print(f"  [✓] Token & Cookie {key} successfully saved!")
            else:
                print(f"  [!] Failed to update {key}")

        print(
            "[+] Background Worker: Done! Waiting 1 hour for the next refresh.\n"
        )
        time.sleep(3600)


@app.route("/")
def index():
    return "Proxy Transmedia Active! Access playlist via /playlist.m3u"


@app.route("/playlist.m3u")
def get_master_playlist():
    m3u_text = "#EXTM3U\n"
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    host_url = request.host

    for channel_key in CHANNELS.keys():
        channel_name = (
            "Trans 7"
            if channel_key == "trans7"
            else "Trans TV"
            if channel_key == "transtv"
            else channel_key.upper()
        )
        m3u_text += f'#EXTINF:-1 tvg-id="{channel_key}" tvg-name="{channel_name}", {channel_name}\n'
        m3u_text += f"{scheme}://{host_url}/live/{channel_key}\n"

    return Response(m3u_text, content_type="audio/x-mpegurl")


@app.route("/live/<channel>")
def stream_proxy(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    cached_data = STREAM_CACHE.get(channel)
    if not cached_data:
        return "The token is being prepared, please try again...", 503

    m3u8_url = cached_data["url"]
    cookies = cached_data["cookies"]

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://20.detik.com/",
        "Origin": "https://20.detik.com",
    }

    res = requests.get(m3u8_url, headers=headers, cookies=cookies)
    if res.status_code != 200:
        print(f"[-] CDN Return Status: {res.status_code}")
        return f"Error CDN Detik: {res.status_code}", res.status_code

    content = res.text
    base_url = m3u8_url.rsplit("/", 1)[0] + "/"
    scheme = request.headers.get("X-Forwarded-Proto", "https")

    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("#") or not line.strip():
            new_lines.append(line)
        else:
            full_url = (
                line if line.startswith("http") else urljoin(base_url, line)
            )
            encoded_url = requests.utils.quote(full_url)
            new_lines.append(
                f"{scheme}://{request.host}/ts_proxy?channel={channel}&url={encoded_url}"
            )

    return Response(
        "\n".join(new_lines), content_type="application/vnd.apple.mpegurl"
    )


@app.route("/ts_proxy")
def ts_proxy():
    segment_url = request.args.get("url")
    channel = request.args.get("channel", "trans7")

    if not segment_url:
        return "Invalid URL segment", 400

    target_url = unquote(segment_url)
    cached_data = STREAM_CACHE.get(channel, {})
    cookies = cached_data.get("cookies", {})

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://20.detik.com/",
        "Origin": "https://20.detik.com",
    }

    scheme = request.headers.get("X-Forwarded-Proto", "https")

    if ".m3u8" in target_url:
        res = requests.get(target_url, headers=headers, cookies=cookies)
        if res.status_code != 200:
            return f"Error CDN: {res.status_code}", res.status_code

        base_url = target_url.rsplit("/", 1)[0] + "/"
        lines = res.text.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("#") or not line.strip():
                new_lines.append(line)
            else:
                full_url = (
                    line if line.startswith("http") else urljoin(base_url, line)
                )
                encoded_url = requests.utils.quote(full_url)
                new_lines.append(
                    f"{scheme}://{request.host}/ts_proxy?channel={channel}&url={encoded_url}"
                )

        return Response(
            "\n".join(new_lines), content_type="application/vnd.apple.mpegurl"
        )

    res = requests.get(
        target_url, headers=headers, cookies=cookies, stream=True
    )
    return Response(
        res.iter_content(chunk_size=1024 * 32), content_type="video/MP2T"
    )


if __name__ == "__main__":
    worker_thread = threading.Thread(
        target=background_token_worker, daemon=True
    )
    worker_thread.start()

    port_env = os.environ.get("PORT", "5000")
    try:
        port = int(port_env)
    except ValueError:
        port = 5000

    print(f"[+] Proxy server active on port {port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
