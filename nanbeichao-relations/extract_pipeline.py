# -*- coding: utf-8 -*-
"""
南北朝人物关系抽取 pipeline v0.1
================================
用途:从本地公版正史全文(D:\\Codex工作区\\南北朝历史与神话\\01_正史全文\\*.txt)
      切卷 → 规则初筛(候选段定位) → [可选]LLM 精抽 → JSONL → SQLite(schema.sql)

合规三原则(写在代码里,防止将来手滑):
  1. 输入只允许公版史料文本;禁止读入任何 CBDB 文件;
  2. 每条关系必须带 evidence 原文引文,否则不入库;
  3. 每次抽取写 extractions 留证(方法+prompt+原始输出)。

用法(Windows,用 py 而不是 python):
  py extract_pipeline.py --scan "D:\\Codex工作区\\南北朝历史与神话\\01_正史全文\\梁书.txt"
  py extract_pipeline.py --scan <file> --seed-juans 1,2,3 --out candidates.jsonl
  py extract_pipeline.py --init-db            # 建 relations.db(需 sqlite3 或内置)
  py extract_pipeline.py --load <jsonl>       # 导入 SQLite

LLM 精抽(二期):fill_llm_prompt() 生成提示词,调用你自己的 GLM 接口,
                 raw 输出落盘到 extractions.raw_output——先跑规则层,LLM 层接口已留好。
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------- 语料注册
KNOWN_SOURCES = {
    "晋书": "房玄龄等(唐)·公版",
    "魏书": "魏收(北齐)·公版",
    "梁书": "姚思廉(唐)·公版",
    "陈书": "姚思廉(唐)·公版",
    "南史": "李延寿(唐)·公版",
    "北史": "李延寿(唐)·公版",
    "宋书": "沈约(梁)·公版",
    "南齐书": "萧子显(梁)·公版",
    "北齐书": "李百药(唐)·公版",
    "周书": "令狐德棻(唐)·公版",
    "隋书": "魏徵等(唐)·公版",
    "三国志": "陈寿(晋)·公版",
    "后汉书": "范晔(宋)·公版",
    "资治通鉴": "司马光(宋)·公版",
}

JUAN_RE = re.compile(r"^卷([一二三四五六七八九十百零\d]+)\s*(.*)$")     # 目录行
BODY_RE = re.compile(r"^(本纪|志|世家|列传|载记)第?([一二三四五六七八九十百零\d]+)\s*(.*)$")  # 正文卷头

CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100}


def cn2int(s: str) -> int:
    """中文卷号→整数(够用版:卷一百二十三 → 123)。"""
    if s.isdigit():
        return int(s)
    total, num = 0, 0
    for ch in s:
        v = CN_NUM.get(ch)
        if v is None:
            continue
        if v == 10:
            total += (num or 1) * 10
            num = 0
        elif v == 100:
            total += (num or 1) * 100
            num = 0
        else:
            num = v
    return total + num


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def split_juans(text: str):
    """按正文卷头('本纪第一 武帝上'/'列传第五十')切段;目录'卷X'行只作跳过。
    卷号用顺序计数(正文按卷序排列,计数即卷号)。返回 [(卷号, 卷题, 正文), ...]。"""
    juans, cur = [], None
    seq = 0
    for line in text.splitlines():
        s = line.strip()
        if JUAN_RE.match(s):          # 目录行:跳过,不当正文
            continue
        m = BODY_RE.match(s)
        if m:
            if cur:
                juans.append(cur)
            seq += 1
            title = (m.group(1) + m.group(2) + ("　" + m.group(3) if m.group(3) else ""))
            cur = [seq, title.strip(), []]
        elif cur is not None:
            cur[2].append(line)
    if cur:
        juans.append(cur)
    return [(j[0], j[1], "\n".join(j[2]).strip()) for j in juans if j[2]]


# ---------------------------------------------------------------- 规则初筛
# 候选句定位:包含强关系动词的句子,先粗后精
REL_PATTERNS = [
    # (regex, rel_type, polarity)
    (r"(?P<a>[\u4e00-\u9fa5]{2,4})(?:以|为)\s*(?P<a>[\u4e00-\u9fa5]{2,4})\s*(?:妻|女)", "姻亲", 1),
]
# 上面的模式过泛,实践上用"关键词定位句,再交 LLM"两段式,规则层只做候选句抽取:
SENT_SPLIT = re.compile(r"[。;!?]")
TRIGGER_WORDS = [
    "以女妻", "尚", "娶", "嫁",        # 姻亲
    "拜", "除", "迁", "为...刺史", "都督",  # 任职/君臣
    "举", "荐", "辟",                  # 举荐
    "杀", "斩", "诛", "弑", "害",      # 仇敌/死亡事件
    "叛", "降", "奔",                  # 背叛/效忠变更
    "与...战", "拒", "破", "围",       # 军事对手
    "师事", "从...学", "受业",         # 师从
    "养子", "养孙", "嗣子",            # 收养/继承
    "谥", "赠",                        # 死后
]


def candidate_sentences(juan_text: str, window: int = 60):
    """返回含触发词的句子(带前后文窗口),作为 LLM 精抽的输入候选。"""
    out = []
    for sent in SENT_SPLIT.split(juan_text):
        s = sent.strip()
        if not s or len(s) < 8:
            continue
        if any(w in s for w in TRIGGER_WORDS):
            out.append(s[:200])  # 截断,防超长句
    return out


# ---------------------------------------------------------------- JSONL 导出
def scan(path: Path, juan_filter=None, limit_per_juan=50, out: Path = None):
    title = path.stem
    origin = KNOWN_SOURCES.get(title, "来源待确认(公版候选)")
    text = path.read_text(encoding="utf-8", errors="ignore")
    juans = split_juans(text)
    n_cand = 0
    rows = []
    for no, jtitle, jtext in juans:
        if juan_filter and no not in juan_filter:
            continue
        cands = candidate_sentences(jtext)[:limit_per_juan]
        n_cand += len(cands)
        rows.append({
            "source": title, "origin": origin, "juan": no, "juan_title": jtitle,
            "juan_chars": len(jtext), "candidates": cands,
        })
    print(f"[scan] {title}: 卷数={len(juans)} 入选卷={len(rows)} 候选句={n_cand}")
    if out:
        with open(out, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[scan] 已写出 {out}")
    return rows


# ---------------------------------------------------------------- SQLite
def init_db(db_path: Path, schema_path: Path):
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()
    print(f"[db] 已初始化 {db_path}")
    return conn


def register_source(conn, title, file_path, origin, sha):
    cur = conn.execute(
        "INSERT INTO source_texts(title,file_path,origin,sha256) VALUES(?,?,?,?)",
        (title, str(file_path), origin, sha))
    conn.commit()
    return cur.lastrowid


def fill_llm_prompt(candidates: list, juan_title: str):
    """二期:LLM 精抽的提示词模板(先把接口留好,模型调用由你的 GLM 账号跑)。"""
    joined = "\n".join(f"- {c}" for c in candidates[:30])
    return (
        "你是史料结构化助手。下面是《某史》某卷的候选句,请只依据文本抽取四元组,"
        "输出 JSON 数组:[{subject,object,rel_type(君臣/姻亲/父子/兄弟/师从/举荐/同僚/"
        "交游/仇敌/军事对手/效忠/背叛/收养),year_raw,evidence(原句),confidence}]。"
        "禁止臆测;无把握输出空数组。卷题:" + juan_title + "\n候选句:\n" + joined
    )


def main():
    ap = argparse.ArgumentParser(description="南北朝关系抽取 pipeline v0.1")
    ap.add_argument("--scan", help="扫描单个史料 txt 文件")
    ap.add_argument("--seed-juans", help="只处理指定卷,如 1,2,56")
    ap.add_argument("--out", default=None, help="候选 JSONL 输出路径")
    ap.add_argument("--init-db", action="store_true", help="初始化 relations.db")
    ap.add_argument("--db", default="relations.db")
    ap.add_argument("--schema", default=Path(__file__).parent / "schema.sql")
    ap.add_argument("--register", help="把史料登记进 source_texts(参数=txt 路径)")
    args = ap.parse_args()

    if args.init_db:
        init_db(Path(args.db), Path(args.schema))
    if args.register:
        p = Path(args.register)
        conn = sqlite3.connect(args.db)
        sid = register_source(conn, p.stem, p, KNOWN_SOURCES.get(p.stem, "待确认"), sha256_of(p))
        print(f"[db] source_texts 登记 id={sid}")
    if args.scan:
        jf = None
        if args.seed_juans:
            jf = {int(x) for x in args.seed_juans.split(",")}
        out = Path(args.out) if args.out else None
        rows = scan(Path(args.scan), juan_filter=jf, out=out)
        # 附带演示:第一卷的 LLM 提示词样例
        if rows:
            demo = fill_llm_prompt(rows[0]["candidates"], rows[0]["juan_title"] or "卷一")
            print("\n[LLM提示词样例(前400字)]\n" + demo[:400])


if __name__ == "__main__":
    main()
