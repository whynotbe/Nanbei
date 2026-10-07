# -*- coding: utf-8 -*-
"""同名/异写消歧工具 v1
用法:
  py dedup_cli.py scan     # 扫描疑似同一人的候选组(同名/别名交叉/异写表)
  py dedup_cli.py merge A B # 合并 B 入 A(关系/别名迁移,删 B)
判定键: 本名相同 + (时代交叠 或 籍贯相近);或别名表交叉命中。
人工确认后执行 merge——90% 精度目标的最后一道工序。"""
import sqlite3, sys

# 已知异写对照表(史文异写,自动归并建议)
KNOWN_VARIANTS = [
    ("羊鲲", "羊从"),          # 南史作"从"
    ("杜掞", "杜崱"),          # 梁书掞/南史崱
    ("朱异", "硃异"),
    ("尔朱荣", "尔硃荣"),
    ("羊从", "羊鹍"),
]

def scan():
    conn = sqlite3.connect("relations.db")
    rows = conn.execute("SELECT id,name,era,home_region,title_label FROM persons").fetchall()
    byname = {}
    for r in rows:
        byname.setdefault(r[1], []).append(r)
    print("== 同名组(需人工判断是否同人) ==")
    for name, grp in byname.items():
        if len(grp) > 1:
            print(f"[{name}] x{len(grp)}:")
            for g in grp:
                print(f"   id={g[0]} era={g[2]} home={g[3]} label={g[4]}")
    alias = {}
    for pid, al in conn.execute("SELECT person_id, alias FROM person_aliases"):
        alias.setdefault(al, []).append(pid)
    print("== 别名指向多人(高危) ==")
    for al, pids in alias.items():
        if len(set(pids)) > 1:
            print(f"   别名[{al}] -> persons {sorted(set(pids))}")
    # 异写自动建议
    print("== 异写自动归并建议 ==")
    idmap = {r[1]: r[0] for r in rows}
    for a, b in KNOWN_VARIANTS:
        if a in idmap and b in idmap and idmap[a] != idmap[b]:
            print(f"   建议合并: {a}(id={idmap[a]}) <- {b}(id={idmap[b]})")
    # 疑似拆分:同人名出现于两个 person(含别名内)
    print("== 别名等于他 人本名(疑似同人) ==")
    for pid, al in conn.execute("SELECT person_id, alias FROM person_aliases"):
        if al in idmap and idmap[al] != pid:
            print(f"   person id={pid} 的别名[{al}] 与本名 id={idmap[al]} 冲突")

def merge(a_id, b_id):
    conn = sqlite3.connect("relations.db")
    if a_id == b_id:
        raise SystemExit("同一人")
    # 关系迁移
    conn.execute("UPDATE relations SET subject_id=? WHERE subject_id=?", (a_id, b_id))
    conn.execute("UPDATE relations SET object_id=? WHERE object_id=?", (a_id, b_id))
    conn.execute("UPDATE event_participants SET person_id=? WHERE person_id=?", (a_id, b_id))
    # 别名迁移:B 的本名变成 A 的别名
    bname = conn.execute("SELECT name FROM persons WHERE id=?", (b_id,)).fetchone()[0]
    try:
        conn.execute("INSERT INTO person_aliases(person_id,alias,alias_type) VALUES(?,?,?)", (a_id, bname, "合并-本名"))
    except sqlite3.IntegrityError:
        pass
    for al, in conn.execute("SELECT alias FROM person_aliases WHERE person_id=?", (b_id,)).fetchall():
        try:
            conn.execute("INSERT INTO person_aliases(person_id,alias,alias_type) VALUES(?,?,?)", (a_id, al, "合并迁移"))
        except sqlite3.IntegrityError:
            pass
    # 去重完全相同的关系
    conn.execute("""DELETE FROM relations WHERE id NOT IN
        (SELECT MIN(id) FROM relations GROUP BY subject_id,object_id,rel_type,evidence)""")
    conn.execute("DELETE FROM persons WHERE id=?", (b_id,))
    conn.commit()
    print(f"merged {b_id} -> {a_id}")

if __name__ == "__main__":
    if sys.argv[1] == "scan":
        scan()
    elif sys.argv[1] == "merge":
        merge(int(sys.argv[2]), int(sys.argv[3]))
