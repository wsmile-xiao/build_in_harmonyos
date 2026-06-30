# 知识图谱引擎优化方案 V2

> **文档版本**: V2 (基于业界对标分析重构)
> **文档对象**: SKILL 维护适配组
> **基线版本**: build_in_harmonyos_new @ f461d901
> **前置条件**: 熟悉 scripts/ohc/engine.py、graph.py、pre_scan.py 和 knowledge/graph/ 目录结构

---

## 零、业界对标分析

V1 版本低估了业界已有方案的成熟度。经调研发现两个直接对标的开源项目，
其设计理念与我们的知识图谱系统高度重合，但在数据规模、匹配精度和工程化方面领先。

### 0.1 deadends.dev — 最接近的对标项目

定位: 通用构建/部署错误知识库，MIT 许可证 (代码) + CC BY 4.0 (数据)。

| 维度 | 我们的系统 | deadends.dev | 差距 |
|------|-----------|--------------|------|
| 条目数 | 100 个 | **2339 个** (54 个领域) | 23 倍 |
| 关系网络 | 定义了但引擎没用 | **2524+ 条错误链边**，实际用于级联预测 | 完全浪费 |
| 失败方案 | forbid_N_* 规则 (手动) | **4923 条 dead ends** (已知走不通的路径) | 50 倍 |
| 修复方案 | rec_* + 多级 fallback | **5477 条 workarounds** | 50 倍 |
| 匹配方式 | 子串 + 正则 | 正则 + **REST API** (/api/v1/match.json) | 缺标准接口 |
| 数据格式 | 自研 KV | **JSON ErrorCanon** (版本化记录) | 缺工具链 |
| API | Python 函数 | **REST API + MCP Server** (8 个工具) | 缺标准化 |
| 输出格式 | 4 种 | **18 种** (JSON/OpenAPI/JSON-LD/llms.txt/NDJSON/Atom...) | 缺格式 |
| 质量度量 | 无 | fail rate / success rate / confidence / freshness | 无法评估 |

核心启示:

1. 关系网络是核心价值 — 2524 条边证明这不是装饰数据
2. dead ends 概念 = 我们的 forbid_N_*，但规模差 50 倍，需要系统化积累
3. 质量度量 (success_rate) 让知识库可以自我优化，淘汰低质量条目

### 0.2 FixHive (TheMagicTower) — 云端社区方案

定位: 开发者社区错误知识共享平台，MIT 许可证，TypeScript。

| 维度 | 我们的系统 | FixHive | 差距 |
|------|-----------|---------|------|
| 匹配方式 | 子串 + 正则 | **AI 归一化 + pgvector 语义相似度** | 缺语义层 |
| 存储 | 本地文件 | **Supabase + pgvector** (云端) | 架构不同 |
| 核心创新 | 原则库自动拒绝 | **错误签名归一化** (占位符替换) | 值得借鉴 |
| 社区 | 草稿审核 | **社区投票** (upvote/downvote) | 无 |
| 部署 | 纯本地 | 云端 (需 OpenAI API + Supabase) | 不适用 |

核心启示:

1. 错误签名归一化 — 把 `Cannot find module 'react'` 归一化为 `Cannot find module {module}`
2. 语义向量检索 — 解决子串匹配无法处理的"措辞不同但本质相同"问题
3. 社区投票 — 让用户反馈驱动条目质量，无需人工全量审核

### 0.3 我们独有的优势 (两个项目都没有)

1. **原则库自动拒绝** — critical 级 forbid_pattern 自动拦截危险方案 (安全防线)
2. **预扫描** (pre_scan.py) — 编译前扫源码提前发现风险
3. **OHOS/musl 领域特化** — musl 缺失函数表、config.guess 替换等
4. **闭环学习** — extract_rules_from_patch 从补丁反提取规则
5. **无云端依赖** — 纯本地运行，OHOS 真机可用

---

## 一、现状总结

### 1.1 系统架构

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
         关键词子串匹配: if kw.lower() in error_lower -> score += 1
         严重度加权: sev3 -> x3, sev2 -> x2
         取 top-5 候选

Phase B: 加载 top-5 的 .kv 文件
         error_signature 正则精排 (+5 分/命中)
         match_keywords 辅助 (+1 分/命中)
         选出最佳匹配

Phase C: 加载最佳匹配的完整 .kv
         解析方案/回退/禁止规则 -> ErrorEntry 对象

