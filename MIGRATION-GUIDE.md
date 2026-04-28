# 归档迁移手册 — 旧结构 → ARCHIVE-SPEC v2.0

> 版本: 1.0 | 日期: 2026-04-28 | 适用对象: 协作者（人或 AI）
> 配套规范: `knowledge/ARCHIVE-SPEC.md`（v2.0）

## 1. 概述

### 为什么要迁移

旧归档结构存在以下问题，导致维护困难、职责不清：

1. **冗余文件泛滥** — `_meta.yaml` 与 `manifest.yaml` 元数据分散在两个文件中，信息重复且易不一致
2. **职责混淆** — 版本级 `README.md` 与软件级 `README.md` 职责重叠，难以区分"软件描述"和"版本编译记录"
3. **命名不直观** — `PROGRESS.md` 暗示"进行中"，但实际包含适配笔记，应称为 `notes.md`
4. **过时产物残留** — 大量 `.handoff.json`、`.verify-passed`、`.packaged` 等编译流程内部状态文件散落在归档目录中
5. **安装脚本重复** — 每个软件都有 `install.sh`，但 `cmd-pkgs` 仓库已有统一的公共安装脚本
6. **临时产物未清理** — `packaging/pkg-*/` 解压目录、`debug-symbols/`、`patches/.patch-backup-*/` 占用大量空间

ARCHIVE-SPEC v2.0 通过**最小文件集 + 唯一真相源**原则，将每个软件/版本归档精简为 2 个核心文件（`manifest.yaml` + `README.md` 或 `notes.md`），消除冗余、明确职责。

### 新旧结构对比

| 维度 | 旧结构 | 新结构 (v2.0) |
|------|--------|---------------|
| 软件级元数据 | `RELEASENOTE.md` + `_index.yaml` | 单一 `manifest.yaml`（含版本索引） |
| 软件级描述 | `README.md`（可能与版本级 README 混淆） | `README.md`（职责明确：是什么、依赖、OHOS 适配） |
| 版本级元数据 | `manifest.yaml` + `_meta.yaml` | 单一 `manifest.yaml` |
| 版本级笔记 | `PROGRESS.md` + `README.md` | 单一 `notes.md` |
| 安装脚本 | `{sw}/install.sh` + `{ver}/packaging/install-*.sh` | 无（由 cmd-pkgs 公共脚本替代） |
| 编译状态文件 | `.handoff.json`, `.knowledge-done`, `.verify-passed` 等 10+ 个 | 无（由 `.gitignore` 管理） |
| 打包临时产物 | `pkg-{name}-{ver}/`, `debug-symbols/` | 不保留（由 `.gitignore` 管理） |

---

## 2. 旧→新文件映射

### 2.1 软件级文件（`archives/{letter}/{name}/`）

| 旧文件 | 处理 | 说明 |
|--------|------|------|
| `RELEASENOTE.md` | **删除** | 版本信息合并到 `manifest.yaml` 的 `versions` 索引 |
| `install.sh` | **删除** | 由 cmd-pkgs 公共安装脚本替代 |
| `_index.yaml` | **删除** | 索引信息归入 `manifest.yaml` |
| `README.md` | **保留并审查** | 需确保内容符合新规范（简介、OHOS 适配、依赖、参考） |

### 2.2 版本级文件（`archives/{letter}/{name}/{version}/`）

