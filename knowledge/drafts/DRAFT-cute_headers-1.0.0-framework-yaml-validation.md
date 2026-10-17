# DRAFT-cute_headers-1.0.0-framework-yaml-validation

> **路径 B 知识草稿**（成对 `.kv` ↔ `.md`，同 stem：`DRAFT-cute_headers-1.0.0-framework-yaml-validation`）
> **来源**：cute_headers 1.0.0 R05 本地闭环真实复验（task_id=`cute_headers-1.0.0-r05-local-framework-recovery-finish-revalidation-pc1-70-20260831T015655Z`）
> **严重度**：⚠️ 中（不影响 cute_headers 库本身，但阻塞共享验证框架的后处理步骤）
> **分类**：framework / yaml / parser / validation

---

## 问题 (problem)

共享验证框架存在两类 YAML 解析缺陷，在 cute_headers 1.0.0 本地闭环中阻塞了 finish 的后处理步骤（W5 知识图谱完整性检查、Step8 生成 SUMMARY.md），但这两处缺陷都不属于 cute_headers 库自身的构建/配方/平台问题：

1. **W5 必填字段判空误报（YAML 块标量）**：`scripts/ohc/workflow_checks.py` 的 `check_knowledge_completeness` 用
   `re.match(r"^(\w+):\s*(.*)")` 逐行提取 `.kv` 必填字段，遇到合法 YAML **块标量声明**
   `root_cause: |` 或 `rec_approach: >` 时只取到标记值 `"|"` / `">"`，原有判空条件
   `val == "|"` 命中，于是把字段内容完整的知识条目（如 E219/E253/E305）误判为字段为空。
2. **summary.py 先标量后列表键崩溃**：`_parse_yaml_simple` 遇到"先标量后列表"的键时崩溃。例如
   `archives/q/qpdf/12.3.2/manifest.yaml` 中 `knowledge_gained: []` 先被存为字符串 `"[]"`，随后
   `knowledge_gained:` 后跟缩进的 `- item` 列表项，`data.setdefault(current_list_key, []).append(item)`
   对已存在的字符串调用 `.append` → `AttributeError: 'str' object has no attribute 'append'`，
   导致 Step8 `gen_summary` 整体失败。

## error_signature

```
AttributeError: 'str' object has no attribute 'append'       # summary.py _parse_yaml_simple
root_cause 为空 / rec_approach 为空 / 必填字段判空            # W5 块标量误报
```

## 根因 (root_cause)

- **W5 判空**：正则提取器不识别 YAML 块标量（`|` / `>`）语义，把"声明符"当作"空值"。
- **summary.py**：`setdefault(current_list_key, [])` 假设该键始终是列表；当同一键先出现标量（如 `"[]"`）再出现列表时类型冲突，`append` 在字符串上崩溃。

## 最小临时方案 (solution / rec_approach)

仅限当前 worktree 本地复验，已完成并**完全恢复**：

1. `workflow_checks.py`：必填字段判空
   `if not val or val.startswith("TODO") or val == "|":` → `if not val or val.startswith("TODO"):`
   （把 `"|"` / `">"` 视为合法块标量声明，而非空值）
2. `summary.py`：列表项追加前做类型兜底——若 `current_list_key` 当前值非 list，先置空列表再 append。

复验完成后通过 `git checkout HEAD -- <file>` 完全恢复；所有框架文件
（E219.kv / E253.kv / E305.kv / summary.py / workflow_checks.py / SUMMARY.md）
SHA-256 与修复前基线逐一一致，git 状态全 clean。

## 真实验证证据 (verification_evidence)

- **最小复现**：
  - qpdf manifest：`_parse_yaml_simple('archives/q/qpdf/12.3.2/manifest.yaml')` 修复前 `AttributeError 'str' has no 'append'`；修复后 OK（`requires` 2 项 / `knowledge_gained` 4 项）
  - E219/E253/E305：W5 必填字段判空，修复前 `root_cause`/`rec_approach` 判空误报；修复后全部通过
- **finish 完整复验**（修复 + W3 基线豁免并存）：
  - W3 本地 CI：prdiff 13 文件，JC_RESULT=pass，Pass rate 100%
  - W5 知识图谱完整性：通过
  - Step8 gen_summary：SUMMARY.md 生成完成
  - W2 原子性：通过（无变更文件）
  - Step10 submit 就绪：就绪
  - finish 自然终态 exit=0；`.ci-result.json` 生成（`exit_code=0, step=W3_local_ci`）

## 适用边界 (applicable_scope)

- 适用于**所有依赖 W5 判空与 gen_summary 的库收尾流程**，只要其 `.kv` 使用了合法块标量、或其 manifest 存在"先标量后列表"键。
- 不适用的情形 (`not_applicable_when`)：
  - 若失败实际源于**库自身 YAML 数据错误**（非框架解析缺陷），应归因于库 manifest/.kv 数据，而非本条目；
  - 若共享框架已正式修复并发布，应关联新的正式条目编号并标记本草稿使命完成。

## 恢复/交付边界 (framework_delivery_boundary)

- **恢复边界**：两处临时修复仅用于 cute_headers 本地验证，已恢复为原始内容；框架文件不进入任何提交或 PR。
- **交付边界**：本草稿**不宣称**共享框架已正式交付修复。正式修复必须：
  - 以独立框架交付（修改 `scripts/`）进行，并经过 CI 全量复验；
  - 不得在 cute_headers PR 中携带框架修改；
  - 何时应创建独立框架交付：当该缺陷被多个库复现、修复已稳定，且需对共享验证框架做正式变更时；
  - 何时不适用：缺陷仅个别库数据问题、或框架已修复，无需重复沉淀。

## 查重与差异

- 查重范围：`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*`、`knowledge/` 全树 grep。
- 相关既有条目：
  - **E141**（manifest.yaml `configure_options` YAML 列表被 regex 解析为字面 `[]` 导致 quoting 错误）：同为"YAML 被正则误解析"，但对象是 `clean_verify.py`/manifest 字段，本次是 W5 对 `.kv` 块标量判空 + summary.py 先标量后列表崩溃，对象文件/根因/修复点不同。
  - **DRAFT E327**（restinio 0.6.19 草稿）：记录了同款 `'str' has no 'append'` 崩溃现象（gen_summary 内部 bug），但属于该库适配笔记，未提炼为共享框架通用 YAML 解析条目，也未覆盖块标量判空误报。
- 结论：无同 stem、无同主题完整条目；本次为**新增**可复用知识草稿。

## 引用

- 成对条目：`knowledge/drafts/DRAFT-cute_headers-1.0.0-framework-yaml-validation.kv`（同 stem）
- 来源证据：`.oh-executor/cute_headers-r05-finish.log`、`reports/w3-local-ci.log`、`.ci-result.json`
