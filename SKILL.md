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
SKILL_ROOT="$(dirname "$(find "$HOME/.opendesk" -name "SKILL.md" -path "*openharmony-compile-agent*" 2>/dev/null | head -1)")"
```

> `ohc-run.py` 内部自动定位项目根目录（`find_project_dir()`），不需要手动 `export` 环境变量。
> **R13**: 用完整路径调用，如 `python3 $SKILL_ROOT/scripts/ohc-run.py build ...`。不要用相对路径 `./scripts/xxx`。

### §0.1 协作模式（⭐ 默认生效）

本 skill 默认以**协作者模式**运行，基于 Git + GitCode PR 协作。详见 `CONTRIBUTING.md`。| 模式 | 触发方式 | 职责 |
|------|---------|------|
| 协作者（默认） | 直接使用 | 编译软件、提取知识、生成 conanfile.py、创建分支并提交 PR |
| 主编 | `OHC_ROLE=editor` | 审核 PR、合并知识、重建索引 |

**协作者 Git 铁律（违反=越权）**：
- ❌ 不推 main，不走捷径：创建功能分支 `git checkout -b feat/{软件名}-{版本}` → push → GitCode PR
- ❌ 不碰基础设施：`SKILL.md`/`references/`/`templates/`/`scripts/`/`ci/`/`index.tsv`/`SUMMARY.md` 只读
- ❌ 不碰他人归档目录
- ✅ 新增知识用 `ohc-run.py graph add E{N} --draft`

**Agent ID**：自动获取 4 位随机标识（如 `A7F3`），用于分支后缀和草稿归属，可通过 `OHC_AGENT_ID` 预设。

### §0.2 适配工作流规程（⭐ 强制执行）

以下 4 条规程在每次软件适配中**强制执行**，违反=流程缺陷：

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

**W2 — PR 原子性**
每个 PR **只允许包含一个配方软件及其知识图谱草稿**。如果对 SKILL 框架本身有修改（`scripts/`/`templates/`/`ci/`/`SKILL.md`/`references/` 等），**必须单独提交 PR**。
> 混合提交=审核困难+回滚困难。配方 PR 和框架 PR 的审核标准不同。

**W3 — 本地 CI 模拟**
每个配方适配完成后，**必须**按照 CI 模式本地模拟验证通过后再提交 PR：
```bash
# 使用 CI 同款脚本验证
bash ci/conan/setup.sh                          # 环境初始化
bash ci/conan/build_and_test.sh <软件名>/<版本>  # conan create + L4/L5
```
> 本地不过=CI 必挂。不要把已知失败的配方推给 CI。

**W4 — 知识图谱完整性检查**
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
# → 内含 13 步：init→patches→pre-scan→configure→make→install→staging→conan-init→conan-verify→finish→...
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

# Step 3: 收尾（6 步自动）
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed|archived
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

### 1.2 铁律摘要（33 条，违反=bug）

| # | 规则 |
|---|------|
| R1-R5 | **参数/补丁/链接/源码**：参数最少化(只需`--prefix`)；探索阶段不生成.patch(改源码+记notes)；补丁只用`refresh-patch --auto`；危险库静态编译；软链接`rm -f && ln -s` |
| R6-R10 | **源码与文件**：只改源文件不改生成文件(`track-edit`)；安全弹窗先触发再测试；源码"四不"(`#ifdef __OHOS__`)；门禁FAIL禁标success；临时文件用`$TMPDIR` |
| R11-R15 | **失败与历史**：失败先查归档再动手；先匹配错误模式再修复；脚本用完整路径；脚本失败=手动模式入口；历史仅供参考不盲从 |
| R16-R20 | **协作与打包**：协作不越权(走PR)；知识先草稿(`graph add --draft`)；依赖先查预编译；禁止手动打包(用`conan create`+`conan upload`)；~~DESTDIR模式~~(废弃) |
| R21-R25 | **自检与清理**：探索结束自检零介入；finish前必须通过conan验证；平台检测优先于改生成文件；归档清理failed必删；notes.md防重复(finish自动清理) |
| R26-R31 | **Conan 配方**：系统同名库禁止动态链接(避免污染`/lib`/`/lib64`)，默认动态由Conan管理依赖链；依赖引用必须`@ohpcd/stable`；conanfile.py必须有`test_package/`；conan_verify通过才标published；conan-verify失败必须查询知识图谱；知识图谱未命中必须生成草稿 |
| R32 | **OHOS 平台兼容**：recipe 内 `settings.os` 判断必须 `in ("Linux", "OHOS")`，不能 `== "Linux"` |
| R33 | **build() 禁止依赖未定义的 shell 环境变量**：编译器/标志必须从 Conan Toolchain 或 `self.conf_info` 获取，不能裸用 `${CC}`/`${CFLAGS}` 等 shell 变量（release worker 上为空→编译静默失败） |
| W1-W4 | **适配工作流**：每次适配前同步main(W1)；PR原子性=一配方一PR(W2)；本地CI模拟通过再提PR(W3)；适配结束检查知识图谱完整性(W4) |

