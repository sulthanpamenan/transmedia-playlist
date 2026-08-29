import re
import requests

CHANNELS = {
    "Trans7": "https://20.detik.com/live/trans-7",
    "Trans TV": "https://20.detik.com/live/trans-tv",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
    "Referer": "https://20.detik.com/",
}


def get_m3u8_direct(page_url):
    session = requests.Session()
    try:
        res = session.get(page_url, headers=HEADERS, timeout=10)
        res.raise_for_status()

        pattern = r'https://video\.detik\.com/[^"\']+\.m3u8\?[^"\']+'
        matches = re.findall(pattern, res.text)

        if matches:
            return matches[0]

        embed_pattern = r'https://20\.detik\.com/watch/[^"\']+'
        embed_matches = re.findall(embed_pattern, res.text)

        if embed_matches:
            embed_url = embed_matches[0]
            embed_res = session.get(embed_url, headers=HEADERS, timeout=10)
            matches_embed = re.findall(pattern, embed_res.text)
            if matches_embed:
                return matches_embed[0]

    except Exception as e:
        print(f"  [!] Error on {page_url}: {e}")

    return None


def generate_playlist():
    m3u_content = "#EXTM3U\n"

    for name, url in CHANNELS.items():
        print(f"Fetching stream for {name}...")
        stream_url = get_m3u8_direct(url)

        if stream_url:
            print(f"  [+] Success: {stream_url[:75]}...")
            m3u_content += f'#EXTINF:-1 tvg-name="{name}", {name}\n'
            m3u_content += f"{stream_url}\n"
        else:
            print(f"  [-] Failed to retrieve m3u8 for {name}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

    print("\n[✓] Finished processing playlist.m3u")


if __name__ == "__main__":
    generate_playlist()