Phase D: 查 principles.kv
         映射原则名, critical 级 forbid_pattern 自动拒绝

Phase E: 格式化输出 (inline/json/autofix/interactive)
```

### 1.3 调用链路

| 调用方 | 位置 | 用途 |
|---|---|---|
| driver.py | _run_engine() (line 317) | 编译失败时匹配错误, 驱动自动重试 |
| conan_verify.py | _gate0_precheck() (line 375) | conan create 前预检已知风险 |
| conan_verify.py | _query_knowledge_graph() (line 152) | conan create 失败时匹配, 未命中则生成草稿 |
| engine CLI | engine_cli() (line 502) | 命令行查询: ohc engine "error text" |

---

## 二、问题分析 (基于业界对标)

### P1: 匹配精度不足 — 缺少错误归一化 (高优先级)

现状: Phase A 用子串匹配，不同编译器版本、语言的措辞差异导致漏匹配。

业界对标: FixHive 用占位符归一化解决同类问题:

```
原始错误: Cannot find module 'react'
归一化后: Cannot find module {module}
-> 一个签名匹配所有模块缺失错误
```

我们的 match_keywords 靠手动列举变体，无法穷举。需要引入签名归一化。

### P2: 关系网络未被利用 (高优先级)

现状: .kv 定义了 causes/caused_by/similar_to 关系，引擎完全没用。

业界对标: deadends.dev 的 2524 条边实际用于级联故障预测。这是知识图谱的核心价值。

### P3: 无质量度量 (高优先级)

现状: 条目只有 last_updated，无法评估修复方案的有效性。

业界对标: deadends.dev 每个 workaround 记录 success_rate / fail_rate / confidence。
没有质量度量就无法淘汰低质量条目，知识库会膨胀。

### P4: KV 自研格式缺少工具生态 (中优先级)

现状: 手写逐行解析器，无 lint / IDE 高亮 / 多行嵌套支持。

业界对标: deadends.dev 用 JSON ErrorCanon，FixHive 用 JSON + pgvector。

### P5: 缺少标准化 API (低优先级)

现状: 只有 Python 函数调用。

业界对标: deadends.dev 提供 REST API + MCP Server，AI 工具可直接查询。

---

## 三、解决方案

### 方案 A: 错误签名归一化 (解决 P1, 借鉴 FixHive)

**目标**: 引入占位符归一化，让一个签名匹配所有变体错误。

**改造范围**: engine.py 新增 `_normalize_error()` + Phase A 前置归一化

1. 在 engine.py 中新增归一化模块:

```python
import re

# 归一化规则: 把可变部分替换为占位符
_NORMALIZE_RULES = [
    # 路径归一化
    (re.compile(r'/[\w./-]+\.\w{1,4}'),       '{path}'),
    # 版本号归一化
    (re.compile(r'\b\d+\.\d+\.\d+\b'),         '{version}'),
    (re.compile(r'\b\d+\.\d+\b'),              '{version}'),
    # 模块/库名归一化 (Cannot find module 'xxx')
    (re.compile(r"'([a-zA-Z@/_-]+)'"),         "'{module}'"),
    (re.compile(r'\b([a-zA-Z_]\w+)\.so\.\d+'), r'{lib}.so.{version}'),
    # 行号归一化
    (re.compile(r':\d+:\d+'),                  ':{line}'),
    (re.compile(r'line \d+'),                  'line {line}'),
    # 十六进制地址
    (re.compile(r'\b0x[0-9a-fA-F]+\b'),        '{addr}'),
]


def normalize_error(error_text: str) -> str:
    """把错误日志中的可变部分归一化为占位符。

    这样不同项目、不同版本的同类错误会生成相同的归一化签名，
    大幅提升匹配召回率。

    例:
        "Cannot find module 'react'"   -> "Cannot find module {module}"
        "undefined reference to dlopen" -> "undefined reference to {func}"
        "foo.c:42:5: error"            -> "{path}:{line}:{line}: error"

    Args:
        error_text: 原始错误日志

    Returns:
        归一化后的错误文本
    """
    result = error_text
    for pattern, replacement in _NORMALIZE_RULES:
        result = pattern.sub(replacement, result)
    return result
```

2. 在 `run_engine()` 入口处调用:

```python
# engine.py run_engine() 开头:
def run_engine(error_text, project_dir=None, top_n=5, sig_bonus=5):
    # 新增: 归一化
    normalized = normalize_error(error_text)
    # Phase A 同时用原始文本和归一化文本匹配
    candidates = _phase_a_dual(error_text, normalized, index_entries)
    ...
