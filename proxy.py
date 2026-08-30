import os
import re
import threading
import time
from urllib.parse import unquote, urljoin
from flask import Flask, Response, request
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


def fetch_detik_token(page_url):
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://20.detik.com/",
    }
    m3u8_url = None
    cookies_dict = {}

    try:
        session = requests.Session()
        res = session.get(page_url, headers=headers, timeout=15)

        if res.status_code == 200:
            pattern = r'https://[^\s"\']+\.m3u8\?[^\s"\']*wowzatoken[^\s"\']*'
            matches = re.findall(pattern, res.text)

            if matches:
                m3u8_url = matches[0].replace("\\/", "")
            else:
                video_id_match = re.search(r'video_id\s*:\s*["\']([^"\']+)["\']', res.text) or \
                                 re.search(r'data-id=["\']([^"\']+)["\']', res.text)
                
                if video_id_match:
                    video_id = video_id_match.group(1)
                    api_url = f"https://20.detik.com/api/video/stream?id={video_id}"
                    api_res = session.get(api_url, headers=headers)
                    if api_res.status_code == 200:
                        data = api_res.json()
                        m3u8_url = data.get("stream_url") or data.get("m3u8")

            for c in session.cookies:
                cookies_dict[c.name] = c.value

    except Exception as e:
        print(f"[!] Fetch Error ({page_url}): {e}")

    return m3u8_url, cookies_dict


def background_token_worker():
    while True:
        print("\n[+] Background Worker: Fetching stream tokens...")
        for key, url in CHANNELS.items():
            token_url, cookies = fetch_detik_token(url)
            if token_url:
                STREAM_CACHE[key] = {"url": token_url, "cookies": cookies}
                print(f"  [✓] {key} token successfully cached!")
            else:
                print(f"  [!] Failed to extract token for {key}")

        print("[+] Background Worker: Waiting 15 minutes for next refresh.\n")
        time.sleep(900)


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
    
    if not cached_data or not cached_data.get("url"):
        token_url, cookies = fetch_detik_token(CHANNELS[channel])
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

    try:
        res = requests.get(m3u8_url, headers=headers, cookies=cookies, timeout=10)
        if res.status_code != 200:
            token_url, cookies = fetch_detik_token(CHANNELS[channel])
            if token_url:
                STREAM_CACHE[channel] = {"url": token_url, "cookies": cookies}
                res = requests.get(token_url, headers=headers, cookies=cookies, timeout=10)

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

    except Exception as e:
        return f"Stream error: {e}", 500


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
