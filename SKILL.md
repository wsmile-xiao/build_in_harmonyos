---
name: openharmony-compile-agent
description: 鸿蒙PC原生应用/C/C++三方库适配编译Agent。当用户需要将开源C/C++库适配到HarmonyOS PC平台（arm64）、编写conanfile.py配方、执行conan构建发布流水线、排查CI构建失败时触发。覆盖源码获取、依赖解析、Conan配方编写、交叉编译、制品仓发布全流程。
version: 11.4
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

**Agent ID**：自动获取 4 位随机标识（如 `A7F3`），用于分支后缀和草稿归属，可通过 `OHC_AGENT_ID` 预设。

### §0.2 适配工作流规程（⭐ 强制执行）

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

**W2 — PR 原子性 + 结构完整性（嵌入 finish）**
每个 PR **只允许包含一个配方软件及其知识图谱草稿**。如果对 SKILL 框架本身有修改（`scripts/`/`templates/`/`ci/`/`SKILL.md`/`references/` 等），**必须单独提交 PR**。
> 混合提交=审核困难+回滚困难。配方 PR 和框架 PR 的审核标准不同。
>
> **结构完整性由 `finish` step [5/9] 强制执行**（L0a-L0e 等效检查）：test_package/ 目录
> 存在、conanfile.py 存在、测试源文件存在、MANIFEST.yml 存在。不通过 → HANDOFF + exit 1。
> 历史教训：CI 审计发现 181 个结构缺失失败（115 缺测试源 + 66 缺 MANIFEST）。

**W3 — 本地编译验证（⭐ 嵌入 finish step [5/9]，HANDOFF 强制）**

> **不是散乱脚本，而是 finish 流程内部的阻塞步骤。** AI 跑 finish 时自动执行，
> 无法跳过。失败输出 HANDOFF 块（含根因+修复命令+resume 指令），AI 修复后 `--resume` 继续。

`finish` step [5/9] 内部执行：
1. **W2 结构检查**（L0a-L0e）：test_package/ 完整性 → 不通过 HANDOFF
2. **R36 依赖检查**：`conan download --only-recipe` 验证依赖已发布 → 未发布 HANDOFF
3. **conan create 编译验证**：实际运行 `conan create` → 失败 HANDOFF（含知识图谱匹配的根因）
4. **通过** → 自动写入 `.ci-result.json`（含 conan create 日志 SHA256 哈希，防伪造）

> **⚠️ 禁止手动创建或修改 `.ci-result.json`**。此文件由 finish step [5/9] 写入，
> 含日志哈希。`submit` 会验证此哈希与实际日志匹配。
> 历史教训：CI 审计发现 431 个编译失败流入 CI（55%），根因是 AI 跳过 conan create
> 验证或手动伪造 `.ci-result.json`。嵌入式 HANDOFF 从结构上消除此可能。

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

