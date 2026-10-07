# 游戏数据导出说明

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
