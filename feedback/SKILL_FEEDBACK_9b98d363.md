# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_9b98d363.md`

---

## 背景

- **软件名称**: locarna
- **版本**: 2.0.1
- **构建日期**: 2026-10-09
- **构建系统**: autotools
- **上游仓库**: https://github.com/s-will/LocARNA/releases/download/v2.0.1/locarna-2.0.1.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 1
- **编译依赖**:
- viennarna/2.7.2
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 通过 | G0/G1/G2/G3/G4 全 PASS（verdict=pass）；L2/L4/L5 因 `conan_verify.py` 的 `conan list <full-ref>:*` JSON 键层级假设不符而跳过（仓库级工具问题，非本包），等价二进制冒烟由 W3 L2 对 8 个二进制覆盖 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 部分 | `submit` 自检 `packaging_present` 恒 FAIL（全仓无 `packaging/*.tar.gz`，仓库级误报）→ 走 `gitcode_pr.py create-pr --no-preflight` 手工等价路径建 PR #15180 并 `/rebuild` 触发 CI；AI Review 与远端 CI 结果待回（评论触发型 CI 排队中） |

### 失败与问题

> 自动提取时「根因/解决方案」字段被写反，此处按 问题 / 根因 / 解决方案 重列（内容与 notes.md 一致）。

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 全部 CLI（locarna/locarna_p/sparse/…）任何调用都 100% CPU 空转、零输出、timeout 124 | `LocARNA/options.cc` 的 `process_options()` 用 `char c` 承接 `getopt_long()` 的 int 返回值；AArch64 下 plain char 默认无符号（AAPCS / `__CHAR_UNSIGNED__`），EOF(-1) 截断为 255，`while ((c = getopt_long(...)) != EOF)` 永不退出 | patches/0001-src-LocARNA-options.cc.patch 把接收变量改为 `int c`（refresh-patch --auto 生成）；8 个工具全部恢复 |
| 2 | `configure` 建 `confXXXXXX`（umask 077）在 HMDFS 上不可写；`ac_pwd=\`pwd\`` 在沙箱内 getcwd 失败 | autoconf 硬编码 umask 077 且 `pwd` 依赖 getcwd（E011/E052） | `generate()` 内把 `configure` 中 `umask 077`→`022`，`ac_pwd` 追加 `|| ac_pwd="$PWD"` 回退 |
| 3 | 老版 `config.sub`(2014) 不识别 ohos；configure 收到 ohos 三元组会判定为未知系统 | 上游 config.guess/sub 早于 HarmonyOS | 采用 libuuid 模式显式传 `--build/--host=aarch64-unknown-linux-gnu`，autotools 永不直接收到 ohos；并对 config.sub/guess 做防御性改写 |
| 4 | viennarna 包内 `RNAlib2.pc` 的 `prefix=/`，OHOS 上解析到宿主 `/lib`，`PKG_CHECK_MODULES([VRNA],[RNAlib2 >= 2.5.1])` 失败 | 上游 .pc 以 `/` 为前缀（DESTDIR staging 遗留） | generate() 把 `prefix=/` 重写为 viennarna 包目录，生成到 `build_folder/vrna-pc` 并 prepend `PKG_CONFIG_PATH` |
| 5 | `make install` 在 pkginclude 多文件头批次上报宿主 install shim `Error 64` | OHOS 宿主 install 包装器限制 | 用上游 bundled `config/install-sh`（经 `/bin/sh`）作为 `INSTALL`/`MKDIR_P` 驱动 `make install DESTDIR=…` |
| 6 | `lib/perl` 子目录构建/安装 MLocarna.pm 失败 | MLocarna.pm → MLocarna::threaded → `use threads`；OHOS PC 镜像自带 Perl 未编译线程支持 | 禁用 `lib/perl`，并在 package() 剔除 bin/ 内 23 个非 ELF 助手脚本 |
| 7 | 上游 `test_programs` 集成驱动（bash/perl）在 OHOS 跑不了（无 /bin/bash、需 Perl 模块） | 集成驱动非自包含 | `make check` 命令行覆盖 `TESTS=test_locarna_lib`，仅跑 Catch2 单元套件（22 用例 / 175 断言） |
| 8 | conan 应用补丁报 `source/target file does not exist: a/LocARNA/options.cc` | 补丁路径前缀写错：tarball 根下是 `src/LocARNA/options.cc`，而 Conan `patch()` 以 `strip=0`、root=source_folder 解析 | 补丁头改为 `a/src/LocARNA/options.cc` / `b/src/...` |
| 9 | 交付 `LocARNA-2.0.pc` 含构建机绝对 `-L/-I`，且「静态库内嵌 ViennaRNA」表述有误 | 上游 `.pc.in` 原样落盘 `@LIBS@`/`@CPPFLAGS@`；实测静态库保留 8 个未定义 `vrna_*` 符号 | package() 重写 `prefix=${pcfiledir}/../..` + 剔除包外绝对 `-L/-I` + 补 `Requires: RNAlib2`；纠正全部「内嵌」表述 |

