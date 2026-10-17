# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_1595b5cb.md`

---

## 背景

- **软件名称**: reflex
- **版本**: 20241231
- **构建日期**: 2026-09-29
- **构建系统**: autotools
- **上游仓库**: https://invisible-island.net/reflex/（Thomas Dickey 维护的 flex 2.5.4 分支；发布源 https://invisible-island.net/archives/reflex/reflex-20241231.tgz）
- **适配路径**: 路径 A + 路径 B（知识库扩展赛道；新增 6 条知识草稿）
- **补丁数量**: 1（`patches/0001-skel.c.patch`，+3 行，`type: bugfix`，`platform_only: false`）
- **编译依赖**:
  - bison/3.8.2（tool_requires，提供 `YACC = bison -y`）
  - diffutils/3.12（tool_requires，`make check` 的逐字节比对）
- **最终状态**: built

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 下载源为官方 `invisible-island.net`，sha256 与声明逐字一致 |
| build | 编译构建 | 成功 | 首次即定位并修复上游 C++ 骨架守卫缺陷；`make check` + 6 种压缩模式全过 |
| conan-verify | 配方验证 | 第 1 轮 G2 FAIL → 修复后全门禁通过 | G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS；失败点是消费者脚本用了裸命令名 `sh` |
| finish | 归档收尾 | 完成 | W3 本地 CI 模拟 exit 0（阻塞门禁通过）；状态 built；`.ci-result.json` 已写 |
| submit | PR提交+AI检视+CI | PR #13879 已建，CI 已触发 | 自检仅 `packaging_present` 恒 FAIL（已知误报），按等价手工步骤完成建 PR；按流程到 PR 即停，不等待 CI/AI 检视 |

### 失败与问题

- **1**: 根因=上游 C++ 生成路径缺陷（骨架把 C-only 的 `yy_init_globals()`/`yylex_destroy()` 排在 non-C++ 守卫区块之外，C++ 输出引用 `yyFlexLexer` 成员名 → 10 处 undeclared identifier），解决方案=补丁 0001 用骨架自带 `%-`/`%*` 标记把两函数包回 non-C++ 区（C 路径输出逐字节不变，自举比对仍成立）。
- **2**: 根因=补丁落点错误（首轮把骨架补丁打在 `flex.skl`，`make check` 报 `yy_c_buf_p = NULL` vs `(char *) 0`），解决方案=发布包内 `skel.c` 与 `flex.skl` 内容分叉而 mtime 同秒（`2025-01-01 05:56`）→ make 不触发 `skel.c: flex.skl` 规则，真正生效的是发布版 `skel.c`；补丁改打 `skel.c`，并在 `build()` 用 `os.utime` 钉住确定性。
- **3**: 根因=`config.guess: unable to guess system type`（vintage config.guess 不识别 HongMeng 内核），解决方案=显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（canonical 相等 ⇒ `cross_compiling=no` ⇒ `@no_cross@` 非空 ⇒ `make check` 真正执行）。
- **4**: 根因=conan-verify G2 第 1 轮失败 `FileNotFoundError: 'sh'`（消费者脚本用裸命令名 `["sh","-c","command -v nm"]`；本机 `posix_spawn` 快路径不做 PATH 查找），解决方案=改为「显式绝对路径 → 已知候选路径 → `shutil.which`（纯 Python）→ 裸名兜底」三级解析。
- **5**: 根因=上游 `bigcheck` 首项裸 `-C` 被本版选项解析器吞成后续参数的后缀（`./flex: unknown -C option '/'`），解决方案=判为上游缺陷（pristine 源码可复现、平台无关），不改上游测试驱动，改为显式驱动可用 6 种压缩模式并在 `test_package/MANIFEST.yml`/`notes.md` 记录排除。
- **6**: 根因=finish 内置「干净构建校验 G0」用裸 `./configure`（不带本包必需的 `--build/--host`）故报 configure 失败，解决方案=判为工具侧误报：以 conan-verify 的 G2 与 W3（走 recipe 注入的正确参数、完整 `check successful` ×7）为准，并已把该结论写入知识草稿备注。
- **7**: 根因=submit 自检 `packaging_present` 恒 FAIL（框架遗留误报，仓内无任何已发布包满足），解决方案=不伪造 `packaging/`，按先例走等价手工步骤（push → `create-pr --no-preflight` → `trigger-ci`）并在 PR 正文披露 PF9 命中与 PF1–PF8 实测通过。
- **8**: 根因=W3 的 EXIT 还原逻辑会把 `conandata.yml` 的 `sources.url` 写成 `file://…/.build-cache/predl_cache/…`，解决方案=close 阶段已自动还原为官方 URL，提交前逐行 `git diff -- archives/` 复核确认（官方单值 https，无镜像/代理残留）。
- **9（远端 CI 首轮真实失败）**: 根因=CI worker 上该次构建进程的 `TMPDIR` 落在 **HMDFS 用户卷**（`$HOME/.cache/tmp`），而 `config.status` 建临时目录后立刻重定向写入 → 新目录权限元数据未生效 → `subs.sed`/`subs.frag`/`out`/`in`/`undefs.sed` 全部 `Permission denied`；`configure` 本身通过，症状酷似随机抖动。判据=失败步骤为 `conan-build-test`（#65021 是 `git-clone` 基础设施失败、未跑到此处，不能计入同点复现）；性质=**间歇竞态**（同代码 #65023 失败、#65046 通过），不可依赖重试。解决方案=补丁 `0002-configure-hmdfs-tmpdir.patch`（去 `umask 077` 依赖 + 显式 `chmod 700 "$tmp"`，该行随 heredoc 流入生成的 `config.status`）+ recipe `_pin_tmpdir()`（`configure` 前把 `TMPDIR`/`TMP`/`TEMP` 钉到经「建目录→立刻写入→回读」探针验证的可写根，优先非 HMDFS 的 `/data/storage/el2/base/cache`）+ `test_reflex.py` 的 `_workdir()` 同法探针化。

