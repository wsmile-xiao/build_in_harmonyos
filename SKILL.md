---
name: openharmony-compile-agent
description: 鸿蒙PC原生应用/C/C++三方库适配编译Agent。当用户需要将开源C/C++库适配到HarmonyOS PC平台（arm64）、编写conanfile.py配方、执行conan构建发布流水线、排查CI构建失败时触发。覆盖源码获取、依赖解析、Conan配方编写、交叉编译、制品仓发布全流程。
version: 12.22
---

> **每次编译任务前先读本文档。** 骨架 + 要点，详解按需从 references/ 加载。
> KNOW_YOUR_WHY.md 回答"为什么"，本文档回答"怎么做"。

⭐ **回答用户问题时保持简洁。先给命令，再给解释。不要重复 SKILL.md 的原文，直接执行。**

## §0.0 环境准备（Python + Conan）

> 前提条件。首次使用或环境缺失时按此安装。

### Python 安装

```bash
# 注意：如果已安装"Python安装器"应用，需要先卸载
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- python 3.12.9
```

### pip 源配置（新社区源，必须配置）

```bash
python3 -m ensurepip                          # 首次安装 pip
pip3 config set global.index-url https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple
pip3 config set global.trusted-host pypi.cnb.cool
```

> 鸿蒙社区 PyPI 源托管 OHOS 适配版 conan 及其他适配包，必须配置才能正确安装。

### Conan 安装

```bash
pip3 install conan                            # 从配置的社区源安装 OHOS 适配版（基线 2.29.1）
```

> 此 conan 已适配 OHOS 平台（`os=OHOS` 枚举、`aarch64-linux-ohos` triplet、`CMAKE_SYSTEM_NAME` 映射等）。
> 不要从官方 PyPI 安装，否则 `os=OHOS` 会报 `not a valid os`。

---

## §0 初始化

```bash
SKILL_ROOT="$(dirname "$(find "${ATOMCODE_HOME:-$HOME/.atomcode}" -name "SKILL.md" -path "*openharmony-compile-agent*" 2>/dev/null | head -1)")"
# 回退到 OpenDesk
[ -z "$SKILL_ROOT" ] && SKILL_ROOT="$(dirname "$(find "$HOME/.opendesk" -name "SKILL.md" -path "*openharmony-compile-agent*" 2>/dev/null | head -1)")"
```

> `ohc-run.py` 内部自动定位项目根目录（`find_project_dir()`），不需要手动 `export` 环境变量。
> **R13**: 用完整路径调用，如 `python3 $SKILL_ROOT/scripts/ohc-run.py build ...`。不要用相对路径 `./scripts/xxx`。

### §0.1 协作模式（⭐ 默认生效）

本 skill 默认以**协作者模式**运行，基于 Git + GitCode PR 协作。详见 `CONTRIBUTING.md`。| 模式 | 触发方式 | 职责 |
|------|---------|------|
| 协作者（默认） | 直接使用 | 编译软件、提取知识、生成 conanfile.py、创建分支并提交 PR |
| 主编 | `OHC_ROLE=editor` | 审核 PR、合并知识、重建索引 |

### §0.2 积分赛事 PR 模板（⭐ 积分赛专用）

使用 AtomCode 提交积分赛 PR 时，必须使用专用模板：

- **模板文件**：`templates/积分赛事PR模板.md`
- **触发条件**：提示词中包含 **"积分赛"、"依赖项"、"知识库扩展"、"高难度挑战"** 时自动启用
- **PR 标题**：提示词中包含`积分赛`必须以 `【积分赛】`为前缀，包含`依赖项`必须以 `【依赖项】`为前缀，包含`知识库扩展`必须以 `【知识库扩展】`为前缀，包含`高难度挑战`必须以 `【高难度挑战】`为前缀，且标题中仅存在一种关键词前缀
- **PR 正文**：严格按 `templates/积分赛事PR模板.md` 填写，包含：
  - 三方库信息（名称、版本、仓库地址、适配路径、使用知识库）
  - 测试用例对比（上游 vs 适配后）
  - 上游测试用例修改说明
  - 补全测试用例说明
  - 验证结果（编译状态、测试通过率）
  - 补充说明

**协作者 Git 铁律（违反=越权）**：
- ❌ 不推 main，不走捷径：创建功能分支 `git checkout -b feat/{软件名}-{版本}` → push → GitCode PR
- ❌ 不碰基础设施：`SKILL.md`/`references/`/`templates/`/`scripts/`/`ci/`/`index.tsv`/`SUMMARY.md` 只读
- ❌ 不碰他人归档目录
- ✅ 新增知识用 `ohc-run.py graph add E{N} --draft`

**Agent ID**：自动获取 4 位随机标识（如 `A7F3`），用于知识图谱草稿归属（不用于分支命名，分支名不带后缀），可通过 `OHC_AGENT_ID` 预设。

### §0.3 适配工作流规程（⭐ 强制执行）

以下 6 条规程在每次软件适配中**强制执行**，违反=流程缺陷：

**W0 — 依赖发布检查（适配前第一件事）**
开始适配任何软件前，**必须**先检查其所有依赖是否已发布到制品仓。这是适配的第一步，**在拉代码、看源码之前就要做**：
```bash
# 方法一：运行本地预检脚本（推荐）
bash ci/scripts/preflight_check.sh <软件名>/<版本>

# 方法二：手动检查（R35: 禁止用 conan list 判断，必须用 conan download）
conan download "依赖包名/版本" -r=ohpcd --only-recipe
```
检查结果决定下一步：
- **所有依赖已发布** → 正常继续适配
- **有依赖未发布** → **停止当前适配**，先适配并发布缺失的依赖（R36）
- **多层依赖链 C→B→A** → 按拓扑序从最底层 A 开始，逐层适配→发布→再回到上层

> 跳过此步=可能花数小时编译后发现依赖链断裂，浪费大量时间。先查依赖，再动手。

**W0b — 历史经验核验 + CI 能力矩阵（选型/立项阶段，PR6096 教训）**
适配对象在本仓库有历史归档（含 notes.md）时，**必须先读历史 notes.md**，并做两项核验：

1. **环境语义可迁移性**：历史成功是在什么环境取得的？设备原生工具链的成功**不可迁移**到 CI（远端 clean 环境）。实测案例：mcfly 0.9.4 历史 notes 记录"设备 rustc 1.96 原生构建成功"，但 CI 无 Rust 工具链——照搬历史结论产出必然红 CI 的 PR。核验口径：**历史命令在 CI 环境里逐字可执行吗？** 工具链不存在的，先看能否 `tool_requires` 补齐（pdfsandwich 正例：历史设备编译 OCaml → 新配方 `tool_requires ocaml/4.14.1.1.4`，CI 可绿）；补不齐 → 选型即止，`--status env_unsupported` 上报，禁止动手。
2. **历史踩坑必须比对**：历史 notes 记录的绕坑命令（如 mcfly 的 `cargo build --release --no-default-features`）是**验证过的结论**，新配方必须逐项比对遵循；偏离时 notes.md 里写明原因与验证证据。

**CI 能力矩阵（远端 clean 环境硬约束，立项前对照）**：

| 工具链 | CI 现状 | 对策 |
|---|---|---|
| Rust（cargo/rustc） | ❌ 无 | Rust 包直接 `env_unsupported`（除非先立项 rust 工具链包） |
| OCaml | ❌ 无系统级 | `tool_requires ocaml/4.14.1.1.4`（registry 已有，PR6097 正例） |
| gcc/clang/make/cmake/ninja | ✅ | 正常 |
| bash 脚本类 | ✅ | 正常 |
| 其他冷门工具链 | 先在 CI 侧实证 | 未知=先小包试跑，勿假设 |

**W1 — 同步主仓库**
每次适配新软件前，**必须**拉取主仓库 main 最新变更，以匹配最新框架要求与知识库：
```bash
git checkout main
git pull origin main
# 仓库地址：
#   https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git
#   git@gitcode.com:OpenHarmonyPCDeveloper/build_in_harmonyos.git
```
> 不同步=用过期知识库+旧框架要求工作，可能重复踩已修复的坑。

**W2 — PR 原子性 + 结构完整性（嵌入 finish，CI JC6 硬拦截）**
每个 PR **只允许提交一个软件**：只包含一个 `archives/<首字母>/<软件名>/<版本>/` 配方目录及其知识图谱草稿。一个 PR 中出现两个及以上软件目录 = **CI JC6 直接拦截（Hard Fail）**。如果对 SKILL 框架本身有修改（`scripts/`/`templates/`/`ci/`/`SKILL.md`/`references/` 等），**必须单独提交 PR**。
> 混合提交=审核困难+回滚困难。配方 PR 和框架 PR 的审核标准不同。
> 多软件适配任务=按软件逐个开分支 `feat/<软件名>-<版本>`、逐个提 PR，每次从最新 main 切出（W1）。
>
> **结构完整性由 `finish` step [5/10] 强制执行**（L0a-L0e 等效检查）：test_package/ 目录
> 存在、conanfile.py 存在、测试源文件存在、MANIFEST.yml 存在。不通过 → HANDOFF + exit 1。
> 历史教训：CI 审计发现 181 个结构缺失失败（115 缺测试源 + 66 缺 MANIFEST）。

**W3 — 本地编译验证（⭐ 嵌入 finish step [5/10]，HANDOFF 强制）**

> **不是散乱脚本，而是 finish 流程内部的阻塞步骤。** AI 跑 finish 时自动执行，
> 无法跳过。失败输出 HANDOFF 块（含根因+修复命令+resume 指令），AI 修复后 `--resume` 继续。

`finish` step [5/10] 内部执行：
1. **W2 结构检查**（L0a-L0e）：test_package/ 完整性 → 不通过 HANDOFF
2. **R36 依赖检查**：`conan download --only-recipe` 验证依赖已发布 → 未发布 HANDOFF
3. **conan create 编译验证**：实际运行 `conan create` → 失败 HANDOFF（含知识图谱匹配的根因）
4. **通过** → 自动写入 `.ci-result.json`（含 conan create 日志 SHA256 哈希，防伪造）

> **⚠️ 禁止手动创建或修改 `.ci-result.json`**。此文件由 finish step [5/9] 写入，
> 含日志哈希。`submit` 会验证此哈希与实际日志匹配。
> 历史教训：CI 审计发现 431 个编译失败流入 CI（55%），根因是 AI 跳过 conan create
> 验证或手动伪造 `.ci-result.json`。嵌入式 HANDOFF 从结构上消除此可能。
>
> **⭐ 构建超时预算（W3 与 CI 同源）**：`conan create` 默认 3600s，可按包覆盖（3600~57600s）。
> 配置文件：`ci/config/build_timeouts.txt`（精确 `name/version 秒数`）。工具化管理：
> `ohc-run.py timeout get <name> <ver>` 查询 / `timeout set <name> <ver> <秒> [--force]` 新增覆盖 /
> `timeout list` / `timeout validate`（与 CI AWK 校验同构）。本地 W3 自动读取同一配置
> （环境变量 `OHC_W3_TIMEOUT=<秒>` 可临时只调本地）。实战案例：ScaLAPACK 2.2.3 上游 100 项
> 测试实测 4451s 超默认预算，测试全过却被 conan create 超时判负 → `timeout set scalapack 2.2.3 10800`。

**W3 外部依赖阻塞止损（⭐ 硬性规则，task 3659 教训）**

W3/finish/submit 卡在**环境外部因素**时，禁止无限重试 workaround。满足任一条件**立即止损**：

- conan registry / git remote / 下载源**连续 3 次不可达，且重试跨度超过 30 分钟**
- 失败原因明确属于：registry_unreachable / 上游包未发布 / DNS·TLS 网络故障

**止损动作**：立即写 result.json 终止本包（见 Step 7），`--status dependency_missing`，`--failed-reason` 写清"缺什么 + 为什么环境内无法解决"，`--missing` 列裸包名，`--missing-evidence` 贴实际报错输出。**工具已强制（双层）**：①result 命令对每个 missing 包自动实测 `conan list <pkg>/* -r=ohpcd`，实测结果追加进 `missing_evidence`——凭推断谎报会被 `[probe] ... EXISTS (探测到配方，请复核是否真缺)` 当场戳穿；②create-pr 前置硬闸 **PF4 依赖闸**逐个探测制品仓，requires 缺失时建 PR 都建不出来——捎带适配依赖在工具层封死（goblinrs #6642 四包捎带教训）。

**止损后严禁**（为绕过依赖）：伪造 `.ci-result.json`、dummy 包顶替、跳过 W3、伪造 result.json。

**R43 调参螺旋止损（内部死循环，2026-08-20 新增）**：R41 管外部阻塞，本条管内部死循环——自研 conanfile.py 反复调参（cmake 组件名 `components`/`cmake_file_name`、目标名、include/lib 路径等）**同一错误类别连续 5 次修改仍失败** → 停止调参，写 result.json（`--status failed_build`，`--failed-reason` 附 5 次尝试的错误摘要与已排除的方向）退出。实测教训：task 3681 对 `Qt5::3DCore` 的 component/cmake_file_name/includedirs 反复推演 3.5 小时无一次阶段性上报，直到预算耗尽。触发前自查：错误信息与上次是否同类？若同类，第 5 次尝试前就该收手——5 次同方向失败基本可断定方法性错误（查 references/iron-rules.md（R41-R43 详解）或上游 conanfile 参考），继续盲试不会收敛。

**现象 → status 判定对照表**：

| 现象 | result status |
|---|---|
| conan remote 上游包不存在/未发布，本地无法构建 | `dependency_missing` |
| registry 网络不可达且非本机问题 | `dependency_missing` |
| 编译期缺系统头文件 / 工具链版本不符 | `env_unsupported` |
| conan create 编译报错（源码/配方问题） | `failed_build` |
| 换包版本/打 patch 可能修复 | 继续修复，不构成止损条件 |

判定口径：**"换个网络正常的机器能否解决"**——能 → `dependency_missing`；不能 → `env_unsupported`。

**W4 — Pre-PR 独立审计（⭐ 嵌入 submit，HANDOFF 强制）**

> **不是独立脚本，而是 submit 流程内部的前置检查。** AI 跑 submit 时自动检查 W4 是否完成，
> 未完成则 HANDOFF 拒绝 push。审计本身由独立子任务执行（上下文隔离，避免自审盲区）。

**`submit` 内部执行**：
1. 检查 finish 已完成（manifest 状态 = published/built）→ ❌ HANDOFF "先完成 finish"
2. 检查 W4 审计结果存在（`.audit-result.json`）→ ❌ HANDOFF 输出审计步骤：

```
┌── HANDOFF ──────────────────────────────────────┐
│ W4 REQUIRED: Pre-PR audit not yet completed       │
│                                                    │
│ Step 1: 生成审计输入                                │
│   python3 $SKILL_ROOT/scripts/pre_pr_audit.py generate \  │
│     --repo-dir $REPO_DIR --package <软件名> --version <版本>   │
│                                                    │
│ Step 2: 派发审计子任务 (createSubTask)              │
│   objective: templates/audit-prompt.md            │
│   输入: /tmp/audit-input-*.json                    │
│   输出: /tmp/audit-result-*.json                  │
│                                                    │
│ Step 3: 处理审计报告                                │
│   python3 $SKILL_ROOT/scripts/pre_pr_audit.py report \  │
│     --audit-result /tmp/audit-result-*.json       │
│                                                    │
│ Resume: ohc-run.py submit <软件名> <版本> --resume │
└────────────────────────────────────────────────────┘
```

3. 检查审计判定 = pass（P0/P1 清零）→ ❌ HANDOFF "修复 P0/P1 后重新审计"
4. **全部通过** → `git push` + 创建 PR

