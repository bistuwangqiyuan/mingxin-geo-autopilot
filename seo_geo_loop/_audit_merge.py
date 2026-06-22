# -*- coding: utf-8 -*-
import json, time

p = "outputs/gsc_index_status_audit.json"
batch = json.load(open("_audit_batch.json", encoding="utf-8"))
d = json.load(open(p, encoding="utf-8"))
d["results"].update(batch)
d["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
# recompute summary
summ = {}
for v in d["results"].values():
    summ[v] = summ.get(v, 0) + 1
d["summary"] = dict(sorted(summ.items(), key=lambda x: -x[1]))
d["done"] = len(d["results"])
d["remaining"] = d["total"] - d["done"]
d["not_indexed_or_other"] = sorted(k for k, v in d["results"].items() if v != "indexed")
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"merged {len(batch)} -> done={d['done']} remaining={d['remaining']} summary={d['summary']}")
