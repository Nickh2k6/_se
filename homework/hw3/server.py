#!/usr/bin/env python3
"""金門返台交通助手 後端

只用 Python 標準函式庫。負責：
- 管理 TDX 的 OAuth token，代理 TDX（航班、公車、船班航線）與中央氣象署 API
- 快取（記憶體 + cache/ 目錄），避免撞到 TDX 的限流；API 失敗時回傳舊資料
- 綜合航班狀態、能見度、濃霧特報、預報，算出停飛風險燈號
- 模擬模式（?demo=1）：重播 data/demo/ 裡的霧季停飛資料

用法：python3 server.py [port]
"""
import gzip
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import ships

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT, "cache")
DATA_DIR = os.path.join(ROOT, "data")
TW = timezone(timedelta(hours=8))

TDX_TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_BASE = "https://tdx.transportdata.tw/api/basic"
CWA_BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

KINMEN_STATION = "467110"   # 氣象署金門站（金城鎮）
AIRPORT_TOWN = "金湖鎮"      # 尚義機場所在鄉鎮，用它的預報

AIRPORTS = {
    "KNH": "金門", "TSA": "臺北松山", "TPE": "桃園", "RMQ": "臺中", "KHH": "高雄",
    "TNN": "臺南", "CYI": "嘉義", "MZG": "澎湖", "LZN": "馬祖南竿", "MFK": "馬祖北竿",
    "HUN": "花蓮", "TTT": "臺東", "PIF": "屏東",
}
AIRLINES = {"AE": "華信航空", "B7": "立榮航空", "DA": "德安航空", "CI": "中華航空", "BR": "長榮航空"}

# 各資料快取秒數
TTL = {"dep": 120, "arr": 120, "obs": 600, "fog": 600, "fcst": 1800, "bus_eta": 60,
       "bus_routes": 86400, "ship_routes": 86400}


# ---------- 設定 ----------

def load_env():
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


# ---------- HTTP 與快取 ----------

def http_json(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers={
        "Accept-Encoding": "gzip", "User-Agent": "kinmen-trip-helper/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw)


_cache = {}
_cache_lock = threading.Lock()


def cached(key, ttl, fetch):
    """回傳 (data, meta)。過期就重抓；重抓失敗則回傳舊資料並標示 stale。"""
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            path = os.path.join(CACHE_DIR, key + ".json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    entry = _cache[key] = json.load(f)
    if entry and time.time() - entry["ts"] < ttl:
        return entry["data"], {"updated": entry["ts"], "stale": False}
    try:
        data = fetch()
    except Exception as e:  # 網路錯誤、限流、金鑰錯誤都走這裡
        if entry:
            return entry["data"], {"updated": entry["ts"], "stale": True, "error": str(e)}
        raise
    entry = {"ts": time.time(), "data": data}
    with _cache_lock:
        _cache[key] = entry
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, key + ".json"), "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
    return data, {"updated": entry["ts"], "stale": False}


# ---------- TDX ----------

_tdx_lock = threading.Lock()
_tdx_token = {"value": None, "exp": 0}
_tdx_last_call = [0.0]


def tdx_token():
    if _tdx_token["value"] and time.time() < _tdx_token["exp"] - 60:
        return _tdx_token["value"]
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": os.environ["TDX_CLIENT_ID"],
        "client_secret": os.environ["TDX_CLIENT_SECRET"],
    }).encode()
    d = http_json(TDX_TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body)
    _tdx_token.update(value=d["access_token"], exp=time.time() + d.get("expires_in", 3600))
    return _tdx_token["value"]


def tdx(path, **params):
    params.setdefault("$format", "JSON")
    url = f"{TDX_BASE}{path}?{urllib.parse.urlencode(params)}"
    with _tdx_lock:  # TDX 限流很嚴，所有請求排隊、間隔至少 1.5 秒
        wait = 1.5 - (time.time() - _tdx_last_call[0])
        if wait > 0:
            time.sleep(wait)
        try:
            return http_json(url, {"Authorization": "Bearer " + tdx_token()})
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"TDX {e.code}（{'限流' if e.code == 429 else e.reason}）") from None
        finally:
            _tdx_last_call[0] = time.time()


