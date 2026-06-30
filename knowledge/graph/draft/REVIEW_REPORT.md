# 知识图谱草稿审核报告

**审核日期**: 2026-06-30
**审核人**: OpenDesk (主编)
**草稿总数**: 85 → 处理后 27 (B级退回修订)

## 处理结果

| 等级 | 数量 | 操作 |
|------|------|------|
| A级 | 33 | ✅ 已提升为正式条目 (E035-E202) |
| B级 | 27 | ⚠️ 退回修订（见下方具体意见） |
| C级 | 15 | ❌ 已删除（空模板/格式错误/不可用） |
| D级 | 10 | 🔀 已合并到对应A级条目 |

正式条目: 101 → 134

---

## B级草稿修订意见（27个）

### 格式通用问题
1. **分隔符**: 统一用 `key: value`（冒号后一个空格），不用 `key=value`
2. **模板注释**: 删除 `_template.kv` 头部注释
3. **占位符**: 替换所有 `source_event: "# 触发此条目创建的编译事件(如有)"` 为实际事件
4. **rec_command**: 必须是可执行 shell 命令，不能是描述性文字
5. **标准字段**: 必须包含 id, trigger_tool, phase, error_signature, severity, category, match_keywords, title, root_cause, affected_scope, verification_cmd, rec_priority, rec_description, rec_command, draft, contributor_id

### 逐条修订意见

| # | 文件 | 问题 | 修订要求 |
|---|------|------|----------|
| 1 | E007-draft-AE5A | 结构混乱，部分行缺key前缀 | 重写为标准格式，确保每行有key: |
| 2 | E068-draft-6A43 | 模板注释残留，source_event占位符 | 删注释，填实际事件 |
| 3 | E079-draft-9A6D | 模板注释残留，fallback/forbid全空，source_event占位符 | 删注释，填source_event，删空字段或填充 |
| 4 | E080-draft-libdatachannel | YAML式solution_steps，缺rec_command，contributor非标准 | 改为.kv格式，补rec_command |
| 5 | E081-draft-137C | rec_command含\n转义 | 改为单行命令或用\|块格式 |
| 6 | E081-draft-64A4 | YAML式格式，缺id字段，notes过长 | 改为标准.kv格式，补id |
| 7 | E081-draft-8726 | 混合格式，trigger_tools应为trigger_tool | 修正key名 |
| 8 | E081-draft-B018 | 模板注释残留，source_event占位符，fallback/forbid空 | 删注释，填字段 |
| 9 | E081-draft-C21A | rec_command是代码片段非命令 | 改为可执行命令或标记rec_auto_fix=false |
| 10 | E091-draft-D1C5 | 模板注释残留 | 删注释 |
| 11 | E093-draft-EC85 | 模板注释残留 | 删注释 |
| 12 | E100-draft-45C7 | 模板注释残留，error_signature双重转义 | 删注释，改\\\\为\\ |
| 13 | E100-draft-94BC | severity=4(非标准)，rec_command含表情，principles非标准 | severity改0-3，删表情，改principles格式 |
| 14 | E103-draft-0756 | 非标准key名(forbidden_practice等) | 改为forbid_N_pattern等标准名 |
| 15 | E103-draft-07AC | 模板注释残留，rec_command是代码注释，source_event占位符 | 删注释，改rec_command，填source_event |
| 16 | E105-draft-E573 | 非标准key名(solution_steps等) | 改为标准key名 |
| 17 | E110-draft-00D1 | 模板注释残留，底部冗余非标准key | 删注释和冗余key |
| 18 | E110-draft-9ADA | 缺id/trigger_tool/phase等字段，无contributor_id | 补全标准字段 |
| 19 | E112-draft-4C16 | 模板注释残留，rec_command用YAML块，source_event占位符 | 删注释，改rec_command，填source_event |
| 20 | E112-draft-9683 | INI式[E112]格式，非标准key名 | 改为标准.kv格式 |
| 21 | E112-draft-F0C2 | 模板注释残留，rec_command是echo到notes.md，source_event占位符 | 改rec_command为实际修复命令，填source_event |
| 22 | E113-draft-A53B | 等号格式，缺标准字段 | 改冒号格式，补字段 |
| 23 | E113-draft-AE00 | 非标准key名(solution_steps等)，无contributor_id | 改标准key名，补contributor_id |
| 24 | E113-draft-E0C1 | INI式格式，非标准key名 | 改标准.kv格式 |
| 25 | E115-draft-12CD | rec_command为空 | 填写可执行命令 |
| 26 | E999-draft-BC38 | trigger_tools应为trigger_tool，无contributor_id | 修正key名，补contributor_id |
| 27 | E999-draft-BD24 | 缺id/trigger_tool/phase等标准字段 | 补全标准字段 |

---

## 修订完成后
将修订后的B级草稿重新提交审核，通过后提升为正式条目。