**W5 — 知识图谱完整性检查**
适配结束时**必须**检查知识图谱内容的完整性和合规性：
```bash
# 检查草稿/正式条目字段完整性
python3 $SKILL_ROOT/scripts/ohc-run.py graph validate
# 确认草稿已生成（如本次编译有新错误模式）
ls knowledge/drafts/DRAFT-*.kv 2>/dev/null
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

# Step 5: SKILL_FEEDBACK (submit 成功后自动调用，也可手动运行)
python3 $SKILL_ROOT/scripts/ohc-run.py feedback <软件名> <版本>
# 如 HANDOFF 后填写建议并验证:
python3 $SKILL_ROOT/scripts/ohc-run.py feedback <软件名> <版本> --resume
# 如 HANDOFF 后填写建议并验证:
python3 $SKILL_ROOT/scripts/ohc-run.py feedback <软件名> <版本> --resume
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

### 1.3 铁律摘要（40 条，违反=bug）

| # | 规则 |
|---|------|
| R1-R5 | **参数/补丁/链接/源码**：参数最少化(只需`--prefix`)；探索阶段不生成.patch(改源码+记notes)；补丁只用`refresh-patch --auto`；危险库静态编译；软链接`rm -f && ln -s` |
| R6-R10 | **源码与文件**：只改源文件不改生成文件(`track-edit`)；安全弹窗先触发再测试；`#ifdef __OHOS__`守卫可用但须有实质逻辑(禁止空壳stub)；门禁FAIL禁标success；临时文件用`$TMPDIR` |
| R11-R15 | **失败与历史**：失败先查归档再动手；先匹配错误模式再修复；脚本用完整路径；脚本失败=手动模式入口；历史仅供参考不盲从 |
| R16-R20 | **协作与打包**：协作不越权(走PR)；知识先草稿(`graph add --draft`)；依赖先查预编译；禁止手动打包(用`conan create`+`conan upload`)；~~DESTDIR模式~~(废弃) |
| R21-R25 | **自检与清理**：探索结束自检零介入；finish前必须通过conan验证；平台检测优先于改生成文件；归档清理failed必删；notes.md防重复(finish自动清理) |
| R26-R31 | **Conan 配方**：系统同名库禁止动态链接(避免污染`/lib`/`/lib64`)，默认动态由Conan管理依赖链；conanfile.py必须有`test_package/`；conan_verify通过才标published；conan-verify失败必须查询知识图谱；知识图谱未命中必须生成草稿 |
| R32 | **OHOS 平台兼容**：recipe 内 `settings.os` 判断必须 `in ("Linux", "OHOS")`，不能 `== "Linux"` |
| R33 | **build() 禁止依赖未定义的 shell 环境变量**：编译器/标志必须从 Conan Toolchain 或 `self.conf_info` 获取，不能裸用 `${CC}`/`${CFLAGS}` 等 shell 变量（release worker 上为空→编译静默失败） |
| R34 | **test 必须实质依赖被测包**：test_package 源文件必须调用被测包的 API / 执行被测包的二进制，禁止只打印字符串的空壳测试（CI L1e 破坏性反向验证兜底） |
| R35 | **禁止用 conan list/search 判断 binary 是否存在**：cnb.cool 搜索 API 对 binary 返回不完整（显示 "No packages found" 但实际已上传），必须用 `conan install --requires=...` 或 `conan download` 验证预编译包 |
| R36 | **依赖必须先发布再构建下游**（机械门禁）：依赖包必须先通过 release 流水线发布到制品仓，再构建下游包。未发布的依赖会导致 `--build=missing` 从源码编译，耗时且易失败。依赖链 `C→B→A` 的发布顺序必须是 A→B→C。`finish` step [5/9] 和 CI L0i 均 Hard Fail（不止警告） |
| R37 | **版本号 = 上游版本 + 适配修复后缀**：首次适配用上游版本 `X.Y.Z`，修复适配问题后加后缀 `X.Y.Z.N`（N 从 1 递增）。原因：cnb.cool 制品仓不支持同版本多 revision 并存，必须用版本号区分 |
| R38 | **命令行工具必须声明 commands.json**：如果构建产物包含可执行文件，必须在**软件级别**目录下创建 `commands.json`（hicmd 格式）。库类型不需要。CI 门禁 L0k 自动校验 |
| R39 | **源码 URL 必须为官方源**：conandata.yml 中 URL 必须指向官方正式源（GitHub releases、官方网站）或权威镜像源，禁止个人 fork/网盘/不明 CDN。CI 自动添加镜像 fallback |
| R40 | **深度适配库需验证适配完整性**：图形渲染/UI框架/多媒体/外设/系统底层类库，编译通过≠适配完成，需检查实质性平台适配代码（非 stub/return 0） |
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
| **G3** | 系统同名库隔离 (R26) | readelf -d 检查系统同名库未输出 .so 到系统路径 |
| **G4** | 产物完整性 | bin/lib/include 产物检查 |
| **L2/L4/L5** | smoke test / 安全扫描 / 产物基线 | `--version`可执行 / NX·PIE·RELRO / SHA256 基线对比 |

**知识图谱集成（R30/R31）**：G2 失败时自动调用 `run_engine()` 匹配 E-entry。命中→展示根因+修复命令；未命中→自动生成 `knowledge/drafts/DRAFT-*.kv` 草稿。G2 通过 = 可标记 `published`（R29）。

