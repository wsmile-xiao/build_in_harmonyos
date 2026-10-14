# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_9e30970a.md`

---

## 背景

- **软件名称**: ksystemstats
- **版本**: 6.7.2
- **构建日期**: 2026-09-27
- **构建系统**: cmake
- **上游仓库**: https://invent.kde.org/plasma/ksystemstats
- **源码**: https://download.kde.org/stable/plasma/6.7.2/ksystemstats-6.7.2.tar.xz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 17
- **编译依赖**:
- qtbase/6.11.1.1
- kcoreaddons/6.18.0
- kcrash/6.18.0
- solid/6.26.0
- libksysguard/6.7.2
- qtdeclarative/6.11.1
- kservice/6.18.0
- libnl/3.11.0
- eudev/3.2.14
- libdrm/2.4.133
- ecm/6.26.0
- dbus/1.14.10.1
- kconfig/6.18.0
- ki18n/6.18.0
- kauth/6.18.0
- kpackage/6.18.0.1
- knewstuff/6.26.0
- karchive/6.18.0
- kwidgetsaddons/6.18.0
- qtshadertools/6.11.1
- qtbase-sql-dbus/6.11.1
- dbus/1.14.10
- expat/2.8.2
- zlib/1.3.2
- openssl/3.5.6.1
- **未使用（列出但未声明）**: lm-sensors/3.6.0、kio/6.26.0 —— 见「失败与问题」#1 与「知识图谱覆盖」
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 官方 KDE release，sha256 独立复算校验通过 |
| build | 编译构建 | 成功 | 构建系统: cmake（Ninja；make jobserver mkfifo 被沙箱拒绝）；104 个目标 100/100 |
| conan-verify | 配方验证 | 通过 | G1 配方完整性 PASS、G0 预扫描 PASS、G2 干净 `conan create` PASS、G3 系统同名库隔离 PASS、G4 产物完整性 PASS；结论「可标记 status: published」。注：finish Step3 的独立 G0 干净构建（通用 `configure` 探测）对纯 CMake 项目非阻塞失败（exit 127，项目无 configure 脚本），自包含性以 G2 实证 |
| finish | 归档收尾 | 完成 | 首次因 JC 以陈旧 `origin/main` 为基线误报 709 包而 HANDOFF；修正基线后 `finish_success`，W3 通过并写入 `.ci-result.json` |
| submit | PR提交+AI检视+CI | 通过（PR #13269） | 四项门禁（token/finish/W3/W4）+ 6 项自检全过 → git push ✅；PR 创建经平台 API 完成；AI Review: 仅收到「进行中」通知，**未产出任何检视意见**；CI 通过（build #62944） |

### 失败与问题

