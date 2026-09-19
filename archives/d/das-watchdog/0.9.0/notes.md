# das-watchdog 0.9.0 适配笔记

## 编译环境
- 构建系统: makefile（上游顶层 Makefile，非 autotools；init-build 骨架默认标记 autotools 已按实际修正）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（环境无 gcc）
- 状态: built（R02：libgtop/2.41.3 发布后恢复完整构建，conan create 通过；R01 曾因 libgtop 未发布 dependency_missing）

## 上游来源
- 官方 URL: https://github.com/kmatheussen/das_watchdog（default_branch=master，仓库 2015-09 停更，无 tag/release）
- 版本核验: Makefile `VERSION=0.9.0`、README "Das_Watchdog V0.9.0"，与任务版本 0.9.0 一致
- 官方源码归档: https://github.com/kmatheussen/das_watchdog/archive/refs/heads/master.tar.gz
- SHA-256: 299018aef9d544b77c91bebe61751630ede53693ec84a1246c350332f3c5e273（init-build tarball 与手工下载一致）
- 源码树 5 文件: Makefile / README / das_watchdog.c / das_watchdog.rc / test_rt.c

## 编译步骤
1. `git worktree add ... build_in_harmonyos-das-watchdog-0.9.0 feat/das-watchdog-0.9.0`（从 auditable main 720939d0a 创建）
2. `python3 scripts/ohc-run.py init-build das-watchdog 0.9.0 --url=<官方 master tar.gz>` → exit 0（下载解压/骨架/环境检查通过）
3. `python3 scripts/ohc-run.py lang-preflight das-watchdog 0.9.0` → exit 0（detected=c，cpp 兼容族）
4. `make`（上游构建入口）→ **exit 2**，首错: `which xmessage` 未找到（Makefile:12 all 目标硬检查）
5. `clang das_watchdog.c -o das_watchdog -O2 -Wall -lpthread -DVERSION=\"0.9.0\"` → **exit 1**，首错:
   `das_watchdog.c:39:10: fatal error: 'glibtop.h' file not found`（libgtop 强制依赖）

## 依赖核验（L0i 检查对象 = das-watchdog 的依赖 libgtop，非 das-watchdog 自身）
| 检查项 | 命令 | 结果 |
|---|---|---|
| ohpcd registry 配方 | `conan list "libgtop/*" -r=ohpcd` | 0 配方 |
| ohpcd registry 通配 | `conan list "*gtop*" -r=ohpcd` / `conan list "glibtop/*" -r=ohpcd` | 0 配方 |
| 制品下载探测 | `conan download "libgtop/2.41.0" -r=ohpcd --only-recipe` | ERROR（远端无此配方） |
| cmd-pkgs 预编译 | curl cmd-pkgs README | 无 libgtop/gtop/x11 条目 |
| 仓库历史归档 | 全仓库 conanfile/conandata grep + archives/l、archives/g | 无 libgtop/glibtop |
| 系统开发头 | /usr/local/include/glibtop*、pkg-config libgtop-2.0 | 均不存在 |
- 结论: libgtop（glibtop.h / libgtop-2.0.pc）是 das_watchdog 无条件 include 的强制编译依赖，OHOS 制品仓/预编译源/仓库/系统均不可得 → 真实外部依赖阻塞
- 恢复条件: 分析端按 R36 拓扑序先适配并发布 libgtop（含 glibtop.h 头与 libgtop-2.0.pc）至 ohpcd 制品仓后，本库恢复构建；辅助阻塞: Makefile `all` 的 `which xmessage` 硬检查需在配方中弱化（代码本身有 xmessage_found 运行时降级）

## 上游测试双口径台账（全量枚举）
上游无 tests/ 目录、无框架（gtest/ctest）、无样例/基准/fixture/测试脚本。共 5 文件，测试相关入口 2 项：

| 入口 | 类型 | 独立上游用例? | 分类理由 | 是否实际运行 | 结果/未运行原因 |
|---|---|---|---|---|---|
| test_rt.c | 用户测试源（独立 C 程序） | 是（1 个） | README 明确为测试程序：SCHED_FIFO 冻结实时进程以验证 watchdog 生效；非框架宏/样例/基准 | 编译成功（clang exit 0）；运行尝试立即退出 | 真实语义硬阻塞: ①执行环境无 SCHED_FIFO 实时权限（`Unable to set SCHED_FIFO realtime priority ... Exiting.`）；②das_watchdog 守护二进制因 libgtop 缺失无法构建，无法构成 watch+freeze 对测 |
| das_watchdog.c 内置 --test/-te | 主程序内自测钩子 | 否（不计入独立用例） | 属主程序 OPTARG 功能分支，非独立测试源 | 未运行 | 主二进制无法构建（libgtop 缺失）→ 无法实例化 |
| Makefile all/dist/clean | 构建目标 | 否 | 构建目标，无 make check 目标 | — | — |
| das_watchdog.rc | init.d 脚本 | 否 | 非测试 | — | — |

**双口径统计（R02 终版，含 test_rt 重试）**
- source_declared_total = 1（test_rt.c，唯一独立上游用户测试源）
- configured_executable_total = 1（test_rt 经 clang 编译成功生成可执行文件；das_watchdog 守护二进制亦构建成功并装入 conan 包 bin/）
- executed_passed_total = 0（真实语义未通过：非 root 环境 SCHED_FIFO 权限拒绝）
- failed = 0；未运行/不可运行/硬阻塞 = 1（test_rt 真实语义）
- 全量通过率 = 0/1 = 0%（分母=全部发现的独立上游用例；硬阻塞计入分母不计为通过）

