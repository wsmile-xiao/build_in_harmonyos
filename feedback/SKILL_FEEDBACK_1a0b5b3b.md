# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成骨架，由执行 Agent 按真实过程填写。
> 文件位置: `feedback/SKILL_FEEDBACK_1a0b5b3b.md`

---

## 背景

- **软件名称**: cyrus-sasl-digestmd5
- **版本**: 2.1.28
- **构建日期**: 2026-09-26
- **构建系统**: autotools（configure + make，in-source）
- **上游仓库**: https://github.com/cyrusimap/cyrus-sasl （tag `cyrus-sasl-2.1.28`；与同族 cyrus-sasl / cyrus-sasl-login / cyrus-sasl-gssapiv2 同一 tarball）
- **适配路径**: 机制子包（DIGEST-MD5）静态最小闭包 + 3 个 portability 补丁
- **补丁数量**: 3（`0001-utils-testsuite.c.patch` +1/-1、`0002-config-config.guess.patch` +11/-0、`0003-config-config.sub.patch` +2/-2，均由 `refresh-patch --auto` 生成并经 `patch_ng` 验证 apply=True）
- **编译依赖**: `openssl/3.5.6`（唯一强制第三方依赖；DIGEST-MD5 的 DES 机密性层 `$(LIB_DES)=-lcrypto`）
- **最终状态**: 本地全流程绿（W3 100%、conan-verify PASS、test_package 8/8、JC/KC PASS）；按用户要求停在 commit/push/PR 前等待确认

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| W0 | 依赖发布检查 | 完成 | `conan download openssl/3.5.6`（recipe + binary）rc=0；对照组 rc=1 语义可比 |
| W1 | 同步 main | 完成 | `git fetch origin main` → `2e478fc4a2`；worktree `feat/cyrus-sasl-digestmd5-2.1.28` |
| R47 | 语言预检 | 完成（含工具伪阳性） | `lang-preflight` 全树判 `mixed`（`mac/libdes/src/Makefile.PL` 被当成项目 manifest）；过滤平台无关遗留子树后判 `c`（autotools，主体 80% C）→ 与任务 `cpp` 兼容族匹配 |
| init-build | 源码下载/解压 | 完成 | 首次误写 skill 主仓，补 `--project-dir` 后归位；sha256 三方一致 |
| build | 编译构建 | 成功 | configure rc=0 / make rc=0；`LIB_DES=-lcrypto`、`WITH_SSL_DES=1`、`STATIC_DIGESTMD5=1`、`DO_DLOPEN=0` |
| conan create | 配方验证 | **通过** | test_package 8/8；`HMBS_UPSTREAM_TEST_RESULT`/`HMBS_TEST_PACKAGE_RESULT` 均留痕 |
| conan-verify | 配方验证 | **PASS** | G0/G1/G2/G3/G4 全 PASS（G1 曾因 `exports_sources` 属性写法被判 FAIL，改为 `def export_sources()` 后通过） |
| finish | 归档收尾 | W3 通过（100%），rc=1 | W3 `exit_code=0` + `.ci-result.json`；rc=1 来自非阻塞项（见下） |
| submit | PR 提交+AI检视+CI | 未执行（按用户指令停在确认前） | — |

### 失败与问题（真实首错 → 根因 → 修复）

1. **`configure: error: cannot guess build type`** —— config.guess（2018-02-24）不识别 `uname -s=HarmonyOS`（E007）→ 打补丁产出 `aarch64-unknown-linux-ohos`；**未使用** `--build/--host`。
2. **内置 `patch-autotools-ohos.pl` 静默失效** —— 脚本按较新 config.guess 的 `GUESS=` 变量惯用法插入分支，本版各分支以 `echo <triplet>; exit ;;` 结束 → 插入的 arm 只赋值不输出；脚本自身仍打印 `[ok] Added HarmonyOS system identification`。
3. **`config.sub aarch64-unknown-linux-ohos` 被拒** —— `maybe_os` 与 os 合法列表均无 `linux-ohos*`（两处最小修改）。
4. **`config.status: can't create ./conf*/subs1.awk: Permission denied`** —— HMDFS setgid + autoconf `umask 077`（E129）→ 配方 `build()` 运行时 `umask 077`→`022`。
5. **`utils/testsuite` 运行即 `Failed with: Invalid parameter`** —— `char c` 承接 getopt 返回值，char 无符号时 `!= EOF` 恒真（同族 cyrus-sasl-sql 先例）→ `int c` 补丁。
6. **`sasl_checkpass() failed on simple case`** —— harness `main()` 第二动作 `test_checkpass()` 需 sasldb；机制包 `--with-dblib=none` 必然阻塞 → 如实留痕 `status=blocked_by_userdb`，不冒充通过。
7. **本机 CLI `patch` 是 toybox 0.8.12** —— 对 `diff --git`/hunk 补丁静默 no-op（rc=0 且打印 `patching <file>`，实际未改）→ 补丁有效性证据改用 `patch_ng` + 真实构建。
8. **`refresh-patch --auto` 生成 62 KB/2438 行补丁** —— 用会规范化行尾空白的编辑器改源码造成 353 行噪声差异 → 改为 python 字节级替换（保持行尾空白）。
9. **test_package `OpenSSL::Crypto` 目标不存在 / `openssl/des.h` 找不到** —— Conan CMakeDeps 用 `openssl::openssl`，且该目标对消费者未提供 include 目录 → 改为不引用 openssl 头，仅以链接期符号解析证明 DES 闭包。
10. **test_package `HMBS_TEST_PACKAGE_RESULT` 首轮 8/8 但 `client-listmech` 只见 EXTERNAL** —— `sasl_client_new` 会按 `client_mech_list`（GETOPT/config 路径）裁剪 conn 级列表；改以「服务端 conn 列表含 DIGEST-MD5 + 空 SASL_PATH 下仍含」作为机制注册证明（与上游 pluginviewer 口径一致）。