**审计规则文件**（位于仓库 `.gitcode/` 目录）：
- `code-style.md` — 代码规范性标准 (conanfile.py/shell/C++/YAML/Python)
- `review-memory.md` — PR 审查规则 (欺骗检测/配方质量/文件规范/PR合规)

**审计判定**：P0/P1 → ❌ 必须修复 | P2/P3 → ⚠️ 警告不阻塞 | 全部 P0/P1 清零 → ✅ 通过

> **为什么 W4 不能跳过？** submit 是唯一的 PR 创建入口，W4 是 submit 的前置条件。
> AI 无法绕过 submit 直接 `git push`（无 finish 标记 = submit 拒绝 = 无法创建 PR）。

**产物路径（唯一权威，不要试探）**（task 3659 教训：审计结果存错位置来回打转 11 分钟）

| 产物 | 权威路径 | 关键格式 |
|---|---|---|
| W3 本地 CI 结果 | `<archives/首字母/软件/版本>/.ci-result.json` | `exit_code=0`，**带点前缀**，finish 自动写入，禁止手改 |
| W4 审计结果 | `<archives/首字母/软件/版本>/reports/audit-result.json` | `verdict=pass`（P0/P1=0），**无点前缀**，必须在 `reports/` 下 |
| 最终任务结果 | `$HOME/ohpcd-ai-worker-result.json`（或 result 命令 `--out`/`OHC_RESULT_OUT` 指定位置） | Step 7 result.json 格式 |

> 归档根目录的 `.audit-result.json`（带点前缀 + 错误层级）是**错误路径**，submit 不会读。
> **工具已强制**：submit 在找不到 `reports/audit-result.json` 但发现根目录 `.audit-result.json` 时，报错会直接指出错误位置和唯一正确路径（不再需要试错）。

**W5 — 知识图谱完整性检查**
适配结束时**必须**检查知识图谱内容的完整性和合规性：
```bash
# 检查草稿/正式条目字段完整性
python3 $SKILL_ROOT/scripts/ohc-run.py graph validate
# 确认草稿已生成（如本次编译有新错误模式）
ls knowledge/drafts/*.kv 2>/dev/null  # 两种命名: DRAFT-*.kv 与 E###-draft-<AgentID>.kv
# 确认 doc/ 与 graph/ 配套（E###.md ↔ E###.kv）
```
> 每个 E###.kv 必须有配套的 doc/E###.md，关键字段（error_signature、root_cause、rec_approach）不得为空。

---

## §1 快速参考

### 1.1 两套模式

**模式 A：Conan 驱动（推荐，适合已有 conanfile.py 的软件）**
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py build <软件名> [<版本>]
# → 内含 14 步：预分析→init→patches→pre-scan→configure→make→install→staging→conan-init→conan-verify→finish→...
```

**模式 B：探索性编译（适合首次/复杂软件）**
```bash
# Step 1: 初始化（自动）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL]

# Step 2: 读取上下文，手动编译（唯一需要 AI 的步骤）
source .build-context-<name>-<ver>
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j2 && make install DESTDIR=$TEST_PREFIX
make check  # 必须执行，超时可 Ctrl+C 跳过并记录原因

# Step 2.5-2.6: 生成并验证 Conan 配方（⭐ v3.0 新核心步骤）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本>
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>

# Step 3: 收尾（9 步自动，详见 §3 Step 3）
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed|archived

# Step 4: 提交 PR（内含 W4 前置检查 + AI Review 监控 + CI 监控，HANDOFF 强制）
python3 $SKILL_ROOT/scripts/ohc-run.py submit <软件名> <版本>
# 如 AI Review HANDOFF 后修复并继续:
python3 $SKILL_ROOT/scripts/ohc-run.py submit <软件名> <版本> --resume

# Step 6: SKILL_FEEDBACK (submit 成功后自动调用，也可手动运行)
python3 $SKILL_ROOT/scripts/ohc-run.py feedback <软件名> <版本>
# 如 HANDOFF 后填写建议并验证:
python3 $SKILL_ROOT/scripts/ohc-run.py feedback <软件名> <版本> --resume

# Step 7: RESULT — 任务终态上报（⭐ 强制：任何终态都必须输出 result.json）
# result.json 是跨设备/跨 AI 交换文件（非 PR 内容）；输出位置: --out > $OHC_RESULT_OUT > 仅 stdout
python3 $SKILL_ROOT/scripts/ohc-run.py result <软件名> <版本> --status success --out <输出位置>
python3 $SKILL_ROOT/scripts/ohc-run.py result <软件名> <版本> --status dependency_missing \
    --missing "zlib,libpng" --missing-evidence "conan download zlib -r=ohpcd -> 404" \
    --failed-reason "依赖未发布" --out <输出位置>
```

**如何选择**：已有 conanfile.py / 简单编译 → 模式 A；首次编译 / 复杂依赖 / 需深度调试 → 模式 B。

**特殊情况**：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libnew 1.0 --url=https://...    # 新软件
python3 $SKILL_ROOT/scripts/ohc-run.py init-build --resume                          # 恢复中断
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto <软件名> <版本>         # 只做补丁
python3 $SKILL_ROOT/scripts/ohc-run.py status                                        # 查看所有进行中编译
python3 $SKILL_ROOT/scripts/ohc-run.py engine "错误日志"                              # 独立运行知识图谱引擎
```

### 1.2 版本号策略（⭐ 强制执行）

**版本号 = 上游版本 + 可选适配修复后缀。**

| 场景 | 版本号 | 示例 |
|------|--------|------|
| 首次适配上游 X.Y.Z | `X.Y.Z` | `zlib/1.3.1` |
| 同一上游版本，修复适配问题 | `X.Y.Z.N`（N 从 1 递增） | `zlib/1.3.1.1`、`zlib/1.3.1.2` |
| 上游发布新版本 | 新版本号，后缀重置 | `zlib/1.3.2` |
| 上游停更，我们 fork 维护 | `X.Y.Z` 不变 | conandata.yml 指向 fork 源码 |

**原因**：cnb.cool 制品仓不支持同版本多 recipe revision 并存（上传新 revision 会被 409 拒绝），必须用版本号后缀区分适配修复。

**CI 门禁（L0j）**：PR 阶段自动检查——如果制品仓中已存在同版本，且 conanfile.py/conandata.yml 有修改，直接 fail 并提示递增版本号。

**下游引用规范**：
```python
self.requires("zlib/1.3.1")      # 精确引用首次版本
self.requires("zlib/1.3.1.2")    # 精确引用第 2 次适配修复
```

### 1.3 铁律摘要（52 条，违反=bug）

| # | 规则 |
|---|------|
| R1-R5 | **参数/补丁/链接/源码**：参数最少化(只需`--prefix`)；探索阶段不生成.patch(改源码+记notes)；补丁只用`refresh-patch --auto`；危险库静态编译；软链接`rm -f && ln -s` |
| R6-R10 | **源码与文件**：只改源文件不改生成文件(`track-edit`)；安全弹窗先触发再测试；`#ifdef __OHOS__`守卫可用但须有实质逻辑(禁止空壳stub)，**patches/ 补丁文件中默认禁止平台宏，例外（如 libc 探针）须在 PR 说明理由（口径以 iron-rules.md R8 为准）**；门禁FAIL禁标success；临时文件用`$TMPDIR` |
| R11-R15 | **失败与历史**：失败先查归档再动手；先匹配错误模式再修复；脚本用完整路径；脚本失败=手动模式入口；历史仅供参考不盲从 |
| R16-R20 | **协作与打包**：协作不越权(走PR)；知识先草稿(`graph add --draft`)；依赖先查预编译；禁止手动打包(用`conan create`+`conan upload`)；~~DESTDIR模式~~(废弃) |
| R21-R25 | **自检与清理**：探索结束自检零介入；finish前必须通过conan验证；平台检测优先于改生成文件；归档清理failed必删；notes.md防重复(finish自动清理) |
| R26-R31 | **Conan 配方**：系统同名库禁止动态链接(避免污染`/lib`/`/lib64`)，默认动态由Conan管理依赖链；conanfile.py必须有`test_package/`；conan_verify通过才标published；conan-verify失败必须查询知识图谱；知识图谱未命中必须生成草稿 |
| R32 | **OHOS 平台兼容**：recipe 内 `settings.os` 判断必须 `in ("Linux", "OHOS")`，不能 `== "Linux"` |
| R33 | **build() 禁止依赖未定义的 shell 环境变量**：编译器/标志必须从 Conan Toolchain 或 `self.conf_info` 获取，不能裸用 `${CC}`/`${CFLAGS}` 等 shell 变量（release worker 上为空→编译静默失败） |
| R34 | **test 必须实质依赖被测包**：test_package 源文件必须调用被测包的 API / 执行被测包的二进制，禁止只打印字符串的空壳测试（create-pr 前置硬闸 PF3 先拦，CI L1e 破坏性反向验证兜底） |
| R35 | **禁止用 conan list/search 判断 binary 是否存在**：cnb.cool 搜索 API 对 binary 返回不完整（显示 "No packages found" 但实际已上传），必须用 `conan install --requires=...` 或 `conan download` 验证预编译包 |
| R36 | **依赖必须先发布再构建下游**（机械门禁）：依赖包必须先通过 release 流水线发布到制品仓，再构建下游包。未发布的依赖会导致 `--build=missing` 从源码编译，耗时且易失败。依赖链 `C→B→A` 的发布顺序必须是 A→B→C。`finish` step [5/10] 和 CI L0i 均 Hard Fail（不止警告） |
| R37 | **版本号 = 上游版本 + 适配修复后缀**：首次适配用上游版本 `X.Y.Z`，修复适配问题后加后缀 `X.Y.Z.N`（N 从 1 递增）。原因：cnb.cool 制品仓不支持同版本多 revision 并存，必须用版本号区分 |
| R38 | **命令行工具必须声明 commands.json**：如果构建产物包含可执行文件，必须在**软件级别**目录下创建 `commands.json`（hicmd 格式）。库类型不需要。CI 门禁 L0k 自动校验 |
| R39 | **源码 URL 必须为官方源**：conandata.yml 中 URL 必须指向官方正式源（GitHub releases、官方网站）或权威镜像源，禁止个人 fork/网盘/不明 CDN。CI 自动添加镜像 fallback |
| R40 | **深度适配库需验证适配完整性**：图形渲染/UI框架/多媒体/外设/系统底层类库，编译通过≠适配完成，需检查实质性平台适配代码（非 stub/return 0） |
| R41 | **外部依赖阻塞止损**：registry/git remote 连续 3 次不可达且超 30 分钟，或失败明确属于环境外部因素（上游未发布/网络故障）→ 立即写 result.json 止损，禁止无限重试；多包任务单包止损不连坐（成功包不白干）；剩余预算 <40 分钟只收尾不启大步骤 |
| R42 | **PR 创建即写 partial 草稿 + 预算内闭环 CI 到绿 + 修复循环机器可数（v12.14）**：PR 创建成功那一刻先写 result.json 草稿（`--status partial` + PR 链接，防猝死丢工作）；然后默认继续工具化监控 CI（`submit` 内置 2400s 轮询）——**CI 红 ≠ 放弃**：失败详情自动提取进 HANDOFF + `.ci-repair-state.json` 轮次计数（第 N/2 轮），按报错修复 → `git push` → **必须 `submit --resume` 续环触发重跑（push 本身不会触发 CI——评论触发型，resume 自动评论 /rebuild）**，直到 CI 绿自动升级 result 为 success；连续 2 轮修复仍红 → 停损（HANDOFF 切换为上报 build_failed + 人工介入，勿再盲目重试）；CI 转绿自动清零轮次；检视意见闭环不完整与 CI 失败两分支均自动写 loop_pending 草稿（环未闭信号，worker 可 sweep dispatch 续环）。禁止 agent 自己写 sleep 轮询 CI（工具已有轮询）；仅当剩余预算 <40min（R41）或显式 `--no-wait` 时停在 partial 退出，**v12.12 修正：CI 是评论触发型，无人评论 `/rebuild` 就不自动跑，AI Review 也需会话内闭环——『平台异步』假设已证伪；PR 创建 ≠ 成功，成功 = 检视意见闭环 + CI 绿（success 硬闸强制，双缺一不可）。--no-wait/预算不足退出时 result 草稿自动写 milestone=loop_pending（摘要内嵌续环命令）+ feedback 事件；v12.14 pr_url 统一 `/merge_requests/N` 格式（平台 ECS 归一化对齐）** **修复轮聚焦（心愿单 0902 S4：conan 依赖类 60% + 编译链接类 32%）**：CI FAILED 诊断优先查依赖版本/缺包提示（conan 源遗漏/版本约束冲突），次查编译链接错误（缺头文件/链接符号/交叉编译目标不符）——两大类覆盖 92% 失败，修复动作按此排序 |
| R43 | **调参螺旋止损**：同一错误类别（cmake 组件/目标/include 路径等 conanfile 调参）连续 5 次修改仍失败 → 停止调参，写 result.json（`failed_build` + 5 次尝试的证据）退出；与 R41 互补：R41 管外部阻塞，R43 管内部死循环 |
| R44 | **CI 失败必须先自诊断再修（submit --resume 失败时）**：CI 红后的第一步是 `gitcode_pr.py diagnose --repo ... --number N`——CI 侧分类 ~60% 落"未知"，diagnose 对评论内嵌的失败日志做本地二次归类（链接/编译/cmake/依赖/配方/补丁/权限/网络/文件缺失/测试空壳），输出证据行+修复要点；禁止对"未知"失败盲改重推（采样：同一 PR 反复重推同类失败=纯浪费 CI 额度）。修复循环: diagnose → 修复 → W3 复验 → push → `submit --resume`；连续 2 轮同错误仍红 → 停损上报（衔接 R43） |
| R45 | **SKILL_FEEDBACK 防丢失协议（骨架前置+事件累积+终态兜底+完成入仓，工具强制）**：feedback 不再是"流程走完才生成"——①PR 创建瞬间与 R42 result 草稿同步前置生成骨架（submit 内置，幂等）；②全流程事件（HANDOFF/CI红绿/pr_created/闭环）经 `_emit_submit_handoff` 单一咽喉自动累积进骨架的"过程事件时间线"——失败任务的经验不再丢失（旧流程失败分支从不生成 feedback=幸存者偏差）；③result 终态无论成败自动兜底补骨架并落 `feedback_pending` 字段（ECS 回收工作区前据此收割）；④反馈填完闭环（`feedback --resume` rc=0）时自动 commit+push 到任务分支随 PR 进 main（只推终稿不推占位稿——防 PR 转绿后再触发 CI 重跑；运行时状态存顶层 `.ohc/feedback-state/`（v12.10.1 迁出 archives 树，已 gitignore，永不触发 JC5）；OHC_FEEDBACK_PUSH=0 可关）。AI 仍需做的唯一动作：终局填 4 个建议占位符 + 效率/检视小节 |
| R46 | **result.json 全程生命周期草稿（工具强制，0828 批量复盘新增）**：五挂点自动写草稿 init-archive(task_started)/conan-init(recipe_generated)/conan-verify(conan_verify_passed)/finish(w3_finish_started)/submit(pr_created)——任务前 80% 时长不再裸奔；草稿 `draft:true`+`milestone`，终态 `draft:false`（ECS 区分中断/终态）；输出位置 `--out`>`OHC_RESULT_OUT`>`$HOME/ohpcd-ai-worker-result.json` 兜底；终态不降级覆盖；手写/残留检测后覆盖。AI 照常走流程即可，草稿全自动 |
| R47 | **语言预检前置（AI Worker 协议 v0.8 附录 D，2026-08-29 冻结；缺字段=PROTOCOL_VIOLATION 拒收）**：checkout 源码后、进入适配主流程**前**必须跑 `lang-preflight`（scripts/ohc/lang_detect.py）——判定优先级 manifest>构建系统>源码统计(≥70%)，边界规则：C/C++ 混编按主体判不算 mixed、pybind11 绑定包判 cpp、辅助脚本不算主体、manifest 与统计矛盾判 mixed；任务语言取 `--lang`/`OHPCD_LANG`（默认 cpp），**c↔cpp 视为兼容族不迁移**（conan 流程通吃）；不匹配 → 立即终态 `env_unsupported` + `detected_language`（§4.6 枚举，禁自由文本）+ `language_evidence` 三项（各≤200 字符），**禁止硬着头皮适配**（0828 报告 ~20% 任务浪费在非 C/C++ 源码上）；匹配 → 草稿 milestone=lang_checked，正常进主流程；**激励: 带 detected_language 上报 → 平台转 lang_hold 挂起等生态（非失败）——缺字段 = PROTOCOL_VIOLATION 记失败（反馈 0831 P1: 9 例违规源于旧版/手写绕过 CLI,终态上报必须走 result 命令）** |
| R48 | **预算感知收尾（反馈 0831 修订版：边界双方已对齐）**：动态预算/硬杀在平台侧（attempt 递增 1.0/1.5/2.0×，上限 12h，随 dispatch 下发 `OHC_TASK_DEADLINE` ISO 绝对时刻 + `OHC_TASK_BUDGET_SEC` 秒数）；SKILL 唯一配合项 = 预算接近耗尽时主动收尾——三件套：①`budget-check` 命令（scripts/ohc/budget.py）每个长阶段（W3 编译/CI 监控/重试循环）前调用，三态：ok 继续作业 / near_limit（剩余<40min=R41 阈值：停止新编译新 PR，立即写 checkpoint 收尾）/ exhausted（exit 3，**自动写终态——status=failed + error_type/error_code 双写 `budget_exhausted`（受控扩展，协议 §4.5 枚举外、平台 0831 部署已识别，勿报 unknown）+ `checkpoint_steps` 结构化数组（已完成里程碑=续跑断点）+ error_detail 续跑命令**，平台 retry_context.resume 已就绪，续跑带已完成步骤不丢成果）；②R46 生命周期草稿写前自动查预算，超限直接升级上述终态（忘调 budget-check 也有兜底，防被杀后停在 draft:true 被平台归一化 unknown——76 例根因）；③预算判定源优先级 OHC_TASK_DEADLINE>OHC_TASK_BUDGET_SEC>OHPCD_BUDGET_MINUTES（旧自造）>240 兜底；起点=feedback 时间线**最后一条** task_started（reset-rerun 后新起点生效；`submit --resume` 入口自动刷新计时，续跑不被旧时间线误杀）。闭环：平台给足预算（12h 顶格）+ SKILL 主动收尾上报 → 大库任务要么预算内完成，要么断点续跑接力 **v12.17 S3 修订（心愿单报告）**：停止自行预算判定——240min 兜底与 OHPCD_BUDGET_MINUTES 自造 env 已退役（R48 违约 6 例 budget 自裁教训：与平台 12h 动态预算冲突过早自裁）；**仅在平台 env（OHC_TASK_DEADLINE/OHC_TASK_BUDGET_SEC）存在时判定，两者皆无 → 恒 ok 不判定** |
| R49 | **依赖注入必须用 build_folder 私有 prefix**（asterisk-srtp 反馈，知识 E524）：generate() 中依赖注入目标 = `os.path.join(self.build_folder, "prefix")`，CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH 全指向私有 prefix，work 目录用 build_folder 子目录（conan 构建目录天然可执行）。三禁止：①注入共享 `/usr/local`（SYS_PREFIX）——CI worker 与本地共享文件系统互相污染（E524：19 轮 CI 全挂根因）；②`os.access(X_OK)` 探测 work 目录——HMDFS chmod 被忽略、权限固定 660，X_OK 恒 False 永远回退 noexec 路径；③只加 `ac_cv_prog_cc_works=yes` 不补 REQUIRED 依赖。参考：archives/a/asterisk-srtp/22.10.1/conanfile.py |
| R50 | **回执完整性铁律（心愿单报告 0902 S1：08-30 后 208 个空 pr_url 回执→ 误判 generic-failure → infra 重试三连恒同）**：①PR 创建后**所有落盘**（草稿+终态）必带 pr_url——write_lifecycle_draft 新增 pr_url 参数，submit 六个草稿挂点全部显式传 `pr_url=pr_url`（不靠推导链）；②CI PASSED 后 submit **自动**写终态 success（_maybe_upgrade_result 显式传 pr_url/pr_number/branch/commit_hash 四必填项，值取自 .submit-state.json+git HEAD），**不再依赖 agent 手动跑 result 命令**，且不再要求 OHC_RESULT_OUT 已设置（result 自带 OHC_RESULT_OUT>$HOME fallback 链，环境变量缺失/串扰机也落盘）；③success 自动上报带 `--no-ci-verify`——该调用仅在 submit 已实证 CI 绿的分支发生，复跑 API 核验遇通道抖动会 ERROR 误降级 partial（黑洞机制之一）；守门仍约束手动上报路径（防 CI 红谎报 success，PR6096 教训）（v12.20 注：原以 R49 编号登记与 iron-rules R49 冲突，主编重编号为 R50，详解见 iron-rules.md） |
| R51 | **上游测试三步法**：适配前清点上游测试（tests/ 目录数 + ctest/pytest 注册数，写入 notes.md 申报表）→ 可运行环境实际运行（真机/CI，逐项列"具体技术原因"，"没环境"不是理由）→ PR 如实回填实测 N/N′/通过率（禁占位符）；"上游确无测试"须附清点证据。真人评审第一拒绝原因（"硬性不通过" 495 次），v12.20 新增 |
| R52 | **审计证据一致性**：.audit-result.json 等自审文件必须由 W4 工具生成、结论附被检文件 sha256；preflight 交叉校验——审计 pass 但硬闸命中 → "审计失真"一票否决档（#2204/#4237/#4321）。v12.20 新增 |
| W0-W5 | **适配工作流**：适配前先查依赖(W0)；同步main(W1)；PR原子性+结构完整性(W2,嵌入finish)；本地编译验证(W3,嵌入finish,阻塞+HANDOFF)；提PR前独立审计(W4,嵌入submit,HANDOFF强制)；知识图谱完整性(W5) |