def cwa(dataset, **params):
    params["Authorization"] = os.environ["CWA_API_KEY"]
    url = f"{CWA_BASE}/{dataset}?{urllib.parse.urlencode(params, doseq=True)}"
    d = http_json(url)
    if d.get("success") != "true":
        raise RuntimeError("氣象署 API 回傳失敗")
    return d["records"]


# ---------- 資料整理 ----------

def flight_status(remark):
    """把 FIDS 的備註轉成狀態代碼。"""
    r = remark or ""
    if "取消" in r:
        return "cancelled"
    if "延" in r:
        return "delayed"
    if any(k in r for k in ("已飛", "出發", "離站", "抵達", "已到")):
        return "done"
    if "更改" in r:
        return "changed"
    if any(k in r for k in ("檢查", "安檢", "登機", "報到")):
        return "boarding"
    return "ontime"


# 備註用語不直覺，統一成好懂的說法（TDX 的「檢查」就是官網的「安檢」）
REMARK_LABEL = {"檢查": "安檢中", "安檢": "安檢中", "已飛": "已起飛", "出發": "已起飛", "離站": "已起飛"}


def flight_record(date, airline, number, airport, sched, actual, est, remark, gate="", booking=None):
    status = flight_status(remark)
    m = re.search(r"預計(?:到站)?(\d{1,2}:\d{2})", remark)
    if m:
        est = m.group(1)
    # TDX 和官網都會在還沒起飛／抵達的航班填「實際時間」（其實是預估），只在已完成時才採用
    if status != "done":
        actual = ""
    return {
        "date": date, "flight": f"{airline} {number}".strip(),
        "airline": AIRLINES.get(airline, airline),
        "airport": airport, "airport_name": AIRPORTS.get(airport, airport),
        "scheduled": sched, "actual": actual, "estimated": est if est != sched else "",
        "gate": gate, "remark": remark, "label": REMARK_LABEL.get(remark, remark),
        "status": status, "booking": booking,
    }


def normalize_flights(rows, kind):
    """TDX FIDS → 統一格式。"""
    out = []
    for f in rows:
        d = "Departure" if kind == "dep" else "Arrival"
        out.append(flight_record(
            f.get("FlightDate"), f.get("AirlineID", ""), f.get("FlightNumber", ""),
            f["ArrivalAirportID"] if kind == "dep" else f["DepartureAirportID"],
            f.get(f"Schedule{d}Time", "")[11:16], f.get(f"Actual{d}Time", "")[11:16],
            f.get(f"Estimated{d}Time", "")[11:16], f.get(f"{d}Remark", ""), gate=f.get("Gate", "")))
    out.sort(key=lambda x: (x["date"] or "", x["scheduled"]))
    return out


# ---------- 金門航空站官網 ----------

KMA_URL = {"dep": "https://www.kma.gov.tw/main/MoreDeparture.aspx",
           "arr": "https://www.kma.gov.tw/main/MoreArrival.aspx"}
# 用表頭的中文找欄位，官網調整欄位順序也不會抓錯
KMA_COLS = {"date": "日期", "airline": "航空公司", "flight": "班次", "airport": "機場",
            "sched_dep": "預計起飛", "act_dep": "實際起飛", "sched_arr": "預計到站",
            "act_arr": "實際到站", "remark": "備註", "booking": "訂位"}
KMA_AIRLINES = {"華信": "AE", "立榮": "B7", "德安": "DA"}
KMA_AIRPORTS = {"臺北": "TSA", "台北": "TSA", "桃園": "TPE", "臺中": "RMQ", "台中": "RMQ", "嘉義": "CYI",
                "臺南": "TNN", "台南": "TNN", "高雄": "KHH", "澎湖": "MZG", "屏東": "PIF",
                "花蓮": "HUN", "臺東": "TTT", "台東": "TTT"}


