#!/usr/bin/env python3
"""Tarayıcı: bir pencere için bir shard'ın şehir gruplarını tarar (Madrid → grup gidiş, grup → Madrid dönüş).

  python3 collect.py --window 2026-11-13 --shard 0 --of 4 --out out/

Çıktı out/<pencere>-<shard>.json: {"legs": [{"city", "kind", "date", "flights": [...]}], "queries", "failed", "blocked"}.
fli (Google Flights) komutunu kullanır; sorgular arası bekler; art arda hata olursa shard'ı durdurur (engelleme koruması).
"""
import argparse
import json
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FLI = shutil.which("fli") or "fli"
PAUSE = (1.2, 2.6)
BLOCK_AFTER = 6   # art arda bu kadar başarısız (JSON yok/zaman aşımı) sorguda shard durur


def fli_json(args, timeout=120):
    try:
        out = subprocess.run([FLI, *args, "--format", "json"], capture_output=True, text=True, timeout=timeout).stdout
        return json.loads(out)
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return None


def simplify(d):
    out = []
    for f in d.get("flights", []):
        if not f.get("price"):
            continue
        legs = f["legs"]
        out.append({
            "price": f["price"], "dur": f["duration"], "stops": f.get("stops", len(legs) - 1),
            "dep": legs[0]["departure_time"], "arr": legs[-1]["arrival_time"],
            "frm": legs[0]["departure_airport"]["code"], "to": legs[-1]["arrival_airport"]["code"],
            "al": "/".join(dict.fromkeys(l["airline"]["name"] for l in legs)),
            "fn": ",".join(l["airline"]["code"] + l["flight_number"] for l in legs),
            "via": [l["arrival_airport"]["code"] for l in legs[:-1]], "url": f.get("booking_url"),
        })
    out.sort(key=lambda x: x["price"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", required=True)
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--of", type=int, required=True)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    t = json.loads(Path("targets.json").read_text())
    w = next(x for x in t["windows"] if x["id"] == a.window)
    names = sorted(t["groups"])[a.shard::a.of]
    legs, queries, failed, streak, blocked = [], 0, 0, 0, False
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = []
    for n in names:
        codes = t["groups"][n]
        jobs.append((n, "out", w["out"], t["origin"], codes, w["out_time"]))
        jobs.append((n, "ret", w["ret"], codes, t["origin"], w["ret_time"]))
    random.shuffle(jobs)
    for i, (city, kind, day, o, d, win) in enumerate(jobs):
        if i:
            time.sleep(random.uniform(*PAUSE))
        args = ["flights", o, d, day, "--stops", str(t["max_stops"]), "--currency", t["currency"], "--time", win]
        res = fli_json(args)
        queries += 1
        if res is None:
            failed += 1
            streak += 1
            if streak >= BLOCK_AFTER:
                blocked = True
                print(f"shard durduruldu: {streak} art arda başarısız sorgu", file=sys.stderr)
                break
            continue
        streak = 0
        fl = [f for f in simplify(res) if f["stops"] == 0 or f["dur"] <= t["max_duration_min"]][:6]
        legs.append({"city": city, "kind": kind, "date": day, "flights": fl})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.window}-{a.shard}.json").write_text(json.dumps({
        "window": a.window, "shard": a.shard, "started": started, "legs": legs, "queries": queries, "failed": failed, "blocked": blocked}, ensure_ascii=False))
    print(f"{a.window} shard {a.shard}/{a.of}: {queries} sorgu, {failed} başarısız, {len(legs)} bacak, blocked={blocked}")
    return 0 if not blocked else 2


if __name__ == "__main__":
    sys.exit(main())
