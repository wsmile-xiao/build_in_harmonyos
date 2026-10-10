# Conan 验证报告 — letta-code 0.28.17

> **报告性质**：本文件是**本机（HarmonyOS PC aarch64 真机）本地验证记录**，由适配流程手工汇总，
> **不是** CI 侧 `conan-verify` 工具产出的 G0–L5 机器报告（本机不存在该生成器，仓库 `ci/`、`code/`、
> `tools/` 下均未找到 "Conan Verify Report" 生成逻辑）。CI 上的 Shadow CI / L0–L5 门禁结果**待 CI 回填**，
> 本文件不预标其结论。

**本机结论**: 本地 PASS（build 期冒烟 + test_package 全绿）
**Reference**: `letta-code/0.28.17`
**Recipe revision**: `7ae675efc21403e3f25f26fbc70e903e`
**Package id**: `6b129b068851896169fae42d399fa922d239ce8a`
**Package revision**: `e39be2c224045fbc42f8e4a3ea55a4ef`
**Profile**: `ohos-aarch64`（host=builder 同为 ohos-aarch64：os=OHOS os.version=6.0 arch=armv8 compiler=clang15 build_type=Release）
**日期**: 2026-09-27（首轮） / 2026-09-28（rule4 复核后复跑，退出码 0）
**完整日志**（rule4 复核后复跑实测留存 130 行 / 6687B；按仓库 `.gitignore` 的 `*/reports/*.log` 约定不入库，关键片段已内联于本报告与 `notes.md`）: `reports/conan-create.log`（个人绝对路径已脱敏为 `$HOME`）

## 1. 本地门禁结果

| 门 | 结果 | 证据 |
|----|------|------|
| 配方静态校验（`python3 -m py_compile`、YAML 解析、`sh -n`） | ✅ PASS | 见 `notes.md`「本机与真机验证」 |
| `conan inspect`（name/version/license/conandata 可解析） | ✅ PASS | `conan inspect .` 退出码 0 |
| G2 `conan create`（含 build 期真冒烟） | ✅ PASS | `CONAN_CREATE_EXIT=0`；日志含 `built letta-exec trampoline (-static)`、`bin/letta --version -> '0.28.17 (Letta Code)'`、`build smoke OK` |
| `test_package`（**53 条断言**，真实执行目标程序） | ✅ PASS | `RUN: "/system/bin/sh" .../test_package/test.sh` → `0.28.17 (Letta Code)` → `letta-code 0.28.17 consumer checks: PASS (assertions=53)`；断言= 1 版本横幅 + 3 帮助段头 + 21 条 USAGE 命令行 + 27 条 SUBCOMMANDS 条目 + 1 断言数自检，且整块按 `USAGE` / `SUBCOMMANDS` 区块逐条对真实 `--help` 输出校验 |
| 源码身份（npmjs 官方 tarball SHA256 双处声明） | ✅ PASS | `reports/source-verification.md` |
| 产物洁净（无构建缓存/临时 env 脚本泄漏） | ✅ PASS | 产物仅 `bin/{letta,letta-exec}` + `libexec/letta-code/<npm 发布物>` + `licenses/LICENSE`；`test_package/` 仅 `conanfile.py`/`test.sh`/`MANIFEST.yml`（本机 `conan create` 会在该目录就地生成 `conan*.sh`、`__pycache__/`、`metadata/`，均被仓库 `.gitignore` 覆盖、不入库） |
| 个人绝对路径 / 令牌扫描 | ✅ PASS | 对 `archives/l/letta-code/**` 扫描「个人绝对路径前缀」与「访问令牌参数名」关键字：均无命中（`conan-create.log` 中仅第 1 行为脱敏说明；日志本身按仓库约定不入库） |
| CI 侧 L0–L5 / Shadow CI | ⏳ TODO | 待 PR CI 执行并回填 |

> **rule4 复核后复跑（2026-09-28）**：`CONAN_CREATE_EXIT=0`，日志含 `built letta-exec trampoline (-static)`、
> `build smoke OK: packaged launcher --version banner and --help sections verified through an inherited
> (polluted) environment` 与 `letta-code 0.28.17 consumer checks: PASS (assertions=53)`；
> recipe revision `7ae675efc21403e3f25f26fbc70e903e` 与 package revision `e39be2c224045fbc42f8e4a3ea55a4ef`
> 与首轮**完全一致**（本次只改 `test_package/test.sh` 与文档，未触碰配方/打包内容）。