| 旧文件 | 处理 | 说明 |
|--------|------|------|
| `_meta.yaml` | **删除** | 元数据合并到版本级 `manifest.yaml` |
| `PROGRESS.md` | **重命名为 `notes.md`** | 内容格式需手动调整（见第 5 节） |
| `README.md` | **删除，有价值内容合并到 `notes.md`** | 版本级不再有独立的 README |
| `packaging/install-*.sh` | **删除** | 同 install.sh 理由 |
| `packaging/pkg-*/` | **删除** | 解压临时产物 |
| `packaging/debug-symbols/` | **删除** | 临时产物 |
| `packaging/.packaged` | **删除** | 由 `.gitignore` 管理 |
| `.handoff.json` | **删除** | 编译流程内部状态 |
| `.knowledge-done` | **删除** | 同上 |
| `.verify-passed` | **删除** | 同上 |
| `.g0-verified` | **删除** | 同上 |
| `.staging-verified` | **删除** | 同上 |
| `.g0-passed` | **删除** | 同上 |
| `.verify-passed-partial` | **删除** | 同上 |
| `.patch-staging` | **删除** | 同上 |
| `patches/.patch-backup-*/` | **删除** | 临时备份 |

### 2.3 保留不变的文件

| 文件 | 说明 |
|------|------|
| `{sw}/manifest.yaml` | 软件级元数据（如不存在需创建） |
| `{ver}/manifest.yaml` | 版本级元数据（保留，需审查字段） |
| `{ver}/patches/*.patch` | 实际应用的补丁文件 |
| `{ver}/packaging/*.tar.gz` | 打包产物（预编译二进制） |
| `{ver}/reports/*.md` | 构建报告（有价值的保留） |

---

## 3. 新文件创建规则

### 3.1 软件级 `manifest.yaml`

如软件级 `manifest.yaml` 不存在，需要创建。字段规范引用自 `ARCHIVE-SPEC.md` §4.1。

```yaml
software: {name}              # 必须，小写，与目录名一致
display: "{显示名}"            # 必须
description: "{一句话描述}"     # 必须
category: build-tool           # 必须，见 ARCHIVE-SPEC 分类列表
homepage: "https://..."        # 推荐
license: {SPDX}                # 推荐
build_system: cmake            # 推荐

ohos_adaptation:               # 推荐
  key_points: []
  common_dependencies: []

versions:                      # 必须，从 RELEASENOTE.md 或版本目录列表构建
  "{version}":
    status: published          # published | built | failed | archived
    build_date: "YYYY-MM-DD"
```

### 3.2 版本级 `manifest.yaml`

保留已有的版本级 `manifest.yaml`，检查字段完整性。缺失字段参考 `ARCHIVE-SPEC.md` §4.2 补充。

关键字段检查清单：
- `version` — 必须有
- `status` — 必须有（published / built / failed / archived）
- `build_date` — 必须有
- `source.url` — 推荐有
- `build.system` — 推荐有

### 3.3 `notes.md`

由旧 `PROGRESS.md` 重命名而来。内容需要按 `ARCHIVE-SPEC.md` §2.3 的模板调整格式。

模板骨架：
```markdown
# {软件名} {版本} 适配笔记

## 编译环境
- 构建系统: cmake / autotools / makefile / meson / custom
- 编译日期: YYYY-MM-DD
- 编译器: clang / clang++
- 状态: published / built / failed

## 编译步骤
（用文字描述实际做了什么，而非空 checkbox）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|

## 源码修改（按需）
## 依赖版本（推荐）
## 验证结果（按需）
## 交付物（按需）
## 注意事项（按需）
```

### 3.4 软件级 `README.md`

如缺失则需创建。内容参考 `ARCHIVE-SPEC.md` §2.1 的章节建议。

---

## 4. 迁移步骤（逐软件）

以下是可直接复制执行的 shell 命令序列。对每个软件执行一次：