> 详解见 references/iron-rules.md

### 1.3 决策树

```
新三方库？
├─ registry 有记录 → ohc-run.py init-build <name> <ver>
├─ 有 URL → ohc-run.py init-build <name> <ver> --url=URL
└─ 都没有 → ohc-run.py search-url <name> <ver> → 从候选选 URL

缺依赖？
├─ 从 cmd-pkgs README 查询预编译包 → curl install.sh | sh
├─ conan 制品仓有 → conan install --requires=name/ver@ohpcd/stable
└─ 无预编译包 → 查 dependencies.md 编译顺序 → 先编依赖

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

> **⭐ R18 强化：预编译包优先原则**
> 编译过程中发现的任何依赖缺失，**必须先查 cmd-pkgs README** 和 Conan 制品仓。
> 只有两者都没有才手动编译依赖。

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
| 软件迁移/新适配 | references/migration-guide.md | 迁移或新软件适配时 |
| 构建系统适配 | knowledge/operations/build-systems.md | configure 前 |
| CI 脚本契约 | ci/conan/build_and_test.sh（内联注释） | ci/ 脚本修改时 |

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

**conan-init 后 AI 必须检查**：`requirements()`(R27 `@ohpcd/stable`)、`generate()`(R26 系统同名库静态)、`package_info()`(cpp_info.libs)、`conandata.yml`(sha256)。

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

### Step 3: finish — 6 步自动收尾

```bash
$SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed
```

| 步骤 | 内容 | 失败处理 |
|------|------|---------|
| [1/6] refresh-patch --auto | 补丁生成 | 跳过，继续归档 |
| [2/6] close-archive | 归档关闭 | exit 2 |
| [3/6] conan-verify | Conan 配方验证（⭐ v3.0） | ❌ 阻塞 |
| [4/6] finalize-archive | 清理+校验+版本索引 | 非致命 |
| [5/6] check-knowledge-gap | 知识完整性检查 | 非阻塞 |
| [6/6] gen_summary | 重新生成 SUMMARY.md | 非致命 |

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

发现 SKILL 自身问题时记录到 `reports/skill-feedback.md`。

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
| `finish` | 补丁+归档+conan-verify+CI模拟+知识+PR原子性+摘要（8 步） |
| `engine` / `graph add\|update\|validate\|promote` | 知识图谱查询/管理/草稿提升 |
| `req add\|list\|close\|validate` | ⭐ 需求图谱管理（系统能力缺口跟踪） |
| `resolve-deps [--install]` | 查询/安装预编译依赖 |
| `verify-build` / `refresh-patch` | 门禁复查 / 补丁管线 |
| `status` / `handoff` / `track-edit` | 状态恢复 / 源码追踪 |

**独立脚本**（`scripts/` 目录，不通过 ohc-run.py）：

| 脚本 | 用途 |
|------|------|
| `scripts/gen-test-packages.py` | 批量为缺 test_package/ 的配方生成测试文件 |
| `scripts/sync-recipes.py` | 从 conan 缓存同步配方到 archives/ |
| `scripts/migrate_kv_to_yaml.py` | KV→YAML 渐进迁移 |

### Pre-commit Hook（⭐ 建议安装）

```bash
cp ci/conan/hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

提交前自动检查 L0a-L0h（conanfile 语法/sha256/test源码/test()方法/MANIFEST/patch格式/环境变量依赖）。

### CI 脚本（ci/ 目录，由 Buildbot Worker 执行，纯 shell，无 AI）

| 脚本 | 用途 |
|------|------|
| `ci/conan/setup.sh` | Conan 环境初始化 + profile + remote |
| `ci/conan/build_and_test.sh` | conan create + L4/L5 检查 |
| `ci/conan/upload.sh` | conan upload 到 CNB 制品仓（仅 release） |
| `ci/artifacts/sign.sh` | GPG 签名（非阻塞） |
| `ci/conan/profiles/ohos-aarch64` | Conan 编译 profile |

---

*SKILL.md v8.9 — 2026-07-06 — 模板统一(删除重复无.tmpl模板)+Step0 checkpoint+pre-commit L0h修复(R33对齐)+§9新脚本文档
