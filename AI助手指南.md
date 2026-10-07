# AI 助手指南(南北朝神鬼游戏项目)

> 给新电脑上的 AI 助手(Claude/ZCode/ChatGPT 等)看的说明书。

## 两个仓库的关系

| 仓库 | 内容 | 用途 |
|---|---|---|
| **Nanbei**(本仓库) | 游戏项目产出(策划案/关系库/通史稿/地图/原型) | 做游戏 |
| **NANBEI-history** | 史料原文(14部正史/志怪/现代研究/CBDB/维基对照本) | 查资料/抽取 |

新电脑上两个都要 clone:
```bash
git clone https://github.com/whynotbe/Nanbei.git
git clone https://github.com/whynotbe/NANBEI-history.git
```

## 本仓库目录导航

### 做游戏开发 → 看 `nanbeichao-design/`

| 文件 | 内容 |
|---|---|
| `00-游戏框架总纲.md` | 定位/循环/系统清单(**从这里开始读**) |
| `01-角色养成系统.md` | 属性/技能树/身份/装备 |
| `02-关系网系统.md` | 295人网络/polarity/拉拢/背叛 |
| `03-战斗系统.md` | 人战+鬼战/武器/骑乘/以步制骑 |
| `04-冤气超度系统.md` | 怨气法则/阴阳眼/超度/范缜难题 |
| `05-围城经济系统.md` | 130天生存/粮价/疫病/援军 |
| `06-信息战系统.md` | 情报/伪造/童谣/离间 |
| `07-宗室名册系统.md` | 家族树/威胁值/死亡预警 |
| `08-地图探索系统.md` | 三层地图/移动/发现 |
| `09-事件改写系统.md` | 39节点/后果链/6种结局 |
| `10-谶谣预言系统.md` | 84条志怪/解读/反向操作 |
| `11-UI框架.md` | HUD/对话/关系网可视化/键位 |
| `12-数值框架.md` | 成长曲线/伤害公式/资源平衡 |
| `02a-主线剧本-对话文案版.md` | 12节点全对话(可直接导对话树) |
| `03-序章-岭南.md` | 序章三幕设计 |
| `04-NPC卡.md` | 20张核心NPC卡 |
| `05-世界观规则.md` | 怨气/显形/佛寺/天命 |
| `06-决策记录.md` | 四项默认方案+推翻开关 |
| `prototype.html` | Web原型垂直切片 |

### 做数据操作 → 看 `nanbeichao-relations/`

| 工具 | 用途 | 用法 |
|---|---|---|
| `relations.db` | SQLite(295人/279关系/195事件) | `py -c "import sqlite3; ..."` |
| `export_data.py` | 导出JSON/CSV | `py export_data.py export` |
| `extract_pipeline.py` | 从史料切卷+初筛 | `py extract_pipeline.py --scan <txt>` |
| `load_batch2.py` | 种子入库(evidence校验) | `py load_batch2.py <seed.json> <corpus.txt> <卷号>` |
| `dedup_cli.py` | 同名消歧 | `py dedup_cli.py scan` / `py dedup_cli.py merge <id1> <id2>` |
| `verify_quotes.py` | 引文对核 | `py verify_quotes.py` |
| `llm_client.py` | GLM API批量精抽 | `set GLM_API_KEY=key && py llm_client.py --corpus <txt>` |

### 查历史背景 → 看 `nanbeichao-shigao/`

10幕通史稿(7万字),每幕含:叙事/人物志/大事年表/机制图鉴/叙事资产。
地图: `地图集.html`(七页疆域)/ `全图.html`(548三国)/ `建康城详图.html`(关卡)/ `岭南-三吴区域图.html`(动线)

### 恢复AI记忆 → 看 `_memory/`

把此目录的 .md 文件复制到 ZCode 记忆目录:
```
C:\Users\<用户名>\.zcode\cli\memories\projects\default-<hash>\memory\
```

## 关键设计决策(已定,附推翻开关)

| 决策 | 方案 | 改法 |
|---|---|---|
| 主角 | 岭南寒门武人 | 换序章+初始关系网 |
| 起局 | 547年正月(高欢死) | 改548则砍教学段 |
| 超自然 | 冤气体系化+明面克制 | 改 `anima_threshold` 参数 |
| 尺度 | 惨剧侧写+机制化 | 红线设计,不建议改 |

## 合规底线(勿删)

1. 数据从公版正史独立抽取(维基文库优先),不用中华书局点校本
2. 每条关系带 evidence 原文引文
3. 不碰 CBDB 数据库(CC BY-NC-SA 禁商用)
4. schema 按游戏玩法定义,不复刻 CBDB 分类

## 快速预览

```bash
cd <本仓库>
py -m http.server 8613 --bind 127.0.0.1
# 浏览器打开:
# http://127.0.0.1:8613/nanbeichao-design/prototype.html  ← Web原型
# http://127.0.0.1:8613/nanbeichao-shigao/qqtu.html       ← 548全图
```

## 史料库路径约定

精抽工具引用 D 盘路径: `D:\Codex工作区\南北朝历史与神话\`
新电脑上把 NANBEI-history clone 到此路径,或修改工具中的路径变量。

---

*创建: 2026-10-07 | 史料库: https://github.com/whynotbe/NANBEI-history*