```bash
# ══════════════════════════════════════════════════
# 迁移脚本 — 单个软件
# 用法: cd 到项目根目录，然后执行本脚本
# 变量: LETTER=软件首字母 NAME=软件名
# ══════════════════════════════════════════════════

SW_DIR="archives/${LETTER}/${NAME}"

# ── 1. 进入软件目录 ──
cd "${SW_DIR}" || exit 1

# ── 2. 处理软件级文件 ──

# 2a. 删除 RELEASENOTE.md
rm -f RELEASENOTE.md

# 2b. 删除 install.sh
rm -f install.sh

# 2c. 删除 _index.yaml
rm -f _index.yaml

# 2d. 创建软件级 manifest.yaml（如不存在）
# ⚠️ 需要手动填写字段，参考第 3.1 节或 templates/manifest-software.yaml
if [ ! -f manifest.yaml ]; then
    echo "⚠️ 需要创建 ${SW_DIR}/manifest.yaml — 请参考 templates/manifest-software.yaml"
fi

# 2e. 确保 README.md 存在（如缺失则需创建）
if [ ! -f README.md ]; then
    echo "⚠️ 需要创建 ${SW_DIR}/README.md — 请参考 ARCHIVE-SPEC.md §2.1"
fi

# ── 3. 处理每个版本目录 ──

for ver in */; do
    # 跳过非版本目录（如文件）
    [ -d "$ver" ] || continue
    
    echo "  处理版本: ${ver%/}"

    # 3a. 删除 _meta.yaml
    rm -f "${ver}_meta.yaml"

    # 3b. 删除版本级 README.md
    # ⚠️ 先检查是否有有价值内容需合并到 notes.md
    if [ -f "${ver}README.md" ]; then
        echo "    ⚠️ ${ver}README.md 存在，请先检查内容再删除"
        # 确认无价值内容后再删除：
        # rm -f "${ver}README.md"
    fi

    # 3c. 重命名 PROGRESS.md → notes.md
    if [ -f "${ver}PROGRESS.md" ]; then
        if [ -f "${ver}notes.md" ]; then
            echo "    ⚠️ ${ver}notes.md 已存在，跳过重命名（请手动合并 PROGRESS.md 内容）"
            rm -f "${ver}PROGRESS.md"
        else
            mv "${ver}PROGRESS.md" "${ver}notes.md"
            echo "    ✅ ${ver}PROGRESS.md → ${ver}notes.md"
        fi
    fi

    # 3d. 清理 packaging 临时产物
    rm -rf "${ver}packaging/pkg-"*/
    rm -rf "${ver}packaging/debug-symbols/"
    rm -f "${ver}packaging/install-"*.sh
    rm -f "${ver}packaging/.packaged"

    # 3e. 删除编译流程内部状态文件（点文件）
    rm -f "${ver}.handoff.json"
    rm -f "${ver}.knowledge-done"
    rm -f "${ver}.verify-passed"
    rm -f "${ver}.g0-verified"
    rm -f "${ver}.g0-passed"
    rm -f "${ver}.verify-passed-partial"
    rm -f "${ver}.patch-staging"
    rm -f "${ver}.staging-verified"

    # 3f. 清理 patches 临时文件
    rm -rf "${ver}patches/.patch-backup-"*/

    # 3g. 删除其他临时文件
    rm -f "${ver}TASK_CARD.md"
    rm -f "${ver}EXCLUDE_LIST"
    rm -f "${ver}DIAGNOSIS_"*
    rm -f "${ver}MISSING_"*
    rm -f "${ver}WORKFLOW_"*
    rm -f "${ver}WORKPLAN_"*
    rm -f "${ver}SCAN_"*

    echo "    ✅ 版本 ${ver%/} 清理完成"
done

echo "✅ 软件 ${NAME} 迁移完成"
```

### 批量迁移（按字母）

```bash
# 对某个字母下的所有软件执行迁移
for sw_dir in archives/{letter}/*/; do
    NAME=$(basename "$sw_dir")
    LETTER=$(basename "$(dirname "$sw_dir")")
    echo "═══ 迁移: ${NAME} ═══"
    # ... 执行上面的单软件迁移脚本 ...
done
```

---

## 5. notes.md 内容迁移指南

### 5.1 信息来源

`notes.md` 的内容来自两个旧文件：

