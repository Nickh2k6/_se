"""小三通船班表：從交通部航港局下載每月公告的 PDF，解析成 data/ships/YYYY-MM.json。

航港局公告頁：https://www.motcmpb.gov.tw/Information?SiteId=1&NodeId=543
每個月一則公告，內含「金廈船班表」與「金泉航班表」兩個 PDF。

PDF 轉文字需要 poppler 的 pdftotext（Ubuntu：sudo apt install poppler-utils；macOS：brew install poppler）。
用法：python3 ships.py   （下載當月與下個月）
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
SHIP_DIR = os.path.join(ROOT, "data", "ships")
MPB = "https://www.motcmpb.gov.tw"
LIST_URL = MPB + "/Information?SiteId=1&NodeId=543"
TW = timezone(timedelta(hours=8))
ROUTES = {"金廈": "KMXM", "金泉": "KMQZ"}  # PDF 標題關鍵字 → TDX 航線代碼


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 kinmen-trip-helper"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def list_months():
    """回傳 {(年, 月): 公告網址}，年份已由民國轉為西元。"""
    page = get(LIST_URL).decode("utf-8", "ignore")
    out = {}
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        m = re.search(r"(\d+)年(\d+)月金門小三通航班表", re.sub(r"<[^>]+>", "", text))
        if m and "/Information/Detail/" in href:
            out[(int(m.group(1)) + 1911, int(m.group(2)))] = MPB + html.unescape(href)
    return out


def pdf_links(detail_url):
    page = get(detail_url).decode("utf-8", "ignore")
    return [MPB + html.unescape(h) for h in re.findall(r'href="(/ServerFile/Get/[^"]+)"', page)]


def pdf_to_text(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True,
                              text=True, check=True).stdout


def parse(text, year, month):
    """解析 pdftotext -layout 的輸出。

    表格每列是「日期 星期 船名×N」，N 等於表頭的開航時間數；前一半是金門出發，後一半是回金門。
    某天欄位數對不上（例如停航、加班船）時不猜，標記成 irregular，請使用者看原始 PDF。
    """
    title = next((l.strip() for l in text.splitlines() if "小三通" in l), "")
    route = next((rid for k, rid in ROUTES.items() if k in title), None)
    lines = text.splitlines()
    times = []
    for line in lines:
        found = re.findall(r"\b\d{1,2}:\d{2}\b", line)
        if len(found) >= 2 and not re.match(r"\s*\d{1,2}/\d{1,2}", line):
            times = found
            break
    if not route or not times or len(times) % 2:
        raise ValueError(f"無法辨識的船班表格式：{title or '（無標題）'}")
    half = len(times) // 2
    days, irregular = {}, []
    for line in lines:
        m = re.match(r"\s*(\d{1,2})/(\d{1,2})\s+週.\s+(.*)", line)
        if not m:
            continue
        date = f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
        ships = m.group(3).split()
        if len(ships) != len(times):
            irregular.append(date)
            continue
        days[date] = {
            "outbound": [{"time": t, "ship": s} for t, s in zip(times[:half], ships[:half])],
            "inbound": [{"time": t, "ship": s} for t, s in zip(times[half:], ships[half:])],
        }
    # 備註區的金門端訂位電話，例如「大榮海運(馬可波羅1號)：082-373007」；被換行切斷的就不抓
    phones = [{"company": c, "phone": p} for c, p in
              re.findall(r"([^\s\d.、：]+\([^)]+\))：\s*(082-\d[\d、~\-]*)", text)]
    return {"route_id": route, "title": title, "month": f"{year}-{month:02d}",
            "outbound_times": times[:half], "inbound_times": times[half:],
            "days": days, "irregular_days": irregular, "phones": phones}


def update(months_ahead=1, log=print):
    """下載當月起算 months_ahead 個月的船班表。回傳成功存檔的檔名。"""
    if not shutil.which("pdftotext"):
        raise RuntimeError("找不到 pdftotext，請先安裝 poppler-utils")
    now = datetime.now(TW)
    wanted = []
    y, m = now.year, now.month
    for _ in range(months_ahead + 1):
        wanted.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    available = list_months()
    os.makedirs(SHIP_DIR, exist_ok=True)
    saved = []
    for ym in wanted:
        if ym not in available:
            log(f"{ym[0]}-{ym[1]:02d}：航港局尚未公告")
            continue
        result = {"source": available[ym], "fetched": now.isoformat(), "routes": {}}
        for link in pdf_links(available[ym]):
            try:
                data = parse(pdf_to_text(get(link)), *ym)
            except (ValueError, subprocess.CalledProcessError) as e:
                log(f"  略過 {link}：{e}")
                continue
            data["pdf"] = link
            result["routes"][data["route_id"]] = data
            log(f"  {data['title']}：{len(data['days'])} 天，每天金門出發 {len(data['outbound_times'])} 班"
                + (f"，{len(data['irregular_days'])} 天格式特殊" if data["irregular_days"] else ""))
        if result["routes"]:
            name = f"{ym[0]}-{ym[1]:02d}.json"
            with open(os.path.join(SHIP_DIR, name), "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=1)
            saved.append(name)
            log(f"{name} 已儲存")
    return saved


def today_schedule(route_id, now):
    """回傳 (今天的班次 dict, 這個月的資料) 或 (None, None)。"""
    path = os.path.join(SHIP_DIR, now.strftime("%Y-%m") + ".json")
    if not os.path.exists(path):
        return None, None
    with open(path, encoding="utf-8") as f:
        month = json.load(f)
    r = month["routes"].get(route_id)
    if not r:
        return None, None
    return r["days"].get(now.strftime("%Y-%m-%d")), {**r, "source": month["source"]}


if __name__ == "__main__":
    try:
        update()
    except Exception as e:
        print("更新失敗：", e)
        sys.exit(1)
