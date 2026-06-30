# 知识图谱引擎优化方案

> **文档对象**: SKILL 维护适配组
> **基线版本**: build_in_harmonyos @ 1830ccd0
> **前置条件**: 熟悉 `scripts/ohc/engine.py`、`graph.py`、`pre_scan.py` 和 `knowledge/graph/` 目录结构

---

## 一、现状总结

### 1.1 系统架构

当前知识图谱系统由以下组件构成:

```
knowledge/
├── graph/
│   ├── index.tsv              # 100 行主索引 (11 列 TSV, Phase A 粗筛数据源)
│   ├── E001.kv ~ E105.kv      # 100 个错误模式条目 (自研 KV 格式)
│   ├── principles.kv           # 21 条原则 (方案过滤器)
│   ├── pre-scan-rules.yaml     # 预扫描规则
│   └── draft/                  # ~200 个草稿 (闭环学习)
└── doc/
    └── E001.md ~ E089.md       # 88 个详细文档

scripts/ohc/
├── engine.py                   # 五阶段匹配引擎 (515 行)
├── graph.py                    # 知识图谱 CRUD (1014 行)
├── pre_scan.py                 # 预编译源码风险扫描 (489 行)
├── conan_verify.py             # G0-G4 + L2/L4/L5 门禁 (1002 行)
└── driver.py                   # 13 步编译管线驱动
```

### 1.2 匹配引擎工作流 (engine.py)

```
Phase A: 扫 index.tsv 全部 100 行
         关键词子串匹配: if kw.lower() in error_lower → score += 1
         严重度加权: sev3 → ×3, sev2 → ×2
         取 top-5 候选

Phase B: 加载 top-5 的 .kv 文件
         error_signature 正则精排 (+5 分/命中)
         match_keywords 辅助 (+1 分/命中)
         选出最佳匹配

Phase C: 加载最佳匹配的完整 .kv
         解析方案/回退/禁止规则 → ErrorEntry 对象

Phase D: 查 principles.kv
         映射原则名, critical 级 forbid_pattern 自动拒绝

Phase E: 格式化输出 (inline/json/autofix/interactive)
```

### 1.3 调用链路

| 调用方 | 位置 | 用途 |
|---|---|---|
| driver.py | `_run_engine()` (line 317) | 编译失败时匹配错误, 驱动自动重试 |
| conan_verify.py | `_gate0_precheck()` (line 375) | conan create 前预检已知风险 |
| conan_verify.py | `_query_knowledge_graph()` (line 152) | conan create 失败时匹配, 未命中则生成草稿 |
| engine CLI | `engine_cli()` (line 502) | 命令行查询: `ohc engine "error text"` |

---

## 二、问题分析

### 2.1 匹配精度不足 (P1 - 高优先级)

**现象**: Phase A 使用纯子串匹配 (`kw.lower() in error_lower`)，不同编译器版本、不同语言的错误措辞差异会导致漏匹配。

**示例**:
```
条目 E003 match_keywords: "pthread, undefined reference, -lpthread"
实际错误日志: "ld.lld: error: undefined symbol: pthread_create"
→ "pthread_create" 不在 keywords 中, 但本质是同一问题
```

**根因**: 子串匹配无法处理同义词、词形变化、上下文变体。

### 2.2 关系网络未被利用 (P2 - 高优先级)

**现象**: 每个 .kv 文件都定义了关系字段:
- `causes`: 该错误会导致什么
- `caused_by`: 该错误由什么引起
- `similar_to`: 相似错误
- `conflicts_with`: 冲突方案
- `prerequisite_of`: 前置条件

但引擎的 Phase A-E **没有任何一个阶段查询这些关系**。关系数据是死数据。

**示例**:
```
E001 (编译器缺失) caused_by → E007 (config.guess 不识别 OHOS)
当前: 匹配到 E001 后不会推荐检查 E007
期望: 匹配到 E001 后, 顺 caused_by 链推荐 E007 的修复方案
```

### 2.3 KV 自研格式缺少工具生态 (P3 - 中优先级)

**现象**: 手写的 `_kv_get()` / `_kv_set()` 逐行解析器 (graph.py 第 115-146 行)。

**问题**:
- 不支持多行值嵌套
- 不支持注释保留 (写入时丢失)
- 没有 lint 校验工具
- 没有 IDE 语法高亮
- YAML/JSON 都有成熟的工具链而我们没有