> 详解见 references/iron-rules.md

### 1.3 决策树

```
新三方库？
├─ registry 有记录 → ohc-run.py init-build <name> <ver>
├─ 有 URL → ohc-run.py init-build <name> <ver> --url=URL
└─ 都没有 → ohc-run.py search-url <name> <ver> → 从候选选 URL

缺依赖？
├─ 从 cmd-pkgs README 查询预编译包 → curl install.sh | sh
├─ conan 制品仓有 → conan install --requires=name/ver
├─ 制品仓没有 → 先适配并发布依赖包（R36：依赖发布优先级）
│   ├─ 依赖包走完整适配流程 → conan create → CI → release → conan upload
│   └─ 依赖发布成功后，回来继续构建当前包
└─ 多层依赖链 C→B→A → 按拓扑序从最底层 A 开始逐层发布

configure 失败？
├─ 缺依赖 → HANDOFF → AI 安装预编译包 → --resume-from=Step3
├─ 平台不识别 → 改 config.guess/sub（build-systems.md §3.1）
├─ conftest pipe → configure 中 `| cat` 修复
└─ 其他 → 引擎匹配 graph/index.tsv → 按 E 编号查找

编译成功 → 固化为 Conan 配方
├─ ohc-run.py conan-init <name> <ver>     生成 conanfile.py + conandata.yml + test_package/
├─ 检查生成的配方（requirements, package_info, 系统同名库静态配置）
└─ ohc-run.py conan-verify <name> <ver>   验证配方可复现
```

> **⭐ R18+R35+R36 强化：预编译包优先 + 查询方式 + 发布优先级**
>
> - **R18**：编译过程中发现的任何依赖缺失，**必须先查 cmd-pkgs README** 和 Conan 制品仓。只有两者都没有才手动编译依赖。
> - **R35**：查制品仓时**禁止用 `conan list "*/*:*/*"` 判断 binary 是否存在**（cnb.cool 搜索 API 对 binary 返回不完整）。必须用 `conan install --requires=name/ver` 或 `conan download` 验证。
> - **R36**：如果依赖包尚未发布到制品仓，**必须先适配并发布依赖包**（走 release 流水线 `conan upload`），再回来构建当前包。多层依赖按拓扑序逐层发布。

---

## §2 文件检索时机

| 触发场景 | 加载文件 | 何时 |
|---------|---------|------|
| 技能触发 | **SKILL.md**（本文档） | 每次 |
| 开始编译 | references/compile-guide.md | Step 2 前 |
| 生成 Conan 配方 | templates/conanfile-*.py.tmpl + docs/ADAPTATION_GUIDE.md | conan-init 时 |
| 验证 Conan 配方 | ci/conan/profiles/ohos-aarch64 | conan-verify 时 |
| 预编译风险扫描 | knowledge/graph/pre-scan-rules.yaml | build Step 2.5（自动） |
| **W3/CI 构建超时** | ci/config/build_timeouts.txt + `ohc-run.py timeout` | W3/CI 超时发生时 |
| **源码风险预扫** | pre-scan-rules.yaml + 知识条目 prescan_pattern 字段（运行时动态派生） | 下载源码后 / build Step 2.5 / `prescan` 独立命令 |
| 编译出错 | knowledge/graph/index.tsv → graph/E*.kv | 错误发生时 |
| 缺少依赖 | ohc-run.py resolve-deps --list-available | init-build Step 7 |
| 失败处理 | references/failure-handling.md | R11+R12 流程 |
| HANDOFF 交接 | references/handoff-protocol.md | 脚本→AI 交接时 |
| 补丁生成 | references/patch-pipeline.md | finish 内部 |
| 归档收尾 | knowledge/ARCHIVE-SPEC.md | finish 内部 |
| 铁律详解 | references/iron-rules.md | 需要时 |
| 软件迁移/新适配 | references/migration-guide.md + knowledge/operations/ohos-adaptation-patterns.md | 迁移或新软件适配时 |
| 构建系统适配 | knowledge/operations/build-systems.md | configure 前 |
| Conan 发布/上传 | knowledge/operations/release.md | conan upload 发布时 |
| CI 脚本契约 | ci/conan/build_and_test.sh（内联注释） | ci/ 脚本修改时 |
| **Pre-PR 审计 (W4)** | **.gitcode/code-style.md + .gitcode/review-memory.md** | **提 PR 前 (W4)** |
| **PR 管理** | **scripts/gitcode_pr.py** | **创建/跟踪/回复 PR 时** |

---

## §3 核心流程

### Step 1: init-build — 全自动

```bash
$SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL] [--no-download] [--resume]
```
内部 9 步：registry→URL→下载→解压→历史检索→骨架创建→依赖解析→环境检查→输出 `.build-context-<name>-<ver>`。

### Step 1.5: lang-preflight — 语言预检（⭐R47，协议 v0.8 附录 D，强制）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight <软件名> <版本> \
    --src $BUILD_SRC_DIR    # 任务语言自动取 OHPCD_LANG（默认 cpp）
