# -*- coding: utf-8 -*-
"""F2: 数据导出 JSON/CSV(游戏引擎可用格式)
用法: py export_data.py [output_dir]"""
import sqlite3, json, csv, sys, os
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("export")
OUT.mkdir(exist_ok=True)
conn = sqlite3.connect("relations.db")
conn.row_factory = sqlite3.Row

# ============ JSON(主格式,适合 Godot/Unity/Web) ============
data = {"persons": [], "relations": [], "events": [], "participants": [], "aliases": []}

for r in conn.execute("SELECT * FROM persons ORDER BY id"):
    data["persons"].append(dict(r))
for r in conn.execute("SELECT * FROM relations ORDER BY id"):
    d = dict(r)
    # 附加双端名字(引擎端省一次 join)
    d["subject_name"] = conn.execute("SELECT name FROM persons WHERE id=?", (d["subject_id"],)).fetchone()[0]
    d["object_name"] = conn.execute("SELECT name FROM persons WHERE id=?", (d["object_id"],)).fetchone()[0]
    data["relations"].append(d)
for r in conn.execute("SELECT * FROM events ORDER BY year_ce, month"):
    data["events"].append(dict(r))
for r in conn.execute("""SELECT ep.*, p.name as person_name, e.title as event_title
                         FROM event_participants ep JOIN persons p ON p.id=ep.person_id JOIN events e ON e.id=ep.event_id"""):
    data["participants"].append(dict(r))
for r in conn.execute("SELECT pa.*, p.name as person_name FROM person_aliases pa JOIN persons p ON p.id=pa.person_id"):
    data["aliases"].append(dict(r))

json.dump(data, open(OUT / "gamedata.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[JSON] gamedata.json: {len(data['persons'])} persons, {len(data['relations'])} relations, {len(data['events'])} events")

# ============ 游戏专用视图(轻量版,适合直接加载) ============
game = {"npc_seeds": [], "network_edges": [], "rewrite_nodes": [], "zhgai_events": []}

# NPC 种子:核心度前 50 人物
for r in conn.execute("""
    SELECT p.*, COUNT(r.id) as degree FROM persons p
    LEFT JOIN relations r ON r.subject_id=p.id OR r.object_id=p.id
    GROUP BY p.id ORDER BY degree DESC LIMIT 50"""):
    d = dict(r)
    d["aliases"] = [a[0] for a in conn.execute("SELECT alias FROM person_aliases WHERE person_id=?", (d["id"],))]
    game["npc_seeds"].append(d)

# 网络边(只保留 confidence > 0.5)
for r in conn.execute("""
    SELECT r.*, p.name as s, q.name as o FROM relations r
    JOIN persons p ON p.id=r.subject_id JOIN persons q ON q.id=r.object_id
    WHERE r.confidence > 0.5"""):
    game["network_edges"].append({"source": r["s"], "target": r["o"], "type": r["rel_type"],
                                   "polarity": r["polarity"], "evidence": r["evidence"]})

# 改写节点
for r in conn.execute("SELECT * FROM events WHERE is_rewrite_node=1 ORDER BY year_ce"):
    game["rewrite_nodes"].append(dict(r))

# 志怪事件
for r in conn.execute("SELECT * FROM events WHERE event_type='志怪' ORDER BY year_ce"):
    game["zhgai_events"].append(dict(r))

json.dump(game, open(OUT / "game_views.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[JSON] game_views.json: {len(game['npc_seeds'])} NPC seeds, {len(game['network_edges'])} edges, "
      f"{len(game['rewrite_nodes'])} rewrite nodes, {len(game['zhgai_events'])} zhgai events")

# ============ CSV(给 Excel/表格工具) ============
for table in ["persons", "relations", "events"]:
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    if rows:
        with open(OUT / f"{table}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 1").description])
            w.writeheader()
            for r in rows:
                w.writerow(dict(zip([d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 1").description], r)))
        print(f"[CSV] {table}.csv: {len(rows)} rows")

# ============ 引擎映射说明 ============
readme = """# 游戏数据导出说明

## 文件
- `gamedata.json` — 全量数据(persons/relations/events/participants/aliases)
- `game_views.json` — 游戏专用视图(NPC 种子 50 人/网络边/改写节点/志怪事件)
- `persons.csv` / `relations.csv` / `events.csv` — CSV 版本

## 字段映射(引擎端)

### persons → NPC
| DB 字段 | 游戏字段 | 说明 |
|---|---|---|
| name | npc_name | 本名 |
| courtesy | npc_courtesy | 字 |
| title_label | npc_title | 称谓(显示在头顶) |
| era | npc_faction_era | 时代(过滤用) |
| death_year | npc_death_year | 死亡年(>当前年=活) |
| death_cause | npc_death_cause | 死因(任务/对话用) |
| home_region | npc_home | 籍贯(地图标记) |
| faction | npc_faction | 阵营 |

### relations → 关系网边
| DB 字段 | 游戏字段 | 说明 |
|---|---|---|
| subject_name → object_name | edge(from→to) | 网络两端 |
| rel_type | edge_type | 关系类型 |
| polarity | edge_polarity | 1正/-1负/0中性 |
| weight | edge_weight | 互动频率 |
| evidence | edge_lore | 原文引文(对话框展示) |

### events → 世界事件
| DB 字段 | 游戏字段 | 说明 |
|---|---|---|
| year_ce + month | event_date | 触发时间 |
| title | event_name | 事件名 |
| is_rewrite_node | is_player_interactable | 1=可改写节点 |
| event_type | event_category | 战争/政变/志怪... |

## 使用(Godot 示例)
```gdscript
var data = JSON.parse_string(FileAccess.get_file_as_string("res://game_views.json"))
for npc in data.npc_seeds:
    spawn_npc(npc.npc_name, npc.npc_title, npc.npc_death_year)
```

## 使用(Web/JS 示例)
```javascript
const data = await fetch('game_views.json').then(r=>r.json());
data.network_edges.forEach(e => graph.addLink(e.source, e.target, {type:e.type, polarity:e.polarity}));
```
"""
open(OUT / "README.md", "w", encoding="utf-8").write(readme)
print(f"[DOC] README.md 引擎映射说明")
print(f"\n导出完成 → {OUT.resolve()}")