### 2.4 无版本化溯源 (P4 - 低优先级)

**现象**: 条目只有 `last_updated` 时间戳，无法回答"这个条目是谁在什么 PR 中添加的"。

**影响**: 当一个条目的修复方案导致构建失败时，无法快速定位责任人。

---

## 三、解决方案

### 方案 A: Phase A 升级为 BM25 排序 (解决 P1)

**技术选型**: Python 内置 `sqlite3` + FTS5 扩展 (零额外依赖)

**原理**: FTS5 是 SQLite 的全文检索扩展，内置 BM25 排序算法。比子串匹配精准得多——支持分词、词频归一化、前缀匹配。

**改造范围**:

1. 新增 `scripts/ohc/kb_index.py` — 索引管理模块

```python
"""知识图谱 FTS5 索引管理。

用 SQLite FTS5 替代 index.tsv 的子串匹配。
索引存储在 knowledge/graph/kb_index.db (自动生成, 不入 git)。
"""
import sqlite3
import os
import re
from pathlib import Path

SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
    id UNINDEXED,
    severity UNINDEXED,
    keywords,
    signature,
    title,
    category,
    tokenize = 'unicode61'
);
"""


def build_index(graph_dir: str) -> str:
    """扫描所有 .kv 文件, 构建 FTS5 索引。

    在 knowledge/graph/kb_index.db 生成 SQLite 数据库。
    每次引擎启动时自动调用 (检测 .kv 比 .db 新则重建)。
    """
    db_path = os.path.join(graph_dir, "kb_index.db")

    # 增量更新: 检测是否有 .kv 比 .db 新
    db_mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else 0
    needs_rebuild = False
    kv_files = []
    for f in sorted(os.listdir(graph_dir)):
        if re.match(r'^E\d+\.kv$', f):
            kv_path = os.path.join(graph_dir, f)
            kv_files.append(kv_path)
            if os.path.getmtime(kv_path) > db_mtime:
                needs_rebuild = True

    if not needs_rebuild and os.path.exists(db_path):
        return db_path

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM kb_fts")

    for kv_path in kv_files:
        data = _parse_kv(kv_path)
        keywords = data.get("match_keywords", "").replace("\n", " ").strip()
        signature = data.get("error_signature", "").replace("|", " ").strip()
        conn.execute(
            "INSERT INTO kb_fts (id, severity, keywords, signature, title, category) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                data.get("id", ""),
                int(data.get("severity", "0")),
                keywords,
                signature,
                data.get("title", ""),
                data.get("category", ""),
            ),
        )

    conn.commit()
    conn.close()
    return db_path


def search(error_text: str, graph_dir: str, top_n: int = 5) -> list[dict]:
    """BM25 全文检索, 返回 top-N 候选。

    Args:
        error_text: 编译错误日志文本
        graph_dir: knowledge/graph/ 目录路径
        top_n: 返回候选数量

    Returns:
        [{"id": "E001", "score": -2.34, "severity": 3}, ...]
        (FTS5 bm25() 返回负值, 越接近 0 越相关)
    """
    db_path = build_index(graph_dir)
    conn = sqlite3.connect(db_path)

    # 构建 FTS5 查询表达式
    # 从错误文本中提取有意义的 token (过滤太短/太通用的词)
    tokens = _extract_query_tokens(error_text)

    # 用 OR 连接, 匹配 keywords 和 signature 列
    query = " OR ".join(f'"{t}"' for t in tokens)
    if not query:
        conn.close()
        return []

    rows = conn.execute(
        "SELECT id, severity, bm25(kb_fts) AS score "
        "FROM kb_fts WHERE kb_fts MATCH ? "
        "ORDER BY score ASC LIMIT ?",
        (query, top_n),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "id": row[0],
            "severity": row[1],
            "score": row[2],
        })
    return results


# 过滤太短 (<3 字符) 和太通用 (the/for/with 等) 的词
_STOPWORDS = frozenset({
    "the", "for", "with", "and", "not", "are", "but", "you", "all",
    "any", "can", "had", "her", "was", "one", "our", "out", "has",
    "have", "him", "his", "how", "its", "may", "new", "now", "old",
    "see", "them", "then", "this", "will", "your", "from", "that",
    "make", "error", "warning", "failed", "file", "line",
})


def _extract_query_tokens(text: str) -> list[str]:
    """从错误文本提取有意义的查询 token。"""
    tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _parse_kv(path: str) -> dict:
    """简化版 KV 解析 (与 graph.py 的 _kv_get 兼容)。"""
    data = {}
    current_key = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("#"):
                continue
            m = re.match(r'^([a-z_]+):\s*(.*)', line)
            if m:
                current_key = m.group(1)
                data[current_key] = m.group(2).strip()
            elif current_key and line.startswith(" "):
                data[current_key] += " " + line.strip()
    return data
```