### 知识图谱使用情况

- **引用知识条目**: **E007**（config.guess 无 HarmonyOS 分支 → 打补丁，禁 `--build/--host`）、**E129**（HMDFS setgid + `umask 077` → config.status 属主不可写）
- **新增知识草稿**: 2 对（kv+md 一一对应，均通过 KC）
  - `DRAFT-cyrus-sasl-digestmd5-2.1.28-toolbox-patch-silent-noop`（toybox patch 静默 no-op，补丁有效性证据口径）
  - `DRAFT-cyrus-sasl-digestmd5-2.1.28-testsuite-unsigned-char-userdb-gates`（testsuite 双门槛：无符号 char/getopt + sasldb 前置）
- **引擎命中情况**: E007（Phase B: 7）、E129（Phase B: 2）、G0 命中 E490（autotools helper 可执行位，本包不适用）
- **测试统计**: test_package 8/8（含 2 项鸿蒙特有）；上游 harness discovered 19 / executed 1 / passed 0 / failed 1 / skipped 18（`blocked_by_userdb`，如实申报）；pluginviewer 2/2；上游样例 5 个全部构建并运行
- **未覆盖的错误模式**: 见下方「知识图谱覆盖」

### AI 检视结果

- **检视阶段到达**: —（未进入 submit，按用户指令停在 PR 前）
- **变更摘要评估**: —
- **检视意见数量**: —
- **检视意见处理**: —

### CI 结果

- **本地 CI 模拟 (W3)**: **通过**（L0 pass / L1 pass / L4 warn / L5 pass，Pass rate 100% (1/1)；`.ci-result.json` exit_code=0，integrity_hash `8cab89996221a267`）
- **远程 CI (PR 校验)**: 未触发（未 push）
- **CI 失败原因**: 无（本地 W3 首轮因 JC full 模式命中 **origin/main 中他包已跟踪文件** `archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、`archives/k/kics/2.1.20/.staging-verified` 而失败；改用 CI 同口径 prdiff 模式后 JC 全绿）

### 效率分析

- **HANDOFF 次数**: 7（语言预检 2 次 + G0 1 次 + W3 3 次 + W3 resumable 1 次）
- **重试次数**: 约 8 次有效修复循环（不含环境性重试）
- **关键瓶颈**:
  1. **主机资源耗尽（约 30 分钟）**：`zsh: fork failed: resource temporarily unavailable`，交互 shell 反复 SIGSEGV，`nohup` 后台进程仍可跑 → 改为「离线母脚本 + filemgr 读日志」模式推进；
  2. **`filemgr` 编辑会规范化行尾空白** → 触发 62 KB 噪声补丁，需从 pristine 重建；
  3. **补丁验证假阳性**（toybox patch）→ 浪费一轮验证；
  4. **G1 的 `export_sources` 子串检查**（`exports_sources` 属性不含 `export_sources` 子串）→ 一轮 verify 失败。
- **耗时较长的步骤**: 环境恢复期；conan create 三轮（每轮 ~5-6 分钟，含 harness 构建与 test_package）

---

## 建议

### SKILL 设计改进

1. **补丁有效性口径应写入 R 规则**：本机 `patch` 可能是 toybox/busybox 精简实现（`patch --version` 判据），对含 `diff --git` 头的补丁**静默 no-op 且 rc=0**。建议在 `refresh-patch`/`clean-verify` 的文档与 HANDOFF 中明确：补丁有效性只认「与 pristine 的 diff 内容」「`patch_ng` apply=True」「真实构建读数（`Apply patch` + configure 三元组）」三选一，禁止以 CLI `patch` 的退出码为证据。
2. **`patch-autotools-ohos.pl` 需版本适配 + 自校验**：脚本对 2018 版 config.guess 的 `echo …; exit ;;` 惯用法静默失效（插入 arm 只赋值 `GUESS` 不输出），但自身打印 `[ok]`。建议脚本在改写后**自校验**（运行 `./config.guess` 并断言输出为三元组），失败即报错而非静默成功。
3. **`G0 clean-verify` 的平台语义需说明**：G0 以**手工 `./configure`** 复现，不走配方 `build()` 的 OHOS 运行时修补（本例 E129 的 `umask 077`→`022`），因此对「修补在配方内完成」的包必然报 `configure 失败`。建议 G0 明确标注「非阻塞 + 仅覆盖纯补丁型适配」，或在 G0 中复用配方 `build()` 的前置处理器。
4. **CI 镜像回退改写后必须还原**：W3 的 `build_and_test.sh` 会把 `conandata.yml` 的官方 URL 改写成以 `gh-proxy.com` 打头的列表（并在 EXIT trap 中还原）；当流程**中途失败/被杀**时还原未执行，工作区留下**镜像优先**的 URL（与 R39/PF7 冲突，若被提交即违规）。建议改为「改写副本 + 显式还原校验」，或在 JC/PF7 前置检查中加入「工作区 conandata 与 HEAD 不一致」告警。
5. **JC full 模式与「未提交分支」的互斥**：分支尚未 commit 时 `git diff origin/main...HEAD` 为空 → JC 回退 full 模式整仓扫描，命中**他包已跟踪的运行时状态文件**（本例 3 个）导致 W3 必然失败。建议本地 W3 在「无提交」时提示使用 `JUNK_PR_DIFF`（CI prdiff 同口径）或自动按未跟踪文件构造清单。
6. **`filemgr` 类编辑器不可用于源码补丁准备**：其写入会规范化行尾空白，产生数百行噪声差异。建议在 `refresh-patch` 输出中加入「空白噪声占比」提示（如「本次差异 354 行中 353 行为行尾空白」）。

### 模板改进

1. **autotools conanfile 模板**应内置：`def export_sources()`（方法而非 `exports_sources` 属性，兼顾 G1 检查）、`umask 077`→`022` 运行时修补、`CC_FOR_BUILD/CPP_FOR_BUILD=clang`、`--without-staticsasl` 与 `--disable-shared` 的互斥说明。
2. **test_package 模板**应包含「机制/目标注册证明」与「链接期闭包证明」两种范式：当依赖（如 openssl）在 CMakeDeps 下不向消费者暴露 include 目录时，避免直接 `#include` 依赖头文件，改用符号解析证明。
3. **MANIFEST.yml 模板**增加 `build_time_smoke:` 段（记录 build() 内的上游工具冒烟断言，如本例 `pluginviewer` 的 `best SSF: 128`）。
4. **test-report 模板**增加「已知告警逐条归因」表（本例 G0/L4/JC/知识图谱 4 项），便于评审一次看清哪些与本 PR 无关。

