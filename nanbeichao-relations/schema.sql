-- 南北朝人物关系库 schema v0.1(为游戏玩法自设,不复刻 CBDB 分类体系)
-- 合规原则:数据只从公版史料原文独立抽取;每条数据保留 source 引文底稿;
--           不下载/导入 CBDB 任何文件;错误指纹独立产生,不复用任何第三方消歧结论。

PRAGMA foreign_keys = ON;

-- 语料登记(留证:每份输入文本的来源与哈希)
CREATE TABLE source_texts (
  id          INTEGER PRIMARY KEY,
  title       TEXT NOT NULL,            -- 书名,如《梁书》
  file_path   TEXT NOT NULL,            -- 本地文件路径
  origin      TEXT NOT NULL,            -- 来源说明,如"维基文库对照本"
  sha256      TEXT,                     -- 全文哈希(防篡改留证)
  charset     TEXT DEFAULT 'utf-8',
  ingested_at TEXT DEFAULT (datetime('now'))
);

-- 文本切片(按卷切段,抽取的最小输入单元)
CREATE TABLE chunks (
  id          INTEGER PRIMARY KEY,
  source_id   INTEGER NOT NULL REFERENCES source_texts(id),
  juan        INTEGER,                  -- 卷号
  juan_title  TEXT,                     -- 卷题,如"列传第十·侯景"
  char_start  INTEGER,
  char_end    INTEGER,
  text        TEXT NOT NULL,
  sha256      TEXT
);

-- 人物(游戏需要的最小字段;宁缺毋滥,置信度<0.6 的不进正式表)
CREATE TABLE persons (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,            -- 本名
  courtesy    TEXT,                     -- 字
  xiaozihao   TEXT,                     -- 小字(如 黑獭/寄奴)
  title_label TEXT,                     -- 最常用称谓(如 梁武帝/宇宙大将军)
  era         TEXT,                     -- 大时代标签(东晋/宋/齐/梁/陈/北魏/东魏/西魏/北齐/北周/隋)
  birth_year  INTEGER,
  death_year  INTEGER,
  death_cause TEXT,                     -- 死因标签(战死/赐死/饿死/被俘杀/病卒...)——玩法直接可用
  home_region TEXT,                     -- 籍贯(粗粒度:郡级)
  faction     TEXT,                     -- 阵营标签(怀朔系/武川系/北府/侨姓/吴姓/岭南...)
  confidence  REAL DEFAULT 1.0,         -- 0-1
  notes       TEXT,
  UNIQUE(name, courtesy, home_region)
);

-- 人名消歧(同名/别名归并——本库最大难点,错误会在关系网传染)
CREATE TABLE person_aliases (
  id          INTEGER PRIMARY KEY,
  person_id   INTEGER NOT NULL REFERENCES persons(id),
  alias       TEXT NOT NULL,            -- 别名/字/小字/官称(如 兰陵王/韦虎/任蛮奴)
  alias_type  TEXT,                     -- 字/小字/封号/官称/谥号/史称
  UNIQUE(alias, person_id)
);

-- 关系(按游戏玩法定义的类型体系——自设,非 CBDB 编码)
-- 类型枚举(首期):君臣 姻亲 父子 母子 兄弟 师从 举荐 同僚 交游 仇敌 军事对手 效忠 背叛 收养
CREATE TABLE relations (
  id          INTEGER PRIMARY KEY,
  subject_id  INTEGER NOT NULL REFERENCES persons(id),
  object_id   INTEGER NOT NULL REFERENCES persons(id),
  rel_type    TEXT NOT NULL,
  rel_detail  TEXT,                     -- 一句话事实描述,如"以五百甲士劫杀之"
  start_year  INTEGER,
  end_year    INTEGER,
  weight      REAL DEFAULT 1.0,         -- 玩法权重(互动频率/剧情重要度)
  polarity    INTEGER DEFAULT 1,        -- 1 正面 -1 敵对 0 中性
  confidence  REAL DEFAULT 0.8,
  evidence    TEXT NOT NULL,            -- 史料原文引文(合规底稿,必填!)
  chunk_id    INTEGER REFERENCES chunks(id)
);

-- 事件(时间轴:编年体骨架,通鉴/帝纪抽取)
CREATE TABLE events (
  id          INTEGER PRIMARY KEY,
  year_ce     INTEGER,                  -- 公元年
  year_raw    TEXT,                     -- 原文纪年,如"太清二年十月"
  month       INTEGER,
  title       TEXT NOT NULL,            -- 事件名,如"采石渡江"
  summary     TEXT,
  event_type  TEXT,                     -- 战争/政变/灾异/外交/制度/文化/志怪
  location    TEXT,                     -- 地点(粗粒度)
  evidence    TEXT,                     -- 史料原文引文(合规底稿)
  is_rewrite_node INTEGER DEFAULT 0,    -- 是否游戏改写节点(对应通史稿的①-⑩体系)
  source_id   INTEGER REFERENCES source_texts(id),
  chunk_id    INTEGER REFERENCES chunks(id)
);

-- 事件-人物关联(N:N)
CREATE TABLE event_participants (
  event_id    INTEGER NOT NULL REFERENCES events(id),
  person_id   INTEGER NOT NULL REFERENCES persons(id),
  role        TEXT,                     -- 主帅/守将/被杀者/立王者...
  PRIMARY KEY (event_id, person_id)
);

-- 抽取留证(每次 LLM/规则抽取的完整记录——独立创作的证据链)
CREATE TABLE extractions (
  id          INTEGER PRIMARY KEY,
  batch_id    TEXT NOT NULL,            -- 抽取批次
  chunk_id    INTEGER REFERENCES chunks(id),
  method      TEXT NOT NULL,            -- 'rule-v0' / 'glm-5.3-prompt-v1' ...
  prompt_ver  TEXT,
  raw_output  TEXT,                     -- 原始输出(JSONL)
  reviewed    INTEGER DEFAULT 0,        -- 人工抽查标记
  review_note TEXT,
  created_at  TEXT DEFAULT (datetime('now'))
);

-- 人工抽查表(90% 精度目标的质检流程)
CREATE TABLE reviews (
  id          INTEGER PRIMARY KEY,
  target_table TEXT NOT NULL,           -- persons/relations/events
  target_id   INTEGER NOT NULL,
  verdict     TEXT NOT NULL,            -- accept/fix/reject
  fix_note    TEXT,
  reviewer    TEXT DEFAULT 'human',
  created_at  TEXT DEFAULT (datetime('now'))
);

-- 索引
CREATE INDEX idx_rel_subject ON relations(subject_id);
CREATE INDEX idx_rel_object  ON relations(object_id);
CREATE INDEX idx_rel_type    ON relations(rel_type);
CREATE INDEX idx_alias       ON person_aliases(alias);
CREATE INDEX idx_event_year  ON events(year_ce);
CREATE INDEX idx_chunk_src   ON chunks(source_id, juan);

-- 视图:某人物的一跳关系网(游戏 UI 直接可用)
CREATE VIEW v_person_network AS
SELECT p.id AS person_id, p.name, r.rel_type, r.polarity, q.name AS other_name, q.id AS other_id, r.evidence
FROM persons p
JOIN relations r ON r.subject_id = p.id
JOIN persons q ON q.id = r.object_id;

-- 视图:改写节点事件(主线事件表)
CREATE VIEW v_rewrite_nodes AS
SELECT * FROM events WHERE is_rewrite_node = 1 ORDER BY year_ce, month;
