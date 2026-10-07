# -*- coding: utf-8 -*-
"""A2+A3:event_participants 回填 + person_aliases 补全
用法: py backfill.py"""
import sqlite3, re

conn = sqlite3.connect("relations.db")

# ========== A2: event_participants 回填 ==========
# 策略:扫描 events.title+summary 中出现的人名,若在 persons 表中存在则关联
persons = conn.execute("SELECT id, name FROM persons").fetchall()
name_map = {n: pid for pid, n in persons}
# 按名字长度降序,优先匹配长名(避免"萧纲"匹配到"萧纲的"这种)
sorted_names = sorted(name_map.keys(), key=len, reverse=True)

events = conn.execute("SELECT id, title, summary FROM events WHERE summary IS NOT NULL AND summary != ''").fetchall()
n_added = 0
for eid, title, summary in events:
    text = title + " " + summary
    found = set()
    for name in sorted_names:
        if name in text and name not in found:
            # 检查不与其他已找到的名字重叠(如"萧纲"与"萧纲的某物")
            if not any(name in f or f in name for f in found):
                found.add(name)
    for name in found:
        pid = name_map[name]
        try:
            conn.execute("INSERT INTO event_participants(event_id, person_id, role) VALUES(?,?,?)",
                         (eid, pid, "提及"))
            n_added += 1
        except sqlite3.IntegrityError:
            pass
conn.commit()
print(f"[A2] event_participants 回填: {n_added} 条")

# ========== A3: person_aliases 补全 ==========
# 策略:从 persons 的 courtesy 字段、notes 中的"字XX"模式、title_label 中的常见称谓
alias_added = 0
for pid, courtesy, title, notes in conn.execute("SELECT id, courtesy, title_label, notes FROM persons WHERE courtesy IS NOT NULL AND courtesy != ''"):
    # courtesy 本身就是别名
    try:
        conn.execute("INSERT INTO person_aliases(person_id, alias, alias_type) VALUES(?,?,?)", (pid, courtesy, "字"))
        alias_added += 1
    except sqlite3.IntegrityError:
        pass

# 从 notes 中提取"字XX"格式
for pid, notes in conn.execute("SELECT id, notes FROM persons WHERE notes LIKE '%字%'"):
    m = re.search(r'字([^\s,，;；\)]{1,4})', notes)
    if m:
        alias = m.group(1)
        try:
            conn.execute("INSERT INTO person_aliases(person_id, alias, alias_type) VALUES(?,?,?)", (pid, alias, "字(笔记)"))
            alias_added += 1
        except sqlite3.IntegrityError:
            pass

# 从 title_label 中提取常见称谓(谥号/封号)
title_patterns = [
    (r'谥(\w+)', "谥号"),
    (r'(\w+王)', "封号"),
    (r'(\w+公)', "封号"),
    (r'(\w+侯)', "封号"),
]
for pid, title in conn.execute("SELECT id, title_label FROM persons WHERE title_label IS NOT NULL AND title_label != ''"):
    for pat, typ in title_patterns:
        m = re.search(pat, title)
        if m and len(m.group(1)) >= 2:
            try:
                conn.execute("INSERT INTO person_aliases(person_id, alias, alias_type) VALUES(?,?,?)", (pid, m.group(1), typ))
                alias_added += 1
            except sqlite3.IntegrityError:
                pass

conn.commit()
print(f"[A3] person_aliases 补全: {alias_added} 条")
print(f"[终态] aliases 总数: {conn.execute('SELECT COUNT(*) FROM person_aliases').fetchone()[0]}")
print(f"[终态] event_participants 总数: {conn.execute('SELECT COUNT(*) FROM event_participants').fetchone()[0]}")