```
源码 checkout 后、进入 Step 2 适配主流程**之前**必须执行（R47）：manifest>构建系统>源码统计(≥70%) 三级判定 + 边界规则（C/C++ 混编按主体判 / pybind11 绑定判 cpp / 辅助脚本不算 / 矛盾判 mixed）。**exit 2 = 语言不匹配**：已自动写终态 `env_unsupported` + `detected_language` + `language_evidence`（协议强制字段），**立即终止任务，禁止硬着头皮适配**；exit 0 = 匹配通过（c↔cpp 兼容族），写 milestone=lang_checked 草稿，继续 Step 2。

### Step 2: AI 编译 — 唯一智能步骤

```bash
source .build-context-<name>-<ver> && cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
make check  # 必须执行，超时可 Ctrl+C 跳过
```
执行顺序：configure → make → make install DESTDIR（staging 隔离）→ 安全弹窗(R7) → make check → Staging 验证。
脚本需 AI 介入时输出 HANDOFF 交接块，格式见 references/handoff-protocol.md。

### Conan 配方（Step 2.5-2.6 合并，⭐ v3.0 新核心）

**G0 预构建评估**（init-build 内部自动执行）：基于 `knowledge/graph/pre-scan-rules.yaml` 预查询知识图谱，评估编译风险（已知平台陷阱、依赖冲突等），**非阻塞**，结果写入 `.build-context`。

```bash
# 生成 conanfile.py + conandata.yml + test_package/
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本>
# 验证配方（8 道门禁）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>
```

**conan-init 后 AI 必须检查**：`requirements()`(依赖格式 `name/version`)、`generate()`(R26 系统同名库静态)、`package_info()`(cpp_info.libs)、`conandata.yml`(sha256)。

**conan-init 后 AI 必须判断软件类型 (R38)**：
- 如果构建产物包含**可执行文件**（命令行工具，如 `strace`、`bash`、`curl`）→ 在**软件级别**目录（`archives/{letter}/{name}/`）下创建 `commands.json`（参考 [templates/commands.json.template](templates/commands.json.template)）
- 如果构建产物只有**库文件**（.a/.so，如 `zlib`、`openssl`）→ 不需要 commands.json
- 判断依据：conanfile.py 的 `package_info()` 中 `cpp_info.libs` vs `cpp_info.bindirs`/构建系统 install 了可执行文件到 `bin/`

**conan-verify 8 道门禁**（G0-G4 + L2/L4/L5）：

| 门禁 | 名称 | 说明 |
|------|------|------|
| **G0** | 预构建风险评估 | 知识图谱预查询，非阻塞 |
| **G1** | 配方完整性 | conanfile.py + conandata.yml + test_package/ 存在且字段完整 |
| **G2** | conan create | 从干净源码构建，验证配方自包含性 |
| **G3** | 系统同名库隔离 (R26) | 对比系统库目录（/lib、/lib64）基名，检查包内 .so 是否与系统同名冲突 |
| **G4** | 产物完整性 | bin/lib/include 产物检查 |
| **L2/L4/L5** | smoke test / 安全扫描 / 产物基线 | `--version`可执行 / NX·PIE·RELRO / SHA256 基线对比 |

**知识图谱集成（R30/R31）**：G2 失败时自动调用 `run_engine()` 匹配 E-entry。命中→展示根因+修复命令；未命中→自动生成 `knowledge/drafts/DRAFT-*.kv` 草稿。G2 通过 = 可标记 `published`（R29）。

### Step 3: finish — 9 步自动收尾

```bash
$SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed
```

| 步骤 | 内容 | 失败处理 |
|------|------|---------|
| [1/10] refresh-patch --auto | 补丁生成 | 跳过，继续归档 |
| [2/10] close-archive | 归档关闭 | exit 2 |
| [3/10] clean-verify 重建 (G0) | 干净构建验证（非阻塞，平台限制可跳过） | 非阻塞 |
| [4/10] conan-verify | Conan 配方验证（如 Step 2.6 已通过且配方未修改则跳过） | 失败降级 status 并记录 |
| [5/10] W2结构+R36依赖+W3本地CI | 结构检查(L0a-L0e)+依赖发布(conan download)+conan create（超时预算读 build_timeouts.txt），写入 .ci-result.json（integrity_hash + 日志 SHA256） | ❌ 阻塞 (HANDOFF) |
| [6/10] finalize-archive | 清理+校验+版本索引（commands.json 声明由 CI L0k 门禁校验） | 非致命 |
| [7/10] check-knowledge-gap | 知识完整性检查 (W5) | 非阻塞 |
| [8/10] gen_summary | 重新生成 SUMMARY.md | 非致命 |
| [9/10] PR 原子性检查 (W2) | 框架文件混入检测 | 警告 |
| [10/10] submit 就绪预检 | test-report/packaging/staging/build-closed 标记检查 | 警告 |

> **W4 Pre-PR 独立审计不在 finish 内部**，在 `submit` 内部作为前置检查执行。
> 流程顺序：`finish`（含W2+W3）→ `submit`（前置检查W4→git push→创建PR→**preflight 硬闸 PF1-PF9+R52 交叉校验**→**result 草稿 + FEEDBACK 骨架前置（R42+R45）**→**AI Review 监控**(5阶段)→**检视意见闭环校验**→**CI 监控（红→R44 diagnose 修复循环）**→**SKILL_FEEDBACK 填充闭环→完整即自动入仓（R45）**）。全程事件自动累积进骨架（R45），agent 任何时点死亡经验都不丢。
>
> **⭐ PR 创建前置硬闸 PF1-PF9+R52 交叉校验（工具强制，不可绕过；PF5/PF6 为 v12.17 新增，PF7-PF9/扩面/R52 为 v12.20 新增）**：
> `create-pr` 是所有建 PR 路径（ohc submit / 手工 / harness 机器人）的唯一咽喉点，创建前自动执行：
> - **PF1 单包闸**：一个 PR 只允许动一个 `archives/<字母>/<包>` 目录（JC6 同口径前置，多包捎带直接拦）
> - **PF2 制品闸**：禁止提交压缩包/归档（JC3 同口径前置，源码仓只收源码与配方）
> - **PF3 测试闸**：`test_package/conanfile.py` 的 `test()` 必须有 `self.run` 实际执行逻辑，空壳/print-only/pass-only 拦（L0c/R34 前置——建 PR 前拦截，省一轮 CI）
> - **PF4 依赖闸**：conanfile 的 `requires/tool_requires` 逐个探测制品仓（conan.cnb.cool 公开 API），缺失 → 拦截并提示立即 `result --status dependency_missing` 上报终止，**禁止捎带适配依赖**（W1/R36 前置）
- **PF5 平台宏闸**（R8 前置，v12.17+20 扩面）：patches/*.patch 新增行禁 `__OHOS__`（上下文行/存量豁免，例外须 PR 说明）；v12.20 扩面堵绕道——conanfile.py 新增行的 `-D__OHOS__` 注入与 `replace()` 动态注入同拦（语料 64+27 例）
- **PF6 前缀闸**（R49/E524 前置，v12.17）：禁注入共享系统前缀——`environ` 读 SYS_PREFIX、引号包裹 `/usr/local` 字面量即拦；合法形态（DEFAULT_PREFIX 可覆盖 + `~/usr/local` 用户级）豁免
- **PF7 源URL闸**（R39 前置，v12.20）：conandata.yml/manifest.yaml 源 URL 必须 https 官方源——镜像域名黑名单（gh-proxy.com/ghfast.top/cnb.cool 等语料实证 14 域）/明文 http/`file://` 泄漏/绝对路径/Debian 重打包/gitcode·gitee 搬运源一律拦（官方托管例外须 PR 说明+显式跳过）
- **PF8 配方静态闸**（R38/L0p/L0m 前置，v12.20）：settings 四项齐全；包目录 slug 规范；version 与版本目录一致；CLI 包（application/bindirs 非空）必须有 commands.json 且 name/type=tool/versions.ref 对齐，纯库包必须无
- **PF9 分支/路径闸**（L0n 前置，v12.20）：archives 变更须全落单一 `包/版本` 目录（防 "No packages to build"）；分支名须为 `pkg-version` 或 `feat|fix/pkg-version`
- **R52 交叉校验**（v12.20）：`.audit-result.json` 判 pass 但硬闸命中 → "审计失真"发现（一票否决档）——审计文件必须 W4 工具生成+sha256 佐证
>
> 逃生口：`--no-preflight` / `OHC_PREFLIGHT=0`（自担风险，与 result 硬闸 `--no-ci-verify` 命名一致）。
> 依据（goblinrs 744 PR 采样）：test() 空壳类 CI 失败 ~20%、多包捎带被 JC6 事后拦浪费整轮 CI——现在全部在建 PR 前拦。
>
> ⚠️ **完成标准（硬性）**：所有检视意见必须在讨论串内回复完毕（accept=修复+标记已解决 / reject=回复原因），闭环校验不通过不会进入 CI 监控；CI 必须 PASSED 才算流程完成。
> AI 操作路径：`finish` → `submit`，两条命令，不可跳过。
>
> **⭐ AI Review 监控（5 阶段，嵌入 submit，HANDOFF 强制）**：
> PR 创建后，submit 自动进入 atomgit-bot AI 检视监控流程：
> - Phase 1: 等待"变更摘要"生成（每 5 分钟轮询，30 分钟超时）
>   - atomgit-bot 先发"正在生成合并请求摘要"和"AI 代码检视正在进行中" → 继续等待
>   - 出现"变更摘要"字段 → 进入 Phase 2
> - Phase 2: AI 评估变更摘要（HANDOFF）→ 检查摘要中是否有必须修改的点
>   - AI 评估后 push 修复（如有）并 `--resume` 继续
> - Phase 3: 等待检视意见出现（每 5 分钟轮询，30 分钟超时）
>   - 继续等待 atomgit-bot 评论中出现三类以外的检视意见
>   - 出现检视意见 → 进入 Phase 4；超时无新意见 → 直接进入 CI 监控
> - Phase 4: AI 处理检视意见（HANDOFF）
>   - ⚠️ **检视意见不一定正确，需严格判断是否合理才能修改**
>   - 合理的修改并 push，不合理的回复说明原因
>   - 所有意见处理完毕后 `--resume` 继续
> - Phase 5: AI Review 完成 → 进入 CI 监控（平台 CI 需主动评论 /rebuild 触发，_monitor_ci 自动处理；手动触发用 `python3 scripts/gitcode_pr.py trigger-ci --repo <owner>/<repo> --number <PR号>`）
>
> 状态文件 `.submit-state.json` 记录 review_phase（1/3/5），`--resume` 从正确阶段恢复。
>
> **⭐ R42 批量任务模式（PR 创建即上报 + CI 闭环，2026-08-20 新增）**：
>
> **默认（预算充裕）——完整闭环**：
> 1. PR 创建成功瞬间：工具自动写 partial 草稿 result.json（OHC_RESULT_OUT 已设置时；这是防猝死保底，不是终点）
> 2. submit 继续内置监控 AI Review + CI（2400s 轮询，agent 无需自己写 sleep）
> 3. **CI 红 = 修复循环**：HANDOFF 自动携带最新失败评论的报错摘要 → 定位原因 → 修复 → 本地 W3 复验 → `git push origin <branch>`（CI 自动重跑）→ `python3 scripts/ohc-run.py submit <软件> <版本> --resume` 继续监控
> 4. CI 绿：工具自动升级 result 为 success（终态）
> 5. **`--no-wait` 退出（环未闭，v12.12）**：result 草稿自动写 `milestone=loop_pending`（summary 含完整 resume 命令）+ feedback 事件 `loop_pending`——CI 是评论触发型（无人评论 `/rebuild` 不自动跑），`loop_pending` 即『需 follow-up 续环』的机器可读信号，S8 重置重跑/worker 扫描可据此派发
>
> **预算不足（R41 <40min）或显式跳过等待**：`--no-wait` / `OHC_SUBMIT_NO_WAIT=1`——PR 建后立即返回（partial 草稿已落），CI/AI 闭环交由 follow-up 任务续环（工具已自动写 `loop_pending` 草稿信号；平台不会自动接手——CI 必须有人评论 `/rebuild` 才启动）（follow-up 只需 `submit --resume`，从断点续，不重跑 W1-W4）。
>
> 依据（task 3681 实测）：agent 建完 PR #4629 后**自己写 sleep 盲等** CI，等待中被节点超时杀死，result 未写被判 failed，90% 工作量丢失。教训不是"不等 CI"，而是"不裸等"：先落草稿，再用工具轮询，红了修到绿。
>
> **⭐ R44 CI 失败自诊断协议（R42 修复循环的失败分支细化，2026-08-26 新增，goblinrs 744 PR 采样教训）**：
>
> CI 红后的标准动作序列（submit --resume 的 HANDOFF 已内置此指引）：
> 1. `python3 scripts/gitcode_pr.py diagnose --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number <N>` —— 解析最新失败评论；CI 报 `类别: 未知` 时对评论内嵌的"失败步骤完整日志"做本地二次归类，输出 `本地归类 + 证据行 + 修复要点`（`--json` 供 harness 程序化消费）
> 2. 按修复要点改代码 → 本地 W3 复验（不带着已知错误去撞 CI）→ `git push`
> 3. `submit --resume <N>` 续监控；连续 2 轮同错误类别仍红 → 停损上报（R43 口径）
>
> 采样依据：open PR 中 CI 失败率 45%，其中 ~60% CI 报"未知"导致机器人无法自愈而反复盲推；test() 空壳类占 ~20%（现已被 preflight PF3 在建 PR 前拦截）。

> **⭐ R45 SKILL_FEEDBACK 防丢失协议（2026-08-26 v12.10，修复"12 建PR→13 才建 FEEDBACK"间隙丢失 bug）**：
>
> 旧流程三大丢失路径：①CI 绿后 feedback 生成前 agent 死亡→工作区回收→永久丢失；②失败分支（AI review/闭环/CI 红）从不生成→幸存者偏差，SKILL 迭代只收集顺利样本；③feedback/ 只写本地不 commit→main 上 13 个文件是零星漏网非机制保证。
>
> 工具化防线（AI 无需主动执行，全部内置）：
> 1. **骨架前置**：PR 创建瞬间与 R42 result 草稿同步落骨架（`ensure_feedback_skeleton`，幂等；resume 路径补齐旧任务）
> 2. **事件累积**：HANDOFF/CI 红绿/pr_created 经 `_emit_submit_handoff` 单一咽喉自动追加进 `.ohc/feedback-state/<l>/<sw>/<ver>.json`（v12.10.1 迁出 archives 树——曾因写进 `archives/.../` 且未 gitignore 被 JC5 拦截），并刷新进骨架的"过程事件时间线"（`<!-- EVENTS:BEGIN/END -->` 标记块，自动统计 HANDOFF/重试次数）
> 3. **终态兜底**：`result` 写盘时自动调 `feedback_pending_flag`——缺失即补骨架 + result.json 落 `feedback_pending` 字段；ECS 回收工作区前据此判断收割
> 4. **完成入仓**：`feedback --resume` 闭环（rc=0）时自动 commit+push 任务分支（只推终稿；OHC_FEEDBACK_PUSH=0 关）
> 5. **收割对接**：post-merge 收割同时认旧路径 `archives/.../reports/skill-feedback.md` 和新路径 `feedback/SKILL_FEEDBACK_<id>.md`（旧链路只认前者，基本空转）
>
> AI 仍需做的唯一动作：终局把骨架里 4 个建议占位符 + 效率分析/检视结果小节填实（cmd_feedback 校验，未填会再次 HANDOFF）。

> **⭐ R46 result.json 全程生命周期草稿（2026-08-29 v12.11，0828 批量复盘驱动）**：
>
> 复盘证据：600 失败任务中 D 类 SUCCESS_NO_PR 140→163 是唯一还在增长的类别——R42 草稿只在 PR 创建瞬间落盘（write_pr_draft 仅 submit 两处调用），任务前 80% 时长（适配/构建阶段）agent 预算耗尽或会话正常终止但未到 PR 步 → result.json 完全缺失（35 例 result_missing + 105 例 parse_error 疑似手写/跨任务残留）；且 OHC_RESULT_OUT 未注入的机器上草稿机制整体静默失效。
>
> 工具化防线（AI 无需主动执行，全部内置）：
> 1. **五挂点自动草稿**：init-archive(task_started) / conan-init(recipe_generated) / conan-verify 通过(conan_verify_passed) / finish 启动(w3_finish_started) / submit(pr_created，即原 R42)——任何时刻死亡，最后一份草稿就是上报内容
> 2. **输出位置兜底**：`--out` > `OHC_RESULT_OUT` > `$HOME/ohpcd-ai-worker-result.json`（环境变量缺失不再静默跳过）
> 3. **draft 显式标记**：草稿 `draft:true` + `milestone`（校验器强制 draft=true 仅允许 status=partial）；终态 `draft:false`——ECS 据 draft 字段区分"中断待续"与"终态上报"，不再误判 SUCCESS_NO_PR
> 4. **防降级 + 手写检测**：终态已写入（draft:false）时跳过里程碑草稿（不把 success 改回 partial）；覆盖前检测 checkpoints 末条非 result.json 的手写/残留文件并警告
>
> AI 仍需遵守：终态必须走 `result` 命令（手写 JSON 是协议红线，会被检测覆盖）；草稿只是保险，不是终态的替代。



**前置条件**：test-report 存在 + Staging 验证完成 + conanfile.py 存在。
**状态值**：`published`(verify通过+CI upload) | `built`(verify通过未upload) | `failed`(编译或验证失败) | `archived`(旧版本归档)。

### Step 4-5: 质量门禁与 CI 流水线

```bash
# Step 4: 独立复查（可选，finish 已自动调用 conan-verify）
$SKILL_ROOT/scripts/ohc-run.py verify-build <软件名> <版本>
```

**Step 5: CI 流水线**（外部驱动，无 AI 参与。CI 纯 zsh + conan，不依赖 ohc-run.py/知识图谱/草稿机制）

| 流水线 | 触发 | 执行步骤 | Upload |
|--------|------|---------|--------|
| PR 校验 | PR 创建/更新 | setup.sh → build_and_test.sh | ❌ |
| 正式发布 | PR 合并到 main | setup.sh → build_and_test.sh → upload.sh → sign.sh | ✅ CNB |

**CI 脚本说明**：`ci/conan/setup.sh`(环境初始化)、`build_and_test.sh`(conan create + L4/L5)、`upload.sh`(仅 release)、`sign.sh`(GPG 签名)。

**Upload 安全边界**：密钥仅存 CI 执行机，PR 校验不 upload，合并 main 后才 upload。
**CI 只读 4 文件**：`conanfile.py`/`conandata.yml`/`test_package/`/`patches/`。不读 `manifest.yaml`/`notes.md`/`reports/`。

> 详解见 references/compile-guide.md

### Step 6: SKILL_FEEDBACK — 流程终态反馈

```bash
# submit 成功后自动调用，也可手动运行
$SKILL_ROOT/scripts/ohc-run.py feedback <软件名> <版本>
```

在 SKILL 整个流程结束时自动生成反馈报告，写入 `feedback/SKILL_FEEDBACK_{random}.md`（项目根，与 `knowledge/` 同级）。

**报告结构**：
| 部分 | 内容 | 自动填充 |
|------|------|---------|
| 背景 | 软件/版本/构建系统/上游仓库/依赖/补丁/状态 | ✅ |
| 情况 | 执行概要/失败分析/知识图谱/AI检视/CI/效率 | ✅ (部分需 AI 补充) |
| 建议 | SKILL设计/模板/自动化/知识图谱覆盖 | ❌ (AI 填写) |
| 作者 | 姓名/邮箱 (git config)/Agent ID/时间戳/PR编号 | ✅ |

**数据来源**：manifest.yaml + conandata.yml + conanfile.py + notes.md + test-report.md + .ci-result.json + .submit-state.json + patches/ + knowledge/graph/draft/

**文件命名**：`SKILL_FEEDBACK_{8位随机hex}.md`（`secrets.token_hex(4)` 生成，防碰撞）

**HANDOFF 强制**：生成后检查 `(请填写)` 占位符，有残留则 emit HANDOFF（step_failed=feedback），AI 填充建议后 `--resume` 验证完整性。状态文件 `.ohc/feedback-state/<l>/<sw>/<ver>.json`（顶层，gitignore）记录 feedback_id。