2. 修改 `engine.py` 的 `_phase_a()`

```python
# 改造前 (engine.py 第 52-85 行):
def _phase_a(error_text, index_entries, min_score=2, top_n=5):
    error_lower = error_text.lower()
    for entry in index_entries:
        score = 0
        for kw in entry.keywords:
            if kw.lower() in error_lower:
                score += 1
        ...

# 改造后:
def _phase_a(error_text, index_entries, min_score=2, top_n=5):
    from kb_index import search as fts_search
    graph_dir = _get_graph_dir()  # knowledge/graph/ 路径
    fts_results = fts_search(error_text, graph_dir, top_n=top_n)

    # 如果 FTS5 可用, 优先使用
    if fts_results:
        candidates = []
        for r in fts_results:
            entry = _find_entry_by_id(index_entries, r["id"])
            if entry:
                # BM25 score 是负值, 转为正值用于与 Phase B 加权
                candidates.append(_Candidate(entry, abs(r["score"]) * 2))
        return candidates[:top_n]

    # 回退: 原子串匹配逻辑 (兼容性保障)
    return _phase_a_legacy(error_text, index_entries, min_score, top_n)
```

3. 保留原 `_phase_a` 逻辑为 `_phase_a_legacy` 作为回退

**验证方法**:

```bash
# 在 OHOS 真机上测试
python3 scripts/ohc-run.py engine "undefined reference to pthread_create"
# 改造前: 可能不命中 (因为 keywords 中是 "pthread" 不是 "pthread_create")
# 改造后: 应命中 E003 (BM25 分词后 "pthread" 和 "create" 都匹配)
```

**注意事项**:
- `kb_index.db` 是自动生成的, 加入 .gitignore
- FTS5 是 SQLite 的编译选项, Python 内置 sqlite3 通常已包含. 验证命令:
  ```python
  python3 -c "import sqlite3; c=sqlite3.connect(':memory:'); c.execute('CREATE VIRTUAL TABLE t USING fts5(x)'); print('FTS5 OK')"
  ```
- 如果 OHOS 真机的 Python 没有编译 FTS5, 回退到原 `_phase_a_legacy` 逻辑

---

### 方案 B: 激活关系网络遍历 (解决 P2)

**改造范围**: engine.py 新增 `_phase_b_plus()` 步骤

1. 在 Phase B 选出最佳匹配后, 新增关系扩展步骤:

```python
def _phase_b_plus(best_id, candidates, gdir, index_entries):
    """Phase B+: 关系网络扩展.

    沿 best_id 的 similar_to / caused_by 边扩展候选列表,
    让关联条目也参与 Phase C 的方案生成.
    """
    best_kv = parse_kv_file(os.path.join(gdir, f"{best_id}.kv"))

    # 收集关系目标
    relation_ids = set()
    for rel_field in ("similar_to", "caused_by"):
        raw = best_kv.get(rel_field, "").strip()
        if raw:
            # 格式: [E042, E080] 或 E042, E080
            for rid in re.findall(r'E\d+', raw):
                relation_ids.add(rid)

    # 为关联条目创建候选
    existing_ids = {c.entry.id for c in candidates}
    for rid in relation_ids:
        if rid not in existing_ids:
            entry = _find_entry_by_id(index_entries, rid)
            if entry:
                # 关联条目给一个中等分数, 让 Phase B 的正则可以提升它
                candidates.append(_Candidate(entry, score=1))

    return candidates
```

2. 在 `run_engine()` 中调用:

```python
# engine.py run_engine() 中, Phase B 之后, Phase C 之前:
match_id, b_score, a_score = _phase_b(error_text, candidates, gdir)

# ▼ 新增: 关系网络扩展
candidates = _phase_b_plus(match_id, candidates, gdir, index_entries)

entry = _phase_c(match_id, gdir)  # Phase C 不变
```

3. 输出中增加关系信息:

```python
# format_inline() 中增加:
if entry.relations:
    lines.append(f"  🔗 关联: {', '.join(entry.relations)}")
```

