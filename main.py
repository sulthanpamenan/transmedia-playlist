from playwright.sync_api import sync_playwright

CHANNELS = {
    "Trans7": "https://20.detik.com/live/trans-7",
    "Trans TV": "https://20.detik.com/live/trans-tv",
}


def capture_m3u8(page_url):
    m3u8_url = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def handle_request(request):
            nonlocal m3u8_url
            url = request.url
            if ".m3u8" in url and "wowzatokenhash" in url:
                if not m3u8_url:
                    m3u8_url = url

        page.on("request", handle_request)

        try:
            page.goto(page_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  [!] Error opening {page_url}: {e}")
        finally:
            browser.close()

    return m3u8_url


def generate_playlist():
    m3u_content = "#EXTM3U\n"

    for name, url in CHANNELS.items():
        print(f"Fetching stream for {name}...")
        stream_url = capture_m3u8(url)

        if stream_url:
            print(f"  [+] Success: {stream_url[:75]}...")
            m3u_content += f'#EXTINF:-1 tvg-name="{name}", {name}\n'
            m3u_content += f"{stream_url}\n"
        else:
            print(f"  [-] Failed to retrieve m3u8 for {name}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

    print("\n[✓] Playlist successfully updated in playlist.m3u")


if __name__ == "__main__":
    generate_playlist()