```

3. Phase A 双路匹配 (原始 + 归一化):

```python
def _phase_a_dual(error_text, normalized, index_entries, min_score=2, top_n=5):
    """双路匹配: 原始文本 + 归一化文本, 取并集."""
    raw_candidates = _phase_a(error_text, index_entries, min_score, top_n)
    norm_candidates = _phase_a(normalized, index_entries, min_score, top_n)

    # 合并去重 (归一化命中给额外加权)
    merged = {}
    for c in raw_candidates:
        merged[c.entry.id] = c
    for c in norm_candidates:
        if c.entry.id in merged:
            merged[c.entry.id].score += c.score  # 双重命中加分
        else:
            c.score += 2  # 仅归一化命中也加分
            merged[c.entry.id] = c

    result = sorted(merged.values(), key=lambda x: x.score, reverse=True)
    return result[:top_n]
```

**验证方法**:

```bash
# 测试 1: 模块缺失
python3 scripts/ohc-run.py engine "fatal error: 'openssl/ssl.h' file not found"
# 归一化后: fatal error: '{path}' file not found
# 应命中 openssl 相关条目

# 测试 2: 版本无关匹配
python3 scripts/ohc-run.py engine "undefined reference to curl_easy_init"
# 归一化后函数名保留, 应命中 curl 链接错误条目
```

---

### 方案 B: Phase A 升级为 BM25 排序 (解决 P1, 用 SQLite FTS5)

**技术选型**: Python 内置 `sqlite3` + FTS5 扩展 (零额外依赖)

**原理**: FTS5 是 SQLite 的全文检索扩展，内置 BM25 排序算法。比子串匹配精准。

**改造范围**:

1. 新增 `scripts/ohc/kb_index.py` — FTS5 索引管理模块

```python
"""知识图谱 FTS5 索引管理。

用 SQLite FTS5 替代 index.tsv 的子串匹配。
索引存储在 knowledge/graph/kb_index.db (自动生成, 不入 git)。
"""
import sqlite3
import os
import re

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
            (data.get("id", ""), int(data.get("severity", "0")),
             keywords, signature, data.get("title", ""),
             data.get("category", "")),
        )

    conn.commit()
    conn.close()
    return db_path


def search(error_text: str, graph_dir: str, top_n: int = 5) -> list:
    """BM25 全文检索, 返回 top-N 候选."""
    db_path = build_index(graph_dir)
    conn = sqlite3.connect(db_path)

    tokens = _extract_query_tokens(error_text)
    query = " OR ".join('"' + t + '"' for t in tokens)
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

    return [{"id": r[0], "severity": r[1], "score": r[2]} for r in rows]


_STOPWORDS = frozenset({
    "the", "for", "with", "and", "not", "are", "but", "you", "all",
    "any", "can", "had", "her", "was", "one", "our", "out", "has",
    "have", "him", "his", "how", "its", "may", "new", "now", "old",
    "see", "them", "then", "this", "will", "your", "from", "that",
    "make", "error", "warning", "failed", "file", "line",
})


def _extract_query_tokens(text: str) -> list:
    """从错误文本提取有意义的查询 token."""
    tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _parse_kv(path: str) -> dict:
    """简化版 KV 解析."""
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

2. 修改 engine.py 的 `_phase_a()`:

```python
def _phase_a(error_text, index_entries, min_score=2, top_n=5):
    from kb_index import search as fts_search
    graph_dir = _get_graph_dir()
    try:
        fts_results = fts_search(error_text, graph_dir, top_n=top_n)
    except Exception:
        fts_results = []  # FTS5 不可用时回退

    if fts_results:
        candidates = []
        for r in fts_results:
            entry = _find_entry_by_id(index_entries, r["id"])
            if entry:
                candidates.append(_Candidate(entry, abs(r["score"]) * 2))
        return candidates[:top_n]

    # 回退: 原子串匹配逻辑
    return _phase_a_legacy(error_text, index_entries, min_score, top_n)
```

3. 保留原 `_phase_a` 为 `_phase_a_legacy` 作为回退

**注意事项**:
- kb_index.db 加入 .gitignore
- FTS5 验证: `python3 -c "import sqlite3; c=sqlite3.connect(':memory:'); c.execute('CREATE VIRTUAL TABLE t USING fts5(x)'); print('FTS5 OK')"`
- 如果 OHOS 真机的 Python 没有 FTS5, 自动回退到 `_phase_a_legacy`

