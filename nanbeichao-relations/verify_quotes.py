# -*- coding: utf-8 -*-
"""引文对核:从通史稿的加粗引文标记中提取引文,在语料库全文中匹配。
输出:命中/未命中报告。用法: py verify_quotes.py"""
import re, glob, sqlite3
from pathlib import Path

SHIGAO = Path(r"C:\Users\L_why\.zcode\workspace\default\nanbeichao-shigao")
SRC = Path(r"D:\Codex工作区\南北朝历史与神话\01_正史全文")

# 语料:全部正史全文+对照本(合并为一个查找串,去掉空白)
corpus = ""
for f in SRC.glob("*.txt"):
    corpus += f.read_text(encoding="utf-8", errors="ignore")
corpus_c = re.sub(r"\s+", "", corpus)

def norm(s):
    s = re.sub(r"\s+", "", s)
    return s.replace(',','，').replace(':','：').replace(';','；').replace('!','！').replace('?','？')
corpus_c = norm(corpus)

# 提取引文:半角双引号对 "..." 且长度6-80
quote_pat = re.compile(r'"([^"]{6,80})"')
files = [f for f in sorted(SHIGAO.glob("0*.md")) + sorted(SHIGAO.glob("1*.md")) if not f.name.startswith("00")]
hit, miss = [], []
for f in files:
    text = f.read_text(encoding="utf-8")
    text = re.sub(r"\*\*|\*|#+\s*", "", text)  # 去 markdown 标记
    for m in quote_pat.finditer(text):
        q = m.group(1).strip()
        if any(w in q for w in ["改写节点","叙事资产","NPC","机制","玩家","游戏","蓝本","默认方案","文案","你的","本作"]):
            continue
        if len(q) < 6:
            continue
        if norm(q) in corpus_c:
            hit.append((f.name, q))
        else:
            miss.append((f.name, q))
print(f"引文总数(含改写节点等非引文已滤): 命中 {len(hit)}, 未命中 {len(miss)}")
print("\n== 未命中清单(可能是记忆偏差或改写) ==")
for fn, q in miss:
    print(f"  [{fn}] {q}")