## 2. 关键回归：launcher 的 `LD_LIBRARY_PATH` 剥离（真实缺陷，已修）

本机实测确认（均为真机复现，非推断）：

| 实验 | 命令要点 | 结果 |
|------|----------|------|
| V0 污染环境直跑 node 真 JS | `LD_LIBRARY_PATH=<host libs> node -e 'console.log(1)'` | ❌ `Check failed: 12 == (*__errno_location())` / Signal 5 / exit 133 |
| V0b 同环境但只跑 `node --version` | 不初始化 V8 | ✅ 假绿（**不能**作为验证手段） |
| V1 `unset LD_LIBRARY_PATH` 后启动 | `/system/bin/sh` 下 unset | ❌ 仍崩（该 shell 的 `unset` 未把变量从子进程环境摘掉） |
| V1b 置空 `LD_LIBRARY_PATH=` | 空值等价 cwd 项 | ❌ 同样致命 |
| V2 仅 `env -u LD_LIBRARY_PATH node …`（无 trampoline） | 去掉 trampoline 后重跑 launcher | ❌ Signal 5 / exit 133 |
| V3 `env -u` + 安装态 trampoline | `<pkg>/bin/letta --version` | ✅ `0.28.17 (Letta Code)`（含 3 层嵌套 shell 场景） |

结论：仅剥离环境变量**不足以**在本机 OHOS 运行时上稳定启动 node；当前配方 = `env -u` 真剥离
**+** 构建期编译的 `bin/letta-exec`（静态 trampoline，清环境后 `execvp` node）两者共同承重。
反向验证：把 launcher 退回旧写法（裸 `exec node`）时 `build()` 冒烟即失败（exit 1），
证明新冒烟能拦住该类回归。

## 2b. rule4「少报」复核修订（2026-09-27）

判定原文：`编译 + 通过率 + 少报` 中「**少报: 上游实测 N=29 > 声明 N=8**」。复核与处置：

| 项 | 初版 | 修订后 |
|----|------|--------|
| `test_package` 断言数 | 11（只查 6 个命令 / 9 处片段） | **53**（1 版本 + 3 段头 + 21 USAGE + 27 SUBCOMMANDS + 1 自检） |
| CLI 接口面覆盖 | 6/48 | **48/48**（交付包 `--help` 的全部可验证条目，非抽样） |
| 上游测试口径 | 只写运行器范围（553，未列拆分） | 多口径穷举表：全库 553 = 541 `.ts` + 12 `.tsx`；白名单 24 目录 433；`src/channels` 82；根级 31；`src/integration-tests` 8（排除）；isolated 19；非 src 2 |

口径原则：**声明值 ≥ 任何单一口径实测值**；只按实测扩充，不虚改数字。
上游 `bun:test` 仍为 `cases_run = 0`（设备 `execve` 拒非本会话产出的二进制，见第 3 节），**不虚报通过率**。

## 3. 未完成 / 遗留

| 项 | 状态 | 说明 |
|----|------|------|
| 上游单元测试（bun:test，553 个测试文件） | ⛔ 本机不可运行（已定论，非"未跑"） | **二进制级**阻断已实测：设备上 `execve` 对"非本会话产出"的二进制一律 **EACCES(13)**——官方 musl 变体 `@oven/bun-linux-aarch64-musl@1.4.2`（72.6MB，INTERP=`/lib/ld-musl-aarch64.so.1`）、glibc 变体（99.9MB）、Debian `ld-linux-aarch64.so.1`(203KB)、`/system/bin/sh` 副本(306KB) 全部被拒；而同目录本机 clang 产物（18KB–70MB，静态/动态 ET_EXEC、ET_DYN PIE）与自写脚本可执行（`stat`/`listxattr` 逐字段一致）。`cases_run = 0`、`cases_passed = 0`，**不虚报**；对照矩阵与逐条排除实验见 `notes.md`「上游测试清点与验证」 |
| CI Shadow CI / L0–L5 | ⏳ TODO | 由 PR CI 产出 |
| 真机交互路径（依赖 Letta 后端/网络） | ⏳ 未覆盖 | 本地仅覆盖离线 CLI 入口（`--version` / `--help`）与启动前置 |
