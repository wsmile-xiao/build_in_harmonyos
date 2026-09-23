# irsim 9.7.104 适配笔记

## 编译环境
- 构建系统: makefile（自制 configure，scripts/configure 为 autoconf 生成）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX`
   - 修复 config.guess（2014 版无 HarmonyOS 分支）：补 `*:HarmonyOS:*:*` echo 分支 + config.sub 补 `linux-ohos` 三元组
   - 修复 configure 中 umask 077 → 022（HMDFS 平台 E011：umask 077 创建的临时目录对当前进程不可写）
   - 修复 configure 图形分支：非 Tcl 非 X11 时 gr_srcs 错误保留 thread.c（依赖 X11/Xlib.h 无法编译），改为回退 `${NULL_SRCS}`（noana.c）
2. `make -j1`
   - 修复 base/mem.c：GetMoreCore 在 OHOS 平台 sbrk 返回失败（SYSV/BSD 分支），扩展 malloc 分支条件 `__OHOS__`（与上游 CYGWIN/APPLE 先例一致）
   - 修复 analyzer/noana.c：补全无图形模式缺失的 OffsetNode/OffsetVector/EnableInput/DisableInput 符号
3. `make install DESTDIR=<staging>`——成功，产物含 bin/irsim、bin/gentbl、bin/genspktbl、lib/irsim/prm 参数库、man 页

## 问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS（cannot guess build type） | 2014 版 config.guess 无 HarmonyOS 分支 | 补 `*:HarmonyOS:*:*` 分支输出 aarch64-unknown-linux-ohos |
| 2 | config.status could not setup config files machinery（Permission denied） | HMDFS 上 umask 077 临时目录不可写（E011） | configure 中 umask 077 → 022 |
| 3 | analyzer/thread.c 需 X11/Xlib.h（configure 报 X11 缺失后仍编译 thread.c） | 非 Tcl 非 X11 时 gr_srcs 未回退 NULL_SRCS | configure 图形分支补 else 分支用 ${NULL_SRCS} |
| 4 | irsim 启动 MEMORY WARNING：sbrk(4MB) 失败 | OHOS 上 sbrk 返回 -1（BSD/SYSV 分支） | mem.c GetMoreCore 扩展 `__OHOS__` 到 malloc 分支 |
| 5 | 链接失败：undefined EnableInput/DisableInput/OffsetNode/OffsetVector | noana.c 缺无图形模式需要的 4 个符号 | noana.c 补全（与上游 analyzer.c 语义一致，均为 no-op return 1） |

## 上游测试台账（双口径）

### 枚举口径（source / 测试入口全集）

| 入口 | 路径 | 类型 | 是否独立上游用例 |
|------|------|------|------------------|
| foo.sim | lib/test/foo.sim | .sim 网表示例（2 电容节点） | 否（示例数据，无断言）——实际加载验证通过（exit 0，4 nodes，time=0） |
| z.test 目录 | lib/test/z.test/ | control.ps + foo.c + foo.ps（波形 PostScript 样例） | 否（样例/基准，无可执行测试逻辑） |
| prm 参数库 | lib/prm/、lib/calibrate_hspice/、lib/calibrate_spice3/ | 工艺参数数据文件（.prm） | 否（数据资源，非测试） |
| Makefile 测试目标 | 顶层 Makefile、各子目录 Makefile、rules.mak | 无 test/check/loci/regress 目标 | 无测试目标 |
| ctest / GTest / 测试脚本 | 全仓 | 无 tests/ 目录、无注册清单、无测试脚本 | 无 |
| 辅助工具 | irsim/gentbl、irsim/genspktbl（已构建） | 建表工具（非测试） | 否——冒烟运行通过 |

### 双口径结论

- `source_declared_total` = 0：官方 tag 源码（9.7.104）不含可复制枚举的独立测试用例声明（无 ctest -N 注册、无 GTest TEST_CASE、无 make check）。irsim 为 SPICE 电路仿真器 CLI，上游不以单元测试形式提供自测程序。
- `configured_executable_total` = 0（当前 OHOS 配置无独立测试可执行用例；irsim 主程序本身为产品程序，lib/test 为示例数据）。
- `executed_passed_total` = 0；失败 0；未运行/未实例化 0。
- 表示方式：0/0 (N/A)，因为分母为 0（上游无独立测试用例）。示例数据 foo.sim 已实际加载、c 命令因网络无时钟节点属预期数据特性、d/p 命令正常、进程 exit 0；gentbl/genspktbl 冒烟 exit 0。

### 逐项映射说明

源码声明 -> 预处理/构建条件 -> 构建目标 -> 注册项 -> 执行日志：上游无测试声明，故无映射链；lib/test 属于示例数据（classified as sample），不构成独立用例（framework macro / sample / bench 不计入独立用例）。任务硬门禁"全部独立上游测试通过"在分母为 0 时自然满足（0/0 无未通过项），完整性由上述全仓枚举证据支撑。

## 源码修改

- scripts/configure + scripts/configure.in：HarmonyOS 三元组支持、umask 022、NULL_SRCS 回退
- scripts/config.guess：HarmonyOS 识别分支
- scripts/config.sub：linux-ohos 三元组
- base/mem.c：`__OHOS__` 走 malloc 分支
- analyzer/noana.c：补 4 个符号

## 知识候选台账（四范围查重 + 七轴）

### K0 — config.guess/config.sub HarmonyOS 支持（复用既有，不建草稿）

- 真实错误: `cannot guess build type; you must specify one`（2014 版 config.guess）
- 根因: 标准 config.guess 无 HarmonyOS 分支（E007/E160 同根因）
- 修复/验证: 补 `*:HarmonyOS:*:*` 分支输出 aarch64-unknown-linux-ohos + config.sub
  linux-ohos 三元组；configure/make/conan create 全绿
- 适用: 所有 autotools C 项目
- 查重: 正式库 E007（config.guess）、E160/E205/E533（config.guess HarmonyOS 补丁）
  已覆盖 → `exact_duplicate`，复用不建草稿
- 七轴: exact_duplicate=是；causal_duplicate=是（同为无法识别平台）；其余轴无新增

### K1 — configure 临时目录 umask 077 → 022（复用既有，不建草稿）

- 真实错误: `config.status: can't create ./conf*/subs1.awk: Permission denied`
- 根因: HMDFS 上 umask 077 临时目录对当前进程不可写（E011/E129/E223）
- 修复/验证: configure 中 umask 077 → 022；configure 重新生成 defs.mak 成功
- 适用: 所有 autotools 项目在 HMDFS 上 configure
- 查重: 正式库 E011/E129/E223 已覆盖 → `exact_duplicate`，复用不建草稿
- 七轴: exact_duplicate=是；边界一致；无新增