### Step 3: finish — 9 步自动收尾

```bash
$SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed
```

| 步骤 | 内容 | 失败处理 |
|------|------|---------|
| [1/9] refresh-patch --auto | 补丁生成 | 跳过，继续归档 |
| [2/9] close-archive | 归档关闭 | exit 2 |
| [3/9] clean-verify 重建 | 干净构建验证（非阻塞，平台限制可跳过） | 非阻塞 |
| [4/9] conan-verify | Conan 配方验证（如 Step 2.6 已通过且配方未修改则跳过） | ❌ 阻塞 |
| [5/9] W2结构+R36依赖+W3编译 | 结构检查(L0a-L0e)+依赖发布(conan download)+conan create，写入.ci-result.json(含日志哈希) | ❌ 阻塞 (HANDOFF) |
| [6/9] commands.json 检查 (R38) | 命令行工具声明验证 | 非阻塞（警告） |
| [7/9] finalize-archive | 清理+校验+版本索引 | 非致命 |
| [8/9] check-knowledge-gap | 知识完整性检查 (W5) | 非阻塞 |
| [9/9] gen_summary + PR 原子性 | 重新生成 SUMMARY.md (W2 检查) | 非致命 |

> **W4 Pre-PR 独立审计不在 finish 内部**，在 `submit` 内部作为前置检查执行。
> 流程顺序：`finish`（含W2+W3）→ `submit`（前置检查W4→git push→创建PR→**AI Review 监控**(5阶段)→**检视意见闭环校验**→**CI 监控**→**SKILL_FEEDBACK 自动生成**）。
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

**HANDOFF 强制**：生成后检查 `(请填写)` 占位符，有残留则 emit HANDOFF（step_failed=feedback），AI 填充建议后 `--resume` 验证完整性。状态文件 `.feedback-state.json` 记录 feedback_id。

> 模板: templates/skill-feedback.md

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

---

## §5 知识图谱

### 5.1 目录结构

```
knowledge/graph/           # 结构化数据
├── index.tsv              # 主索引（211 条目）
├── principles.kv          # 编译原则（20 条）
├── pre-scan-rules.yaml    # 预编译风险扫描规则集
├── E001.kv ~ E211.kv      # 错误模式条目
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
ls knowledge/drafts/DRAFT-*.kv

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

---

## §9 工具一览

### AI 工具（scripts/ohc-run.py，本地开发环境使用）

| 子命令 | 用途 |
|--------|------|
| `build` | 14 步编译驱动（含预分析+conan 配方生成+验证）★ 主入口 |
| `init-build` | 下载/解压/骨架/环境/依赖解析 |
| `pre-analysis` | ⭐ 鸿蒙PC平台适配预分析（图形/音视频/系统集成/平台代码扫描） |
| `conan-init` | 生成 conanfile.py + conandata.yml + test_package/ ⭐ |
| `conan-verify` | conan create + G0-G4 + L2/L4/L5 + 知识图谱(R30) + 草稿(R31) ⭐ |
| `finish` | 补丁+归档+clean-verify+conan-verify+W2结构+R36依赖+W3编译(阻塞,HANDOFF)+知识+摘要（9步）⭐ |
| `engine` / `graph add\|update\|validate\|promote` | 知识图谱查询/管理/草稿提升 |
| `req add\|list\|close\|validate` | ⭐ 需求图谱管理（系统能力缺口跟踪） |
| `resolve-deps [--install]` | 查询/安装预编译依赖 |
| `verify-build` / `refresh-patch` | 门禁复查 / 补丁管线 |
| `status` / `handoff` / `track-edit` | 状态恢复 / 源码追踪 |
| `search-url` / `submit` / `review` / `post-merge` / `feedback` | URL搜索 / **PR提交(W4→AI Review→CI→SKILL_FEEDBACK,HANDOFF,--resume)** / 主编审核 / 合并后索引 / **流程终态反馈(HANDOFF,--resume)** |
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