### 知识图谱使用情况

- **引用知识条目**: E077（OHOS ELF 须带 `.codesign` 才能执行 → `build()` 内先签名生成器才可跑 `make check`，`package()` 内再签 `bin/reflex`、`bin/reflex++`）；E490（autotools helper 脚本执行位/HMDFS，本包不适用——发布包脚本执行位完好）；E540（CC/CXX 路径与 recipe 命令 PATH —— 本包据此确认 conan 走签名垫片）
- **新增知识草稿**: 6 条（`knowledge/drafts/reflex-20241231-*.{kv,md}`，均含非空 `error_signature` + `root_cause` + `rec_approach`）
  1. `reflex-20241231-skel-c-flex-skl-mtime-divergence` — 生成物/模板 mtime 同秒且内容分叉 → 补丁落点与 `os.utime` 确定性
  2. `reflex-20241231-cxx-skeleton-guard-misplacement` — 骨架区块边界错位 → 非默认语言输出不可编译
  3. `reflex-20241231-reflexpp-stdout-form-required` — `-o` 丢序言行，C++ 生成须走 `-t` stdout
  4. `reflex-20241231-bootstrap-check-build-host-equality` — 自举 `make check` 在交叉构建下被 `@no_cross@` 静默置空（假通过）
  5. `reflex-20241231-bigcheck-bare-c-compression-option` — 上游测试目标不可用时"归属判定 + 显式枚举可用模式 + 记录排除"范式
  6. `reflex-20241231-hmdfs-tmpdir-config-status-eacces` — **本地全绿 / CI 间歇失败**：`config.status` 写不进自己刚在 HMDFS 上建的临时目录（同代码一次失败一次通过）；TMPDIR 钉定 + 显式 `chmod 700` 双保险
- **引擎命中情况**: `engine` 未新增 DRAFT；conan-verify 的 G0 预查询命中 E540/E490（均为提示性，按上述逐条判定后未触发实际修改）
- **未覆盖的错误模式**: 见"知识图谱覆盖"小节（裸命令名 posix_spawn、骨架 mtime 同秒分叉、`@no_cross@` 假通过、HMDFS 临时目录 EACCES 四条建议沉淀为 E-entry）

### AI 检视结果