- **1**: 根因=`find_package(KF6 ... KIO ...)` 失败, 解决方案=上游顶层硬性要求 KIO，而 KF6 6.18 系列没有可用 kio。实测 `kio/6.26.0` 硬依赖 `kcoreaddons/6.26.0`，与 `libksysguard/6.7.2`（KF6 6.18 矩阵）冲突；强制 override 会级联到 `kpackage/6.18.0.1`→`karchive/6.18.0` 并迫使 libksysguard 放弃预编译包从源码重建。→ 把 KIO 变为可选开关 `KSYSTEMSTATS_USE_KIO`（配方置 OFF）并为 disks 插件提供等价的 `QStorageInfo` 实现。
- **2**: 根因=KF6 版本墙, 解决方案=上游要求 KF6 ≥ 6.26.0，已发布矩阵是 6.18。→ 补丁把 `KF6_MIN_VERSION` 降为 6.18.0（libksysguard 6.7.2 先例）。
- **3**: 根因=`find_package(KSysGuard)` 报 `Qt6::Qml`/`KF6::Service` 目标不存在, 解决方案=KSysGuardConfig.cmake 只 `find_dependency` 了 Qt6Core/Network/Widgets 与 KF6Config/KF6I18n，但其导出目标的链接接口含 Qt6::Qml/Qt6::Quick/KF6::Service。→ 在 `find_package(KSysGuard)` **之前**显式 `find_package(Qt6Qml/Qt6Quick/KF6Service)`，并补 qtdeclarative/kservice 直接依赖。
- **4**: 根因=`ksystemstats_plugin_cpu` 链接失败：`target_link_libraries` 签名混用, 解决方案=上游该目标用 plain 签名，我新增的调用用了 PRIVATE。→ 新增调用改回 plain 签名（CMake 要求同一目标签名一致）。
- **5**: 根因=`libdrm/i915_drm.h` 找不到, 解决方案=Intel helper 目标没有任何 include；该头位于 `<libdrm 包>/include/libdrm/`，不在默认搜索路径。→ `find_path(LIBDRM_INCLUDE_DIR NAMES libdrm/i915_drm.h)` 后显式加 include。
- **6**: 根因=`std::ranges::transform` 不存在, 解决方案=OHOS SDK libc++（clang 15）ranges 算法集不全（libksysguard 0005 同因）。→ 改写为经典 `std::transform`，语义不变。
- **7**: 根因=`redefinition of 'sockaddr_storage'`（内含两次返工）, 解决方案=命中知识条目 **E091**。bionic `sys/socket.h` 仅在 `__MUSL__` 下引入 `linux/socket.h`，否则自带该结构，而 libnl 会拉入内核头。第一次按 E091 原文在 libnl include 周围重命名，结果 `__linux_sockaddr_storage` 二次重定义 + 宏泄漏到 `netinet/in.h`；最终版为：先解析 libc 头，仅在 `#include <linux/socket.h>` 周围用 `#if defined(__linux__) && !defined(__GLIBC__)` 重命名，依赖该头自身 include guard 使后续引入成为空操作。
- **8**: 根因=`disks.cpp` 报 `const QStorageInfo (QString)` 不是结构体, 解决方案=最烦琐解析（most vexing parse）。→ 路径先绑定具名变量再构造。
- **9**: 根因=TestLinuxCpu 编译失败：缺 `KLocalizedString` / `sensors/sensors.h`, 解决方案=该 autotest 直接编译插件源文件，但没有继承插件的私有依赖。→ 为测试目标补 KF6::I18n 与（启用时）lm-sensors 的 include/lib。
- **10**: 根因=`undefined symbol: KSysGuard::makeSensorsFeatureSensor`, 解决方案=已发布 `libksysguard/6.7.2` 未启用 lm-sensors（其 `systemstats/CMakeLists.txt` 用 `if(SENSORS_FOUND)` 门控 `SensorsFeatureSensor.cpp`，而头文件在裸 `#ifdef Q_OS_LINUX` 下无条件声明），实测其 5 个库中该符号数为 0。→ 属 R36 情形（依赖已发布但配置不满足下游）；经确认后不声明 lm-sensors，新增中立开关 `KSYSTEMSTATS_WITH_LM_SENSORS`/`HAVE_SENSORS` 与 libksysguard 同语义门控，并如实记录功能缺口与恢复路径。
- **11**: 根因=上游 ctest 运行期 `Error loading shared library ../bin/libKSysGuardFormatter.so` 与 `~/.cache/conan2/...` 绝对路径, 解决方案=已发布 libksysguard 的 ELF 记录了两类带斜杠的 DT_NEEDED：绝对路径指向构建机的旧 Conan cache 前缀 `~/.cache/conan2`，以及相对路径 `../bin/libKSysGuardFormatter.so`（加载器对含 `/` 的 NEEDED 一律按原样解析，不走 LD_LIBRARY_PATH）。→ 命中 E537；配方 `_bridge_legacy_needed_paths()` 建立兼容链接（旧前缀目录 symlink 到活动缓存 + 每个 ctest 工作目录物化 `../bin` 链接）。
- **12**: 根因=`ksystemstatstest` SIGSEGV（访问 0x60）, 解决方案=`libQt6DBus` 用 `QLibrary("libdbus-1")` **运行期**加载 dbus 客户端（readelf 既无 `dbus_*` 未定义符号也无 `libdbus-1.so` 的 NEEDED 项，因此静态检查会误判为"已静态链接、无需共享库"），制品仓只有**静态** `libdbus-1.a` → 加载失败，`QDBusConnection::sessionBus()` 返回未连接对象（`isConnected()==false`）→ QtDBus 无空值保护崩溃。→ 复刻 kglobalacceld 方案：从官方 dbus 1.14.10 源码编译共享 `libdbus-1.so`，纳入运行期 `LD_LIBRARY_PATH` 并随包安装到 `lib/`。
- **13**: 根因=打包后的守护进程 `No plugins found`, 解决方案=KDEInstallDirs 把插件装到 `<prefix>/lib/plugins`，而 `package_info` 里写的是 `<prefix>/plugins`。→ 修正 runenv `QT_PLUGIN_PATH` 为 `lib/plugins`。
- **14**: 根因=`--print-address` 读不到总线地址, 解决方案=重定向到文件的 stdout 是块缓冲，地址迟迟不落地（`--print-address=3` 在 conan 的 shell 包装下 fd 不可用）。→ 消费端测试改用 `dbus-run-session --config-file=<tcp conf>` 自行启动并导出地址，脚本在其内部 re-exec。

