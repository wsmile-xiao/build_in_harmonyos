# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_708efef1.md`
> 说明：背景/情况小节中带「自动采集失效，已按实修正」标注的字段为人工纠正值，
> 对应的采集缺陷在「自动化补全」节逐条给出文件与行号。

---

## 背景

- **软件名称**: zgen
- **版本**: 0-20150919
- **构建日期**: 2026-09-21
- **构建系统**: custom（纯 Zsh 脚本，无 configure/Makefile/CMakeLists.txt；init-build 识别为 unknown）
  —— *自动采集失效（渲染成 `{BUILD_SYSTEM}`），已按实修正*
- **上游仓库**: https://github.com/tarjoilija/zgen —— *自动采集失效（"(未知)"），已按实修正*
- **适配路径**: 路径 B（含 1 个可移植性补丁）—— *自动采集失效（"路径 A，无补丁"），已按实修正*
- **补丁数量**: 1（`patches/0001-zgen.zsh.patch`）—— *自动采集失效（0），已按实修正*
- **编译依赖**: 无（运行依赖：zsh 解释器；git 仅联网子命令需要）
- **最终状态**: 成功（本地全门禁通过，PR 待建）

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 首次用 `github.com` 直连超时，改用官方归档域 `codeload.github.com` |
| lang-preflight | 语言预检 | 完成 | detected=other，按检测结果以 `--lang other` 如实申报 |
| build | 编译构建 | 成功 | 无 native 构建步骤；仅应用 shebang 补丁 + 复制脚本 |
| conan-verify | 配方验证 | 通过 | G1 PASS / G2 PASS（第 3 次通过，前两次见「失败与问题」） |
| finish | 归档收尾 + W3 | 通过 | `.ci-result.json` exit_code=0；L1 pass、L4 pass、JC/KC 0 错误、pass rate 100% |
| submit | PR 提交 | 手动完成 | 见「AI 检视结果」 |

### 失败与问题

| # | 阶段 | 现象 | 根因 | 处理 |
|---|------|------|------|------|
| 1 | init-build | `Remote end closed connection without response` | 本机到 `github.com` 直连不可达 | 换用 GitHub 官方归档域 `codeload.github.com`（仓库 286 处先例，不在 PF7 黑名单） |
| 2 | conan-verify G2 | `BadZipFile: File is not a zip file` | 命中 **E483**：codeload 快照 URL 末段是 commit id，`get()` 据此猜格式 | 按 E483 推荐方案在 `get()` 显式传 `filename=` |
| 3 | conan-verify G2 | `ZGEN_INIT: parameter not set` | 自写测试脚本设了 `setopt no_unset`，与 zgen 探测未设变量的实现冲突 | 去掉 `no_unset`，保留 `emulate -L zsh` |
| 4 | conan-verify G2 | 沙箱目录落在 `test_package/` 内，污染归档树 | 未设 layout 时 `self.build_folder` 即 recipe 目录 | 改 `tempfile.mkdtemp()` + `finally` 清理 |
| 5 | **finish W3（阻塞）** | `Patch file does not exist: patches/0001-fix-shebang-for-ohos.patch` | finish step1 的 `refresh-patch --auto` 用固定自动命名重生成补丁，删掉了人工重命名的文件，`conandata.yml` 的 `patch_file` 悬空 | 统一跟随工具命名 `0001-zgen.zsh.patch`，并同步 conandata/manifest/notes/README 引用 |

### 知识图谱使用情况

- **引用知识条目**: E483（codeload 无扩展名 URL → BadZipFile），推荐方案可直接落地，一次修复到位
- **新增知识草稿**: 1 条 —— `knowledge/drafts/E543-draft-27D5.{kv,md}`
  （纯 Zsh 生态包在 lang-preflight 中零覆盖 + zsh 打包范式），`draft-review` 判定 `create`（无高相似条目），
  `graph validate` 全绿
- **引擎命中情况**: 2 次有效查询（E483 命中并解决；lang-preflight 场景查重命中 E404/`DRAFT-dshlibs-…` 但均非同一问题）
- **测试统计**: 总计 26，通过 26，失败 0，跳过 0（上游测试 N=0，已附清点证据）
  —— *自动采集失效（全 0），已按实修正*
- **未覆盖的错误模式**:
  1. 纯 Zsh 项目（`.zsh` + 无扩展名补全函数 `_<命令>` + 无构建系统）的语言判定与打包范式
     —— 本次已补为草稿 E543-draft-27D5；
  2. `refresh-patch --auto` 重生成补丁与 `conandata.yml` 中人工命名不一致导致 W3 阻塞（问题 5），
     属流程耦合缺陷，已写入本报告「SKILL 设计改进」，未单独立条目（非源码/平台问题）。