---

### 方案 C: 激活关系网络遍历 (解决 P2, 借鉴 deadends.dev)

**改造范围**: engine.py 新增 `_phase_b_plus()` 步骤

1. 在 Phase B 选出最佳匹配后, 新增关系扩展:

```python
def _phase_b_plus(best_id, candidates, gdir, index_entries):
    """Phase B+: 关系网络扩展.

    沿 best_id 的 similar_to / caused_by 边扩展候选列表.
    参考 deadends.dev 的级联预测设计.
    """
    best_kv = parse_kv_file(os.path.join(gdir, best_id + ".kv"))

    relation_ids = set()
    for rel_field in ("similar_to", "caused_by"):
        raw = best_kv.get(rel_field, "").strip()
        if raw:
            for rid in re.findall(r'E\d+', raw):
                relation_ids.add(rid)

    existing_ids = {c.entry.id for c in candidates}
    for rid in relation_ids:
        if rid not in existing_ids:
            entry = _find_entry_by_id(index_entries, rid)
            if entry:
                candidates.append(_Candidate(entry, score=1))

    return candidates
```

2. 在 `run_engine()` 中调用:

```python
# Phase B 之后, Phase C 之前:
candidates = _phase_b_plus(match_id, candidates, gdir, index_entries)
```

3. 输出中增加关系信息:

```python
# format_inline() 中增加:
if entry.relations:
    lines.append("  [关联] " + ", ".join(entry.relations))
```

**验证方法**:

```bash
# E001 (编译器缺失) 的 caused_by 包含 E007 (config.guess)
python3 scripts/ohc-run.py engine "cc: not found"
# 输出应包含: [关联] E007 (config.guess 不识别 OHOS)
```

---

### 方案 D: 质量度量 (解决 P3, 借鉴 deadends.dev)

**改造范围**: 新增 `scripts/ohc/kb_metrics.py` + 修改 .kv 模板

1. 在 .kv / .yaml 模板中新增质量字段:

```yaml
# 条目质量度量 (借鉴 deadends.dev)
metrics:
  success_count: 0        # 该修复方案成功次数
  fail_count: 0           # 该修复方案失败次数
  confidence: 0.0         # 置信度 = success / (success + fail)
  last_used: ""           # 最后使用时间
  freshness: "unknown"    # fresh / stale / outdated
```

2. 新增 `kb_metrics.py` 记录和查询:

```python
"""知识图谱质量度量。

每次修复方案执行后记录结果 (成功/失败),
用于计算 confidence 并淘汰低质量条目。
"""


def record_result(graph_dir: str, entry_id: str, success: bool):
    """记录一次修复尝试的结果."""
    kv_path = os.path.join(graph_dir, entry_id + ".kv")
    data = _parse_kv(kv_path)

    success_count = int(data.get("metrics_success_count", "0"))
    fail_count = int(data.get("metrics_fail_count", "0"))

    if success:
        success_count += 1
    else:
        fail_count += 1

    total = success_count + fail_count
    confidence = success_count / total if total > 0 else 0.0

    _kv_set(kv_path, "metrics_success_count", str(success_count))
    _kv_set(kv_path, "metrics_fail_count", str(fail_count))
    _kv_set(kv_path, "metrics_confidence", f"{confidence:.2f}")


def get_low_confidence_entries(graph_dir: str, threshold: float = 0.3) -> list:
    """获取置信度低于阈值的条目 (候选淘汰列表)."""
    low = []
    for f in os.listdir(graph_dir):
        if not re.match(r'^E\d+\.kv$', f):
            continue
        data = _parse_kv(os.path.join(graph_dir, f))
        confidence = float(data.get("metrics_confidence", "0"))
        total = int(data.get("metrics_success_count", "0")) + int(data.get("metrics_fail_count", "0"))
        # 只看有实际使用记录的条目
        if total >= 3 and confidence < threshold:
            low.append({"id": data["id"], "confidence": confidence, "total": total})
    return low
```

3. 在 driver.py 修复成功/失败时调用 `record_result()`:

```python
# driver.py 中, 修复方案执行后:
if repair_succeeded:
    record_result(graph_dir, match_id, success=True)
else:
    record_result(graph_dir, match_id, success=False)
```

**验证方法**:

```bash
# 查看低置信度条目
python3 scripts/ohc-run.py graph low-confidence --threshold 0.3
# 输出示例: E045 confidence=0.20 (1 success, 4 fail)
```

---

### 方案 E: KV -> YAML 格式迁移 (解决 P4)

**原则**: 渐进迁移, 新增用 YAML, 旧 KV 保持兼容。

1. 在 engine.py 和 graph.py 中新增统一读取函数:

```python
def parse_kb_file(path: str) -> dict:
    """读取知识条目, 自动识别 .yaml 和 .kv 格式."""
    yaml_path = path.rsplit(".", 1)[0] + ".yaml"
    if os.path.exists(yaml_path):
        try:
            import yaml
            with open(yaml_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            pass
    return _parse_kv_file(path)
```

2. 新增条目默认生成 .yaml 格式, 模板 `_template.yaml`:

```yaml
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

causes: []
caused_by: []
similar_to: []
conflicts_with: []
prerequisite_of: []

principles: []
doc_file: ""
```

3. 旧 .kv 不强制迁移, `parse_kb_file()` 自动兼容两种格式

4. 提供迁移工具 `scripts/migrate_kv_to_yaml.py` 批量转换 (保留 .kv 备份)

**注意事项**:
- PyYAML 不是 Python 标准库, 验证 OHOS 真机可用性
- 如果环境无 PyYAML, 保留 KV 回退
- pre-scan-rules.yaml 已是 YAML, 说明环境中 PyYAML 可能已可用

---

### 方案 F: 条目溯源 (P6, 低优先级)

**改造范围**: graph.py 的 cmd_add 和 cmd_update

1. 模板中新增溯源字段:

```yaml
source:
  pr_number: null        # 添加该条目的 PR 编号
  commit_sha: ""         # 添加时的 commit SHA
  author: ""             # 添加者
  created_at: ""         # 创建时间 (ISO 8601)
  last_updated: ""       # 最后更新时间
  change_log:            # 变更历史
    - {date: "", author: "", change: "初始创建"}
```

2. `cmd_validate --coverage` 输出溯源覆盖率报告

---

### 方案 G: 标准化 API (P5, 未来方向)

**注意**: 此方案为未来 AI 工具集成做准备, 当前不阻塞。

**参考**: deadends.dev 提供 REST API + MCP Server (8 个工具)

1. REST API (基于 Python http.server, 无额外依赖):

```
GET /api/v1/match?q=<error_text>     -> 匹配错误
GET /api/v1/entry/<id>               -> 获取条目详情
GET /api/v1/stats                    -> 知识库统计
```

2. MCP Server (如果未来需要 AI 工具集成):

```python
# 参考 deadends.dev 的 8 个 MCP 工具:
# - search_errors: 搜索错误
# - get_entry: 获取条目
# - get_dead_ends: 获取已知失败方案
# - get_relations: 获取关系网络
# - record_result: 记录修复结果
# - get_stats: 获取统计
# - get_principles: 获取原则库
# - get_low_confidence: 获取低置信度条目
```

**注意**: 此方案需要 OHOS 环境支持 HTTP 服务, 优先级最低。

---

## 四、实施计划

### 4.1 优先级排序 (V2 调整后)

| 优先级 | 方案 | 来源 | 改造文件 | 预计代码量 | 风险 |
|---|---|---|---|---|---|
| **P0** | 方案 A: 错误签名归一化 | FixHive | 改 engine.py + 新增归一化逻辑 | ~80 行新 | 低 |
| **P0** | 方案 B: BM25 排序 | 通用 | 新增 kb_index.py + 改 engine.py | ~150 行新 + ~30 行改 | 低 (有回退) |
| **P0** | 方案 C: 关系网络 | deadends.dev | 改 engine.py + format 输出 | ~50 行新 | 低 |
| **P1** | 方案 D: 质量度量 | deadends.dev | 新增 kb_metrics.py + 改 driver.py | ~100 行新 | 低 |
| **P1** | 方案 E: YAML 迁移 | 通用 | 新增 parse_kb_file + 迁移工具 | ~100 行新 | 中 (格式变更) |
| **P2** | 方案 F: 条目溯源 | deadends.dev | 改 graph.py | ~40 行改 | 低 |
| **P3** | 方案 G: REST API | deadends.dev | 新增 kb_api.py | ~200 行新 | 中 |

### 4.2 验收标准