- **检视阶段到达**: 未进入（按 §6 流程**到 PR 即停**，不等待 CI/AI 检视；续环交后续跟进）
- **变更摘要评估**: 不适用（本次未触发 AI 检视）
- **检视意见数量**: 0（未等待）
- **检视意见处理**: 不适用；已用 W4 独立审计（verdict=pass，仅 1×P2 + 2×P3）作为提交前自审替代

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`JC_RESULT=pass`；日志含 `Check successful, using COMPRESSION=""/-Ce/-Cm/-f/-Cfea/-CFer/-l` 共 7 次与 `SMOKE-SUMMARY 7/7 checks passed`）
- **远程 CI (PR 校验)**: **首轮失败** → 定位、修复、重推并重触发。本 PR 共三次构建交回结果：**#65021** 失败于 `git-clone`（`cannot exec 'git-remote-https'`，worker 基础设施问题，与配方无关）；**#65023** 失败于 `conan-build-test`（真实缺陷，见下）；**#65046 通过** —— 且该次跑的是**修复前的同一份代码**，说明该缺陷是**间歇竞态**而非必现。修复后本地全量复跑仍全绿（`Check successful` ×7 + `SMOKE-SUMMARY 7/7`）；修复 commit `96ea21fe` 的构建结果在本报告落笔时**尚未回流**（`pending-96ea21fe`）。
- **CI 失败原因（真实缺陷，已修）**: `./config.status: line 244/365/553/690: /storage/Users/currentUser/.cache/tmp/cslDeidH/{subs.sed,subs.frag,out,in,undefs.sed}: Permission denied` → `install-man` 生成失败 → `L1_RESULT=fail`。CI worker 上该次构建进程的 `TMPDIR` 落在 **HMDFS 用户卷**（`$HOME/.cache/tmp`，非 worker 自身导出的 `/data` 路径），而 `config.status` 用 `umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX"` 建目录后**立刻**重定向写入 → 新目录权限元数据尚未生效 → 第一次写入即 EACCES。**性质=时序相关的间歇竞态**（同代码 #65023 失败、#65046 通过），所以"重试"偶尔能蒙对，但根因真实存在、不可依赖重试。修复：补丁 `0002-configure-hmdfs-tmpdir.patch`（去 `umask 077` 依赖 + 显式 `chmod 700 "$tmp"`）+ recipe `_pin_tmpdir()`（`configure` 前把 `TMPDIR`/`TMP`/`TEMP` 钉到经写探针验证的可写根）+ 消费者脚本 `_workdir()` 同法探针化
- **⚠️ 门禁盲区（本次最重要的流程发现）**: `conan-verify`（G0–G4 + L2/L4/L5）、W3 本地 CI 模拟、`junk_check`、W4 独立审计**全部通过**，而远端 CI 在**同一份代码**上仍会失败（间歇：修复前代码一次失败一次通过）。根因是本地与 CI worker 的**环境差异**（本地 `TMPDIR=/data/...`，CI 那次为 `$HOME/.cache/tmp` 的 HMDFS 卷），任何"本地跑得通"的门禁都覆盖不到这一维度。另注：**"本地全绿"也不等于"重试必过"** —— 间歇缺陷最容易被"再跑一次就绿了"掩盖过去。

### 效率分析

- **HANDOFF 次数**: 3 次（conan-verify G2 第 1 轮 `FileNotFoundError: 'sh'`；submit Gate 3 `w4_audit_not_done`；submit 自检 `packaging_present`）
- **重试次数**: conan-verify 2 轮（第 2 轮全绿）；W3 1 轮通过；无构建类重试
- **关键瓶颈**: (1) 定位"补丁该打 `skel.c` 还是 `flex.skl`"耗时最长——两文件 mtime 同秒、内容分叉，`make check` 的 diff 信息（`NULL` vs `(char *) 0`）是唯一线索；(2) 上游 C++ 骨架缺陷的根因定位需要读 `misc.c: skelout()` 的标记语义才能解释 10 处 undeclared identifier
- **耗时较长的步骤**: W3 本地 CI 模拟（强制完整重建 + 7 次自举比对 + 消费者测试）；conan-verify 的 G2 `conan create`

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