### AI 检视结果

- **检视阶段到达**: 未到达（本报告在建 PR 之前定稿并随同一 commit 提交，避免 PR 建立后再推 commit 作废正在进行的检视）
- **变更摘要评估**: 尚未产生
- **检视意见数量**: 0（尚未开始）
- **检视意见处理**: PR 建立后按机器人意见逐条 accept（修复并标记已解决）/ reject（回复理由），
  不在检视进行中推非必要 commit

### CI 结果

- **本地 CI 模拟 (W3)**: 通过 —— `.ci-result.json` `exit_code=0`；
  `L1_RESULT=pass`（test_package executed）、`L4_RESULT=pass`（patches clean）、
  `L2/L5=skip`（无 bin/ 与二进制产物，脚本包预期如此）、`KC_ERRORS=0`、`JC_ERRORS=0`、pass rate 100%
  —— *自动采集失效（"未知"），已按实修正*
- **远程 CI (PR 校验)**: PR 建立后触发，本报告定稿时未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2（W3 补丁路径悬空 1 次；feedback 占位符校验 1 次）
- **重试次数**: `conan-verify` 3 次（2 次失败 → 1 次通过）、`finish` 2 次（1 次 W3 阻塞 → 1 次通过）
- **关键瓶颈**:
  1. finish step1 与人工补丁命名的耦合（问题 5），单独消耗 1 轮完整 W3（含 conan create 与门禁全跑）；
  2. 语言预检对 zsh 零覆盖，需先零副作用地调 `detect_language` 预判，才敢跑 CLI（否则会被写入终态 `env_unsupported`）；
  3. conan-init 对无构建系统项目仍套 autotools 模板，配方/测试需整体重写（非增量修改）。
- **耗时较长的步骤**: `conan-verify`（每次含完整 `conan create` + test_package）与 `finish`（内含二次 conan-verify + W3 全量门禁），
  两者构成本次全部三轮返工成本；源码本身只有 4 个文件、无编译耗时。

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-21T20:03:52 | skeleton_created | result_partial |
| 2026-09-21T20:03:52 | lang_checked | detected=other 与任务 other 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`finish` step1 的 `refresh-patch --auto` 应与 `conandata.yml` 双向对齐**（本次唯一阻塞项，代价 1 轮完整 W3）。
   `scripts/ohc/finish.py:131-135` 无条件调用 `refresh_patch_auto`，它按 `NNNN-<源文件名>.patch` 重生成补丁并清空
   `patches/`；一旦 AI 曾把补丁改成语义化文件名并写进 `conandata.yml`，就会出现
   `ConanException: Patch file does not exist`，且报错发生在 W3（最贵的一步）。
   建议二选一：①重生成前先读 `conandata.yml` 的 `patch_file` 复用既有文件名；
   ②文件名变化时自动改写 `conandata.yml` 的 `patch_file` 并 log_warn。
2. **`lang-preflight` 对「解释型脚本包」应给可继续信号，而不是直接终态**。
   `scripts/ohc/lang_detect.py:273` 默认任务语言 `cpp`，`:40` 的 `LANG_ENUM` 没有 shell 族（只有 `bash`），
   `:47-51` 的 `_EXT_LANG` 没有 `.zsh`。结果：纯 Zsh 项目 → `detected=other` + “无源文件可统计” → exit 2 +
   自动写 `env_unsupported`。而本仓库已有 6 个同形态 zsh 包合入 main（zinit / zimfw / zsh-autopair /
   zsh-autocomplete / zsh-git-prompt / zsh-history-substring-search），规则与实践相互矛盾。
   建议：`detected=other` 且源码含 shebang 脚本/`#compdef` 文件时，输出「疑似脚本包，建议 `--lang other` 继续」
   的提示而非直接判负；并把 `shell` 纳入语言枚举（或允许 `bash` 表示 shell 族并在 evidence 写明解释器）。
3. **建议增加“先预判后落终态”的官方入口**。本次为避免污染回执，只能绕开 CLI 直接 import
   `detect_language` 做零副作用预判。建议给 `lang-preflight` 增加 `--dry-run`（只输出判定，不写 result 草稿）。

### 模板改进

1. **`conan-init` 对无构建系统项目仍回落 autotools 模板**。`scripts/ohc/conan_recipe.py:173`
   `return "autotools"  # default`，而 `:26` 已注册 `conanfile-headeronly.py.tmpl`（v12.21 的无构建/打包族三变体）。
   本次生成的骨架是 `AutotoolsToolchain` + `cpp_info.libs=["zgen"]` + `test_package/test.c` + `CMakeLists.txt`，
   对脚本包全部不可用，只能整体重写并删除两个文件。
   建议：构建系统判定为 `unknown`/`none` 时选 headeronly（脚本工具变体），并生成 `test.sh` 而非 `test.c`。