**方案 A (签名归一化) 验收**:
1. 准备 10 组"同一类错误的不同措辞变体"样本
2. 改造前: 这些样本匹配到不同条目或不命中
3. 改造后: 归一化后匹配到同一条目 (命中数 >= 8/10)
4. 原始文本匹配不受影响 (不回退)

**方案 B (BM25) 验收**:
1. 准备 10 组"旧引擎不命中但应该命中"的错误日志样本
2. 改造后命中数 >= 8/10
3. 旧引擎命中的样本改造后仍然命中 (无回退)
4. OHOS 真机无 FTS5 时自动回退到原逻辑

**方案 C (关系网络) 验收**:
1. 匹配到 E001 时输出包含关联条目 E007
2. 匹配到 E042 时输出包含 similar_to 中的条目
3. 关联条目为空的条目不受影响

**方案 D (质量度量) 验收**:
1. 修复成功/失败后自动更新 metrics 字段
2. `graph low-confidence` 能正确列出低置信度条目
3. confidence 计算: success / (success + fail)

**方案 E (YAML 迁移) 验收**:
1. 新建条目默认生成 .yaml 格式
2. 旧 .kv 文件仍可被引擎正常读取
3. 迁移工具批量转换后, 引擎能正确读取 .yaml

### 4.3 不做什么

以下方案经评估**不推荐**, 请勿实施:

1. **不要引入 LightRAG / GraphRAG**: 依赖 LLM API, OHOS 真机无法调用, 100 条目规模过度工程化
2. **不要引入 Neo4j / 图数据库**: JVM 服务无法在真机运行, 关系规模太小 (100 条目 x 几条边)
3. **不要引入向量数据库** (FAISS / Chroma): 需要 embedding 模型, 真机无 GPU, 用 BM25 + 归一化足够
4. **不要用 pgvector** (FixHive 方案): 依赖 PostgreSQL + Supabase 云端, OHOS 真机不适用
5. **不要一次性迁移所有 KV**: 渐进迁移, 新增 YAML + 旧 KV 兼容, 避免一次性风险
6. **不要引入社区投票** (FixHive 方案): 我们是内部工具, 草稿审核机制已够用

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

### 5.2 业界对标数据

| 指标 | 我们 | deadends.dev | FixHive |
|---|---|---|---|
| 条目数 | 100 | 2339 | 社区驱动 |
| 关系边 | ~50 (未用) | 2524+ | N/A |
| 失败方案 | ~30 | 4923 | N/A |
| 修复方案 | ~100 | 5477 | 社区驱动 |
| 质量度量 | 无 | success/fail rate | 投票 |
| API | Python 函数 | REST + MCP | REST |
| 许可证 | 私有 | MIT + CC BY 4.0 | MIT |

### 5.3 引擎调用点

| 调用方 | 文件 | 行号 | 函数 |
|---|---|---|---|
| 编译驱动 | driver.py | 317 | `_run_engine()` |
| 门禁预检 | conan_verify.py | 375 | `_gate0_precheck()` |
| 门禁错误处理 | conan_verify.py | 152 | `_query_knowledge_graph()` |
| 命令行 | engine.py | 502 | `engine_cli()` |

### 5.4 _phase_a 现有逻辑 (改造基线)

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

### 5.5 关系字段定义 (待激活)

```yaml
# .kv 文件中的关系字段 (当前已定义但未被引擎使用)
causes:           [E042]         # 该错误会导致 E042
caused_by:        [E007]         # 该错误由 E007 引起
similar_to:       [E043, E080]   # 相似错误
conflicts_with:   []             # 冲突的修复方案
prerequisite_of:  []             # 该错误是其他错误的前置条件
```

### 5.6 .gitignore 新增

```
# 知识图谱自动生成的索引 (方案 B)
knowledge/graph/kb_index.db
```

### 5.7 V1 -> V2 变更记录

| 变更 | 说明 |
|---|---|
| 新增: 零章节 | 业界对标分析 (deadends.dev + FixHive) |
| 新增: 方案 A | 错误签名归一化 (借鉴 FixHive), P0 优先级 |
| 新增: 方案 D | 质量度量 (借鉴 deadends.dev), P1 优先级 |
| 新增: 方案 G | REST API / MCP Server, P3 优先级 |
| 调整: 方案排序 | BM25 从 P0 调为 P0 (与归一化并列) |
| 调整: 不做什么 | 新增禁止 pgvector 和社区投票 |
| 新增: 5.2 节 | 业界对标数据表 |
