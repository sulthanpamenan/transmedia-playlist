from datetime import datetime, timedelta
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests

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
                        title = (
                            title_elem.text.replace(start_time, "")
                            .strip()
                            .upper()
                        )
                        if start_time and title:
                            programs.append({
                                "start": start_time,
                                "title": title,
                                "desc": f"Saksikan tayangan {title} hanya di Trans TV.",
                                "category": "Entertainment",
                            })
    except Exception as e:
        print(f"[!] Error Trans TV EPG: {e}")

    return programs


def get_trans7_schedule():
    programs = []
    url = "https://sevenhub.id/live"

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            build_id_match = re.search(r'"buildId":"([^"]+)"', res.text)
            if build_id_match:
                build_id = build_id_match.group(1)
                json_url = f"https://sevenhub.id/_next/data/{build_id}/live.json"
                json_res = requests.get(json_url, headers=HEADERS, timeout=15)

                if json_res.status_code == 200:
                    data = json_res.json()
                    page_props = data.get("pageProps", {})
                    schedules = (
                        page_props.get("schedule", {})
                        or page_props.get("liveSchedule", [])
                    )

                    for item in schedules:
                        title = (
                            item.get("title")
                            or item.get("program_name")
                            or item.get("name")
                        )
                        start_time = item.get("start_time") or item.get("time")
                        desc = item.get("description") or f"Saksikan tayangan {title} di Trans 7."
                        if start_time and title:
                            clean_time = start_time[:5]
                            programs.append({
                                "start": clean_time,
                                "title": title.upper(),
                                "desc": desc,
                                "category": "General",
                            })
    except Exception as e:
        print(f"[!] Error Trans 7 EPG: {e}")

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

                category_elem = ET.SubElement(prog_elem, "category", {"lang": "id"})
                category_elem.text = p.get("category", "General")

            except Exception:
                continue

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    print("[✓] epg.xml successfully generated with full details!")


if __name__ == "__main__":
    t_tv = get_transtv_schedule()
    t_7 = get_trans7_schedule()
    build_xmltv(t_tv, t_7)