> 模板: templates/skill-feedback.md

---

### Step 7: RESULT — 任务终态 result.json 上报（⭐ 强制）

**每个任务到达终态（无论成功、失败还是取消）都必须产出 `result.json`**，它是全链路唯一可信的结果来源（协议: SKILL_RESULT_PROTOCOL_SPEC）。

**定位**：result.json 是**跨设备/跨 AI 的结果交换文件，不属于 PR 提交内容**。输出位置优先级：`--out` 参数 > 环境变量 `OHC_RESULT_OUT` > **不落盘（仅 stdout 输出 JSON，由调用方自行采集）**。`--out`/环境变量接受目录或完整文件路径。典型用法：写到任务工作区/共享目录供调度方或其他 AI 采集。

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py result <软件名> <版本> --status <status> \
    --out <目录或文件路径> [options]
```

**status 枚举（协议 v0.8 §4.5 对齐 + 自有扩展）+ 分类决策树**：

| status | 判定条件 | 必填附加字段 |
|--------|---------|-------------|
| `success` | PR 已合并或已经过 CI 验证，软件包完整 | `pr_url` / `pr_number` / `commit_hash` / `branch`（自动从 .submit-state.json/gh/git 补齐） |
| `build_failed` | conan create 编译失败（协议枚举；旧写法 `failed_build` 仍接受，输出自动规范化为 `build_failed`） | `--failed-reason`（≤500 字符） |
| `bootstrap_failed` | 环境引导失败（协议 v0.8 新增：bootstrap 阶段挂掉而非编译失败） | `--failed-reason` |
| `timeout` | 预算/超时耗尽（协议 v0.8 新增） | `--failed-reason` |
| `internal_error` | 工具/流程内部错误（协议 v0.8 新增） | `--failed-reason` |
| `failed_test` | 编译成功但测试失败 | `--failed-reason` |
| `dependency_missing` | 依赖未发布（can_resolve=False） | `--missing`（裸包名）+ `--missing-evidence`（二次验证证据） |
| `env_unsupported` | 编译器/平台不支持，或 **语言预检不匹配（R47）** | `--failed-reason` + **`--detected-language` + `--ev-build-system/--ev-manifest/--ev-source-stats`（协议 §2.4 规则 4/5 强制，缺失=拒收）** |
| `upstream_issue` | 上游代码缺陷 | `--failed-reason` |
| `user_cancelled` | 用户主动取消 | `--failed-reason` |
| `partial` | 部分目标达成（仅 R46 生命周期草稿使用） | `--failed-reason` |

**CLI 参数 → JSON 字段映射**（字段名与 ECS 消费端严格对齐，改名=ECS 读不到）：

| CLI 参数 | JSON 字段 | ECS 用途 |
|----------|-----------|---------|
| `--pr-number` / `--pr-url` / `--commit-hash` / `--branch` | `pr_number` / `pr_url` / `commit_hash` / `branch` | 成功任务 PR 归档 |
| `--failed-reason` | **`error_detail`** | ECS 失败分支 error_msg 优先取此字段 |
| `--missing` | **`missing_dependencies`**（数组） | ECS 从此读依赖缺口 |
| `--missing-evidence` | `missing_evidence` | 依赖缺失证据留档 |
| `--detected-language` | **`detected_language`**（§4.6 枚举） | 协议 v0.8 语言迁移分支；仅 env_unsupported 允许，其余状态强制 null |
| `--ev-build-system` / `--ev-manifest` / `--ev-source-stats` | **`language_evidence`**（三项，各 ≤200 字符） | 协议 v0.8 判定证据，缺失=PROTOCOL_VIOLATION 拒收 |
| `--error-code` | `budget_exhausted`（受控白名单） | v12.16 受控扩展：error_type/error_code 双写该值，仅 status=failed（预算收尾）允许 |
| `--checkpoint-steps` | `A,B,C`（逗号分隔） | 已完成步骤结构化数组；budget_exhausted 时**必填**——平台 retry_context resume 断点 |
| `--summary`（强烈建议） | `summary` | 一句话结果摘要 |
| （非 success 自动生成） | `error_type` = status | 失败分类 |

**success 的 PR 字段来源链**（S3）：`--pr-number` 显式指定 > `.submit-state.json`（submit step 落盘）> `gh pr view`（需 worker 环境 gh 已认证）> git 推断 branch/commit。全部缺失时 success 校验失败 exit 2（fail-fast），**由生成器拦截而非流入 ECS 触发 SUCCESS_NO_PR 降级**——此时按 HANDOFF 补 `--pr-number` 即可。

**生成器红线**（违反=流程缺陷）：
- **必须用 `ohc-run.py result` 产出**，禁止手写 JSON、禁止事后改字段绕过校验
- `dependency_missing` 声明前**必须二次验证**：提供实际日志行或命令输出作为证据（生成器会自动在 `.ci_logs/` 搜索佐证行）
- **success 上报硬闸（工具强制，PR6096 教训：CI 红却报成功）**：`--status success` 时生成器自动拉取 PR 最新 CI 评论核验，非"校验通过"→ **拒绝写 success，自动降级 partial**（error_detail 注明核验状态与重报路径）。离线等极端场景可用 `--no-ci-verify` 显式跳过（自担风险）
- 校验失败 exit 2 且**不落盘**；成功 exit 0 且自动 `cat result.json`
- checkpoints 最后一条固定为 `message: "result.json"`（`_ohpcd_result` 条目）
- 重报需 `--force`（覆盖前必须确认终态变化）

**⭐ 上报时机（R42，2026-08-20 新增）——草稿保底，success 为终态目标**：
- **partial 是里程碑保底，不是终点**：PR 创建成功 → 立即写 partial（summary 带 PR 链接）；此后工具化监控 CI，红了按 HANDOFF 里的失败详情修复重推，**目标是 CI 绿后升级 success**
- **禁止裸等**：agent 不得自己写 `sleep` 轮询 CI/AI Review——submit 内置监控（2400s 轮询）+ HANDOFF 自动携带失败详情。实测教训：task 3681 自己写 sleep 盲等 CI，被节点超时杀死，result 未写，90% 工作量丢失
- **里程碑草稿（防猝死）**：每个里程碑都重写一次 result.json——W3 本地验证通过（partial）、W4 审计通过（partial）、PR 创建（partial，工具自动）、CI 绿（success，工具自动）。result 命令幂等；任务任何时刻被杀，**最后一份草稿就是上报内容**
- **预算耗尽停在 partial 不算失败**：PR 在、CI 在跑、草稿在——follow-up 任务 `submit --resume` 即可续上；比耗死在轮询里一无所有好得多

**HANDOFF 交接**（references/handoff-protocol.md）：
- 校验失败（exit 2）时自动输出 **HANDOFF 块**：`EXIT_REASON: result_invalid`、`EXIT_CODE: 2 (resumable)`、`STEP_FAILED: Step7`、RESUME_CMD（修正后参数模板）、AI NEXT ACTIONS（逐条校验错误+修复指引）
- **resumable 语义**：仅在 Step7 内修正参数重跑即可，无需回退更早 step（result.json 未落盘、无残留状态）
- 修复闭环：AI 读 HANDOFF 块 → 修正参数（补 evidence/reason/PR 四元组）→ 重跑 RESUME_CMD → exit 0 + `cat result.json` 采集

**⭐ exit 2 = 参数错误，不是任务失败**（S4 红线）：
- exit 2 只说明 result.json 参数不合法（缺 reason / 缺证据 / success 缺 PR 字段），**任务本身的终态判断不受影响**
- **严禁**因收到 exit 2 就改报 `failed_build` / `user_cancelled` 等失败状态"烧任务"——正确动作永远是：读 HANDOFF 块 → 补参数 → 重跑同一命令
- status 是任务级决策（编译真失败才报 failed_build）；工具 exit code 是参数级反馈，两者无关

**示例**：

```bash
# 成功（PR 字段自动从 .submit-state.json + git 补齐）
python3 $SKILL_ROOT/scripts/ohc-run.py result zlib 1.3.1 --status success --out /tmp/task-results/

# 编译失败
python3 $SKILL_ROOT/scripts/ohc-run.py result foo 1.0 --status failed_build \
    --failed-reason "conan create: aarch64-linux-ohos clang 报错 undefined reference to 'bar'" \
    --out ./results/foo-1.0-result.json

# 依赖缺失（必须给二次验证证据）
python3 $SKILL_ROOT/scripts/ohc-run.py result foo 1.0 --status dependency_missing \
    --missing "libbar" \
    --missing-evidence "conan download libbar/2.0 -r=ohpcd --only-recipe -> ERROR: Recipe not found" \
    --failed-reason "上游依赖 libbar 未适配发布" \
    --out /shared/results/

# 用户取消（不带 --out：使用 $OHC_RESULT_OUT；也未设置则仅 stdout 输出，不落盘）
python3 $SKILL_ROOT/scripts/ohc-run.py result foo 1.0 --status user_cancelled \
    --failed-reason "用户要求停止，转向其他任务"
```

> 采集方（CI Worker/调度 AI/其他设备）按 `--out` 或 `OHC_RESULT_OUT` 约定位置读取 result.json；两者都未设置时从 stdout 采集 JSON 全文。

---

## §4 失败处理（R11+R12）

> **详解 + 反面案例**: references/failure-handling.md

```
失败发生
├─ [R11] 查归档：README.md → manifest.yaml → conanfile.py
├─ [R12] 匹配错误：引擎匹配 graph/index.tsv → E*.kv → 方案
├─ 缺依赖？→ conan install 或 resolve-deps --install
└─ 动手修复：归档+知识库都没有 → 记录新问题 → 修复 → 继续
```

### 4.1 历史信息纠正（R15）

> **核心问题**：历史编译记录可能包含错误方案。

**纠错 4 步**：识别差距(对比历史vs本次参数) → 手动编译(正确参数) → 回写历史(conanfile.py+manifest+notes) → 沉淀知识(写入 L1/L2)。

**禁用参数**（native 编译，`--build=`/`--host=`/`--target=` → 一律改 config.guess/config.sub）。

### 4.2 时间预算感知（⭐ 硬性规则，task 3659 教训）

任务开始/恢复时**先算剩余预算**（dispatch 任务带 deadline；本地任务按 4h 惯例预算）。

- **剩余 < 40 分钟**：只做收尾——写 result.json（如实标 status + `--summary` 写明已完成的部分），**不做新的大步骤**（重跑 W3 / 重试 submit / 新一轮 conan create）
- **剩余 < 40 分钟且当前包卡死**：按 W3 止损规则立即止损，写 result 终止
- 反例：18:04 补充节点启动时任务仅剩 27 分钟，Agent 却按完整流程安排工作，收尾时间被吃光
- result.json 如实上报不扣分；耗尽预算一无所有才是最差结局
- **工具已支持**：环境变量 `OHC_TASK_DEADLINE`（ISO8601 或 epoch 秒）设置后，`result`/`dispatch` 入口自动报剩余预算；<40 分钟输出"只收尾"强警告。ECS/调度方下发任务时建议注入此变量

---

## §5 知识图谱

### 5.1 目录结构

```
knowledge/graph/           # 结构化数据
├── index.tsv              # 主索引（以 index.tsv 实时为准，当前 319 条）
├── principles.kv          # 编译原则（20 条）
├── pre-scan-rules.yaml    # 预编译风险扫描规则集
├── E001.kv ~ E320.kv      # 错误模式条目（E257 为空洞，复用请用 graph add 自动分配）
knowledge/drafts/          # 草稿目录（conan-verify 自动生成，R31）
├── DRAFT-001.kv ~         # 待审查的草稿条目
knowledge/doc/             # 人类可读文档（E001.md ~ E211.md）
knowledge/error-patterns.md  # 人类浏览入口
```

### 5.2 引擎匹配（五阶段）

Phase A: index.tsv 粗筛 → Phase B: .kv 精排 → Phase C: 方案生成 → Phase D: 原则过滤 → Phase E: 输出执行。

### 5.3 管理命令

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py graph add E{NNN} [--draft]      # 新增/草稿条目
python3 $SKILL_ROOT/scripts/ohc-run.py graph update E{NNN}              # 更新条目
python3 $SKILL_ROOT/scripts/ohc-run.py graph validate                  # 校验一致性
python3 $SKILL_ROOT/scripts/ohc-run.py engine "错误日志"               # 独立引擎匹配
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps <软件名> [--install] # 检查/安装依赖
```

### 5.4 知识分层