**验证方法**:

```bash
# E001 (编译器缺失) 的 caused_by 包含 E007 (config.guess)
python3 scripts/ohc-run.py engine "cc: not found"
# 改造后输出应包含: 🔗 关联: E007 (config.guess 不识别 OHOS)
```

---

### 方案 C: KV → YAML 格式迁移 (解决 P3)

**原则**: 渐进迁移, 不一次性全改. 新增用 YAML, 旧 KV 保持兼容.

**步骤**:

1. 在 `engine.py` 和 `graph.py` 中新增 YAML 读取能力:

```python
def parse_kb_file(path: str) -> dict:
    """读取知识条目, 自动识别 .yaml 和 .kv 格式.

    优先尝试 YAML (如果 PyYAML 可用), 回退到 KV 解析.
    """
    # 优先读 .yaml 版本
    yaml_path = path.rsplit(".", 1)[0] + ".yaml"
    if os.path.exists(yaml_path):
        try:
            import yaml
            with open(yaml_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            pass

    # 回退到 .kv 解析
    return _parse_kv_file(path)
```

2. 新增条目时使用 YAML 格式:

```bash
# graph.py cmd_add 中, 新条目默认生成 .yaml
# 模板 _template.yaml:
```

```yaml
# _template.yaml — 知识图谱条目模板 (YAML 版)
id: Ennn
title: ""
trigger_tool: ""
phase: ""
error_signature:
  - ""

severity: 0
category: ""
match_keywords:
  - ""

root_cause: ""
affected_scope: ""
verification_cmd: ""

rec_priority: 1
rec_approach: ""
rec_description: ""
rec_command: ""
rec_auto_fix: false
rec_impl: ""

# 关系网络
causes: []
caused_by: []
similar_to: []
conflicts_with: []
prerequisite_of: []

# 原则
principles: []

doc_file: ""
```

3. 旧 `.kv` 文件不做强制迁移, `parse_kb_file()` 自动兼容两种格式

**迁移工具** (一次性, 用于批量转换):

```python
# scripts/migrate_kv_to_yaml.py
"""批量将 .kv 转为 .yaml (保留原始 .kv 作为备份)."""
import os
import re
# ... 见上方 parse_kv 逻辑 ...

def kv_to_yaml(kv_path: str, yaml_path: str):
    data = _parse_kv(kv_path)
    # 将逗号分隔的列表转为 YAML 列表
    for list_field in ("match_keywords", "error_signature", "principles",
                       "causes", "caused_by", "similar_to"):
        if list_field in data and isinstance(data[list_field], str):
            items = [x.strip() for x in data[list_field].split(",") if x.strip()]
            data[list_field] = items
    import yaml
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":
    import sys
    gdir = sys.argv[1] if len(sys.argv) > 1 else "knowledge/graph"
    for f in os.listdir(gdir):
        if re.match(r'^E\d+\.kv$', f):
            kv_path = os.path.join(gdir, f)
            yaml_path = kv_path.rsplit(".", 1)[0] + ".yaml"
            kv_to_yaml(kv_path, yaml_path)
            print(f"  {f} → {os.path.basename(yaml_path)}")
```

**注意事项**:
- PyYAML 不是 Python 标准库. 如果 OHOS 真机没有 PyYAML, 保留 KV 回退
- `pre-scan-rules.yaml` 已经是 YAML 格式, 说明环境中 PyYAML 可能已可用
- 迁移后 `.kv` 文件不要删除, 保留作为备份直到确认所有路径都走 `parse_kb_file()`

---

### 方案 D: 条目溯源 (解决 P4)

**改造范围**: graph.py 的 `cmd_add` 和 `cmd_update`

1. 在 `.kv` / `.yaml` 模板中新增溯源字段:

```yaml
# 条目元数据
source:
  pr_number: null        # 添加该条目的 PR 编号
  commit_sha: ""         # 添加时的 commit SHA
  author: ""             # 添加者 (协作者 ID 或用户名)
  created_at: ""         # 创建时间 (ISO 8601)
  last_updated: ""       # 最后更新时间
  change_log:            # 变更历史
    - {date: "", author: "", change: "初始创建"}
```

2. `cmd_add --field source.pr_number=1567` 设置溯源信息

3. `cmd_validate --coverage` 输出中增加溯源覆盖率:

```
溯源覆盖率: 78/100 (78%)
  有 PR 关联: 65
  有作者: 78
  有变更日志: 45
```

