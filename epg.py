from datetime import datetime, timedelta
import html
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    )
}


def get_transtv_schedule():
    programs = []
    url = "https://www.transtv.co.id/schedule"
    today_str = datetime.now().strftime("%Y-%m-%d")

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            section = soup.find("section", id=today_str) or soup.find(
                "section", class_=re.compile(r"sche__programsBox")
            )

            if section:
                items = section.find_all(
                    "div", class_=re.compile(r"sche__programsList")
                )
                for item in items:
                    time_elem = item.find("h6")
                    title_elem = item.find("a") or item.find("p") or item

                    if time_elem:
                        start_time = time_elem.text.strip()
                        raw_title = (
                            title_elem.text.replace(start_time, "")
                            .strip()
                            .upper()
                        )
                        clean_title = html.unescape(raw_title)
                        if start_time and clean_title:
                            programs.append({
                                "start": start_time,
                                "title": clean_title,
                                "desc": f"Saksikan {clean_title} di Trans TV.",
                                "category": "General",
                            })
    except Exception as e:
        print(f"[!] Error Trans TV EPG: {e}")

    return programs


def get_trans7_schedule():
    programs = []
    url = "https://sevenhub.id/live"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = context.new_page()

            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            page_html = page.content()
            soup = BeautifulSoup(page_html, "html.parser")

            items = soup.find_all(
                "div", class_=re.compile(r"LiveScheduleNew_scheduleItem")
            ) or soup.find_all("div", class_=re.compile(r"scheduleItem|schedule_item"))

            for item in items:
                text = item.text.strip()
                time_match = re.search(
                    r"(\d{2}:\d{2})\s*-\s*\d{2}:\d{2}|\b(\d{2}:\d{2})\b", text
                )
                if time_match:
                    start_time = time_match.group(1) or time_match.group(2)
                    raw_title = re.sub(
                        r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}|\d{2}:\d{2}", "", text
                    ).strip()
                    clean_title = html.unescape(raw_title).upper()
                    if start_time and clean_title:
                        programs.append({
                            "start": start_time,
                            "title": clean_title,
                            "desc": f"Saksikan {clean_title} di Trans 7.",
                            "category": "General",
                        })

            browser.close()
    except Exception as e:
        print(f"[!] Error Trans 7 Playwright EPG: {e}")

    return programs


def format_xmltv_date(dt):
    return dt.strftime("%Y%m%d%H%M%S +0700")


def build_xmltv(transtv_progs, trans7_progs):
    tv = ET.Element("tv", {"generator-info-name": "Transmedia EPG Generator"})

    channels_data = [
        {"id": "transtv", "name": "Trans TV"},
        {"id": "trans7", "name": "Trans 7"},
    ]

    for ch in channels_data:
        channel_elem = ET.SubElement(tv, "channel", {"id": ch["id"]})
        display_name = ET.SubElement(channel_elem, "display-name")
        display_name.text = ch["name"]

    now = datetime.now()
    today = now.date()

    for ch_id, progs in [("transtv", transtv_progs), ("trans7", trans7_progs)]:
        for i, p in enumerate(progs):
            try:
                sh, sm = map(int, p["start"].split(":"))
                start_dt = datetime(
                    today.year, today.month, today.day, sh, sm
                )

                if i < len(progs) - 1:
                    nh, nm = map(int, progs[i + 1]["start"].split(":"))
                    end_dt = datetime(
                        today.year, today.month, today.day, nh, nm
                    )
                    if end_dt <= start_dt:
                        end_dt += timedelta(days=1)
                else:
                    end_dt = start_dt + timedelta(hours=1, minutes=30)

                prog_elem = ET.SubElement(
                    tv,
                    "programme",
                    {
                        "start": format_xmltv_date(start_dt),
                        "stop": format_xmltv_date(end_dt),
                        "channel": ch_id,
                    },
                )
                title_elem = ET.SubElement(prog_elem, "title", {"lang": "id"})
                title_elem.text = p["title"]

                desc_elem = ET.SubElement(prog_elem, "desc", {"lang": "id"})
                desc_elem.text = p.get("desc", "")

                category_elem = ET.SubElement(
                    prog_elem, "category", {"lang": "id"}
                )
                category_elem.text = p.get("category", "General")

            except Exception:
                continue

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    print(
        f"[✓] epg.xml successfully created! (Trans TV: {len(transtv_progs)} programs, Trans 7: {len(trans7_progs)} programs)"
    )


if __name__ == "__main__":
    t_tv = get_transtv_schedule()
    t_7 = get_trans7_schedule()
    build_xmltv(t_tv, t_7)