### 知识图谱使用情况

- **引用知识条目**: E091（`sockaddr_storage` 内核头/libc 冲突，命中后发现其推荐补丁形态需按 bionic 的头文件守卫顺序调整才能生效）、E537（Conan cache 绝对路径 / 相对路径 DT_NEEDED 泄漏与桥接）
- **新增知识草稿**: 6 条（写入 `manifest.yaml` 的 `knowledge_gained`，均为本次实测结论）
- **引擎命中情况**: engine 对 `sockaddr_storage` 报错命中 E091（Phase B）；其余报错无命中，已按要求沉淀为草稿
- **测试统计**: 总计 3, 通过 3, 失败 0, 跳过 0（上游 CTest）；另有消费端 test_package 11 项断言全过
- **未覆盖的错误模式**: 见下方「知识图谱覆盖」小节（4 类建议新增条目，其中 2 类为框架/工具层而非编译层）

### AI 检视结果

- **检视阶段到达**: 阶段 1–2（`atomgit-bot` 仅发出「正在生成合并请求摘要」与「AI 代码检视正在进行中」两条通知，其后约 24 分钟内未再产出任何内容）
- **变更摘要评估**: 未产出摘要（bot 停留在「正在生成」状态），故无可评估内容
- **检视意见数量**: 0 条
- **检视意见处理**: 无意见需处置（非"已全部闭环"，而是平台未给出意见）。**W4 独立审计**（本地派发，非平台 bot）已完整执行并闭环：3 轮审计，第 1 轮发现 P2/R52（manifest 记录的 L4/L5 与实际门禁输出不符）→ 修正；第 2 轮确认修复并发现 P3 文案残留 → 修正；第 3 轮终审 `verdict=pass`（P0/P1=0）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`conan create` EXIT=0；上游 3/3；消费端 PASS 274 传感器；L0 pass / L1 pass / L2 skip / L4 warn / L5 pass；JC/KC pass）
- **远程 CI (PR 校验)**: 通过（build #62944，worker `OpenHarmonyPCDeveloper-CI-040`；`conan-build-test` ✅、L0 结构完整性 ✅、L1 测试执行 ✅、test_package ✅，7 步全 ✅）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 4 次（finish 1 次 = `w3_local_ci_failed`（JC 以陈旧 `origin/main` 为基线误报 709 个包）；submit 2 次 = `self_check_failed`（`packaging_present`/`test_report_present`）、`pr_creation_failed`（GitCode API 通道）；result 1 次 = `result_invalid`（partial 缺 `--failed-reason`））。另有一次 result 成功硬闸因 CI 状态 API 返回 UNKNOWN 而降级 partial（非 HANDOFF，但需改为 `--no-ci-verify` 才写入终态）
- **重试次数**: `conan create` 全量约 10 轮（其中编译/链接类 6 轮、运行期类 3 轮、基线类 1 轮）；`refresh-patch --auto` 约 14 次；`dbus-daemon` 会话总线启动方案迭代 3 次（`--print-address` → `=3` → `dbus-run-session`）
- **关键瓶颈**: ①**git 基线**：本 worktree 的 `origin` 为个人 fork 且 `main`/`origin/main` 严重滞后（`origin/main...HEAD` 含 9873 文件/709 包），导致 JC 与 W4 审计的变更集完全失真，浪费一整轮 `finish`；离线环境下无法刷新该 fork。②**平台通道**：`gitcode_pr.py create-pr` 面向 `api.gitcode.com`，而本环境 remotes 均为 `atomgit.com`，push 落在 fork 后必然报 `Can not find the branch`。③**共享 `$HOME` result 路径**：多任务并发写入同一路径互相覆盖（本次覆盖了兄弟任务 PR #13273 的 partial；同目录另有 lepton-eda 造成同类覆盖的备份文件为证）。④长时 `conan create` 在工具调用间隙被 SIGTERM 回收（需在同一调用内完成轮询）。
- **耗时较长的步骤**: 全流程约 3.5 小时。其中：QtDBus 会话总线不可用的定位（插桩 → 宏探针 → `QLibrary` 日志 → 独立探针二分，约 40 分钟，含 3 次全量重建）；AI Review 等待（约 25 分钟，最终无产出）；`conan create` 全量构建（每轮 6–8 分钟 × 约 10 轮）；上游测试与消费者端到端调试（约 30 分钟，含 `--print-address` 缓冲与插件路径两处返工）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 2 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-27T18:20:59 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit ksystemstats 6.7.2 |
| 2026-09-27T18:25:17 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/ksystemstats-6.7.2 --target main --title 'feat(ksystemstats): 6.7.2 适配完成' |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **【阻断级】PF9 与 PF8 自相矛盾，必须二者取一。** 实测：`preflight.py` PF9（`check_branch_and_paths`，第 570 行 `len(f.split("/")) < 5`）要求所有 `archives/` 变更路径必须有版本目录层，于是**必然**拦下软件级 `archives/<字母>/<包>/{README.md,commands.json,manifest.yaml}`；而同文件 PF8（第 518 行）又强制「CLI 包（`package_type=application` 或 `bindirs` 非空）**必须**有软件级 `commands.json`」。本包是 application 且 bin/ 有产物，**两条硬闸对本包不可同时满足**——这是逻辑上的死锁，不是使用姿势问题。PF9 的单测 `tests/test_v1220.py:134` 明确把 `archives/d/demo/readme.txt` 断言为「应拦」，说明该行为是设计意图而非笔误。**建议**：PF9 白名单化三个规范软件级文件名（`README.md`/`commands.json`/`manifest.yaml`，即 ARCHIVE-SPEC §2.1 与 `.gitcode/review-memory.md` §17 定义的合法集合），并补一条「软件级文件 + 版本目录文件共存」的回归用例。佐证：自 PF9 落地（skill `preflight.py` mtime 2026-09-24）以来，线上已合并提交新增了 **349 个软件级 `commands.json`**（含积分赛 `thc 3.8`、`jaaa 0.9.2`、`jpegjudge 0.0.2`），即线下实际上一直在用逃生口或已被拦后人工放行。