**注意**: 这是低优先级改进, 不阻塞其他方案.

---

## 四、实施计划

### 4.1 优先级排序

| 优先级 | 方案 | 改造文件 | 预计代码量 | 风险 |
|---|---|---|---|---|
| **P0** | 方案 A: BM25 排序 | 新增 kb_index.py + 改 engine.py _phase_a | ~150 行新 + ~30 行改 | 低 (有回退) |
| **P0** | 方案 B: 关系网络 | 改 engine.py + format 输出 | ~50 行新 | 低 |
| **P1** | 方案 C: YAML 迁移 | 新增 parse_kb_file + 迁移工具 | ~100 行新 | 中 (格式变更) |
| **P2** | 方案 D: 条目溯源 | 改 graph.py cmd_add/update | ~40 行改 | 低 |

### 4.2 验收标准

**方案 A 验收**:
1. 准备 10 组"旧引擎不命中但应该命中"的错误日志样本
2. 改造后引擎命中数 ≥ 8/10
3. 旧引擎命中的样本改造后仍然命中 (无回退)
4. OHOS 真机无 FTS5 时自动回退到原逻辑

**方案 B 验收**:
1. 匹配到 E001 时输出包含关联条目 E007
2. 匹配到 E042 时输出包含 similar_to 中的条目
3. 关联条目为空的条目不受影响

**方案 C 验收**:
1. 新建条目默认生成 .yaml 格式
2. 旧 .kv 文件仍可被引擎正常读取
3. 迁移工具批量转换后, 引擎能正确读取 .yaml

### 4.3 不做什么

以下方案经评估**不推荐**, 请勿实施:

1. **不要引入 LightRAG / GraphRAG**: 依赖 LLM API, OHOS 真机无法调用, 100 条目规模过度工程化
2. **不要引入 Neo4j / 图数据库**: JVM 服务无法在真机运行, 关系规模太小 (100 条目 × 几条边)
3. **不要引入向量数据库** (FAISS / Chroma): 需要 embedding 模型, 真机无 GPU, 100 条目用 BM25 足够
4. **不要一次性迁移所有 KV**: 渐进迁移, 新增 YAML + 旧 KV 兼容, 避免一次性风险

---

## 五、附录

### 5.1 现有数据统计

| 指标 | 数值 |
|---|---|
| 错误模式条目 | 100 个 (E001-E105, 缺号 5 个) |
| 原则 | 21 条 |
| 预扫描规则 | 10+ 条显式 + 17 个 musl 硬编码函数 |
| 草稿 | ~200 个 |
| 详细文档 | 88 个 |
| 总数据量 | ~250 KB |
| engine.py 行数 | 515 行 |
| graph.py 行数 | 1014 行 |
| pre_scan.py 行数 | 489 行 |

### 5.2 引擎调用点

| 调用方 | 文件 | 行号 | 函数 |
|---|---|---|---|
| 编译驱动 | driver.py | 317 | `_run_engine()` |
| 门禁预检 | conan_verify.py | 375 | `_gate0_precheck()` |
| 门禁错误处理 | conan_verify.py | 152 | `_query_knowledge_graph()` |
| 命令行 | engine.py | 502 | `engine_cli()` |

### 5.3 _phase_a 现有逻辑 (改造基线)

```python
# engine.py 第 52-85 行 (当前版本)
def _phase_a(error_text, index_entries, min_score=2, top_n=5):
    error_lower = error_text.lower()
    candidates = []
    for entry in index_entries:
        score = 0
        for kw in entry.keywords:
            if len(kw) < 2:
                continue
            if kw.lower() in error_lower:
                score += 1
        if entry.severity >= 3:
            score *= 3
        elif entry.severity >= 2:
            score *= 2
        if score >= min_score:
            candidates.append(_Candidate(entry, score))
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]
```

### 5.4 关系字段定义 (待激活)

```yaml
# .kv 文件中的关系字段 (当前已定义但未被引擎使用)
causes:           [E042]         # 该错误会导致 E042
caused_by:        [E007]         # 该错误由 E007 引起
similar_to:       [E043, E080]   # 相似错误
conflicts_with:   []             # 冲突的修复方案
prerequisite_of:  []             # 该错误是其他错误的前置条件
```

### 5.5 .gitignore 新增

```
# 知识图谱自动生成的索引 (方案 A)
knowledge/graph/kb_index.db
```