1. **`PROGRESS.md`** — 主要来源，包含编译步骤记录、问题与解决方案、知识积累
2. **版本级 `README.md`** — 可能包含编译配置说明、验证命令、已知问题

### 5.2 迁移方法

#### 从 PROGRESS.md 提取

| PROGRESS.md 内容 | → notes.md 对应章节 |
|------------------|---------------------|
| 日期、状态信息 | 编译环境 |
| 步骤记录（Step 1-13） | 编译步骤（精简为文字描述） |
| 错误与修复记录 | 遇到的问题与解决方案 |
| 补丁说明 | 源码修改 |
| "发现与知识"章节 | 依赖版本 / 注意事项 |
| 验证结果 | 验证结果 |

#### 从版本级 README.md 提取

| README.md 内容 | → notes.md 对应章节 |
|----------------|---------------------|
| 编译配置说明 | 编译步骤 |
| 验证命令 | 验证结果 |
| 已知限制 | 注意事项 |
| 依赖列表 | 依赖版本 |

### 5.3 内容转换示例

**旧格式（PROGRESS.md 片段）：**
```markdown
| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 3 configure | ✅ | cmake -DCMAKE_BUILD_TYPE=Release .. |
| Step 4 make | ❌ | undefined reference to foo |
| Step 4 make | ✅ | 添加 -DFOO=ON 后重试成功 |
```

**新格式（notes.md）：**
```markdown
## 编译步骤
使用 cmake 构建，配置参数: `-DCMAKE_BUILD_TYPE=Release -DFOO=ON`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | undefined reference to foo | 默认未启用 FOO 模块 | 添加 -DFOO=ON |
```

### 5.4 注意事项

- 旧 PROGRESS.md 中的空 checkbox（`⏳`）和未完成记录可直接删除
- 编译流程内部状态的自动生成内容（如 HANDOFF 块、CHECKPOINT 块）不需要迁移
- 保留有实际技术价值的记录（错误信息、修复方案、依赖版本）

---

## 6. manifest.yaml 迁移指南

### 6.1 版本级 manifest.yaml

#### 从旧 `_meta.yaml` 提取字段

如果版本目录存在 `_meta.yaml`，将其中的字段合并到 `manifest.yaml`：

```bash
# 查看 _meta.yaml 中的内容
cat "${ver}_meta.yaml"
# 将有价值的字段手动补充到 manifest.yaml
```

常见 `_meta.yaml` 字段映射：

| _meta.yaml 字段 | manifest.yaml 对应位置 |
|-----------------|----------------------|
| `status` | `status`（直接映射，见状态映射表） |
| `build_date` | `build_date` |
| `configure_options` | `build.configure_options` |
| `dependencies` | `build.dependencies` |
| `patches` | `patches_applied` |

#### 状态值映射

旧状态值需要映射到新规范：

| 旧状态 | 新状态 | 说明 |
|--------|--------|------|
| `success` | `published` | 已编译并发布 |
| `partial` | `built` | 编译成功但未完整发布 |
| `compiling` | `built` | 编译中/已编译 |
| `failed` | `failed` | 编译失败 |
| `archived` | `archived` | 旧版本归档 |

### 6.2 软件级 manifest.yaml

#### 从 RELEASENOTE.md 构建版本索引

如果软件目录存在 `RELEASENOTE.md`，从中提取版本列表，构建 `manifest.yaml` 的 `versions` 段：

```yaml
versions:
  "3.30.0":
    status: published
    build_date: "2026-04-15"
  "3.28.3":
    status: archived
    build_date: "2026-03-20"
```

#### 从版本目录列表构建索引

如果没有 `RELEASENOTE.md`，直接扫描版本目录：

```bash
# 列出所有版本目录
ls -d */
# 对每个版本，读取其 manifest.yaml 获取 status 和 build_date
for ver in */; do
    status=$(grep '^status:' "${ver}manifest.yaml" 2>/dev/null | head -1 | awk '{print $2}')
    date=$(grep '^build_date:' "${ver}manifest.yaml" 2>/dev/null | head -1 | awk '{print $2}')
    echo "  \"${ver%/}\": status=${status:-unknown} date=${date:-unknown}"
done
```

