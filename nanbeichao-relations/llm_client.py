# -*- coding: utf-8 -*-
"""F1: LLM API 客户端——连接 GLM API 做批量精抽。
用法(需先设置 API Key):
  set GLM_API_KEY=your_key_here   (Windows)
  py llm_client.py --batch <seed.json> --corpus <corpus.txt>

流程:
  1. 读 corpus → 切段(每段约 2000 字)
  2. 构造 prompt(fill_llm_prompt 格式)
  3. 调用 GLM API(兼容 OpenAI 格式)
  4. 解析返回的 JSON 数组
  5. 写入 seed JSON(可 load_batch2.py 入库)
"""
import json, sys, time, requests
from pathlib import Path

API_BASE = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"  # 或 glm-4-plus

PROMPT_TEMPLATE = """你是史料结构化助手。下面是正史原文的一个片段。请只依据文本抽取人物关系,输出 JSON 数组:
[{{"subject":"人名","object":"人名","rel_type":"类型","detail":"一句话","year":年份或null,"polarity":1或-1或0,"evidence":"原文精确子串(10-30字)"}}]

关系类型从以下选:君臣/姻亲/父子/兄弟/师从/举荐/同僚/交游/仇敌/军事对手/效忠/背叛/收养/杀/谏阻/投降/推举/预言

要求:
- evidence 必须是原文中连续出现的精确文字(不含省略号)
- confidence 设 0.85
- 无把握的关系不要输出
- 如果片段中没有可抽取的关系,输出空数组 []

=== 原文片段 ===
{chunk}"""


def call_glm(prompt, api_key, max_retries=3):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    for i in range(max_retries):
        try:
            r = requests.post(API_BASE, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[retry {i+1}] {e}")
            time.sleep(5)
    return None


def batch_extract(corpus_path, api_key, chunk_size=2000):
    text = Path(corpus_path).read_text(encoding="utf-8")
    # 去头行
    text = text.split("\n", 2)[-1] if text.startswith("corpus") else text
    chunks = [text[i:i+chunk_size] for i in range(0, min(len(text), 20000), chunk_size)]
    all_relations = []
    for idx, chunk in enumerate(chunks):
        prompt = PROMPT_TEMPLATE.format(chunk=chunk)
        print(f"[{idx+1}/{len(chunks)}] 调用 GLM...")
        raw = call_glm(prompt, api_key)
        if not raw:
            print("  失败,跳过")
            continue
        try:
            # 提取 JSON 数组(可能被包裹在 ```json ... ```)
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            items = json.loads(raw.strip())
            # 验证 evidence 在语料中
            valid = [r for r in items if r.get("evidence") and r["evidence"] in text]
            print(f"  抽取 {len(items)} 条,验证通过 {len(valid)} 条")
            all_relations.extend(valid)
        except json.JSONDecodeError:
            print(f"  JSON 解析失败: {raw[:100]}")
    return all_relations


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="语料 txt 文件")
    ap.add_argument("--out", default="llm_seed.json", help="输出 seed JSON")
    ap.add_argument("--batch-name", default="llm-api-batch")
    args = ap.parse_args()

    import os
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        print("请先设置环境变量 GLM_API_KEY")
        print("  Windows: set GLM_API_KEY=your_key")
        sys.exit(1)

    relations = batch_extract(args.corpus, api_key)
    seed = {"batch": args.batch_name, "method": "glm-4-flash-api", "source_title": "LLM",
            "juan": 0, "persons": [], "relations": relations, "events": []}
    Path(args.out).write_text(json.dumps(seed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n完成: {len(relations)} 条关系 → {args.out}")
    print(f"入库: py load_batch2.py {args.out} {args.corpus} 0")