| 层 | 归属 | 特征 | 写入时机 |
|----|------|------|---------|
| L1 平台真理 | knowledge/*.md | 任何软件可能遇到 | 探索阶段实时 |
| L2 模式经验 | knowledge/*.md 章节 | 同类构建系统复现 | 探索阶段实时 |
| L3 本版笔记 | conanfile.py + manifest.yaml | 仅本软件本版本 | 探索阶段+固化阶段 |

### 5.5 知识生命周期（可成长性机制）

知识图谱通过**草稿→审核→正式**流转自动成长：

```
编译失败(conan-verify G2)
  → 引擎未命中 → 自动生成草稿 knowledge/drafts/DRAFT-###.kv
    → 自动提取: match_keywords(从错误日志)、error_excerpt(错误行)
    → 自动去重: 与现有草稿关键词重合>50%则跳过
    → AI 补充: error_signature、root_cause、rec_approach
      → graph promote DRAFT-### → 正式条目 E###.kv
        → 自动: 生成 doc/E###.md、更新 index.tsv、填充 last_updated
```

**命令**：
```bash
# 查看草稿
ls knowledge/drafts/*.kv  # 两种命名均需检查

# 提升草稿为正式条目（自动分配E编号+生成doc+更新index）
python3 $SKILL_ROOT/scripts/ohc-run.py graph promote DRAFT-001

# 指定目标编号提升
python3 $SKILL_ROOT/scripts/ohc-run.py graph promote DRAFT-001 --target-id E215

# 新增草稿（手动）
python3 $SKILL_ROOT/scripts/ohc-run.py graph add E{NNN} --draft

# 更新条目（自动刷新 last_updated）
python3 $SKILL_ROOT/scripts/ohc-run.py graph update E{NNN} --field root_cause="..."
```

**自维护**：
- `last_updated` 字段：`graph add/update` 自动填充当日日期
- `graph validate`：一致性校验（doc↔kv 配套、字段完整、severity 合法、引用有效）
- `principles.kv`：20 条编译原则（P001-P020），Phase D 原则过滤引用

---

## §6 归档规范摘要

> **完整规范**: knowledge/ARCHIVE-SPEC.md (v3.0)

```
archives/{letter}/{name}/
  ├── manifest.yaml              # 软件级元数据 + 版本索引
  ├── README.md                  # 软件描述
  ├── commands.json              # 命令行工具声明（软件级，仅 tool 类型，R38）
  └── {version}/
      ├── conanfile.py           # 【CI 输入】Conan 配方
      ├── conandata.yml          # 【CI 输入】源码 + 补丁声明
      ├── test_package/          # 【CI 输入】Conan L1 测试
      ├── patches/               # 【CI 输入】补丁文件
      ├── manifest.yaml          # 【AI 元数据】编译元数据 + 状态
      ├── notes.md               # 【AI 元数据】适配笔记
      └── reports/               # 【AI 元数据】验证报告
```

| 分类 | 文件 | CI 读取 | AI 读取 |
|------|------|---------|---------|
| CI 输入 | conanfile.py / conandata.yml / test_package/ / patches/ | ✅ | ✅ |
| CI 输入 | commands.json（软件级，仅 tool 类型） | ✅ | ✅ |
| AI 元数据 | manifest.yaml / notes.md / reports/ | ❌ | ✅ |

> 状态定义见 §3 Step 3。归档清理规则（R24）见 knowledge/ARCHIVE-SPEC.md。

---

## §7 Gotchas（鸿蒙关键陷阱）

| 陷阱 | 说明 | 对策 |
|------|------|------|
| /tmp 只读 | E002，写入报 Read-only | 用 `$TMPDIR` 或 `$HOME/tmp` |
| HMDFS 软链接 | 不能 ln -sf 覆盖 | `rm -f && ln -s` 或 wrapper |
| 安全弹窗 | 首次执行二进制弹确认框 | make install 后扫一遍 bin/ |
| chmod 不生效 | E046，SELinux 限制 | 记录为平台限制，不阻塞 |
| 未实现 syscall | E051，setreuid/chroot 等 | 加入 EXCLUDE_LIST 排除 |
| CI/W3 构建超时 | conan create 默认 3600s，重型包实测可超（ScaLAPACK 测试 4451s） | `ohc-run.py timeout set <名> <版本> <3600-57600>`，W3 与 CI 同源生效 |
| ELF 签名 | 必须签名否则不可执行 | CI 流水线 `ci/artifacts/sign.sh` |
| ncurses 共享库 | 编译为 .so 会导致系统崩溃 | conanfile.py `generate()` `--without-shared`（R4） |
| 静态链接 | 系统同名库构建 .so 会污染 `/lib`、`/lib64` | conanfile.py `generate()` `BUILD_SHARED_LIBS=OFF`（R26），仅限系统同名库 |
| 动态链接 | 非 system 同名库默认动态 | Conan 管理依赖链，用户 `conan install` 自动拉取全部依赖 |
| RPATH 解析 | 鸿蒙 `$ORIGIN/../lib` 不稳定 | 系统同名库强制静态（R26）；其他库由 Conan RPATH 管理 |

### 流程自省

发现 SKILL 自身问题时记录到 `reports/skill-feedback.md`（版本级）。
流程结束时自动生成 `feedback/SKILL_FEEDBACK_*.md` 结构化反馈报告（含背景/情况/建议/作者），由 `feedback` 命令驱动。残留 `(请填写)` 时 emit HANDOFF，AI 填充后 `--resume` 验证。

---

## §8 多任务模式

### 8.1 架构

```
主任务：编排调度(依赖排序→派发) → 监控进度(dispatch status) → 结果审计(review) → 提交(git push → PR)
子任务：独立加载 skill → 完整编译流程 → 生成 conanfile.py → 输出结果摘要
```

### 8.2 使用方式

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch plan zlib openssl wget
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch status zlib openssl wget
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch objective zlib 1.3.1
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch script zlib bzip2 openssl wget
```

### 8.3 单包止损，不连坐（⭐ 硬性规则，task 3659 教训）

多包任务中**每包独立走完生命周期**（提取→编译→finish→submit→result）。某包止损/失败后：

1. 该包 result 照常写（status + failed-reason + 证据），**已成功提交的 PR 不撤**
2. **立即继续下一包**，禁止在失败包上耗尽剩余预算（成功包被连坐 = 全部白干）
3. 最终 result.json 按各包结果聚合；部分成功时必须写明哪些包成功、哪些失败

> 反例：apr 已成功（15:41 完成），apr-util 卡死拖掉全任务 4h 预算，最终整体 failed——apr 白干。
> 正确行为：apr-util 按 W3 止损规则 30 分钟内止损 → 写 result → 继续后续包。
> **工具已强制**：`dispatch script` 对 failed 包**不再生成 createSubTask**（改为生成 result.json 补报指令）；`dispatch status` 对 failed 汇总输出止损提示。

---

## §9 工具一览

### AI 工具（scripts/ohc-run.py，本地开发环境使用）

| 子命令 | 用途 |
|--------|------|
| `build` | 14 步编译驱动（含预分析+conan 配方生成+验证）★ 主入口 |
| `init-build` | 下载/解压/骨架/环境/依赖解析 |
| `lang-preflight` | ⭐R47 语言预检（协议 v0.8 附录 D）：三级判定+边界规则；不匹配自动写 env_unsupported+语言字段终态 |
| `budget-check` | ⭐R48 预算检查（读 OHC_TASK_DEADLINE/OHC_TASK_BUDGET_SEC）：三态，耗尽自动写 budget_exhausted 终态（checkpoint_steps 断点+续跑命令） |
| `pre-analysis` | ⭐ 鸿蒙PC平台适配预分析（图形/音视频/系统集成/平台代码扫描） |
| `conan-init` | 生成 conanfile.py + conandata.yml + test_package/ ⭐ |
| `conan-verify` | conan create + G0-G4 + L2/L4/L5 + 知识图谱(R30) + 草稿(R31) ⭐ |
| `finish` | 补丁+归档+clean-verify+conan-verify+W2结构+R36依赖+W3编译(阻塞,HANDOFF)+知识+摘要（9步）⭐ |
| `engine` / `graph add\|update\|validate\|promote` | 知识图谱查询/管理/草稿提升 |
| `req add\|list\|close\|validate` | ⭐ 需求图谱管理（系统能力缺口跟踪） |
| `resolve-deps [--install]` | 查询/安装预编译依赖 |
| `timeout get\|set\|list\|validate` | ⭐ CI/W3 构建超时配置管理（build_timeouts.txt 单一事实源） |
| `draft-review [DRAFT-xxx] [--json]` | ⭐ 草稿预审辅助：相似度证据 + 三态建议（merge-into/review-similar/create）；**纳入决策权在人工审核**，promote 命令不变 |
| `prescan <src_dir> [--json] [--no-writeback]` | ⭐ 预编译源码风险扫描独立命令（评估/选型阶段可单独扫描，不必跑 build 管线）：规则集 24 条 + **知识库动态派生规则**；命中自动回填 hit_count |
| `recipe-search <name> [-b 构建系统] [-d 依赖]` | ⭐ 配方首稿检索：从 2280+ 历史成功配方找最相似骨架（含补丁智慧）作底稿；语料经 finish 自动增长 + 社区 git 汇聚 |
| `kb-report [--scan-logs <glob>]` | ⭐ 知识库质量月报（纯本地）：活跃度/陈旧度 + 预扫描价值 + **未命中错误采购清单**（知识投资定向信号） |
| `selftest` | 核心模块冒烟测试（9 用例：engine 回归/prescan/锁并发/P0 防回归等） |
| `resolve-deps --batch <file>` | 包级拓扑分层输出（同层可并行，配合多机/多进程；状态文件已事务锁） |
| `verify-build` / `refresh-patch` | 门禁复查 / 补丁管线 |
| `status` / `handoff` / `track-edit` | 状态恢复 / 源码追踪 |
| `search-url` / `submit` / `review` / `post-merge` / `feedback` / `result` | URL搜索 / **PR提交(W4→AI Review→CI→SKILL_FEEDBACK,HANDOFF,--resume)** / 主编审核 / 合并后索引 / **流程终态反馈(HANDOFF,--resume)** / **任务终态 result.json 上报(8状态枚举,生成器强制,exit 0/2)** |
| `init-archive` / `close-archive` / `finalize-archive` | 归档初始化 / 关闭 / 清理校验 |
| `check-env` / `clean-verify` / `check-knowledge-gap` | 环境检查 / 干净构建验证 / 知识缺口检查 |
| `dispatch` / `summary` / `conan-migrate` | 多任务调度 / 统计摘要 / Conan 迁移辅助 |

**独立脚本**（`scripts/` 目录，不通过 ohc-run.py）：

| 脚本 | 用途 |
|------|------|
| `scripts/gen-test-packages.py` | 批量为缺 test_package/ 的配方生成测试文件 |
| `scripts/sync-recipes.py` | 从 conan 缓存同步配方到 archives/ |
| `scripts/migrate_kv_to_yaml.py` | KV→YAML 渐进迁移 |
| `scripts/pre_pr_audit.py` | ⭐ W4: Pre-PR 审计工具 (generate/report/check 子命令，由 submit 内部调用) |
| `scripts/gitcode_pr.py` | ⭐ GitCode PR 管理 (创建PR/获取评论/CI状态/回复评论/monitor-review AI检视监控) |

### Pre-commit Hook（⭐ 建议安装）

```bash
cp ci/conan/hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

提交前自动检查 L0a-L0q（conanfile 语法/sha256/test源码/test()方法/MANIFEST/patch格式/环境变量依赖/Go-Rust检测/外部curl下载/settings完整性/exports_sources完整性）。

### CI 脚本（ci/ 目录，由 Buildbot Worker 执行，纯 shell，无 AI）

| 脚本 | 用途 |
|------|------|
| `ci/conan/setup.sh` | Conan 环境初始化 + profile + remote |
| `ci/conan/build_and_test.sh` | conan create + L4/L5 检查 |
| `ci/conan/upload.sh` | conan upload 到 CNB 制品仓（仅 release） |
| `ci/artifacts/sign.sh` | GPG 签名（非阻塞） |
| `ci/conan/profiles/ohos-aarch64` | Conan 编译 profile |

---

*SKILL.md v11.6 — 2026-07-14 — SKILL_FEEDBACK 阶段：新增 feedback 子命令和 ohc/feedback.py 模块，submit 成功后自动生成 feedback/SKILL_FEEDBACK_{random}.md（项目根，与knowledge同级）；HANDOFF强制（残留(请填写)则emit，step_failed=feedback），--resume验证完整性，.feedback-state.json状态文件；git config获取作者，secrets.token_hex生成随机ID；新增templates/skill-feedback.md模板；v11.5→v11.6*

*SKILL.md v11.7 — 2026-08-18 — RESULT 阶段：新增 Step 7 result.json 终态上报（SKILL_RESULT_PROTOCOL_SPEC），ohc/result_report.py 生成器（status 八值枚举、success 必填 PR 四元组、dependency_missing 必带 missing+evidence 二次验证、checkpoints 尾条固定 result.json、校验失败 exit 2 不落盘、成功自动 cat）；结果文件定位为跨设备/AI 交换产物（非 PR 内容），输出位置优先级 --out > OHC_RESULT_OUT 环境变量 > 不落盘仅 stdout，不依赖 archives 目录存在；校验失败自动输出 HANDOFF 块（result_invalid / resumable / Step7，含 RESUME_CMD 与修复指引）；v11.6→v11.7*

*SKILL.md v11.8 — 2026-08-19 — RESULT 字段对齐 ECS 消费端：JSON 字段名改为 missing_dependencies/error_detail/error_type/missing_evidence/summary（--missing → missing_dependencies 数组、--failed-reason → error_detail，ECS main.py/dispatcher 严格按此读取）；新增 --summary 参数；success PR 字段来源链 --pr-number > .submit-state.json > gh pr view > git（全部缺失 fail-fast exit 2，防 SUCCESS_NO_PR 降级）；明确 exit 2 = 参数错误非任务失败（禁止据此改报 failed_build 烧任务）；v11.7→v11.8*

*SKILL.md v11.9 — 2026-08-19 — task 3659 实测失败路径复盘五项（R41）：W3 外部依赖阻塞止损硬性规则（registry 连续 3 次不可达/超 30 分钟 → 立即写 result.json 止损，禁止无限重试/伪造产物）；现象→status 判定对照表（dependency_missing vs env_unsupported 口径："换网络正常机器能否解决"）；产物路径唯一权威表（.ci-result.json 带点前缀在版本目录、reports/audit-result.json 无点前缀、$HOME/ohpcd-ai-worker-result.json，submission.py Gate 唯一决定）；8.3 多包任务单包止损不连坐（成功包不白干，最终聚合如实写明）；4.2 时间预算感知（剩余 <40min 只收尾不启大步骤）；v11.8→v11.9*

*SKILL.md v12.0 — 2026-08-19 — R41 五项工具化落地（文档约束 → 工具强制）：A) result 对 dependency_missing 自动实测 registry（conan list -r=ohpcd 逐包试探，实测输出追加 missing_evidence，谎报当场戳穿）；B) dispatch script 对 failed 包不再生成 createSubTask（改 result.json 补报指令），dispatch status 汇总输出止损提示；C) OHC_TASK_DEADLINE 环境变量预算感知（result/dispatch 入口报剩余，<40min 只收尾强警告）；D) submit 发现根目录 .audit-result.json 时报错直接指出唯一正确路径（消灭 11 分钟试错）；修复 dispatch 在 GBK 控制台 emoji 崩溃；v11.9→v12.0*

*SKILL.md v12.1 — 2026-08-20 — worker 集群实测复盘（task 3677/3680/3681/3659/3664-3666）三项规则：R42 PR 创建即上报（禁止 sleep 等 CI/AI Review——平台异步事件不占预算；工具支持 submit --no-wait / OHC_SUBMIT_NO_WAIT=1，PR 建后自动写 partial 草稿；3681 实测建 PR #4629 后等 CI 被杀被判 failed，90% 工作量丢失）；里程碑草稿机制（W3 过/W4 过/PR 建每步重写 result.json，猝死时最后一份草稿即上报内容）；R43 调参螺旋止损（同错误类别连续 5 次调参失败→带证据退出，3681 实测 Qt5::3DCore 反复调参 3.5h 无上报；与 R41 互补：R41 管外部阻塞，R43 管内部死循环）；铁律 41→43 条；v12.0→v12.1*

*SKILL.md v12.2 — 2026-08-20 — R42 语义升级为"草稿保底 + CI 闭环到绿"（质量要求：确保 CI 通过，红了必修）：submit CI FAILED 时自动提取最新失败评论报错摘要进输出与 HANDOFF（agent 免二次查询）；修复回路写死——按失败详情修复→本地 W3 复验→git push（CI 自动重跑）→submit --resume 续监控；CI PASSED 时 OHC_RESULT_OUT 已设置则自动升级 result 为 success（partial→success 闭环）；agent 禁止自己写 sleep 轮询 CI（工具内置 2400s 轮询）；--no-wait 降级为预算不足（R41 <40min）时的退出通道，红 CI 由 follow-up submit --resume 续；v12.1→v12.2*

*SKILL.md v12.3 — 2026-08-20 — 全量诊断驱动升级（一致性修复 + 超时配置工具化）：①P0 修复 submit git add 草稿路径 knowledge/graph/draft/→knowledge/drafts/（submission/finish/feedback/post-merge/review/dispatch/kb_collab 全链路 8 处，主路径自动化恢复）；②CI 构建超时配置工具化：新增 ohc/build_timeout.py + `timeout get|set|list|validate` 子命令（与 CI AWK 校验同构，3600-57600s），本地 W3（workflow_checks）改读同一配置（原硬编码 600s 误杀中大型包），OHC_W3_TIMEOUT 可临时覆盖，W3 超时 HANDOFF 附 timeout set 指引，.ci-result.json 新增 log_sha256（W3 完整日志哈希）；③规则编号去碰撞：CI L0m 内部 R41/R42 改为 L0m-4/L0m-5（与铁律 R41/R42 冲突），W4/W5 以本文档为唯一权威（W4=Pre-PR审计、W5=知识图谱完整性，代码标签已对齐），KNOW_HOW_WHY→KNOW_YOUR_WHY 拼写修复；④finish 步骤表对齐代码实际 10 步（W3=[5/10]），driver 13步→14步，make check 超时不再误记 PASS（returncode None/负值→TIMEOUT）；⑤submission 7 处 subprocess 超时兜底（create-pr/list-prs/monitor-review/ci-status/trigger-ci），闭环校验 fail-open 改为显式告警；⑥conan_verify G2 镜像注入增加 .bak 备份+崩溃恢复；⑦R43 死链修复（→iron-rules.md），W5 草稿检查命令支持双命名（DRAFT-*.kv 与 E###-draft-*.kv），知识图谱规模声明改为以 index.tsv 为准；⑧文档层同步修复由配套 PR 完成（iron-rules 补 R41-R43 详解、CONTRIBUTING/KNOW_YOUR_WHY 对齐 v12.2、ADAPTATION_GUIDE W4/W5 互换修正等 13 项）；铁律 43 条不变；v12.2→v12.3*

*SKILL.md v12.4 — 2026-08-20 — 知识库治理工具化（借鉴 OpenViking 设计思想，纯规则零 LLM 实现）：①category 受控词表（scripts/ohc/kb_taxonomy.py，核心词 ~55 + 别名 ~200，组合词自动拆分，长尾保留渐进收敛）——存量 319 条已归一（278 种写法→229 种组合），graph add/promote 写入关口自动归一化，validate 新增 C13 词表 lint；②validate 新增 C14 编号连续性检查（id/文件名一致性 error 级，空洞如 E257 warning 级提示复用）；③新增 draft-review 预审辅助工具（FTS5 粗筛 + signature 字面量重叠/keyword Jaccard 精排，三态建议+空壳草稿标记）——**草稿仍按原有方式产生，纳入正式库决策权保留在人工审核**（用户约束），工具仅输出相似度证据加速判断；④engine 新增 --trace 检索轨迹（Phase A 候选分/B 命中明细输出到 stderr，调试误匹配）；⑤模板 _template.kv category 注释列出受控词表；v12.3→v12.4*

*SKILL.md v12.5 — 2026-08-20 — 预扫描全量补齐 + 知识库动态利用闭环：①`prescan` 独立命令（评估/选型阶段可单独扫描源码，规则文件自动发现，--json 供 AI 消费）；②hit_count 闭环回填（命中自动累计写回规则文件，行级更新保留注释；--no-writeback 只读模式）——原"纸面闭环"变真；③规则集 16→24 条，补 linking/build-system/shell/libc 域（dlopen 硬编码路径、构建机 rpath、CMake 绝对路径 DESTINATION、config.guess 过期提示、gettext 宏、bash 专用语法、#!/bin/bash shebang、__GLIBC__ glibc 专用宏），全部挂 kb_ref；④**知识库动态派生规则**：E 条目 .kv 含 prescan_pattern 字段即在 PreScanner 运行时自动派生 PSCAN-KB-{id} 规则（示范：E013 dlopen API / E019 dlopen 绝对路径 / E037 bash shebang）——知识库增长即扫描能力增长，无需改规则文件；修 shebang 误判为注释的漏报、规则 ID 撞名；⑤engine 命中回写 metrics_last_used（激活沉睡度量字段，知识使用反馈）；⑥字段白名单/模板同步（prescan_* 可选字段）；v12.4→v12.5*

*SKILL.md v12.6 — 2026-08-20 — 「又快又好」六杠杆 + 社区本地优先架构：**架构原则：所有能力本地可跑（贡献者单机完成全流程）、git 是唯一同步协议（语料/度量/知识随 PR 汇聚）、CI 仅作干净复现门禁**。L1 配方首稿检索（recipe-search：catalog 索引 2280 配方，相似度=名称0.45+构建系统0.30+依赖0.25+补丁加成；finish 成功自动 upsert → 社区配方库成长即生效）；L2 本地 ccache（OHC_CCACHE=1 显式开启，CCACHE_DIR=~/.ohc-ccache 隔离+5G 限额；autotools 环境注入/cmake launcher；**G0/W3/conan-verify 验证期无条件 CCACHE_DISABLE=1——本地缓存绝不影响验证结果，保证 CI 干净可复现**，红线）；L3 handoff 状态文件改事务式 fcntl 锁（读-改-写全程锁内，修 P1 并发丢失更新，自测验证 60/60）+ resolve-deps --batch 拓扑分层并行排程；L4 engine 命中处方完整注入 HANDOFF（方案/说明/命令[auto]/验证/兜底/关联文档，不再只用单字段）；L5 tests/test_smoke.py 冒烟层 + selftest 命令（9 用例含 P0 路径防回归、锁并发、taxonomy 幂等、engine 已知签名回归）；L6 kb-report 本地质量月报（活跃/陈旧/未命中采购清单，--scan-logs 对本地构建日志逐条跑 engine 找知识盲区）；v12.5→v12.6*

*SKILL.md v12.7 — 2026-08-20 — 垃圾拦截误伤审计与修复（CI 误拦截防护）：审计 JC（junk_check：JC1 状态文件/JC2 二进制/JC3 tarball/JC4 临时产物/JC5 archives 隐藏文件白名单/JC6 W2 原子性）与 KC（knowledge_check：草稿泄漏/占位符/非标准字段/index 一致性）对 v12.5-v12.6 新特性的交互，修复三处误伤链：①build Step 2.5 自动预扫描此前默认回写 hit_count → pre-scan-rules.yaml 属框架文件（_FRAMEWORK_PATHS）→ 每次本地构建后 W2 报"框架文件混入"误拦；改为管线内 writeback=False，回填仅限显式 `prescan` 命令；②engine 命中度量直写共享 E*.kv → 并发包 PR 在同一条目合并冲突 + PR 噪音；改为 gitignored 本地 sidecar knowledge/.metrics-local.json（kb-report 兼读 sidecar 与遗留字段）；③knowledge/recipes/catalog.tsv 取消 git 跟踪（语料事实源=archives/ 随 PR 天然共享，catalog 为本地可重建缓存，--rebuild 即得），杜绝每包 PR 携带追加 diff。.gitignore 增列三项本地文件。审计确认：KC4 字段黑名单为行首锚定（prescan_pattern 安全）、JC5 对 .pre-scan-report.yaml 无风险（落在 $TMPDIR/builds 仓库外）、KC2 占位符 grep 不受新字段影响。v12.6→v12.7*

*SKILL.md v12.8 — 2026-08-20 — 5 PR 审计（6089/6091/6093/6096/6097）三项落地：①success 上报硬闸（result --status success 自动拉 PR 最新 CI 评论核验，非"校验通过"→拒绝写 success 降级 partial 并注明核验状态与重报路径；--no-ci-verify 显式逃生口；PR6096 教训：mcfly CI 红 cargo 不可用却报成功）；②W0b 历史经验核验（历史 notes.md 必读 + 环境语义可迁移性——"历史命令在 CI 环境逐字可执行吗"；mcfly 反例：设备 rustc 1.96 成功≠CI 无 Rust 可行；pdfsandwich 正例：设备 OCaml→tool_requires ocaml 4.14.1.1.4；历史踩坑命令必须逐项比对遵循）；③CI 能力矩阵（Rust ❌→env_unsupported；OCaml ❌系统级→tool_requires 可补；gcc/cmake ✅；冷门先实证）；④JC1 补 .bak/.orig/.rej/.ghfast-bak 备份残留模式（PR6091 教训：conandata.yml.ghfast-bak 混入，全仓库 0 先例）。v12.7→v12.8*

*SKILL.md v12.9 — 2026-08-26 — goblinrs 744 PR 采样审计落地（harness 化三件套）：①PR 创建前置硬闸 PF1-PF4（scripts/ohc/preflight.py，挂在 gitcode_pr.py create-pr 咽喉点——所有建 PR 路径不可绕过）：PF1 单包闸（JC6 前置，多包捎带拦截，#6642 四包教训）/PF2 制品闸（JC3 前置，压缩包拦截）/PF3 测试闸（L0c/R34 前置，test() 空壳 AST 检测，省一轮 CI，采样占失败 20%）/PF4 依赖闸（W1/R36 前置，requires 逐个探测 conan.cnb.cool 制品仓，缺失即拦并引导 dependency_missing 上报）；逃生口 --no-preflight / OHC_PREFLIGHT=0（与 v12.8 --no-ci-verify 命名一致）。②R44 CI 失败自诊断协议：gitcode_pr.py diagnose 子命令——解析最新失败评论，CI 报"类别: 未知"（采样占 60%）时对评论内嵌失败日志本地二次归类（10 类错误表+证据行+修复要点，--json 供 harness 消费）；submit --resume 失败 HANDOFF 与 SKILL Step7 流程串联（diagnose→修复→W3 复验→push→resume，连续 2 轮同错停损衔接 R43）。③流程串联更新：R34 补 PF3 前置、R36 止损动作补 PF4 双层强制、提交流程图更新（finish→submit→push→preflight→AI Review→CI→R44 修复循环）。v12.8→v12.9*

*SKILL.md v12.10 — 2026-08-26 — SKILL_FEEDBACK 防丢失协议（修复"建 PR(12) 与建 FEEDBACK(13) 间隙丢失"bug，R45）：旧流程三条丢失路径（CI 绿后生成前死亡→回收即永久丢；失败分支从不生成→幸存者偏差；只写本地不 commit→main 13 个文件属零星漏网）。工具化五件套：①骨架前置——PR 创建瞬间与 R42 result 草稿同步生成 feedback 骨架（ensure_feedback_skeleton，幂等，resume 补齐旧任务）；②事件累积——HANDOFF/CI 红绿/pr_created 经 _emit_submit_handoff 单一咽喉自动进 .feedback-state.json 并刷入骨架"过程事件时间线"（EVENTS 标记块，自动统计 HANDOFF/重试次数）；③终态兜底——result 写盘自动 feedback_pending_flag：缺失补骨架 + result.json 落 feedback_pending 字段供 ECS 回收前判断收割（失败任务同样产出经验）；④完成入仓——feedback --resume 闭环 rc=0 时自动 commit+push 任务分支随 PR 进 main（只推终稿防 CI 重跑；.feedback-state.json 属 JC5 未白名单文件不入仓；OHC_FEEDBACK_PUSH=0 逃生口，命名对齐 v12.8 --no-ci-verify/v12.9 --no-preflight）；⑤收割对接——post-merge 同时收割旧路径 archives/.../reports/skill-feedback.md 与新路径 feedback/SKILL_FEEDBACK_<id>.md（旧链路基本空转）。cmd_feedback 重构：骨架存在时复用同 id 同文件（不产孤儿文件），两条路径均先刷事件再校验占位符；resume 完成分支补落 status=complete（供 feedback_status/ECS 判断）。AI 唯一动作不变：终局填 4 建议占位符+效率/检视小节。测试 25 项（骨架幂等/孤儿防护/事件刷新/pending 兜底/入仓分支保护/状态闭环）。v12.9→v12.10

*SKILL.md v12.10.1 — 2026-08-27 — JC5 事故修复（lua-mimetypes 1.0 首个 v12.10 bot 任务踩中）：v12.10 把 .feedback-state.json 写进 archives/<l>/<sw>/<ver>/ 且 .gitignore 无此条目 → bot 提交进 PR → JC5 未登记隐藏文件拦截。修复三件：①状态文件迁出 archives 树至顶层 .ohc/feedback-state/<l>/<sw>/<ver>.json（_state_path 统一计算；JC5 只扫 archives/，顶层天然安全）；②_load_feedback_state 自动迁移——发现 archives 内遗留副本即读出→写入新位置→删除旧文件（worker 磁盘自清洁）；③.gitignore 加 .ohc/ 与 **/.feedback-state.json 双保险（任何位置的遗留副本永不再被 add）。FEEDBACK 报告位置不变：顶层 feedback/SKILL_FEEDBACK_<id>.md（与 knowledge 同级，随 PR 入仓）；运行时状态与报告分离——状态属 harness 私有（.ohc/，永不入 PR），报告属交付物（feedback/，闭环后入仓）。R45 文案同步修正。v12.10→v12.10.1

