import os
from urllib.parse import unquote, urljoin
from flask import Flask, Response, request, jsonify
import requests

app = Flask(__name__)

CHANNELS = ["trans7", "transtv"]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

STREAM_CACHE = {}

@app.route("/")
def index():
    return "Proxy Transmedia Active! Access playlist via /playlist.m3u"

@app.route("/update_token", methods=["POST"])
def update_token():
    data = request.json
    if not data or "channel" not in data or "url" not in data:
        return jsonify({"error": "invalid payload"}), 400
    
    STREAM_CACHE[data["channel"]] = {
        "url": data["url"],
        "cookies": data.get("cookies", {})
    }
    print(f"[✓] Token {data['channel']} successfully updated from GitHub Actions!")
    return jsonify({"status": "success", "channel": data["channel"]})

@app.route("/playlist.m3u")
def get_master_playlist():
    m3u_text = "#EXTM3U\n"
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    host_url = request.host

    for channel_key in CHANNELS:
        channel_name = "Trans 7" if channel_key == "trans7" else "Trans TV"
        m3u_text += f'#EXTINF:-1 tvg-id="{channel_key}" tvg-name="{channel_name}", {channel_name}\n'
        m3u_text += f"{scheme}://{host_url}/live/{channel_key}\n"

    return Response(m3u_text, content_type="audio/x-mpegurl")

@app.route("/live/<channel>")
def stream_proxy(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    cached_data = STREAM_CACHE.get(channel)
    if not cached_data or not cached_data.get("url"):
        return "Waiting for a token from GitHub Actions. Please try again in a minute...", 503

    m3u8_url = cached_data["url"]
    cookies = cached_data["cookies"]
    headers = {"User-Agent": USER_AGENT, "Referer": "https://20.detik.com/", "Origin": "https://20.detik.com"}

    res = requests.get(m3u8_url, headers=headers, cookies=cookies)
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
            new_lines.append(f"{scheme}://{request.host}/ts_proxy?channel={channel}&url={encoded_url}")

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
    headers = {"User-Agent": USER_AGENT, "Referer": "https://20.detik.com/", "Origin": "https://20.detik.com"}
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
                new_lines.append(f"{scheme}://{request.host}/ts_proxy?channel={channel}&url={encoded_url}")

        return Response("\n".join(new_lines), content_type="application/vnd.apple.mpegurl")

    res = requests.get(target_url, headers=headers, cookies=cookies, stream=True)
    return Response(res.iter_content(chunk_size=32768), content_type="video/MP2T")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