### 自动化补全

1. **依赖预检**：`preflight_check.sh` 可增加「同族 recipe 一致性」检查（同一 tarball 的 url/sha256 是否与已合入同族包一致），本例 8 份同族 recipe 的 sha256 完全一致，可自动核验。
2. **上游测试证据自动化**：对「有手工测试台（EXTRA_PROGRAMS）但需运行期夹具」的项目，自动生成 `blocked_by_<fixture>` 证据行模板，降低「冒充通过」的动机与工作量。
3. **环境降级自愈**：检测到 `fork failed`/shell SIGSEGV 时，自动切换为「离线脚本 + 文件轮询」模式并提示（本次由人工切换）。
4. **W3 前置**：在 `finish` 调 W3 前自动探测 `git rev-parse origin/main..HEAD` 是否为空，空则提示 `JUNK_PR_DIFF` 用法（避免必然失败的一轮）。

### 知识图谱覆盖

建议新增/扩充以下 E-entry（本次已提交 2 条草稿，另有 2 条建议）：

1. **toybox/busybox `patch` 静默 no-op**（已提交草稿）——「精简工具语义缺失 + 证据口径」类，适用范围远超 autotools。
2. **cyrus-sasl `utils/testsuite` 双门槛**（已提交草稿）——同族 login/crammd5/ntlm/scram/sql/gssapiv2/gs2 通用。
3. **建议新增：`patch-autotools-ohos.pl` 与旧版 config.guess 惯用法不匹配**（E007 的补充条目：脚本静默无效但打印 `[ok]`；判据 = 运行 `./config.guess` 断言三元组）。
4. **建议新增：Conan CMakeDeps 消费者不继承依赖包的 include 目录**（`openssl::openssl` 只有 LINK_DIRS/INCLUDE 的配置表达式；消费者若 `#include` 依赖头会 `file not found`；对策 = 链接期符号证明或显式 `find_package(<pkg> CONFIG)` 并核对 target 属性）。
5. **建议扩充 E129**：区分「generated 脚本运行时修补（配方路径 OK）」与「clean-verify/G0 手工 configure 路径（必然失败）」两种语义，避免把非阻塞项误判为包缺陷。

---

## 作者

- **姓名**: GaoPengqiang
- **邮箱**: GaoPengqiang@noreply.gitcode.com
- **Agent ID**: 215A
- **生成时间**: 2026-09-26（骨架 07:38:28，内容填写 09:0x）
- **PR 编号**: —（未提交，等待用户确认）
- **Git Commit**: 2e478fc4a2（分支 `feat/cyrus-sasl-digestmd5-2.1.28`，尚未 commit）
