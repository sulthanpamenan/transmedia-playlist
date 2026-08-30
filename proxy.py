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


def fetch_token_playwright_light(page_url):
    m3u8_url = None
    cookies_dict = {}

    try:
        with sync_playwright() as p:
            # Gunakan Chromium dengan argumen paling hemat memori
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-zygote",
                    "--single-process",
                ],
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 800, "height": 600},
                extra_http_headers={"Referer": "https://20.detik.com/"},
            )
            page = context.new_page()

            def handle_request(req):
                nonlocal m3u8_url
                url = req.url
                if ".m3u8" in url and "wowzatoken" in url:
                    if not m3u8_url:
                        m3u8_url = url

            page.on("request", handle_request)

            page.goto(page_url, timeout=20000, wait_until="domcontentloaded")
            time.sleep(1.5)

            try:
                page.click("video", timeout=1500)
            except Exception:
                page.mouse.click(400, 300)

            for _ in range(10):
                if m3u8_url:
                    break
                time.sleep(0.5)

            for c in context.cookies():
                cookies_dict[c["name"]] = c["value"]

            browser.close()
    except Exception as e:
        print(f"[!] Playwright Fetch Error ({page_url}): {e}")

    return m3u8_url, cookies_dict


def background_token_worker():
    while True:
        print("\n[+] Background Worker: Fetching M3U8 tokens...")
        for key, url in CHANNELS.items():
            token_url, cookies = fetch_token_playwright_light(url)
            if token_url:
                STREAM_CACHE[key] = {"url": token_url, "cookies": cookies}
                print(f"  [✓] {key} token updated!")
            else:
                print(f"  [!] Failed to update {key}")

        print("[+] Background Worker: Waiting 20 minutes for next refresh.\n")
        time.sleep(1200)


worker_thread = threading.Thread(target=background_token_worker, daemon=True)
worker_thread.start()


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
    
    # Ambil token darurat secara langsung jika cache belum siap
    if not cached_data or not cached_data.get("url"):
        token_url, cookies = fetch_token_playwright_light(CHANNELS[channel])
        if token_url:
            cached_data = {"url": token_url, "cookies": cookies}
            STREAM_CACHE[channel] = cached_data
        else:
            return "Token preparing...", 503

    m3u8_url = cached_data["url"]
    cookies = cached_data["cookies"]

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://20.detik.com/",
        "Origin": "https://20.detik.com",
    }

    res = requests.get(m3u8_url, headers=headers, cookies=cookies)
    if res.status_code != 200:
        # Jika token kedaluwarsa/memicu 403/503, paksa refresh token baru
        token_url, cookies = fetch_token_playwright_light(CHANNELS[channel])
        if token_url:
            STREAM_CACHE[channel] = {"url": token_url, "cookies": cookies}
            res = requests.get(token_url, headers=headers, cookies=cookies)

    if res.status_code != 200:
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
            full_url = line if line.startswith("http") else urljoin(base_url, line)
            encoded_url = requests.utils.quote(full_url)
            new_lines.append(
                f"{scheme}://{request.host}/ts_proxy?channel={channel}&url={encoded_url}"
            )

    return Response("\n".join(new_lines), content_type="application/vnd.apple.mpegurl")


@app.route("/ts_proxy")
def ts_proxy():
    segment_url = request.args.get("url")
    channel = request.args.get("channel", "trans7")

    if not segment_url:
        return "Invalid segment URL", 400

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
                full_url = line if line.startswith("http") else urljoin(base_url, line)
                encoded_url = requests.utils.quote(full_url)
                new_lines.append(
                    f"{scheme}://{request.host}/ts_proxy?channel={channel}&url={encoded_url}"
                )

        return Response("\n".join(new_lines), content_type="application/vnd.apple.mpegurl")

    res = requests.get(target_url, headers=headers, cookies=cookies, stream=True)
    return Response(res.iter_content(chunk_size=32768), content_type="video/MP2T")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