2. **【阻断级】submit 自检 `packaging_present` 与 R19 / ARCHIVE-SPEC v3.0 冲突，应删除或降级。** `submission.py:210 _check_packaging_present` 在 `status ∈ {published, built}` 时要求 `packaging/*.tar.gz` 存在，且该检查在 `cmd_submit` 中为**致命**（第 1078–1094 行），无环境变量或参数逃生口（`submit --help` 仅 `--resume/--no-wait`）。但：①`KNOW_YOUR_WHY.md` S4 与 iron-rules **R19 明令禁止手动打包**（`tar czf`），ARCHIVE-SPEC v3.0 亦已声明「`packaging/` 目录废弃（Conan 体系替代手动 tar.gz）」；②全仓 `git ls-files` 中 `packaging/*.tar.gz` **命中 0 例**；③同族已合并包 `libksysguard/6.7.2`、`kglobalacceld/6.7.2`、`thc/3.8`（均 `status: built`）**均无**该产物却已合并；④`packaging/` 已被 `.gitignore`（第 2 行）覆盖，即设计上不进 PR；⑤其唯一生产者 `package_builder.py` 已无任何调用点与 CLI 入口（死模块）。**建议**：删除该检查，或改为「若 `packaging/` 存在则仅校验其内容」的非阻塞项，与 `_review_single` 中的 WARN 口径一致。