*SKILL.md v12.10.2 — 2026-08-27 — L0n 分支名校验全量化（CI 侧）：废除按 PR 编号分档的宽容逻辑（5200/6000 两阈值系规则上线时给存量 PR 留的活口，当前 PR 编号已 6600+ 且存量 PR 已全部关闭/适配，宽容档只剩死代码）。变更：后缀型分支（含 包名-版本 但带额外后缀，如 abc-1.0.0-ASDH）与完全不包含 包名-版本 的分支一律硬失败（L0_FAILED/branch_name_r40），不再区分 PR 编号；CI_PR_NUMBER 变量从脚本中完全移除。保留：前缀剥离（feat/fix/upgrade/任意）、+→- 版本归一化、REL/main/master/server 跳过。Git bash 7 场景模拟验证（精确/前缀/后缀/不含/main/空分支）。v12.10.1→v12.10.2

*SKILL.md v12.11 — 2026-08-29 — R46 result.json 全程生命周期草稿（0828 批量复盘 600 失败任务驱动，D 类 SUCCESS_NO_PR 140→163 唯一增长类别）：R42 草稿只在 PR 创建瞬间落盘，任务前 80% 时长（适配/构建）无保护；OHC_RESULT_OUT 未设置时草稿静默跳过（35 例 result_missing 可解释）；105 例 parse_error 疑似手写绕过校验或跨任务脏文件残留。落地四项：①生命周期草稿五挂点（init-archive=task_started / conan-init=recipe_generated / conan-verify=conan_verify_passed / finish=w3_finish_started / submit=pr_created 即原 R42），终态已写入（draft:false）不降级覆盖；②输出位置兜底 --out > OHC_RESULT_OUT > $HOME/ohpcd-ai-worker-result.json（环境变量缺失不再静默跳过）；③draft/milestone 显式标记（草稿 partial+draft:true，终态 draft:false，ECS 据此区分"中断"与"终态"，校验器强制 draft=true 仅允许 partial）；④手写/残留检测（checkpoints 末条非 result.json 即警告覆盖）。v12.10.2→v12.11

*SKILL.md v12.12 — 2026-08-29 — R42 闭环续航修正（CI/AI 双缺失驱动：自动批量任务跑完 PR 后 CI 和 AI Review 都不执行，成品变半成品，无法合入无法发布）。根因：①CI 是评论触发型（需评论 /rebuild，_monitor_ci 在 submit 会话内自动戳）——会话在 PR 创建后退出（--no-wait/预算不足/死亡）则无人触发，CI 永远不跑；②旧文案"AI Review 意见与 CI 结果由平台异步产生"在批量场景证伪——平台不接手，AI Review 不 attach；③旧退出路径只在日志里提示 follow-up，result 草稿无机器可读信号。落地：两处 --no-wait 退出路径（PR 创建后/resume 后）自动写 `milestone=loop_pending` 生命周期草稿（summary 含完整 resume 命令）+ feedback 事件 `loop_pending`；文档修正：PR 创建 ≠ 成功，成功 = 检视意见闭环 + CI 绿（success 硬闸强制）；docstring/规则行废除"平台异步"假设。worker/平台侧需求：扫描 draft:true + milestone=loop_pending（或 pr_created 停滞）的 PR 派发 follow-up（submit --resume 已支持断点续环，S8 重置重跑机制可复用）。v12.11→v12.12