本次由会话内手动记录（harness 未累积事件文件）：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-29T22:04 | conan_verify_g2_failed | `FileNotFoundError: 'sh'`（消费者脚本裸命令名） |
| 2026-09-29T22:07 | conan_verify_passed | G0–G4 + L2/L4/L5 全 PASS |
| 2026-09-29T22:11 | w3_local_ci_passed | `JC_RESULT=pass`，W3 阻塞门禁通过 |
| 2026-09-29T22:18 | finish_success | 状态 built，`.ci-result.json` 已写 |
| 2026-09-29T22:2x | w4_audit_passed | verdict=pass（1×P2 + 2×P3） |
| 2026-09-29T22:31 | pr_created | PR #13879 |
| 2026-09-29T22:32 | ci_failed | build #65021 git-clone（worker zsh OOM，基础设施） |
| 2026-09-29T22:34 | ci_failed | build #65023 conan-build-test：HMDFS `config.status` EACCES |
| 2026-09-29T22:50 | ci_fix_authored | 补丁 0002 + `_pin_tmpdir()` + `_workdir()` 探针化 |
| 2026-09-29T22:53 | conan_verify_repqassed | 全量复跑 PASS（patch 0002 已应用，`Using usable TMPDIR=/data/storage/el2/base/cache`，7/7） |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`finish` 内置的 G0 干净构建校验应支持"包特定 configure 参数"**：它固定用裸 `./configure`，对本包（以及任何需要显式 `--build/--host` 才能过 `config.guess` 的包）必然误报失败，而真正权威的 G2/W3 走的是 recipe 注入的参数 —— 同一流程内两个验收入口结论相反，容易误导执行者去改配方。建议 G0 复用 recipe 的 `generate()` 参数，或在失败时显式提示"若 G2/W3 已过，此项可能是工具侧局限"。
2. **`submit` 自检的 `packaging_present` 应改为条件判定或直接移除**：该检查要求 `packaging/*.tar.gz`，但 R19 禁止手工打包、`junk_check` JC3 又拦压缩包入库，仓内**无任何**已发布包满足 → 对所有包恒 FAIL，逼使每次走手工等价步骤。建议改为「若存在则校验，否则跳过」。
3. **PF9 与软件级文件（`commands.json`/`README.md`/`manifest.yaml`）的冲突应显式放行**：R38 强制要求产可执行文件的包声明软件级 `commands.json`，而 PF9 要求变更路径必须落在 `archives/<字母>/<包>/<版本>/` 内，两者对所有"新包首次入库"的 PR 直接对立。建议 PF9 对软件级白名单文件豁免。
4. **`finish` 的 `refresh-patch` 不应重置 AI 已确认的补丁分类**：本次 `patch_classification` 被从 `type: bugfix / platform_only: false / guard: none` 重置为 `type: auto / platform_only: True / guard: pending`，需要人工回改。覆盖时保留已有的人工分类（或只在字段为空时写入）更合理。
5. **`result --json` 类顶层 flag 的位置易错**：`gitcode_pr.py create-pr ... --json` 报 `unrecognized arguments`，必须写成 `gitcode_pr.py --json create-pr ...`。建议在各自子命令上也接受 `--json`，或在错误信息里提示正确位置。
6. **（重要）流程缺"远端 CI 回流后自动定位"的闭环**：本 SKILL 的 §6 明确"到 PR 即停、不等 CI"，但本次首轮 CI 就在 `conan-build-test` 上失败（本地 4 道门禁全绿也照样失败），且它是**间歇竞态**、重试有可能假绿。建议：① `create-pr` 后提供一次「CI 结果拉取 → 失败则 `diagnose` → 判定是否抖动」的**轻量可选步骤**（至少输出构建号、失败步骤与对应 SHA，别只留一句"未等待"）；② `diagnose` 的本地归类表补充 "HMDFS/文件系统权限" 类别——本次它只能凭一行日志猜到"权限问题"，而真正的根因（TMPDIR 落在 HMDFS 用户卷）与"写源码目录"完全无关，"权限问题"这一措辞会把执行者引向错误方向；归类时应要求**先核对失败步骤**（`conan-build-test` 才有意义，`git-clone`/`cleanup`/`worker-prep` 属基础设施），并明确提示"**同点复现不能直接断言确定性**——须核对是否为同一失败步骤/同一失败行，间歇缺陷同样会复现"；③ 门禁说明里明示"W3/conan-verify 与远端 CI 的环境差异点清单"（TMPDIR、HOME、/tmp 可写性、PATH 裸命令名），这些差异无法靠本地门禁覆盖；④ 判读 CI 结果时以**PR 评论正文**（含"构建包"与步骤表）为准，不要用 `ohpcd.atomgit.com/ci?id=<n>` 反查——两者构建号命名空间不同（本次该 id 指向的是 6 天前另一个包 `perl-crypt-openssl-bignum` 的构建）。
7. **`finish`/`conan-verify` 会反复重新生成空壳 `feedback/SKILL_FEEDBACK_<id>.md`**（含 13 处未填的模板占位符），每次跑完都要人工删除，否则入库必触发校验失败；而按流程手写的报告用的是另一个 id，两者并存更易混淆。建议：仅当用户未手写报告时才生成骨架，或生成到 `feedback/drafts/` 而非正式目录。

### 模板改进

