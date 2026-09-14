import json
import html
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
    "Referer": "https://sevenhub.id/",
    "X-Nextjs-Data": "1",
}

def test_trans7():
    base_url = "https://sevenhub.id/live"
    print("[*] Mengakses halaman utama Sevenhub...")
    
    try:
        res_main = requests.get(base_url, headers=HEADERS, timeout=15)
        print(f"Main Page Status: {res_main.status_code}")
        
        if res_main.status_code != 200:
            print("[!] Gagal mengakses halaman utama.")
            return

        soup = BeautifulSoup(res_main.text, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        
        if not script_tag or not script_tag.string:
            print("[!] Tag __NEXT_DATA__ tidak ditemukan.")
            return

        next_data = json.loads(script_tag.string)
        build_id = next_data.get("buildId")
        print(f"[✓] Berhasil mendapatkan Build ID: {build_id}")

        url = f"https://sevenhub.id/_next/data/{build_id}/live.json"
        print(f"[*] Mengambil data dari endpoint: {url}")
        
        res = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Trans 7 API Status: {res.status_code}")

        if res.status_code == 200:
            data = res.json()
            schedules = data.get("pageProps", {}).get("schedules", {}).get("data", {})
            schedule_list = schedules.get("data_schedule", [])
            
            print(f"[✓] Berhasil mengambil {len(schedule_list)} program:")
            for item in schedule_list:
                print(f"[{item.get('time_start')} - {item.get('time_end')}] {html.unescape(item.get('program', ''))}")
        else:
            print(f"[!] Gagal mengambil JSON API. Response text: {res.text[:200]}")

    except Exception as e:
        print(f"[!] Terjadi error: {e}")

if __name__ == "__main__":
    test_trans7()