*SKILL.md v12.13 — 2026-08-29 — 协议 v0.8 附录 D 对齐（AI_WORKER_PROTOCOL_v0.8.md 2026-08-29 冻结，无兼容层，缺语言字段 = PROTOCOL_VIOLATION 拒收）。0828 报告 ~20% 任务浪费在非 C/C++ 源码上（E/F/J 类 123 例）。落地四项：①新工具 lang-preflight（scripts/ohc/lang_detect.py）：checkout 后、适配主流程前强制预检——三级判定 manifest>构建系统>源码统计(≥70%) + 边界规则（C/C++ 混编按主体判不算 mixed / pybind11 绑定包判 cpp / 辅助脚本不算主体 / manifest 与统计矛盾判 mixed），不匹配自动写终态 env_unsupported + detected_language + language_evidence，匹配写 lang_checked 草稿；c↔cpp 兼容族不迁移（conan 流程通吃）；②result 新增 --detected-language + --ev-build-system/--ev-manifest/--ev-source-stats（仅 env_unsupported 允许，其余状态 CLI 层早拒 + 校验器双闸）；③校验器协议规则 4/5：detected_language 必须 §4.6 枚举（禁自由文本），language_evidence 三项必填各 ≤200 字符；④status 枚举对齐协议 §4.5：新增 bootstrap_failed/timeout/internal_error，failed_build 旧写法自动规范化为 build_failed（输出协议枚举）。测试 25/25（判定 11 场景 + CLI 匹配/mismatch + 校验规则），回归 v12.10/v12.11/v12.12 全绿。
*SKILL.md v12.14 — 2026-08-29 — 平台反馈 0829（SKILL_FEEDBACK_0829.md）四条全落地。①反馈1 CI 修复循环闭环：两处 CI FAILED HANDOFF 的『push（CI 自动重跑）』错误指引修正（CI 是评论触发型，push 不触发重跑——21/41 pr_open 卡 CI failed、19 重试仍失败的直接机制）；新增 .ci-repair-state.json 轮次计数（第 N/2 轮机器可数），<2 轮给修复+resume 续环指引，≥2 轮切换停损（上报 build_failed + 人工介入）；CI 转绿自动清零；两处 CI 失败分支自动写 loop_pending 草稿（含轮次+续环命令，worker 可 sweep dispatch）。②反馈2 检视闭环：两处 review_closure_incomplete HANDOFF 同步写 loop_pending 草稿（反馈 0829-2: 完成前必须逐条处理，handle-review-opinion 逐条 accept/reject）。③反馈3 pr_url 统一 /merge_requests/N（submission.py 两处 + result_report.py fallback，共 3 处，新任务源头即规范）。④反馈4 push 后状态刷新：CI 由 resume 自动评论 /rebuild 重触发；AI 检视重跑机制待平台 webhook 联动（分工对接中，SKILL 侧不发明命令）。测试 16/16 + 回归 v12.12(5)/v12.13(25) 全绿。
*SKILL.md v12.15 — 2026-08-31 — SKILL 优化反馈 0831 落地。P0-1 预算耗尽（76 例 unknown）三件套：①新命令 budget-check（scripts/ohc/budget.py）三态检查，exhausted 自动写终态 timeout（协议 §4.5 枚举；error_detail 含已完成里程碑摘要 + finish --resume/reset-rerun 续跑命令，平台按 retry_context 续跑）；②R46 生命周期草稿写前自动查预算，超限升级终态 timeout（防 4h 被杀后停在 draft:true 被平台归一化 unknown——76 例根因）；③预算 OHPCD_BUDGET_MINUTES env>默认 240，起点=feedback 时间线首事件。动态预算（小4h/中6h/大8h）上限在平台侧——SKILL 侧仅预算内主动收尾，无法延长硬杀。P0-2 registry 重试：依赖索引 git fetch 退避重试 3 次（10/30/60s）再判 unreachable（凹晨抖动 111 例误拒）；opendesk 模板步骤（n_96yik）在 agent 平台侧非 SKILL 管辖——瞬时错误 retry 上报建议转 worker/模板侧。P1 语言字段（9 例违规）：v12.13 校验硬闸已闭环，违规源于旧版部署/手写绕过 CLI——R47 补 lang_hold激励说明（带 detected_language → 挂起等生态非失败），终态上报必须走 result 命令。测试 17/17。
*SKILL.md v12.16 — 2026-08-31 — SKILL 优化反馈 0831（修订版：P0-1 归因修正，边界双方对齐）。平台侧已实施动态预算（attempt 递增 1.0/1.5/2.0× 上限 12h，dispatch 下发 OHC_TASK_DEADLINE + OHC_TASK_BUDGET_SEC）；SKILL 唯一配合项 = 预算接近耗尽时主动收尾。①budget 判定源切换到平台真实 env（deadline 绝对时刻优先 > budget_sec > 旧 OHPCD_BUDGET_MINUTES > 240 兜底）；②耗尽上报格式对齐平台 retry_context.resume（已就绪）：status=failed + error_type/error_code 双写 budget_exhausted（勿报 unknown）+ checkpoint_steps 结构化数组（已完成里程碑= 续跑断点不丢成果）+ error_detail 续跑命令；③result 命令新参 --error-code（受控白名单 budget_exhausted，仅 failed 场景）/ --checkpoint-steps，校验器强制 budget_exhausted 必带 checkpoint_steps；④resume/reset-rerun 计时刷新（起点取最后一条 task_started + submit --resume 入口刷新事件，防旧时间线误杀续跑）。闭环：平台给足预算 + SKILL 主动收尾上报 → 大库任务要么预算内完成，要么断点续跑接力。测试 24/24。

*SKILL.md v12.17 — 2026-09-01 — 主编反馈审计批次（20 份 SKILL_FEEDBACK 全量核验后落地）。五项框架修复：①PF0 str/str 崩溃（3 份反馈被迫 --no-preflight）——preflight.run_preflight 入口统一 Path() 包装；②submit git commit 容错补 git 2.45 措辞 `no changes added to commit`（5 份反馈踩中）；③create-pr 假超时（ki18n"第4次"/knewstuff"第3次"）——POST 失败延时 15s list 复核防重复建 PR + 成功后回写 .submit-state.json（ktextwidgets PR#7104 手动路径断链教训）；④conandata file:// 残留（8 份反馈，gulkan 被 W4 判 P0）——build_and_test.sh 预下载重写前备份至 .build-cache/predl_cache + trap EXIT 还原（备份不入归档树避开 JC1）；⑤.ghfast-bak 污染（websocketpp PR#7052 假失败）——conan_verify 崩溃恢复加守卫（仅当前含 ghfast.top 才回滚，陈旧 .bak 直接清理）+ finally 删 .bak。两项规则决议：R8 三方口径统一（iron-rules.md 为唯一权威：patches/ 默认禁止平台宏+例外须 PR 说明，同步 SKILL.md §1.3 与 review-memory.md，ding-libs PR#7133 吃 High 意见根因）；新增 R49 依赖注入私有 prefix（asterisk-srtp 反馈建议的"R44"因编号被 v12.9 占用改编号，知识已入库 E524）；铁律计数 43→49 修正（R44-R48 此前未计数）。iron-rules.md 补齐 R39/R40/R44-R49 共 8 节详解（此前 SKILL.md 声称"详解见"但缺）；audit-prompt.md 增门禁阻断性分级表（ki18n：L5 存量遥测不阻断被误判 P1 引发整轮复审）。已核验无需动作：预下载连字符正则已修（正则注释明确）；E212/E214-216/E327/E328/E332(→E524) 知识已入库；graph validate 540 条全一致。backlog 另立：KF6 模板（ktextwidgets/knewstuff 双份反馈要求同构六件套）、PF4 别名解析、finish 断点续跑、Worker 健康检查、AI Review disputed 机制、知识补充（asio/boost≥1.88 经典 executor 兼容层、autotools configure 重执行 getcwd 失败草稿转正、toybox coreutils 参数差异对照表、HMDFS 权限归一化实测表 700→760 更正）。v12.17b: R8/R49 规则 harness 化——preflight 新增 PF5 补丁平台宏闸（patches/*.patch 新增行含 __OHOS__ 即拦截，上下文行/存量豁免）与 PF6 依赖注入前缀闸（environ 读 SYS_PREFIX 或引号包裹 /usr/local 字面量即拦截，参考配方 DEFAULT_PREFIX+~/usr/local 形态豁免），规则违反从"读文档自觉"升级为"提交前机械拦截"。v12.17a: 20 份反馈文件已清理（内容沉淀于本条日志+知识图谱，git 历史可查）。v12.16→v12.17
*SKILL.md v12.17 — 2026-09-02 — 心愿单评估与改进报告 0902 SKILL 行动项（S1-S4）落地。S1 空回执修复（208 例最大黑洞）：submit 六草稿挂点显式传 pr_url；CI 绿自动 success 上报显式补全四必填项（pr_url/pr_number/branch/commit_hash，源=submit-state+git HEAD）；去掉 OHC_RESULT_OUT 硬依赖（result 自带 HOME fallback，串扰机也落盘）；--no-ci-verify 仅限 submit 实证绿分支（防通道抖动误降级 partial；手动上报守门保留防 CI 红谎报）。S2 回执防损（~124 例 parse_error）：result 写后回读 json.loads 自检，坏则重写一次，仍坏 rc=1 阻断（stdout 完整 JSON 透传 v12.11 已有）。S3 停止自行预算判定（6 例 budget 自裁）：240 兜底/OHPCD_BUDGET_MINUTES 退役，仅平台 env 存在时判定，皆无恒 ok。S4 修复轮聚焦：CI 失败诊断优先 conan 依赖类（60%）次编译链接类（32%），覆盖 92%。测试 27+13。
*SKILL.md v12.18 — 2026-09-02 — v12.17 后系统性自审加固（H1-H3，工具层）。H1 回执原子写：result.json 改 tmp+os.replace 落盘——半写状态被平台读到即 parse_error（~124 例成分），原子替换保证任何时点读到完整文件；写后回读自检（v12.17 S2）保留作二道防线。H2 conan 网络特征重试：conan 命令 stderr 命中网络类特征（reset/timeout/SSL/5xx/unreachable/DNS）时退避 15/30s 重试至 3 次——与依赖解析 git fetch 重试（v12.15，111 例 registry 抖动）补齐对称面；非网络错误（缺包/配方错）不盲目重试。H3 串扰机入口自检：ohc-run 每命令入口比对 OHC_PROJECT_DIR 与脚本所在项目（独立向上找 SKILL.md，不依赖 find_project_dir 的 env 优先）——不一致时 stderr 警告（报告 8.4: 4 台机器 36% 回执缺失集中的会话残留场景）。核查确认安全面：result stdout JSON 透传为无条件分支（env 缺失场景生命线）；CI 监控轮询失败仅延长等待不误判红。测试 v12.18 新 10/10，回归 37+15+5+25+16+27+13 全绿。
*SKILL.md v12.19 — 2026-09-02 — 自审遗留项收尾（feedback 并发修复 + 测试资产固化）。feedback 时间线跨进程安全三层：①record_event 读-改-写整体进 O_EXCL 自旋锁（stale 30s 接管，超时 10s 降级 CAS 合并写——写前复查事件数，他者已写则重读合并，覆盖窗口缩至两条指令间）；②状态文件原子写（tmp+os.replace，Windows 下 replace 遇并发读者 PermissionError 短退避重试 4 次后直写兜底）；③load 读侧瞬态重试（30ms 退避重读，防把瞬态当空状态返回导致回写清空时间线）。实测 4 进程×50 事件并发丢失率从26% 降至 <1%（Windows 杀软环境噪声；Linux worker 上 POSIX rename 语义完备零丢失，实验证明 bad_json=0）。测试资产固化：tests/ 目录 9 套 155 断言（v12.10-v12.19，相对路径 + run_all.py 一命令全回归）。工作区 libxext 残留已还原。
*SKILL.md v12.20 — 2026-09-03 — 7,870 PR 全量评论/检视审计落地（25,616 CI 失败 + 21,151 行级检视 + 11,736 真人评论，语料与报告 ~/tmp/pr_crawl 留档）。preflight 扩至 PF1-PF9+R52：①PF5 扩面堵 R8 绕道（conanfile 新增行 -D__OHOS__/replace 注入，64+27 例）；②PF7 源URL闸（R39 前置：镜像黑名单 14 域/http/file://泄漏/绝对路径/Debian 重打包/gitcode·gitee 搬运，R39 1,061 条违规 90%+ 静态可拦）；③PF8 配方静态闸（R38 commands.json schema/存在性 + L0p settings 四项 + L0m slug/version 一致，705+193 条）；④PF9 分支/路径闸（L0n ~550 + No-packages 490 条）；⑤PF3 扩面（test_package 测试源文件 + MANIFEST 齐全非空，L0c/L0e ~860 条）；⑥R52 审计一致性交叉校验（审计 pass vs 硬闸命中 → 审计失真一票否决，#2204/#4237/#4321）。规则新增：R51 上游测试三步法（真人评审第一拒绝原因"硬性不通过"495 次，SKILL 此前零覆盖）；R52 审计证据一致性。主编重编号：R49 冲突修复——iron-rules R49（依赖注入 prefix）保留，SKILL.md 重复的"回执完整性"重编号 R50 并补入 iron-rules 详解；铁律 49→52（SKILL/iron-rules/CONTRIBUTING 三处对齐）。数据验证：门禁路线时间演进实证（preflight 前置门禁落地后 CI 门禁类失败 529→65 条/PR段）；预计新闸+扩面可在建 PR 前拦截 ~60% bot 检视意见量与 ~2,500 条/轮门禁失败。审计模板门禁分级表同步 PF7-PF9/R51。测试：test_v1220 新套件（新闸行为级 14 断言），run_all 全回归。v12.19→v12.20*
*SKILL.md v12.21 — 2026-09-03 — 全仓构建系统普查落地（3,477 配方：CMake 27%/Autotools 24%/Make 21%/无构建族 26%/Meson 4.8%）。①新模板 conanfile-headeronly.py.tmpl（无构建/打包族三变体：header-only 库/数据资源/脚本工具，普查 26% 配方此前零模板），conan_recipe/init_archive 注册 headeronly；②recipe-search 分类器扩 headeronly/copy（catalog 重建救回 464 配方，构建系统 0.30 相似度权重恢复命中）；③build-systems.md 补四节：Meson 详解（166 配方此前仅一行表格：交叉三元组 host_machine=linux+musl sysroot、wrap-mode=nodownload）、无构建/打包族（§12，R34/R51 同样适用）、QMake-Qt5 存量要点（14 例全存量，新任务不再产生）、Python C 扩展 setup.py build_ext（6 例存量+python-gssapi 系新任务：交叉 CC/LDSHARED 覆盖、plat-name、conan 依赖并入 CFLAGS）。长尾不建模板（QMake/Go/Rust/JVM 已被 R47 挡在门外或纯存量），防模板库通胀。*
*SKILL.md v12.22 — 2026-09-03 — 知识库 metrics 闭环接线（构建成败自动回写，置信度数据从 4% 覆盖起步积累）。背景：kb_metrics.record_result 唯一调用点在 driver._error_recovery 的 auto-retry 窄路径，且直写共享 knowledge/graph/E*.kv——每个包 PR 携带知识文件 diff、并发 PR 在同一条目必然冲突（v12.6.1 sidecar 设计修正所指问题在 driver 旧代码中残留）。三层落地：①engine sidecar v2 结构升级（.metrics-local.json：{entries:{eid:{last,s,f}},pending:[eid]}，兼容 v1 顶层 {eid:date} 读取；_touch_metrics 命中即入 pending；tmp+os.replace 原子写）；②driver 记账改造——_error_recovery 两处 record_result 直写 .kv 改为 engine._record_outcome（sidecar 即时记账+移出 pending，auto-retry 成败语义不变）；三个终局结算出口：run() 全绿 settle(True)、_emit_handoff 失败 sys.exit 前 settle(False)、build_cli RuntimeError 兜底 settle(False)，幂等（pending 空早退）——G0 预扫描命中/worker 手动修复后 RESUME 绿/auto-retry 未覆盖的命中路径全部纳入闭环；③kb_report._parse_kv_metrics 适配 v2（last/s/f + hits_success/hits_fail 列，v1 字符串与 .kv 遗留 metrics_* 字段兜底）。效果：修复成功/失败结果不再进 PR diff（PR 污染归零）；540 正式条目的 confidence 数据可随构建自然积累，为 kb_metrics 低置信度剪枝提供数据基础。tests/test_v1222.py 21 断言（sidecar v2 写入/v1 迁移/记账/结算幂等/driver 无 kb_metrics 引用防回退/kb_report v1-v2 兼容）；test_v1220（PF 闸）与 test_v1221（构建普查）为 worker 环境套件（硬编码 worker git 路径），本机环境性跳过。