1. **`templates/notes.md` 可预置"知识库扩展赛道"分支**：路径 B 需在 `knowledge_gained` 每条附 `knowledge_ref:` 才能在 W5 通过，但模板未提示该字段，首次走路径 B 时容易漏（本次 W5 先报 `unreferenced=5`，补引用后消除）。
2. **`test_package` 模板应内置"禁止裸命令名"的注释**：本机 `subprocess` 走 `posix_spawn` 快路径不做 PATH 查找，`["sh", ...]`/`["clang", ...]` 一律 `FileNotFoundError`。建议在模板里直接给出「显式绝对路径 → 已知候选 → `shutil.which` → 裸名兜底」的解析函数，避免每个包重踩。
3. **autotools 模板应提示"补丁落点判定"**：当 dist 里同时存在生成物与其模板（`skel.c`/`flex.skl`、`parse.c`/`parse.y`…）时，应先比对 mtime 与内容再决定补丁目标，并在需要时用 `os.utime` 钉住确定性 —— 这是本包耗时最多的一个坑，值得写入模板注释。

### 自动化补全

1. **`refresh-patch` 后可自动跑一次"补丁有效性自检"**：即"打了补丁的构建输入是否真的是构建读取的那一份"（比对 mtime 与内容分叉）。本次若首轮就有该检查，可省去一轮 `make check` 失败与回退。
2. **`finish` 的 W5 可自动为 `knowledge_gained` 补 `knowledge_ref:` 骨架**：当发现草稿目录里存在同包同版本命名的 `.kv` 时，按顺序建议对应关系供 AI 确认，而不是只报 `unreferenced=N`。
3. **`submit` 在 Gate 3 通过后应把 W4 审计的 verdict 直接并入 PR 描述生成**：本次审计结论（verdict=pass + P2/P3 清单）是提交前最有价值的自审证据，目前需手工誊抄。

### 知识图谱覆盖

本次发现的四个新错误模式建议沉淀为 E-entry（对应已提交的 6 条草稿中的 4 条）：

1. **发布包内"生成物与模板 mtime 同秒且内容已分叉"**：make 的 `target: template` 规则永不触发，补丁落点必须选生效文件并用 `os.utime` 钉住；否则修复时有时无、且 `make check` 的自举比对会以"写法差异 diff"误导排查方向。
2. **生成器骨架的"语言守卫区块"边界错位**：表现为默认语言路径全绿、非默认语言路径全红（大量 undeclared identifier）；修复应使用生成器自带的区块标记，而非在用户侧加 `#define` 掩盖。
3. **autotools 自举类 `make check` 在交叉构建下被 `@no_cross@` 静默置空**：退出码 0 但一条断言都没跑，是"测试通过"的假阳性；判据是在套件输出里搜其特有字串，而非只看退出码。
4. **（最高价值）`config.status` 在 HMDFS 上写不进"自己刚建的临时目录"**：症状是本地全绿、CI 间歇失败（同一份代码一次失败一次通过），且 `configure` 通过而只有 `config.status` 段炸，极易误判为随机抖动。判据=`conan-build-test` 段失败 + 失败路径在 HMDFS 用户卷 + "configure 过而 config.status 炸"的分段特征；**不要只凭"同点复现"断言确定性**（间歇缺陷也会复现，且不同构建的失败步骤可能根本不是同一根因）。修法=TMPDIR 钉到经写探针验证的可写根 + 在 configure 侧显式 `chmod 700` 临时目录。**这一条同时暴露了流程门禁的系统性盲区：本地门禁无法覆盖"环境差异"类缺陷，也无法区分"确定性缺陷"与"间歇竞态"**，建议单列一条 E-entry 或流程提示。

**门禁环境差异清单（建议纳入 SKILL 门禁说明）**：`TMPDIR`（本地 `/data/...` vs CI `$HOME/.cache/tmp`）、`HOME`、`/tmp` 可写性、PATH 裸命令名解析、HMDFS vs 普通卷的权限/属主语义。凡缺陷只在这些维度上暴露，本地 4 道门禁（conan-verify / W3 / junk_check / W4 审计）**必然全绿**。

---

## 作者

- **姓名**: ohpcd-robot
- **邮箱**: ohpcd-robot@noreply.gitcode.com
- **Agent ID**: runner32
- **生成时间**: 2026-09-29
- **PR 编号**: #13879
- **Git Commit**: 9fac7705533a316efd28e03974fc128b48251e23