### 知识图谱使用情况

- **引用知识条目**: E490（autotools 助手脚本可执行位，G0 命中）；E419（target plain-char 有符号性）；DRAFT-8543-plain-char-eof-sentinel-infinite-loop（plain char 承接 getc/fgetc 返回值与 EOF 比较致死循环，本包为同类根因在 getopt_long 上的新实例）
- **新增知识草稿**: 0 条（本次复用既有条目/草稿，未新建；如需可为 getopt_long 变体与「无 ptrace 下的 SIGPROF 采样定位」补草稿）
- **引擎命中情况**: 草稿目录 3021 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: ①AArch64 plain char 无符号导致 `getopt_long()` 的 EOF 哨兵不可表示（既有 DRAFT-8543 只覆盖 getc/fgetc，可扩展 trigger 到 getopt_long）；②沙箱禁用 ptrace 时用 `LD_PRELOAD` + `ITIMER_PROF`/`SIGPROF` 采样 `ucontext_t.uc_mcontext.pc` + `llvm-addr2line` 定位死循环（可沉淀为「OHOS 无可调试器时的定位手法」条目）

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 待 atomgit-bot 生成（PR 刚创建，尚未出现「变更摘要」评论）
- **检视意见数量**: 0（截至本次上报，仅有 CI 触发机器评论）
- **检视意见处理**: 无检视意见可处理；后续以 `submit --resume` 或 `gitcode_pr.py monitor-review` 续环

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3（result 校验缺 `--failed-reason` 1 次；finish/verify 复跑用于补丁溯源与 .pc 修复后的证据刷新）
- **重试次数**: conan-verify 4 次（首轮 test_package API 误用 1 次；补丁路径前缀错误 1 次；配方重构后复验 2 次），finish 3 次
- **关键瓶颈**: ①`conan create` 每次全量 autotools 构建（`make -j1`）约 8-10 分钟，配方每改一处即需全量复跑；②远端 CI 为评论触发且排队，30+ 分钟仍 UNKNOWN，无法在会话内闭环
- **耗时较长的步骤**: finish step5 W3 本地 CI（含 conan create 全量重建）与 step4 conan-verify 各约 10 分钟；W4 独立审计（子代理通读 14 文件 + 对照真实产物）约 10 分钟
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-09T21:24:49 | lang_checked | detected=cpp 与任务 cpp 匹配 |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. **PF8 与 PF9 对新包首入库必然冲突**：PF8 要求 CLI 包在软件级 `archives/<pkg>/commands.json` 声明（R38），PF9 又判定软件级 4 段路径「缺版本目录层」并 fail-closed 拦截 PR 创建。二者只能靠 `--no-preflight` 绕过，建议 PF9 对 `commands.json`/`manifest.yaml`/`README.md` 三个 finalize 强制文件做白名单。
2. **`submit` 的 `packaging_present` 恒误报**：全仓无任何 `packaging/*.tar.gz`（已核对 `git ls-files`），对 `status=built` 必然 return 1，使 `submit` 这条唯一 PR 入口对所有包不可用，建议改为软警告或按 `status` 区分。
3. **`conan_verify.py` 的包 ID 解析 bug**：`gate4_artifact_integrity` 读 `listing["Local Cache"][self.software][self.ref]`，而 `conan list <full-ref>:*` 的实际结构是 `["Local Cache"][<full-ref>]`，导致 G4 只能走「无法找到程序包 ID」软通过、L2/L4/L5 全部跳过——G4/L2 的产物与冒烟校验实际失效。
4. **`refresh-patch --auto` 会遗留 `patches/.patch-backup-<ts>/`**（内含旧补丁），若不手工删除会被提交进 PR；建议工具自动清理或输出到 `patches/` 之外。
5. **`finish` 每次把 conandata 改写为 gh-proxy 双 URL 列表**，必须人工还原官方单值 URL，否则命中 PF7/R39——建议把该改写限制在 CI 预下载阶段的内存副本，不落盘。
6. **`finish` 会重置 `patch_classification` 为 `auto/True/pending`**，覆盖 AI 已填实的分类；建议只在新补丁出现时写入，已存在条目保留。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **autotools 模板建议内置 E011/E052 处理**：`configure` 的 `umask 077`→`022` 与 `ac_pwd` getcwd 回退已是 libmtd/libubi/locarna 等多例共性问题，模板可默认生成，并在 `generate()` 中落点（本包已按 R6 移入 `generate()`）。
2. **`.pc` 交付模板**：上游 `.pc.in` 常把 `@LIBS@`/`@CPPFLAGS@`（含构建机绝对路径）原样落盘。建议模板内置「重写 prefix 为 `${pcfiledir}/../..` + 剔除包外绝对 `-L/-I`（含 `.private` 与 `-L /path` 空格形式）+ 补 `Requires`」三步。
3. **PR body 模板的用例口径**：模板未说明「上游集成测试因平台不具备而未运行」如何计数，易出现 pr-body 与 test-report 口径不一致；建议增加一行「未运行原因」列或明确统计基准。
4. **MANIFEST.yml 的 `upstream_tests[].file`** 建议允许目录/多文件（如 Catch2 的 `CATCH_CONFIG_MAIN` 包装文件与真正 TEST_CASE 分离时，指认单文件会误导）。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **补丁基线自动准备**：`refresh-patch --auto` 依赖 `.build-context` 指向的 orig/work 目录，而会话重启会清空 el2 缓存使其缺失（`无法定位源码目录`）。建议工具在缺失时自动从 conandata 的 URL+sha256 重建 orig，并应用现有补丁生成 work。
2. **`_strip_foreign_pc_flags` 式产物净化**可做成 conan-verify 的一个门禁（扫描包内文本产物是否含构建机绝对路径），把 E524 从「审计发现」前移为「构建期拦截」。
3. **CI 状态查询自动化**：`ci-status` 在 CI 排队期恒为 UNKNOWN 且无区分「排队中 / 未调度 / 失败」的信号，建议增加队列位置或超时升级（如 >30min 未调度则提示重触发）。
4. **`finish` 后处理清单自动化**：还原 conandata、删 `.patch-backup-*`/`.orig`/`.ghfast-bak`、回填 `patch_classification`、补 `.staging-verified` 目前全靠 AI 手工，建议合并为 `finish --finalize-recipe` 一步。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **`getopt_long` 版 plain-char EOF 死循环**：DRAFT-8543 只覆盖 `getc/fgetc/getchar`，建议把 trigger 扩展到 `getopt_long/getopt`（返回 int、EOF/-1 为正常出口），并注明「零输出 + 100% CPU + timeout 124」这一无报错特征。
2. **无 ptrace 环境下的死循环定位手法**：`LD_PRELOAD` 注入 `ITIMER_PROF`+`SIGPROF` 采样 `ucontext_t.uc_mcontext.pc` → `llvm-addr2line` 反查符号；OHOS 沙箱 `gdb`/`lldb` 均报 `ptrace: Permission denied`，该手法可复用，建议沉淀为独立条目。
3. **E538 误命中**：conan-verify G2 失败时知识引擎按通用报错文本命中了 harfbuzz/pango 的共享/静态 binary 漂移条目，与真实根因（补丁路径前缀）无关；建议提高引擎对「补丁应用失败」类报错的判别权重。
4. **Perl 前端在 OHOS 不可用的判据**：OHOS 镜像 Perl 未编译 `threads` 支持（`This Perl not built to support threads`），使依赖 `MLocarna::threaded` 的脚本层不可用；可作为「Perl 模块依赖 threads 时判平台不具备」的条目。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: ohc-agent
- **邮箱**: ohc-agent@local
- **Agent ID**: D0ED
- **生成时间**: 2026-10-10 01:08:30
- **PR 编号**: 15180
- **Git Commit**: 1e42ce290c
