import time
from playwright.sync_api import sync_playwright

CHANNELS = {
    "Trans7": "https://20.detik.com/live/trans-7",
    "Trans TV": "https://20.detik.com/live/trans-tv",
}


def capture_stream(page_url):
    m3u8_url = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            extra_http_headers={
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://20.detik.com/",
            },
        )

        page = context.new_page()

        # Stealth: Sembunyikan flag navigator.webdriver
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () =>"
            " undefined})"
        )

        def handle_request(request):
            nonlocal m3u8_url
            url = request.url
            if ".m3u8" in url and "wowzatokenhash" in url:
                if not m3u8_url:
                    m3u8_url = url

        page.on("request", handle_request)

        try:
            page.goto(page_url, timeout=40000, wait_until="domcontentloaded")
            time.sleep(3)

            # Simulasi interaksi klik pada player video
            try:
                page.click("video", timeout=3000)
            except Exception:
                page.mouse.click(500, 300)

            # Tunggu hingga token m3u8 terdeteksi
            for _ in range(20):
                if m3u8_url:
                    break
                time.sleep(0.5)

        except Exception as e:
            print(f"  [!] Error: {e}")
        finally:
            browser.close()

    return m3u8_url


def main():
    m3u_content = "#EXTM3U\n"
    success_count = 0

    for name, page_url in CHANNELS.items():
        print(f"Mengambil stream {name}...")
        stream_url = capture_stream(page_url)

        if stream_url:
            print(f"  [+] Berhasil: {stream_url[:75]}...")
            m3u_content += f'#EXTINF:-1 tvg-name="{name}", {name}\n'
            m3u_content += f"{stream_url}\n"
            success_count += 1
        else:
            print(f"  [-] Gagal mendapatkan stream {name}")

    if success_count > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        print("\n[✓] Playlist berhasil diperbarui di playlist.m3u")
    else:
        print("\n[!] Gagal memperbarui playlist.")


if __name__ == "__main__":
    main()
