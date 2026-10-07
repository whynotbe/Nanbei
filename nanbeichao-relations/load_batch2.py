# -*- coding: utf-8 -*-
"""通用批次加载器(支持 person_updates 与 conflicts 记账)。
用法: py load_batch2.py seed_xxx.json <corpus_txt> <起卷号>
corpus_txt 用于登记 chunk 与 evidence 校验。"""
import json, sqlite3, sys, hashlib, importlib.util
from pathlib import Path

seed = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
corpus_path = Path(sys.argv[2])
JUAN = int(sys.argv[3]) if len(sys.argv) > 3 else 0

conn = sqlite3.connect("relations.db")
# 语料登记
src = conn.execute("SELECT id FROM source_texts WHERE title=?", (seed["source_title"],)).fetchone()
if not src:
    origin = {"南史": "李延寿(唐)·公版", "梁书": "姚思廉(唐)·公版", "陈书": "姚思廉(唐)·公版",
              "北齐书": "李百药(唐)·公版", "魏书": "魏收(北齐)·公版", "周书": "令狐德棻(唐)·公版"}.get(seed["source_title"], "公版正史")
    cur = conn.execute("INSERT INTO source_texts(title,file_path,origin,sha256) VALUES(?,?,?,?)",
                       (seed["source_title"], str(corpus_path), origin, hashlib.sha256(corpus_path.read_bytes()).hexdigest()))
    src_id = cur.lastrowid
else:
    src_id = src[0]
body = corpus_path.read_text(encoding="utf-8").split("\n", 2)[-1]  # 去掉文件头行
import re
_body_c = re.sub(r"\s+", "", body)
def ev_ok(ev):
    return ev in body or re.sub(r"\s+", "", ev) in _body_c
exist = conn.execute("SELECT id FROM chunks WHERE source_id=? AND juan=?", (src_id, JUAN)).fetchone()
if exist:
    chunk_id = exist[0]
else:
    cur = conn.execute("INSERT INTO chunks(source_id,juan,juan_title,char_start,char_end,text,sha256) VALUES(?,?,?,?,?,?,?)",
                       (src_id, JUAN, seed.get("juan_title", ""), 0, len(body), body[:200000],
                        hashlib.sha256(body.encode()).hexdigest()))
    chunk_id = cur.lastrowid
conn.commit()

# 人物
ids = {}
for p in seed["persons"]:
    row = conn.execute("SELECT id FROM persons WHERE name=?", (p["name"],)).fetchone()
    if row:
        pid = row[0]
    else:
        cur = conn.execute(
            "INSERT INTO persons(name,courtesy,title_label,era,birth_year,death_year,death_cause,home_region,faction,confidence,notes) VALUES(?,?,?,?,?,?,?,?,?,0.85,?)",
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

# 人物更新(别名/注记)
for pu in seed.get("person_updates", []):
    row = conn.execute("SELECT id,notes FROM persons WHERE name=?", (pu["name"],)).fetchone()
    if row:
        pid, old = row
        conn.execute("UPDATE persons SET notes=COALESCE(notes,'')||? WHERE id=?",
                     ("\n[更新]" + pu.get("note", ""), pid))
        for al in pu.get("aliases", []) if isinstance(pu.get("aliases"), list) else [pu.get("alias")] if pu.get("alias") else []:
            try:
                conn.execute("INSERT INTO person_aliases(person_id,alias,alias_type) VALUES(?,?,?)", (pid, al, "小字/别称"))
            except sqlite3.IntegrityError:
                pass

def resolve(name):
    if name in ids:
        return ids[name]
    row = conn.execute("SELECT id FROM persons WHERE name=?", (name,)).fetchone()
    if row:
        ids[name] = row[0]
        return row[0]
    raise SystemExit("人物不存在于库与本批: " + name)

# 关系(evidence 必须在语料中)
n_rel = 0
bad_ev = []
for r in seed["relations"]:
    if not r.get("evidence"):
        raise SystemExit("缺evidence: " + json.dumps(r, ensure_ascii=False))
    if not ev_ok(r["evidence"]):
        bad_ev.append(r["evidence"]); continue
    sid, oid_ = resolve(r["s"]), resolve(r["o"])
    dup = conn.execute("SELECT id FROM relations WHERE subject_id=? AND object_id=? AND rel_type=? AND evidence=?",
                       (sid, oid_, r["type"], r["evidence"])).fetchone()
    if dup:
        continue
    conn.execute(
        "INSERT INTO relations(subject_id,object_id,rel_type,rel_detail,start_year,polarity,confidence,evidence,chunk_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (sid, oid_, r["type"], r.get("detail"), r.get("year"), r.get("polarity", 1), 0.85, r["evidence"], chunk_id))
    n_rel += 1

# 事件
n_ev = 0
bad_ev2 = []
for e in seed["events"]:
    if e.get("evidence") and not ev_ok(e["evidence"]):
        bad_ev2.append(e["title"] + "|" + e["evidence"]); continue
    dup = conn.execute("SELECT id FROM events WHERE title=? AND year_ce=?", (e["title"], e["year_ce"])).fetchone()
    if dup:
        continue
    conn.execute(
        "INSERT INTO events(year_raw,year_ce,month,title,summary,event_type,location,is_rewrite_node,source_id,chunk_id,evidence) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (e["year_raw"], e["year_ce"], e.get("month"), e["title"], e.get("summary"), e["event_type"],
         e.get("location"), 1 if e.get("rewrite") else 0, src_id, chunk_id, e.get("evidence")))
    n_ev += 1

# 冲突记账
for c in seed.get("conflicts", []):
    conn.execute("INSERT INTO reviews(target_table,target_id,verdict,fix_note,reviewer) VALUES('crosscheck',0,'noted',?,'glm-inline')", (c,))

# 留证
conn.execute("INSERT INTO extractions(batch_id,chunk_id,method,prompt_ver,raw_output,reviewed) VALUES(?,?,?,?,?,1)",
             (seed["batch"], chunk_id, seed["method"], "inline-reading-v1", sys.argv[1]))
conn.commit()

print(f"[load] {seed['batch']}: persons新增{len(ids)} relations新{n_rel} events新{n_ev}")
if bad_ev: print("[!] 关系evidence不在语料,跳过", len(bad_ev)); [print("   ", x[:50]) for x in bad_ev]
if bad_ev2: print("[!] 事件evidence不在语料,跳过", len(bad_ev2)); [print("   ", x[:60]) for x in bad_ev2]