2. **`test_package/MANIFEST.yml` 模板的 `upstream_tests` 缺“上游确无测试”的合法写法**。
   当前模板强制 `- file: <TODO: 测试源文件>` 结构，而 R51 明确允许“上游确无测试 + 附清点证据”。
   建议模板内置 `upstream_tests: []  # 上游 0 项，清点证据见 notes.md` 的注释分支，避免各包自由发挥。
3. **`notes.md` 模板占位符无门禁**。模板给出 `{cmake|autotools|makefile|meson|custom}` 一类占位符，
   但 finish 全流程不检查是否被替换。建议 finish 增加一条非阻塞扫描：
   `grep -nE '\{[a-z]+\|[a-z|]+\}' notes.md` 命中即告警（与 KC2 占位符检查同构）。

### 自动化补全

本次 `feedback` 自动采集有 7 个字段失效，且数据源全部现成（manifest.yaml / conandata.yml /
`.ci-result.json` / `knowledge/drafts/` / test-report.md）：

| 字段 | 自动值 | 实际值 | 定位 |
|---|---|---|---|
| 构建系统 | `{BUILD_SYSTEM}`（占位符未渲染） | custom | `scripts/ohc/feedback.py:527` 附近的背景渲染 |
| 上游仓库 | `(未知)` | github.com/tarjoilija/zgen（`conanfile.py` 的 `homepage`/`url` 与软件级 manifest 均有） | `feedback.py:321` |
| 补丁数量 | 0 | 1（`patches/*.patch` 确实存在） | `feedback.py:295-297` 的 `patches_dir` 未指向归档 patches 目录 |
| 适配路径 | 路径 A（无补丁） | 路径 B（有补丁） | `feedback.py:305`：三元表达式两个分支都写成“路径 A”，`patch_count > 0` 分支形同虚设 |
| 新增知识草稿 | 无 | 1（E543-draft-27D5） | 草稿按 `E###-draft-<AgentID>` 命名，采集端疑似只认 `DRAFT-*` |
| 测试统计 | 0/0/0/0 | 26/26/0/0 | `test_package/MANIFEST.yml` 的 `assertion_count` 与 `reports/test-report.md` 均有 |
| 本地 CI (W3) | 未知 | 通过 | `.ci-result.json` 就在归档根，`exit_code=0` 可直接读 |

另外两处与本次强相关：

- `scripts/ohc/finish.py:337-340` `generate_summary` 抛 `'str' object has no attribute 'append'`，
  step8 每次必失败（本次两轮 finish 均复现），建议加类型防御或修复调用方传参。
- `scripts/ohc/finish.py:375-377` 仍把缺少 `packaging/` 目录报为 submit 就绪的“缺失项”，
  而 ARCHIVE-SPEC v2.0 已废弃该目录 —— 属稳定假告警，建议移除该检查项或降级为 info。

### 知识图谱覆盖

1. **命中良好**：E483（codeload 快照 URL → `BadZipFile`）根因、推荐方案、禁止写法齐全，照做即通过，
   是本次唯一一次“查表即修复”。
2. **覆盖缺口（已补草稿）**：zsh 生态在图谱中只有 E404（OHOS zsh 缺 autoload 函数，属运行期），
   缺少「立项/打包」面的条目。本次新增 `E543-draft-27D5`，覆盖：
   `.zsh`/无扩展名补全文件的判定盲区、任务语言申报口径（禁止用 bash 冒充 zsh）、
   以及 zsh 包打包范式（shebang、`share/zsh/site-functions` + FPATH、`package_id.clear()`、
   `application` + `commands.json`）。建议主编评估 promote。
3. **建议给 E483 增加 `prescan_pattern` 前移**：当前只有构建失败后才命中。
   若在 `conan-init` 阶段扫描 `conandata.yml` 的 URL 末段是否带 `.tar.gz/.tar.xz/.zip` 扩展名，
   即可在写配方时就提示补 `filename=`，把一次 `conan create` 失败提前到秒级静态检查。
4. **建议补一条「零构建系统包」的通用条目**：本次 `G0` 报“构建系统: unknown → 跳过预查询”，
   说明这类包在预扫描阶段完全没有知识可用；可把打包范式（`package_id.clear()`、
   `application` + `commands.json`、`share/` 布局、解释器 shebang 处理）沉淀为一条通用条目，
   供 26% 的无构建族配方复用。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 27D5
- **生成时间**: 2026-09-21
- **PR 编号**: （随本 PR 一同提交）
