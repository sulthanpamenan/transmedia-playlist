from datetime import datetime, timedelta
import json
import html
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://sevenhub.id/",
    "X-Nextjs-Data": "1",
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
                                "end": "",
                                "title": clean_title,
                                "desc": "",
                                "category": "General",
                            })
    except Exception as e:
        print(f"[!] Error Trans TV EPG: {e}")

    return programs


import json

def get_trans7_schedule():
    programs = []
    build_id = "CIO-V18echGfrT93WPcqd"
    url = f"https://sevenhub.id/_next/data/{build_id}/live.json"

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            
            schedules = data.get("pageProps", {}).get("schedules", {}).get("data", {})
            schedule_list = schedules.get("data_schedule", [])
            
            if not schedule_list:
                today_str = datetime.now().strftime("%Y-%m-%d")
                week_schedules = data.get("pageProps", {}).get("schedules", {}).get("weekSchedules", {}).get("data", [])
                for day_sched in week_schedules:
                    if day_sched.get("date_schedule_tv") == today_str:
                        schedule_list = day_sched.get("data_schedule_tv", [])
                        break

            for item in schedule_list:
                raw_title = item.get("program", "")
                start_time = item.get("time_start", "")
                end_time = item.get("time_end", "")
                
                clean_title = html.unescape(raw_title).strip().upper()
                if start_time and clean_title:
                    programs.append({
                        "start": start_time,
                        "end": end_time,
                        "title": clean_title,
                        "desc": "",
                        "category": "General",
                    })
        else:
            print(f"[!] Trans 7 API Error Status: {res.status_code}")
    except Exception as e:
        print(f"[!] Error Trans 7 JSON API: {e}")

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

                if p.get("end"):
                    eh, em = map(int, p["end"].split(":"))
                    end_dt = datetime(
                        today.year, today.month, today.day, eh, em
                    )
                    if end_dt <= start_dt:
                        end_dt += timedelta(days=1)
                else:
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