### K2 — OHOS 上 sbrk() 失败时内存分配器需走 malloc 分支（新建草稿）

- 真实错误: `*** MEMORY WARNING *** / I seem to be short on swap space /
  Will sleep for 15 seconds and try again`，irsim 启动卡死（sbrk(4MB) 返回 -1）
- 根因: 平台 sbrk 失败（RLIMIT_DATA 无限制），SYSV/BSD GetMoreCore 分支
  进入 sleep 15s×5 重试死循环
- 修复/验证: mem.c GetMoreCore 扩展 `__OHOS__` 到 malloc 分支（与上游
  CYGWIN/APPLE 先例一致）；MEMORY WARNING 消失，真实仿真 exit 0，
  conan create + test_ohos 全绿
- 适用: 任何在 OHOS 上用 sbrk 实现自研内存池的 C/C++ 软件（irsim/magic 系）
- 查重: 引擎查 "sbrk" 命中 E476（malloc 对齐，根因不同）与
  DRAFT-ohos-autotools-rpl-malloc（rpl_malloc 符号，不同层面）→ 未命中
- 七轴: exact_duplicate=否；causal_duplicate=否（E476 是 musl 对齐非 sbrk 失败）；
  trigger_overlap=部分（同为 malloc/sbrk 相关标志）；solution_overlap=否；
  combination_novelty=是（新错误签名+新方案）；boundary_novelty=是；
  test_migration_novelty=否