---

## 7. 验证

迁移完成后，对每个软件运行以下验证命令：

### 7.1 文件存在性检查

```bash
SW_DIR="archives/${LETTER}/${NAME}"

# 软件级必须文件
for f in manifest.yaml README.md; do
    if [ -f "${SW_DIR}/${f}" ]; then
        echo "  ✅ ${f}"
    else
        echo "  ❌ ${f} 缺失"
    fi
done

# 版本级必须文件
for ver in "${SW_DIR}"/*/; do
    [ -d "$ver" ] || continue
    VNAME=$(basename "$ver")
    for f in manifest.yaml notes.md; do
        if [ -f "${ver}${f}" ]; then
            echo "  ✅ ${VNAME}/${f}"
        else
            echo "  ❌ ${VNAME}/${f} 缺失"
        fi
    done
done
```

### 7.2 禁止文件检查（不应存在）

```bash
SW_DIR="archives/${LETTER}/${NAME}"

# 检查已删除的文件是否真的被删除
for pat in "RELEASENOTE.md" "install.sh" "_index.yaml"; do
    if [ -f "${SW_DIR}/${pat}" ]; then
        echo "  ⚠️ 软件级 ${pat} 仍存在"
    fi
done

for ver in "${SW_DIR}"/*/; do
    [ -d "$ver" ] || continue
    VNAME=$(basename "$ver")
    for pat in "_meta.yaml" "PROGRESS.md" "README.md"; do
        if [ -f "${ver}${pat}" ]; then
            echo "  ⚠️ ${VNAME}/${pat} 仍存在"
        fi
    done
    for dot in ".handoff.json" ".knowledge-done" ".verify-passed" ".g0-verified" \
               ".g0-passed" ".verify-passed-partial" ".patch-staging" ".staging-verified"; do
        if [ -f "${ver}${dot}" ]; then
            echo "  ⚠️ ${VNAME}/${dot} 仍存在"
        fi
    done
done
```

### 7.3 使用 ohc 工具验证

```bash
# finalize-archive 检查
python3 scripts/ohc-run.py finalize-archive ${NAME} ${VERSION}

# verify-build 检查
python3 scripts/ohc-run.py verify-build ${NAME} ${VERSION}

# 提交自检
python3 scripts/ohc-run.py submit --check ${NAME} ${VERSION}
```

### 7.4 全量扫描

```bash
# 扫描所有软件，统计迁移状态
find archives/ -name "PROGRESS.md" -o -name "_meta.yaml" -o -name "RELEASENOTE.md" | head -50
find archives/ -name ".handoff.json" -o -name ".verify-passed" -o -name ".knowledge-done" | head -50

# 应返回空结果（或仅有少量未迁移的软件）
```

---

## 附录 A：快速参考卡片

```
迁移一句话总结:
  删 RELEASENOTE.md / _meta.yaml / PROGRESS.md(→notes.md) / README.md(版本级)
  删 install.sh / packaging/install-*.sh / pkg-*/ / debug-symbols/
  删所有点文件 (.handoff.json, .verify-passed, .knowledge-done, ...)
  删 patches/.patch-backup-*/
  创建/完善 软件级 manifest.yaml (含 versions 索引)
  确保 软件级 README.md 存在
```

## 附录 B：文件数量对比

| 项目 | 旧结构（典型版本） | 新结构（v2.0） |
|------|-------------------|----------------|
| 软件级文件数 | 4-5 个 | 2 个 (manifest.yaml + README.md) |
| 版本级文件数 | 8-12 个 | 1-3 个 (manifest.yaml + notes.md + 按需) |
| 点文件数 | 8-10 个 | 0 个 |