3. **变更集基线应统一为「官方 main」而非 `origin/main`。** 本次三处基线不一致且含义错位：JC 用 `origin/main...HEAD`（个人 fork，滞后 9873 文件）、preflight 用 `main...HEAD`（本地分支，滞后 4200 文件/301 包）、W4 审计 `pre_pr_audit.py:71` 用 `origin/main...HEAD`。建议统一为「`upstream/main` 或 PR 目标仓的 main」，并在取不到时明确告警而非静默按陈旧基线计算——本次若基线正确，JC/W4 根本不会产出那 709 包/97 条噪音。

4. **`git push` 与 `create-pr` 的目标平台应在运行前校验一致。** 本次 submit 的 `git push ✅` 推到了 fork（AtomGit），而 `create-pr` 调 `api.gitcode.com`，造成「推送成功但建 PR 必然失败」的确定性失败（报 `Can not find the branch ... in project`）。建议在 submit 开头增加一道「remote 平台 ↔ `gitcode_pr.py` API 平台」一致性检查，并把 HANDOFF 的 `手动创建` 提示改为按实际 remote 生成。

5. **共享 `$HOME/ohpcd-ai-worker-result.json` 应改为按任务隔离。** 该兜底路径为多任务共享，本次覆盖了兄弟任务 PR #13273 的 partial 记录；`~/tmp/result-json-overwritten-by-lepton-eda.json` 说明同类事故此前已发生。建议兜底路径含软件名/PR 号（如 `$HOME/ohpcd-ai-worker-result-<pkg>-<ver>.json`），或在写入前检测内容归属并拒绝覆盖他包记录；HANDOFF 应默认打印显式 `--out` 路径。

6. **`finish` Step3 的通用 G0「干净构建」对纯 CMake 项目应跳过或改用项目自身构建系统。** 本项目无 `configure` 脚本，G0 的 `configure` 探测必然 exit 127，产生一条无意义的非阻塞失败与 HANDOFF 噪音。

### 模板改进

1. **`templates/积分赛事PR模板.md` 的「上游库测试用例统计」需要子项定义。** 本次 submit 自动生成的 `reports/pr-body.md` 把它填成 **0/0/0**（实际 3），并把「上游仓库地址」填成 **tarball URL** 而非上游仓库（`https://invent.kde.org/plasma/ksystemstats`），还据补丁存在与否**误判为「是，存在对上游测试用例的修改」**（实际未改任何测试）。建议：①模板为「测试类型」给出判定口径（CTest 注册数 / QTest 函数数 / 上游 `autotests/` 目录数）；②「上游仓库地址」显式区分 repo 与 tarball 字段；③「是否修改上游测试用例」应基于「是否改动测试文件内容」判定（门控类补丁只改 CMake 注册条件，不等于改测试）。
2. **submit 的 pr-body 生成器应消费 `test_package/MANIFEST.yml` 与 `manifest.yaml` 的既有字段**（`upstream_registered`/`upstream_executed`/`upstream_pass_rate`/`upstream_tests`），而不是从 `notes.md` 猜测；否则自动正文与人工申报会互相矛盾，评审需要额外甄别。
3. **`templates/test-report.md` 建议内置「上游测试 vs 消费者端到端」两段式结构**（本次我在报告中自行分为 3.1/3.2），并内置「已知限制 + 恢复路径」小节，便于如实披露功能缺口。
4. **feedback 模板的背景区块应自上游仓库字段取值**（当前取了 `source_url` 即 tarball），并且「测试统计: 总计 0, 通过 3」这类自相矛盾的派生值需要修（总计应为 3）。

### 自动化补全