def kma_fetch(kind):
    """抓官網的當日即時班表，回傳 [{欄位: 文字}]。表格格式不對就丟例外，改用 TDX。"""
    req = urllib.request.Request(KMA_URL[kind], headers={"User-Agent": "Mozilla/5.0 kinmen-trip-helper"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        page = resp.read().decode("utf-8", "ignore")
    page = page[page.find('class="TableList"'):]
    rows = [[" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())
             for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            for r in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)]
    if not rows:
        raise ValueError("官網找不到航班表格")
    head = [h.split(" ")[0] for h in rows[0]]
    idx = {k: i for k, kw in KMA_COLS.items() for i, h in enumerate(head) if kw in h}
    sched = "sched_dep" if kind == "dep" else "sched_arr"
    if not {"date", "airline", "flight", "airport", sched, "remark"} <= idx.keys():
        raise ValueError("官網航班表格式改變")
    return [{k: r[i] for k, i in idx.items()} for r in rows[1:] if len(r) == len(head)]


def normalize_kma(rows, kind, now):
    cn = lambda s: (re.match(r"[一-鿿]+", s or "") or [""])[0]  # 「臺北Taipei」→「臺北」
    out = []
    for r in rows:
        mm, dd = int(r["date"][:2]), int(r["date"][2:4])
        year = now.year - 1 if mm - now.month > 6 else now.year + 1 if now.month - mm > 6 else now.year
        remark = re.sub(r"[A-Za-z][A-Za-z .]*$", "", r["remark"]).strip()  # 「離站DEPARTED」→「離站」
        airline = KMA_AIRLINES.get(cn(r["airline"]), cn(r["airline"]))
        airport = KMA_AIRPORTS.get(cn(r["airport"]), cn(r["airport"]))
        if kind == "dep":
            sched, actual = r.get("sched_dep", ""), r.get("act_dep", "")
        else:
            sched, actual = r.get("sched_arr", ""), r.get("act_arr", "")
        out.append(flight_record(f"{year}-{mm:02d}-{dd:02d}", airline, r["flight"], airport,
                                 sched, actual, "", remark, booking=r.get("booking") or None))
    out.sort(key=lambda x: (x["date"], x["scheduled"]))
    return out


def get_flights(kind, now, errors):
    """先用金門航空站官網；抓不到或格式改變時改用 TDX。回傳 (航班, meta)。"""
    try:
        rows, meta = cached("kma_" + kind, TTL[kind], lambda: kma_fetch(kind))
        if not rows:
            raise ValueError("官網沒有航班資料")
        return normalize_kma(rows, kind, now), {**meta, "source": "金門航空站"}
    except Exception as e:
        kma_error = str(e)
    path = "/v2/Air/FIDS/Airport/" + ("Departure" if kind == "dep" else "Arrival") + "/KNH"
    name = "departures" if kind == "dep" else "arrivals"
    rows, meta = safe(name, lambda: cached(kind, TTL[kind], lambda: tdx(path)), errors)
    if meta is None:
        return [], None
    return normalize_flights(rows or [], kind), {**meta, "source": "TDX", "fallback_reason": kma_error}


def parse_visibility(desc):
    """'>30'、'5'、'<0.1' → 公里數（float），無法解析回傳 None。"""
    m = re.search(r"[\d.]+", desc or "")
    return float(m.group()) if m else None


def summarize_obs(records):
    st = records["Station"][0]
    w = st["WeatherElement"]
    return {
        "station": st["StationName"], "time": st["ObsTime"]["DateTime"],
        "weather": w.get("Weather"), "visibility_desc": w.get("VisibilityDescription"),
        "visibility_km": parse_visibility(w.get("VisibilityDescription")),
        "temp": w.get("AirTemperature"), "humidity": w.get("RelativeHumidity"),
        "wind": w.get("WindSpeed"),
    }


def kinmen_fog_alerts(records, now):
    out = []
    for i in records.get("info", []):
        areas = [a.get("areaDesc", "") for a in i.get("area", [])]
        if not any("金門" in a for a in areas) and "金門" not in i.get("description", ""):
            continue
        if datetime.fromisoformat(i["expires"]) < now:
            continue
        out.append({"headline": i.get("headline"), "description": i.get("description"),
                    "effective": i.get("effective"), "expires": i.get("expires"), "web": i.get("web")})
    return out


def fog_risk(temp, dew, rh, wind, weather):
    """以露點差、濕度、風速推估起霧可能（推估，非官方）。"""
    if weather and "霧" in weather:
        return "high"
    try:
        spread, rh, wind = float(temp) - float(dew), float(rh), float(wind)
    except (TypeError, ValueError):
        return "unknown"
    if spread <= 1.5 and rh >= 90 and wind <= 4:
        return "high"
    if spread <= 3 and rh >= 85:
        return "medium"
    return "low"


def summarize_forecast(records, now):
    loc = records["Locations"][0]["Location"][0]
    by_time = {}
    for e in loc["WeatherElement"]:
        for t in e["Time"]:
            key = t.get("DataTime") or t.get("StartTime")
            by_time.setdefault(key, {}).update(t["ElementValue"][0])
    slots = []
    weather = wind = None
    for key in sorted(by_time):
        v = by_time[key]
        # 天氣現象、風速不是每小時都有，沿用上一筆
        weather = v.get("Weather", weather)
        wind = v.get("WindSpeed", wind)
        if "Temperature" not in v or datetime.fromisoformat(key) < now - timedelta(hours=1):
            continue
        slots.append({
            "time": key, "temp": v.get("Temperature"), "dew": v.get("DewPoint"),
            "humidity": v.get("RelativeHumidity"), "wind": wind, "weather": weather,
            "fog": fog_risk(v.get("Temperature"), v.get("DewPoint"), v.get("RelativeHumidity"), wind, weather),
        })
    return {"town": loc["LocationName"], "slots": slots[:24]}


def analyze(dep, arr, obs, alerts, fcst, now):
    today = now.strftime("%Y-%m-%d")
    todays = [f for f in dep if f["date"] == today]
    count = lambda s: sum(1 for f in todays if f["status"] == s)
    cancelled, delayed = count("cancelled"), count("delayed")
    arr_cancelled = sum(1 for f in arr if f["date"] == today and f["status"] == "cancelled")
    vis = obs.get("visibility_km") if obs else None
    next24 = [s for s in (fcst or {}).get("slots", [])
              if datetime.fromisoformat(s["time"]) <= now + timedelta(hours=24)]
    fog_slots = [s for s in next24 if s["fog"] == "high"]

    reasons = []
    if cancelled:
        reasons.append(f"今天已有 {cancelled} 班離境航班取消")
    if arr_cancelled:
        reasons.append(f"{arr_cancelled} 班飛往金門的航班取消（飛機沒來，回程也會受影響）")
    if delayed:
        reasons.append(f"{delayed} 班航班延誤")
    if vis is not None and vis < 5:
        reasons.append(f"金門目前能見度 {obs['visibility_desc']} 公里")
    if alerts:
        reasons.append("氣象署對金門發布濃霧特報")
    if fog_slots:
        reasons.append(f"未來 24 小時有 {len(fog_slots)} 個時段推估容易起霧（最早 {fog_slots[0]['time'][5:16].replace('T', ' ')}）")

    if cancelled >= 2 or (cancelled and vis is not None and vis < 1.6):
        level, title = "red", "停飛中"
    elif (vis is not None and vis < 1.6) or alerts or delayed >= 3 or cancelled or arr_cancelled:
        level, title = "orange", "可能停飛"
    elif fog_slots or delayed or (vis is not None and vis < 5):
        level, title = "yellow", "請留意"
    else:
        level, title = "green", "正常"

    advice = {
        "green": ["航班大致正常，照原計畫出發即可。"],
        "yellow": ["可能起霧，若行程彈性，可考慮改搭中午前後的航班（霧通常在早晚較濃）。",
                   "出發前再確認一次航班狀態。"],
        "orange": ["盡快聯繫航空公司確認，或先登記後面航班的候補。",
                   "若有台胞證，可評估小三通到廈門再飛臺灣的替代路線。",
                   "隨時留意下方航班狀態變化。"],
        "red": ["已有多班取消：立刻向航空公司辦理改票或候補，霧散後通常會加開班次。",
                "趕時間的話可考慮小三通（水頭碼頭 → 廈門五通）再從廈門轉機飛臺灣，需台胞證。",
                "下方有前往水頭碼頭、機場的公車資訊。"],
    }[level]
    return {"level": level, "title": title, "reasons": reasons or ["目前沒有異常狀況"],
            "advice": advice,
            "stats": {"departures": len(todays), "cancelled": cancelled, "delayed": delayed,
                      "done": count("done"), "arr_cancelled": arr_cancelled}}


# ---------- 模擬模式 ----------

def demo_data(now):
    """讀取 data/demo/，把日期換成今天，讓霧季停飛情境隨時可以展示。"""
    with open(os.path.join(DATA_DIR, "demo", "fog_day.json"), encoding="utf-8") as f:
        d = json.load(f)
    today = now.strftime("%Y-%m-%d")
    for f in d["departures"] + d["arrivals"]:
        f["date"] = today
    d["obs"]["time"] = now.replace(minute=now.minute // 10 * 10, second=0, microsecond=0).isoformat()
    d["fog_alerts"][0]["effective"] = now.replace(hour=5, minute=30, second=0, microsecond=0).isoformat()
    d["fog_alerts"][0]["expires"] = (now + timedelta(hours=4)).replace(second=0, microsecond=0).isoformat()
    base = now.replace(minute=0, second=0, microsecond=0)
    for i, s in enumerate(d["forecast"]["slots"]):
        s["time"] = (base + timedelta(hours=i)).isoformat()
    return d


# ---------- API ----------

def safe(name, fn, errors):
    try:
        return fn()
    except Exception as e:
        errors[name] = str(e)
        return None, None


def api_status(demo):
    now = datetime.now(TW)
    if demo:
        d = demo_data(now)
        meta = {"demo": True}
        analysis = analyze(d["departures"], d["arrivals"], d["obs"], d["fog_alerts"], d["forecast"], now)
        return {"now": now.isoformat(), "analysis": analysis, "departures": d["departures"],
                "arrivals": d["arrivals"], "obs": d["obs"], "fog_alerts": d["fog_alerts"],
                "forecast": d["forecast"], "meta": meta, "errors": {}}

    errors, meta = {}, {}
    dep, meta["departures"] = get_flights("dep", now, errors)
    arr, meta["arrivals"] = get_flights("arr", now, errors)
    obs, meta["obs"] = safe("obs", lambda: cached(
        "obs", TTL["obs"], lambda: cwa("O-A0003-001", StationId=KINMEN_STATION)), errors)
    fog, meta["fog_alerts"] = safe("fog_alerts", lambda: cached(
        "fog", TTL["fog"], lambda: cwa("W-C0033-010")), errors)
    fc, meta["forecast"] = safe("forecast", lambda: cached(
        "fcst", TTL["fcst"], lambda: cwa("F-D0047-085", LocationName=AIRPORT_TOWN)), errors)

    obs = summarize_obs(obs) if obs else None
    alerts = kinmen_fog_alerts(fog, now) if fog else []
    fcst = summarize_forecast(fc, now) if fc else None
    for k in list(errors):
        if meta.get(k) is None:
            meta.pop(k, None)
    for k, m in meta.items():  # 有舊資料可用時，把錯誤一併告訴前端
        if m and m.get("error"):
            errors[k] = m["error"]
    return {"now": now.isoformat(), "analysis": analyze(dep, arr, obs, alerts, fcst, now),
            "departures": dep, "arrivals": arr, "obs": obs, "fog_alerts": alerts,
            "forecast": fcst, "meta": meta, "errors": errors}


def load_alternatives():
    with open(os.path.join(DATA_DIR, "alternatives.json"), encoding="utf-8") as f:
        return json.load(f)


def add_ship_schedules(alt, now):
    """把航港局船班表（ships.py 下載的）裡今天的班次放進替代方案。"""
    for s in alt["ships"]:
        today, month = ships.today_schedule(s["route_id"], now)
        s["departures"] = (today or {}).get("outbound", [])
        s["phones"] = (month or {}).get("phones", [])
        s["pdf"] = (month or {}).get("pdf")
        s["schedule_loaded"] = month is not None


def api_alternatives():
    """替代方案：小三通（航港局船班表 + TDX 航線票價）與公車即時到站。"""
    alt = load_alternatives()
    errors = {}
    add_ship_schedules(alt, datetime.now(TW))

    routes, _ = safe("ship_routes", lambda: cached(
        "ship_routes", TTL["ship_routes"], lambda: tdx("/v3/Ship/Route")), errors)
    tdx_routes = {r["RouteID"]: r for r in (routes or {}).get("Routes", [])}
    for s in alt["ships"]:
        r = tdx_routes.get(s["route_id"])
        if r:
            s["tdx_description"] = r.get("Description")
            s["tdx_price"] = (r.get("TicketPriceDescription") or {}).get("Zh_tw")

    # 公車：一次查回設定檔裡所有「路線 × 上車站」的即時到站
    routes_q = sorted({r for b in alt["buses"] for r in b["routes"]})
    stops_q = sorted({b["from_stop"] for b in alt["buses"]})
    flt = "({}) and ({})".format(" or ".join(f"RouteName/Zh_tw eq '{r}'" for r in routes_q),
                                 " or ".join(f"StopName/Zh_tw eq '{s}'" for s in stops_q))
    eta, _ = safe("bus_eta", lambda: cached(
        "bus_eta", TTL["bus_eta"],
        lambda: tdx("/v2/Bus/EstimatedTimeOfArrival/City/KinmenCounty", **{"$filter": flt})), errors)
    for b in alt["buses"]:
        first = {}  # 環狀路線同一站會出現兩次（起點與終點），取序號最小的「上車」那筆
        for e in eta or []:
            name = e["RouteName"]["Zh_tw"]
            if name in b["routes"] and e["StopName"]["Zh_tw"] == b["from_stop"]:
                if name not in first or e["StopSequence"] < first[name]["StopSequence"]:
                    first[name] = e
        b["eta"] = [bus_eta(e) for e in first.values()]
        b["eta"].sort(key=lambda x: (x["minutes"] is None, x["minutes"] or 0, x["next_bus"]))
    alt["errors"] = errors
    return alt


BUS_STATUS = {1: "尚未發車", 2: "交管不停靠", 3: "末班車已過", 4: "今日未營運"}


def bus_eta(e):
    sec = e.get("EstimateTime")
    return {"route": e["RouteName"]["Zh_tw"],
            "minutes": sec // 60 if sec is not None else None,
            "status": BUS_STATUS.get(e.get("StopStatus"), ""),
            "next_bus": (e.get("NextBusTime") or "")[11:16]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=os.path.join(ROOT, "public"), **kw)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        demo = q.get("demo", ["0"])[0] == "1"
        try:
            if url.path == "/api/status":
                return self.send_json(api_status(demo))
            if url.path == "/api/alternatives":
                return self.send_json(api_alternatives() if not demo else demo_alternatives())
        except Exception as e:
            return self.send_json({"error": str(e)}, 500)
        return super().do_GET()

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))


def demo_alternatives():
    alt = load_alternatives()
    add_ship_schedules(alt, datetime.now(TW))
    with open(os.path.join(DATA_DIR, "demo", "fog_day.json"), encoding="utf-8") as f:
        demo_eta = json.load(f)["bus_eta"]
    for b in alt["buses"]:
        b["eta"] = demo_eta.get(b["id"], [])
    alt["errors"] = {}
    return alt


def ship_updater():
    """背景執行：缺當月船班表就下載；之後每 12 小時檢查一次（月底會抓到下個月的公告）。"""
    while True:
        now = datetime.now(TW)
        nxt = (now.replace(day=1) + timedelta(days=32)).strftime("%Y-%m")
        have = set(os.listdir(ships.SHIP_DIR)) if os.path.isdir(ships.SHIP_DIR) else set()
        if now.strftime("%Y-%m") + ".json" not in have or (now.day >= 20 and nxt + ".json" not in have):
            try:
                ships.update(log=lambda m: print("[船班表]", m))
            except Exception as e:
                print("[船班表] 更新失敗：", e)
        time.sleep(12 * 3600)


def main():
    load_env()
    missing = [k for k in ("TDX_CLIENT_ID", "TDX_CLIENT_SECRET", "CWA_API_KEY") if not os.environ.get(k)]
    if missing:
        print("缺少設定：" + "、".join(missing) + "，請參考 .env.example 建立 .env（模擬模式仍可使用）")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"金門返台交通助手：http://localhost:{port}/   （模擬模式：http://localhost:{port}/?demo=1）")
    threading.Thread(target=ship_updater, daemon=True).start()
    Server(("", port), Handler).serve_forever()


class Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return  # 瀏覽器在回應前關掉連線，不必印錯誤
        super().handle_error(request, client_address)


if __name__ == "__main__":
    main()