- 决定: `new_draft` → knowledge/drafts/DRAFT-irsim-9.7.104-ohos-sbrk-getmorecore-malloc.{kv,md}

### K3 — 无 X11/Tcl 环境 configure 需回退 NULL_SRCS 且无图形桩补符号（新建草稿）

- 真实错误: `thread.c:9:10: fatal error: 'X11/Xlib.h' file not found` 与
  `undefined symbol: EnableInput/DisableInput/OffsetNode/OffsetVector`
- 根因: configure 非 Tcl 非 X11 分支未回退 `${NULL_SRCS}`，gr_srcs 残留
  依赖 X11 的 thread.c；且 noana.c 缺基础模块引用的 4 个符号
- 修复/验证: configure 补 else 分支回退 NULL_SRCS + noana.c 补 4 个符号
  （语义与上游 analyzer.c 一致）；configure/make/conan create/test_ohos 全绿
- 适用: irsim 及同作者 magic 系工具、其他"图形可选"的 autotools C 软件
- 查重: 引擎查"noana/NULL_SRCS"命中 E463（GTK/Broadway 无显示环境，对象不同）
  → 未命中
- 七轴: exact_duplicate=否；causal_duplicate=否（E463 是 GTK Meson 工程）；
  trigger_overlap=部分（同属无图形环境）；solution_overlap=否；
  combination_novelty=是；boundary_novelty=是（magic 系 autotools C 特有路径）；
  test_migration_novelty=否
- 决定: `new_draft` → knowledge/drafts/DRAFT-irsim-9.7.104-ohos-nographics-null-srcs.{kv,md}

### 关系字段

- K3 caused_by E007（平台三元组识别是前置）；K2 similar_to
  DRAFT-ohos-autotools-rpl-malloc（内存分配域，独立层面）
- 适用边界/反例: 真实需图形界面的库不得回退 NULL_SRCS；依赖 sbrk 地址
  连续性语义的分配器改 malloc 前需确认

### 路径决定

- K2/K3 均 verified + 可跨库复用 + 查重未命中 → `new_draft`（路径 B 知识，草稿
  与 irsim 归档同 PR 交付）
- K0/K1 复用既有正式条目 → `reuse_existing`（路径 A 常规适配部分）
- 综合: 任务为【高难度挑战】路径 C（task_type 声明），PR 前缀固定
  【高难度挑战】；知识草稿随本库 PR 一同提交，不另建知识库 PR
## R02 返工：0002 平台宏评估（特性检测 vs __OHOS__）

**结论：保留 `#if defined(CYGWIN) || defined(__APPLE__) || defined(__OHOS__)`，不改为 AC_RUN_IFELSE 特性检测。**

理由（实测证据）：
1. sbrk 探测实验（t2.c）：`sbrk(0)` 返回有效地址，但 `sbrk(4096)`（4KB 小探测）即返回 `0xffffffffffffffff`（SBRK_FAIL）——sbrk 在本平台任何量级都不可用，非"大分配才失败"。探测输出：`sbrk0=0x58ac1e0000 small_4K=0xffffffffffffffff large_4M=0xffffffffffffffff`。
2. 特性检测不可行性：AC_RUN_IFELSE 在 autoconf 判定交叉编译时（本项目配置场景）不运行测试程序，无法得到真实结果；即便本机运行也会如实得到 sbrk 失败结论，等价于硬编码平台分支。
3. 上游先例一致：mem.c 本就为 CYGWIN/APPLE 提供 malloc 分支（平台条件宏模式），`__OHOS__` 并入该分支与上游既有结构一致，非新增 hack。
4. 不得为"消除宏"引入未验证改动（任务原文约束）；现有方案有真实编译+运行+test_ohos 12/12 证据。

