# Knowledge Drafts

本目录存放由 `conan-verify` 自动生成的知识草稿。

## 生成时机

当 `conan create` 失败且知识图谱引擎（`engine.py`）未匹配到任何 E-entry 时，
`conan_verify.py` 的 `_create_draft_entry()` 方法自动生成 `DRAFT-NNN.kv` 文件。

## 草稿内容

每个草稿包含：
- **错误摘录** — conan create 日志中与 error/fail/denied 相关的行（前 1000 字符）
- **自动提取的关键词** — 从错误文本中提取的候选关键词
- **TODO 字段** — `root_cause`、`rec_approach`、`rec_command` 等待人工/AI 填写
- **元数据** — 时间戳、软件名、版本号、门禁名称、完整日志路径

## 提升流程

```
DRAFT-001.kv (草稿)
  ↓ 1. 审查错误摘录，理解根因
  ↓ 2. 填写 TODO 字段（root_cause, rec_approach, rec_command 等）
  ↓ 3. 重命名为 E0XX.kv（下一个可用编号）
  ↓ 4. 移动到 knowledge/graph/E0XX.kv
  ↓ 5. 在 knowledge/graph/index.tsv 添加一行
  ↓ 6. （可选）在 knowledge/doc/E0XX.md 编写人类可读文档
E0XX.kv (正式条目)
```

## 与 R17/R30/R31 的关系

| 铁律 | 描述 | 与草稿的关系 |
|------|------|-------------|
| R17 | 知识先草稿 | 手动新增知识也用 `graph add --draft` |
| R30 | conan-verify 必须查询知识图谱 | 查询失败才生成草稿 |
| R31 | 未命中必须生成草稿 | 本目录草稿的生成规则 |
