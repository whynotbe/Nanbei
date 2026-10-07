# -*- coding: utf-8 -*-
"""加载 seed JSON 到 relations.db:persons/relations/events + chunk 登记 + 抽取留证。
用法: py load_seed.py seed_liangshu_j56.json
合规:每条 relations 必须带 evidence 原文,否则拒绝入库。"""
import json, sqlite3, sys, hashlib
from pathlib import Path

seed_path = Path(sys.argv[1])
seed = json.loads(seed_path.read_text(encoding="utf-8"))
conn = sqlite3.connect("relations.db")

# 1) 语料与 chunk 登记
src = conn.execute("SELECT id FROM source_texts WHERE title=?", (seed["source_title"],)).fetchone()
if not src:
    raise SystemExit("先 --register 登记史料")
src_id = src[0]
full = Path(r"D:\Codex工作区\南北朝历史与神话\01_正史全文\梁书.txt").read_text(encoding="utf-8", errors="ignore")
import importlib.util
spec = importlib.util.spec_from_file_location("ep", "extract_pipeline.py")
ep = importlib.util.module_from_spec(spec); spec.loader.exec_module(ep)
juans = dict((no, (t, b)) for no, t, b in ep.split_juans(full))
jt, jb = juans[seed["juan"]]
exist = conn.execute("SELECT id FROM chunks WHERE source_id=? AND juan=?", (src_id, seed["juan"])).fetchone()
if exist:
    chunk_id = exist[0]
else:
    cur = conn.execute(
        "INSERT INTO chunks(source_id,juan,juan_title,char_start,char_end,text,sha256) VALUES(?,?,?,?,?,?,?)",
        (src_id, seed["juan"], jt, 0, len(jb), jb[:200000], hashlib.sha256(jb.encode()).hexdigest()))
    chunk_id = cur.lastrowid
conn.commit()

# 2) 人物入库(带证据)
ids = {}
for p in seed["persons"]:
    row = conn.execute("SELECT id FROM persons WHERE name=? AND ifnull(home_region,'')=ifnull(?,'')",
                       (p["name"], p.get("home_region"))).fetchone()
    if row:
        pid = row[0]
    else:
        cur = conn.execute(
            "INSERT INTO persons(name,courtesy,title_label,era,birth_year,death_year,death_cause,home_region,faction,confidence,notes) VALUES(?,?,?,?,?,?,?,?,?,0.9,?)",
            (p["name"], p.get("courtesy"), p.get("title_label"), p.get("era"), p.get("birth_year"),
             p.get("death_year"), p.get("death_cause"), p.get("home_region"), p.get("faction"),
             "seed依据:" + p.get("evidence", "")[:80]))
        pid = cur.lastrowid
    for al in p.get("aliases", []):
        try:
            conn.execute("INSERT INTO person_aliases(person_id,alias,alias_type) VALUES(?,?,?)", (pid, al, "史称"))
        except sqlite3.IntegrityError:
            pass
    ids[p["name"]] = pid
conn.commit()

# 3) 关系入库(evidence 必填)
n_rel = 0
for r in seed["relations"]:
    if not r.get("evidence"):
        raise SystemExit("拒绝:evidence 缺失 -> " + json.dumps(r, ensure_ascii=False))
    sid, oid_ = ids[r["s"]], ids[r["o"]]
    dup = conn.execute("SELECT id FROM relations WHERE subject_id=? AND object_id=? AND rel_type=? AND evidence=?",
                       (sid, oid_, r["type"], r["evidence"])).fetchone()
    if dup:
        continue
    conn.execute(
        "INSERT INTO relations(subject_id,object_id,rel_type,rel_detail,start_year,polarity,confidence,evidence,chunk_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (sid, oid_, r["type"], r.get("detail"), r.get("year"), r.get("polarity", 1), 0.9, r["evidence"], chunk_id))
    n_rel += 1

# 4) 事件入库
n_ev = 0
for e in seed["events"]:
    dup = conn.execute("SELECT id FROM events WHERE title=? AND year_ce=?", (e["title"], e["year_ce"])).fetchone()
    if dup:
        continue
    cur = conn.execute(
        "INSERT INTO events(year_raw,year_ce,month,title,summary,event_type,location,is_rewrite_node,source_id,chunk_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (e["year_raw"], e["year_ce"], e.get("month"), e["title"], e.get("summary"), e["event_type"],
         e.get("location"), 1 if e.get("rewrite") else 0, src_id, chunk_id))
    ev_id = cur.lastrowid
    n_ev += 1

# 5) 抽取留证
conn.execute(
    "INSERT INTO extractions(batch_id,chunk_id,method,prompt_ver,raw_output,reviewed) VALUES(?,?,?,?,?,1)",
    (seed["batch"], chunk_id, seed["method"], "inline-reading-v1", str(seed_path) + " sha256=" +
     hashlib.sha256(seed_path.read_bytes()).hexdigest()[:16]))
conn.commit()

print(f"[load] persons={len(ids)} relations_new={n_rel} events_new={n_ev} chunk_id={chunk_id}")
print("[top] 侯景的关系网(按条数):")
rows = conn.execute("""
  SELECT rel_type, COUNT(*) c FROM relations r JOIN persons p ON p.id=r.subject_id
  WHERE p.name='侯景' GROUP BY rel_type ORDER BY c DESC""").fetchall()
for t, c in rows:
    print(f"   {t}: {c}")
print("[志怪事件] ", conn.execute("SELECT COUNT(*) FROM events WHERE event_type='志怪'").fetchone()[0], "条")
print("[改写节点] ", conn.execute("SELECT COUNT(*) FROM v_rewrite_nodes").fetchone()[0], "条")