## R02 返工：test_ohos.sh 临时目录回退链核验（P3）

**结论：现有回退链正确，无需改动。**

- 回退链代码（test_ohos.sh L20）：
  `TMPD=$(mktemp -d "${TMPDIR:-/tmp}/irsim-test-ohos.XXXXXX" 2>/dev/null || mktemp -d "${HOME}/tmp/irsim-test-ohos.XXXXXX")`
- 实测证据（R02 本机）：
  - `TMPDIR=/storage/Users/currentUser/tmp`（已设置，目录存在且可写）
  - `/tmp` 只读（`touch /tmp/.wtest` → `Read-only file system`，与 E002 一致）
  - `${TMPDIR:-/tmp}` 取到 TMPDIR，mktemp 成功；若 TMPDIR 未设置且 /tmp 只读，mktemp 失败后回退 `${HOME}/tmp`（可写）
- 与 SKILL 约束一致：E002 要求 /tmp 只读时用 `$TMPDIR` 或 `$HOME/tmp`；test_ohos 已在 R01 实际运行 12/12 通过（trap EXIT/INT/TERM 清理，不残留、不写包目录），本轮复验继续有效。

## R02 返工：umask 077→022 维持原因（P3，bot 保密性权衡）

**结论：维持 `umask 077 → 022` 修改，本轮不返工。**

- 归属：正规则 E011（HMDFS 文件系统 umask 077 权限问题，severity 3）已覆盖此场景，为既有知识复用而非新引入改动。
- 真实证据：R01 实测 configure `config.status: can't create ./conf*/subs1.awk: Permission denied`（HMDFS 上 umask 077 创建的临时目录对当前进程不可写，root_cause 为 UID 映射 + setgid 位）。
- 保密性权衡（bot 提出）：umask 022 使同组可读——在集成赛 worker 工作区（单用户部署、无多租户共享构建目录）保密风险可接受；configure 临时目录内容为构建中间产物（defs.mak 等配方输入），非凭据/私钥。若未来多用户共享同一构建目录，应改回受限 umask 并改用 E052 的固定临时目录方案，但当前不满足该条件。
- 对照 E052（modify_tmpdir 固定目录方案）也可行，但 umask 022 改动最小且已被大量同类包（E011/E129/E223 引用）验证；不返工符合"不得为修而修引入未验证改动"。
---

**编译结束**: 2026-09-16 23:29
**最终状态**: published

## R02 知识候选台账复核（K0-K3）

- **K2（sbrk→malloc）**：R02 同步草稿。0002 方案维持 `__OHOS__` 平台宏（实测 sbrk(4096) 也失败，AC_RUN_IFELSE 特性检测本机同样失败/交叉编译跳过，等价硬编码分支）；`DRAFT-irsim-9.7.104-ohos-sbrk-getmorecore-malloc.kv/.md` 根因字段已补入 R02 探测证据（sbrk0=0x58ac1e0000, small_4K=-1, large_4M=-1），.kv/.md 配对完整。
- **K0（config.guess/config.sub HarmonyOS）**：复核不变，复用 E007/E160/E205/E533（exact_duplicate），R02 无方案变化。
- **K1（umask 077→022）**：复核不变，复用 E011/E129/E223（exact_duplicate），R02 维持（保密性权衡已记录）。
- **K3（无 X11/Tcl 图形回退 NULL_SRCS + noana 补符号）**：复核不变。R02 仅对 0006/0007 增加覆盖语义注释（thread.c 依赖 X11 必须移除），方案本体未变，草稿 `DRAFT-irsim-9.7.104-ohos-nographics-null-srcs.kv/.md` 无需更新，配对完整。
- 全部草稿随 irsim 归档同 PR 交付，不单独提交知识库。