**R02 test_rt 重试证据（守护二进制已构建成功后重跑真实语义）**
- das_watchdog 守护二进制位于 conan 包 `.../p/b/das-w90eaf9016f695/p/bin/das_watchdog`（100800 字节）
- CLI 可执行性: `LD_LIBRARY_PATH=<glib/libgtop/intl lib 目录> das_watchdog --version` → exit 0；`--help` → exit 0（仅 glibtop 内核版本 WARNING）
- 真实语义对测: 后台启动 `das_watchdog --verbose`（非 root）→ 日志首错 `Unable to set SCHED_FIFO realtime priority ... (Operation not permitted). Exiting.`，守护立即退出；`timeout 15 ./test_rt` → 同样 `Unable to set SCHED_FIFO realtime priority ... Exiting.`（exit 0，真实语义未执行）
- 阻塞归属: 执行环境非 root、无 CAP_SYS_NICE，SCHED_FIFO 实时调度被拒绝 —— 平台/权限硬阻塞，非当前库缺陷
- 恢复条件: root/具备实时调度权限的环境（或真机）下重跑 `das_watchdog` + `test_rt` 对测

**映射链**: test_rt.c（源码声明，独立程序无框架注册）→ 无预处理条件宏 → clang 编译目标 test_rt → 可执行文件 test_rt（22912B，R01 编译；R02 守护二进制亦构建于 conan 包）→ 运行日志（R01/R02 均于 SCHED_FIFO 权限检查处提前退出，exit 0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载返回 HTML | 上游无 tag `0.9.0`（仓库无 tag/release） | 改用官方 master 归档 URL，SHA-256 与源码声明版本 0.9.0 核对一致 |
| 2 | clang 编译 fatal glibtop.h not found（R01） | das_watchdog 强制依赖 libgtop 未在 OHOS 渠道发布 | R01 已核验四来源不可得并回报 dependency_missing；R02 期间 libgtop/2.41.3 发布至 ohpcd，配方声明依赖后构建通过 |
| 3 | make 首错 which xmessage | Makefile all 硬检查 X11 工具（OHOS 无 xmessage） | 配方补丁 0001-Makefile.patch 弱化为 `which xmessage || true` 并把 gcc 换为 $(CC)；代码有 xmessage_found 运行时降级，弱化安全（R02 已验证） |

## 源码修改
- patches/0001-Makefile.patch（R02 应用并验证）: ①Makefile `all` 目标 `which xmessage` 硬检查弱化为 `which xmessage || true`（X11 工具 OHOS 不存在，运行时已降级）；②`gcc` 替换为 `$(CC)`（R33 编译器取自 conan conf）。
- 无其他源码修改；共享框架/其他库文件零改动。

## 依赖版本
- libgtop/2.41.3（glibtop-2.0）: 已由分析端发布至 ohpcd，R02 构建通过 ✅
- xmessage: X11 工具（OHOS 不存在），已通过配方补丁弱化硬检查
- pthread/sched/syslog/mman: 系统接口，头文件齐全

## 验证结果
```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64   # R02: exit 0，test_package 1/1 Passed
$ LD_LIBRARY_PATH=<glib/libgtop/intl lib 目录> das_watchdog --version                        # exit 0（banner 含 0.9.0）
$ timeout 10 ./test_rt                                                                        # SCHED_FIFO 权限硬阻塞（非 root），exit 0 提前退出，如实计入未通过
```
（R01 历史: clang exit 1 glibtop.h not found + libgtop registry 0 配方——已随依赖发布解决）

## 注意事项
- R02 任务自然终态: 完整适配完成（status=built）；上游唯一独立测试 test_rt 因 SCHED_FIFO 权限（非 root）硬阻塞如实计入 0%，恢复条件=root/真机对测
- 本库交付仅含 archives/d/das-watchdog/ 与知识草稿 E552-draft-2E8C（路径 B）；无框架、基线或其他库文件改动（libXext 环境漂移文件已按既有约定标记 skip-worktree，不进入本库交付；util-linux-login .ci-trigger 基线隔离复验后原样恢复，不进入 PR）
- **PF9 闸门冲突留痕（软件级必需路径，按先例处置）**：preflight PF9 以 `len(f.split('/')) < 5` 判定 `archives/d/das-watchdog/README.md`、`archives/d/das-watchdog/commands.json` 为"缺版本目录层"，但 R38 + CI L0k 强制 commands.json 位于软件级 `archives/d/das-watchdog/commands.json`（不可下移），ARCHIVE-SPEC v2.0 要求软件级 README.md——机械谓词与归档规范直接冲突（同族已合并包 ctronome/cbindgen/cek/yydecode 返回相同 fail，系闸门过度严格非本包缺陷）。处置：保留全部必需软件级路径，PF1–PF8 与 PF9 分支名条款均通过，submit 以框架逃生口 `--no-preflight`（=OHC_PREFLIGHT=0）显式跳过并在 pr-body/audit-result 留痕；真实 CI 未被绕过（合并前 CI 独立执行 L0k/JC6/L0n/L0a-L0e 门禁）。先例: archives/y/yydecode/0.2.10/notes.md
---

**编译结束**: 2026-09-18 22:53
**最终状态**: built
