#!/usr/bin/env python3
"""Shard çıktılarını pencere başına birleştirir → latest-<pencere>.json (plan.py'nin legs.json biçimi + meta)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
t = json.loads(Path("targets.json").read_text())
for w in t["windows"]:
    parts = [json.loads(p.read_text()) for p in sorted(src.rglob(f"{w['id']}-*.json"))]
    if not parts:
        print(f"{w['id']}: shard çıktısı yok, atlandı")
        continue
    legs = [l for p in parts for l in p["legs"]]
    stats = {"queries": sum(p["queries"] for p in parts), "failed": sum(p["failed"] for p in parts),
             "blocked_shards": sum(1 for p in parts if p["blocked"]), "shards": len(parts), "expected_shards": t["shards"]}
    out = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "window": w, "origin": t["origin"], "stops": str(t["max_stops"]),
           "max_dur": t["max_duration_min"], "stats": stats, "legs": legs}
    (dst / f"latest-{w['id']}.json").write_text(json.dumps(out, ensure_ascii=False))
    ok = stats["shards"] == stats["expected_shards"] and not stats["blocked_shards"]
    print(f"{w['id']}: {len(legs)} bacak, {stats['queries']} sorgu, {stats['failed']} başarısız, tam={ok}")
