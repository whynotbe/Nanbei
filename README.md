# 南北朝神鬼游戏项目(完整工作区)

## 项目简介

南北朝(548-557 侯景之乱)背景的开放世界 ARPG。太阁立志传(模拟骨架)+ 刀剑封魔录(战斗血肉)。主角为岭南寒门武人,天生阴阳眼,能看见怨气、改写历史。

## 目录结构

```
default/
├── nanbeichao-shigao/       ← 通史稿(7.0万字, 10幕详版)
│   ├── 00-设计决策.md        ← 四项默认方案
│   ├── 01-10 幕通史稿        ← 西晋→隋,每幕含人物志/年表/机制/资产
│   ├── 地图集.html           ← v2 七页疆域图(304-589)
│   ├── 全图.html             ← 548年三国全图(约100城+国境线)
│   ├── 建康城详图.html       ← 台城围城关卡图
│   └── 岭南-三吴区域图.html  ← 主角动线图
│
├── nanbeichao-relations/    ← 人物关系数据库
│   ├── relations.db          ← SQLite(295人/279关系/195事件/84志怪/39改写节点)
│   ├── schema.sql            ← 九表两视图
│   ├── export/               ← JSON/CSV 导出(引擎加载用)
│   ├── seed_*.json           ← 12批精抽种子(每条带原文evidence)
│   ├── corpus_*.txt          ← 语料切分(正史原文)
│   └── *.py                  ← 工具链(7个脚本)
│
├── nanbeichao-design/       ← 游戏设计(13件策划案, 6.3万字)
│   ├── 00-游戏框架总纲.md     ← 定位/循环/三幕/系统清单/依赖图
│   ├── 01-角色养成系统.md     ← 属性/技能树/身份/装备
│   ├── 02-关系网系统.md       ← 295人网络/polarity/拉拢/背叛
│   ├── 03-战斗系统.md        ← 人战+鬼战/武器/骑乘/以步制骑
│   ├── 04-冤气超度系统.md     ← 怨气法则/阴阳眼/超度/范缜难题
│   ├── 05-围城经济系统.md     ← 130天生存/粮价/疫病/援军
│   ├── 06-信息战系统.md       ← 情报/伪造/童谣/离间
│   ├── 07-宗室名册系统.md     ← 家族树/威胁值/死亡预警
│   ├── 08-地图探索系统.md     ← 三层地图/移动/发现
│   ├── 09-事件改写系统.md     ← 39节点/后果链/6种结局
│   ├── 10-谶谣预言系统.md     ← 84条志怪/解读/反向操作
│   ├── 11-UI框架.md          ← HUD/对话/关系网可视化/键位
│   ├── 12-数值框架.md        ← 成长曲线/伤害公式/资源平衡/难度
│   ├── 02a-主线剧本-对话文案版.md ← 12节点全对话
│   ├── 03-序章-岭南.md       ← 序章三幕
│   ├── 04-NPC卡.md           ← 20张核心NPC卡
│   ├── 05-世界观规则.md      ← 怨气/显形/佛寺/天命
│   ├── 06-决策记录.md        ← 四项默认+推翻开关
│   └── prototype.html        ← Web原型垂直切片
│
├── _memory/                 ← AI 记忆文件(转移到新电脑用)
│   └── *.md                  ← 项目记忆/环境坑/用户偏好
│
└── books/                   ← 公版参考书(不进Git,单独传输)
    ├── 吕思勉《两晋南北朝史》
    └── 陈寅恪《隋唐制度渊源略论稿》
```

## 快速开始

```bash
# 1. 克隆到新电脑
git clone <repo_url>

# 2. 启动本地预览
cd default
py -m http.server 8613 --bind 127.0.0.1

# 3. 查看原型
# 浏览器打开 http://127.0.0.1:8613/nanbeichao-design/prototype.html

# 4. 查看地图
# http://127.0.0.1:8613/nanbeichao-shigao/qqtu.html
# http://127.0.0.1:8613/nanbeichao-shigao/建康城详图.html

# 5. 恢复记忆(新电脑上)
# 把 _memory/ 里的文件复制到 ZCode 的记忆目录
```

## 数据库查询示例

```bash
cd nanbeichao-relations
py -c "
import sqlite3
c = sqlite3.connect('relations.db')
print('人物:', c.execute('SELECT COUNT(*) FROM persons').fetchone()[0])
print('关系:', c.execute('SELECT COUNT(*) FROM relations').fetchone()[0])
print('事件:', c.execute('SELECT COUNT(*) FROM events').fetchone()[0])
print('志怪:', c.execute(\"SELECT COUNT(*) FROM events WHERE event_type='志怪'\").fetchone()[0])
"
```

## 合规声明

- 所有数据从公版正史(维基文库对照本)独立抽取
- 每条关系带 evidence 原文引文(合规底稿)
- 未使用任何 CBDB 数据
- schema 按游戏玩法定义,不复刻 CBDB 分类
