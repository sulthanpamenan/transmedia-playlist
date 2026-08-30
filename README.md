# 📺 Transmedia IPTV Proxy & EPG Generator

A lightweight, automated HLS/M3U8 proxy and XMLTV EPG generator for **Trans TV** and **Trans 7** live streams. Designed for seamless integration with IPTV players such as **OTT Navigator**, **TiviMate**, and **IPTV Smarters**.

---

## 🚀 Quick Start / URLs

Directly import these URLs into your preferred IPTV client:

| Resource | URL |
| :--- | :--- |
| **Playlist (M3U)** | https://transmedia-playlist.up.railway.app/playlist.m3u |
| **EPG / Guide (XMLTV)** | https://transmedia-playlist.up.railway.app/epg.xml |

> **Note:** The playlist includes the `url-tvg` tag, allowing modern IPTV players to auto-discover and load the EPG guide automatically upon playlist import.

---

## 📺 Channel Overview

| Channel ID | Channel Name | Category | Group Title |
| :--- | :--- | :--- | :--- |
| transtv | Trans TV | Entertainment / General | General |
| trans7 | Trans 7 | Entertainment / General | General |

---

## 🛠️ Features & Highlights

- **Automated Token Rotation**: Solves Wowza CDN token expiration automatically every 30 minutes.
- **Pre-Roll Ad Bypass**: Intelligent stream link extraction without ad-blocking interruptions.
- **Embedded XMLTV EPG**: Complete electronic program guide with program descriptions and schedules for both channels.
- **High Availability**: Decoupled architecture ensuring continuous playback without memory or resource bottlenecks.

---

## 📱 How to Use in OTT Navigator / IPTV Players

1. Open your IPTV Player (e.g., **OTT Navigator**).
2. Add a new playlist source using **URL**:
   https://transmedia-playlist.up.railway.app/playlist.m3u
3. *(Optional)* If your player does not auto-detect the EPG, add the **EPG / Teleguide URL**:
   https://transmedia-playlist.up.railway.app/epg.xml
4. Reload the playlist and enjoy your stream!

---

## ☕ Support the Developer

If this project is helpful to you, consider supporting the developer to keep this service maintained and running!

<div align="center">

### 🇮🇩 Local Donation (QRIS / E-Wallet / Mobile Banking)

<a href="https://saweria.co/sulthanpamenan" target="_blank">
  <img width="290" height="290" alt="Saweria" src="https://github.com/user-attachments/assets/f2846d1f-a391-4daf-9ce5-a48aadc992a0" />
</a>

<br>

*Scan the QRIS code above using GoPay, DANA, OVO, ShopeePay, LinkAja, or Mobile Banking.*

<br>

<a href="https://saweria.co/sulthanpamenan" target="_blank">
  <img src="https://img.shields.io/badge/Saweria-Support_Project-orange?style=for-the-badge&logo=coffee" alt="Support via Saweria">
</a>

</div>

---