1. **`refresh-patch` 后自动同步 `conandata.yml` 与 `manifest.yaml` 的补丁文件名，并自动清理 `.patch-backup-*`/`.patch-staging`，以及自动删除写入 manifest 的 `patch_generation`/`patch_classification` 段。** 本次 `finish`（内含 refresh-patch）把这两个工具段（含构建机绝对路径）重新写进 `manifest.yaml` 并随提交入库，需事后追加一次修正提交；`patch_generation.source_orig_dir` 泄漏了本机绝对路径。仓库内**0 个已合并包**保留这两段，说明本应自动清理。
2. **`_check_packaging_present` 的替代方案自动化**：若框架确实需要「构建产物归档」，应自动调用 Conan 原生 `conan cache save`（本次为满足该遗留检查所用方案），而不是期望人工 `tar czf`。
3. **会话总线等「环境前置」应工具化**：本次为 `dbus-daemon` 的 TCP+ANONYMOUS 私有总线、`--print-address` 缓冲、`dbus-run-session` 自举迭代 3 轮。建议在 skill 层提供 `ohc-run.py session-bus`（或复用 kglobalacceld 的实现）供测试阶段调用。
4. **长时 `conan create` 与工具调用生命周期解耦**：本环境多次出现后台进程在调用间隙被 SIGTERM 回收（构建日志出现 `Received SIGTERM` 但并非构建失败），建议提供「后台构建 + 状态文件」模式，避免误判为失败并重复全量重建。
5. **`result` 的 CI 状态核验应支持 AtomGit 平台**：本次 `status=success` 被硬闸以「PR 最新 CI 状态 UNKNOWN」降级为 partial，而 CI 实际已绿（平台机器人 build #62944 明确通过）。建议核验逻辑识别 remote 平台并按对应 API 判定，减少无谓的降级与 `--no-ci-verify` 使用。

### 知识图谱覆盖

本次建议新增/扩充以下条目（前 2 类对后续 KDE/Plasma 系适配具有普遍价值）：

1. **【建议新增 E-entry】OHOS 平台判定双轨错配**：OHOS clang 目标 `aarch64-linux-ohos` **同时定义 `__OHOS__` 与 `__linux__`**，故 Qt 的 `qsystemdetection.h` 令 `Q_OS_LINUX` 成立、源码全部走 Linux 分支；而 conan 把 `settings.os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，使上游所有 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` / `MATCHES "Linux"` / `LINUX` 门控为假。两者矛盾会让「源码引用 Linux 后端、CMake 却排除这些源文件」的项目必然编译失败。修复形态：引入单一 `*_LINUX_PLATFORM` 变量统一两侧（本包 `KSYSTEMSTATS_LINUX_PLATFORM`）。影响面广（任何同时使用两种惯用法的项目），且与已有 `qtbase/6.12.0-beta3` 的 `0008-disable-qos-harmony-define.patch`、`isoimagewriter` notes 属同一根因族。
2. **【建议新增 E-entry】依赖侧配置缺口导致 `makeSensorsFeatureSensor` 未定义**：已发布 `libksysguard` 若未启用 lm-sensors（其 `systemstats/CMakeLists.txt` 用 `if(SENSORS_FOUND)` 门控 `SensorsFeatureSensor.cpp`），则**头文件仍在裸 `#ifdef Q_OS_LINUX` 下无条件声明**该函数 → 消费方编译通过、链接失败。判定方法：`readelf -sW --dyn-syms <lib> | grep makeSensorsFeatureSensor` 为 0。属 R36 情形（依赖已发布但配置不满足下游），正确处置是下游按库自身的 `SENSORS_FOUND` 语义门控并如实记录缺口，而非强制重建依赖。
3. **【建议新增/扩充 E537 或新条目】Qt 库经 `QLibrary` 运行期加载系统库**：`libQt6DBus` 既不记录 `libdbus-1.so` 的 NEEDED 项、也无 `dbus_*` 未定义符号（readelf 会误判为「已静态链接」），而制品仓只发布静态 `libdbus-1.a` → 加载静默失败 → `QDBusConnection::sessionBus()` 未连接（`isConnected()==false`）→ 首次 D-Bus 调用 SIGSEGV（访问 0x60）。排查关键：`QT_LOGGING_RULES="*=true"` 才会打印 `qt.core.library: "libdbus-1" cannot load`。修复：vendor 共享 `libdbus-1.so`（官方源码 + 运行期 `LD_LIBRARY_PATH` + 随包安装）。
4. **【建议新增小型条目】KDEInstallDirs 插件安装路径**：KDE/ECM 项目经 `KDE_INSTALL_PLUGINDIR` 安装到 `<prefix>/lib/plugins`（而非 `<prefix>/plugins`），故包的 `runenv_info`/`QT_PLUGIN_PATH` 必须指向 `lib/plugins`，否则 `KPluginMetaData::findPlugins("<app>")` 找不到插件、守护进程静默「No plugins found」。另可附注 `kstatsviewer --list` 对无子对象的容器输出 `<id> <name>`（而非 `<id>/...`），断言需兼容两种形态。
