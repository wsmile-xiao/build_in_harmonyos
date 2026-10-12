- **三方库名称**：alsa-lib（ALSA userspace library：`libasound` + `libatopology`，LGPL-2.1-or-later）
- **上游版本**：1.2.14（官方发布归档 `alsa-lib-1.2.14.tar.bz2`，sha256 `be9c88a0b3604367dd74167a2b754a35e142f670292ae47a2fdef27a2ee97a32`）
- **上游仓库地址**：https://www.alsa-project.org/ （源码归档 https://www.alsa-project.org/files/pub/lib/alsa-lib-1.2.14.tar.bz2）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E007（`config.guess` 无法识别 HarmonyOS 构建类型）、E072（`config.sub` 拒绝 `*-ohos*` 三元组）、E127（HarmonyOS 无 `pthread_cancel` 系列函数）、E050（HMDFS 不跟踪符号链接 → `copy-replace-symlink`）、E129 / E136（`umask 077` 导致 `config.status` 临时目录不可写）、E330 / E331（OHOS 路径下版本化共享库符号链接链不可用）、E228（HMDFS 上无扩展名 Libtool 测试 wrapper 无法直接启动）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | 来源：`test/lsb/Makefile.am` 经 `TESTS` 注册的 Automake 用例 —— `TESTS = config`、`TESTS += midi_event`（源文件 `test/lsb/config.c`、`test/lsb/midi_event.c`） |
| 集成测试 | 0 | 上游无独立集成测试框架；`make check` 即全部注册用例 |
| 其他测试 | 19 | `test/Makefile.am` 的 `check_PROGRAMS` 中 19 个程序只编译、不注册进 `TESTS`，不构成用例（static 模式 18 个，仅 `oldapi` 因需 `ALSA_0.9` 版本符号而排除） |
| **合计** | **2** | 注册用例数；19 个 build-only 程序不计入 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | `lsb-config`、`lsb-midi-event` 在 OpenHarmony PC 目标上经 `make check` 真实执行，shared 与 static 两种形态各 2/2 PASS |
| 集成测试 | 0 | 不变 | 上游无该层 |
| 鸿蒙特有测试 | 11 | 新增 | `test_package/` 的 11 个独立消费者（`AL-FUN-001..006` + `AL-PKG-001..005`），每个编译出独立可执行文件并在目标上真实执行，带 180s 外部超时 |
| **合计** | **13** | **+11** | 逻辑结果 13/13（100%）；shared 与 static 分别各跑一遍，用于验证制品形态，不累加 |

> 另记 60 个 ABI 链接探针（`api_probe.c`，覆盖 60 个公开符号）与 19 / 18 个上游 `check_PROGRAMS` 编译证据：只取函数地址、从不执行，**不计入用例数**。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 1. **修改的测试文件**：`test/pcm-multi-thread.c`（补丁 `0004-pcm-multi-thread-ohos.patch`，2 处 hunk）
>    - **修改原因**：HarmonyOS musl libc 不提供 `pthread_cancel` 系列函数，该程序无条件调用 `pthread_cancel()` 会编译失败（知识条目 E127）。同一补丁在 `configure.ac` / `configure` / `include/config.h.in` 增加 `HAVE_PTHREAD_CANCEL` 特性探测。
>    - **修改内容**：① 头部增加 `#include "config.h"` 以取得探测结果；② 在 `running = 0;` 之后，把 `pthread_cancel()` 循环用 `#ifdef HAVE_PTHREAD_CANCEL` 包裹。线程创建 / 处理 / `pthread_join()` 回收路径**未改动**，唯一变化是：平台无 `pthread_cancel` 时跳过取消调用，直接 join 收尾。
>    - **影响面限定**：该程序**不在** `TESTS` 注册清单内（注册的只有 `test/lsb` 的 `config` 与 `midi_event`），属 19 个 build-only 程序之一，因此**不影响任何注册用例的执行与统计**。

> **注册用例零修改**：`test/lsb/config.c`、`test/lsb/midi_event.c` 与已适配的 1.2.16.1 **逐字节相同**（连同 `test/Makefile.am`、`test/lsb/Makefile.am` 共 4 个边界文件 SHA256 全等），本适配未改动其中任何一行。其余补丁只触及构建系统与库源码（`config.guess`、`config.sub`、`src/Makefile.am|.in`、`src/topology/Makefile.am|.in`、`configure.ac`、`configure`、`include/config.h.in`、`src/pcm/pcm_null.c`、`src/ucm/parser.c`、`src/conf.c`）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 说明：上游**注册测试仅 2 项**且均为 `test/lsb` 的底层 API 契约用例，没有任何校验「打包产物可被下游消费」的测试（上游无 `test_package` 概念，官方归档中该词出现 0 次）。适配后按本仓库惯例补全了消费者侧测试。
>
> - **补全的测试范围**：11 个独立消费者用例，覆盖公共 API 功能面 6 项 + 打包/制品契约 5 项；两种制品形态（shared / static）各执行一遍。
> - **补全原因**：① 上游测试只验源码树内 API 行为，不验 Conan 交付物（头文件布局、未带版本号的 `.so` 命名、SONAME/NEEDED、静态归档、CMakeDeps / PkgConfigDeps 元数据、签名 ELF 清单、license）；② HarmonyOS 侧新增了平台特有适配（`/dev/full` 不可读、`versionsort64` 缺失），需要针对性回归面。
> - **新增测试文件清单**（`archives/a/alsa-lib/1.2.14/test_package/`）：
>   1. `format_roundtrip.c` — `AL-FUN-001` PCM 格式名/值与逻辑-物理位宽契约
>   2. `areas_silence.c` — `AL-FUN-002` 有界交错静音写入，哨兵字节不被触碰
>   3. `areas_copy.c` — `AL-FUN-003` 带偏移交错拷贝，哨兵字节不被触碰
>   4. `null_playback.c` — `AL-FUN-004` null 播放 配置/启动/写/排空/关闭 生命周期
>   5. `null_capture.c` — `AL-FUN-005` null 采集 读/丢弃/关闭 与「不写数据」契约（**补丁 0007 的回归面**）
>   6. `topology_roundtrip.c` — `AL-FUN-006` 内存拓扑清单 构建/解码/保存 往返
>   7. `component_asound.c` — `AL-PKG-001` `ALSA::asound` 组件版本与包树内运行期加载
>   8. `component_atopology.c` — `AL-PKG-002` `ALSA::atopology` 生命周期、版本与依赖闭包
>   9. `feature_contract.c` — `AL-PKG-005` 生成的组件/插件/路径元数据与激活后的运行期环境
>   10. `conanfile.py` — `AL-PKG-003` 重定位后的 pkg-config 元数据 + 2 次运行期加载（完成重定位工作流）
>   11. `conanfile.py` — `AL-PKG-004` 制品/ABI 契约（未带版本号 `.so`、SONAME/NEEDED、静态归档、静态 `fPIC` whole-archive 共享链接回归、头文件、配置文件、CMakeDeps / PkgConfigDeps 元数据、签名 ELF 清单、license，作为**一个失败单元**）
>
> 另有 `probes/dirent64_symbols.c`：libc 能力探针（证明 OHOS 有 `scandir64` / `alphasort64` / `struct dirent64`、无 `versionsort64`），是补丁 0008 的定性依据，**不计入用例数**。

## 验证结果

- 编译状态：通过（`conan create` 全链成功，shared 与 static 两种形态均 rc=0；在 OpenHarmony PC 目标上以原生 aarch64-linux-ohos clang 15.0.4 构建）
- 上游测试用例通过率：2/2（100%）—— 原始汇总 `# TOTAL: 2 / # PASS: 2 / # FAIL: 0 / # SKIP: 0 / # XFAIL: 0 / # XPASS: 0 / # ERROR: 0`，shared 与 static 各一遍
- 新增测试用例通过率：11/11（100%）—— 日志尾行 `validated 11 independent ALSA test-package entries`，shared 与 static 各一遍；逻辑合计 13/13

## 补充说明

**依赖身份**：本包为**依赖项适配**。alsa-lib 是 `qastools/1.4.0`（Qt6 系 ALSA 图形工具集）强制依赖闭包中的一员（与 `qtbase-sql-dbus/6.11.1`、`qtsvg/6.11.1`、`libudev-zero/1.0.4` 并列，见 `knowledge/qastools.md`）；同库 `1.2.16.1` 亦记录为 OpenJ9 / GraalVM 任务依赖闭包的适配。**本配方零第三方 Conan 依赖**（无 `requirements()` / `self.requires()` / `tool_requires`）：libc/POSIX、数学、动态加载、线程与 clock 均为目标系统能力，故无需先发布其它包（W0 无阻塞）。

**八个 portability 补丁**（`patches/`，均在 `conandata.yml` 声明；只改构建系统或库源码，除 0004 外不触碰 `test/`）：

| 补丁 | 目标文件 | 作用 |
|---|---|---|
| 0001 | `config.guess` | 识别 HarmonyOS 内核（E007） |
| 0002 | `config.sub` | 接受 `aarch64-*-linux-ohos` 三元组（E072） |
| 0003 | `src/Makefile.am` / `.in`、`src/topology/Makefile.am` / `.in` | 允许从 make 命令行覆盖 libtool `-version-info`，产出不带版本号的 `.so`（E330 / E331） |
| 0004 | `configure.ac`、`configure`、`include/config.h.in`、`test/pcm-multi-thread.c` | 特性探测 `pthread_cancel` 后再使用（E127，见上节） |
| 0005 | `configure.ac`、`configure` | 在 OHOS 上保留物化的 `include/alsa` 别名（E050） |
| 0006 | `configure` | HMDFS 上 `config.status` 临时目录保持可写（`umask 077` → `022`，E129 / E136） |
| 0007 | `src/pcm/pcm_null.c` | `/dev/full` 在本平台不可读（EACCES），回退到可读的 `/dev/zero` |
| 0008 | `src/ucm/parser.c`、`src/conf.c` | 跳过 OHOS 缺失的 `versionsort64` 分支（逐字节回移植上游 1.2.16 的 `!defined(__OHOS__)` 判据，两处站点） |

**真实验证摘要**（上游测试在配方 `build()` 内执行，`conan create` 无法绕过；命令 `make -j1 check LOG_COMPILER=/system/bin/timeout AM_LOG_FLAGS=180`）：

```
PASS: config
PASS: midi_event
# TOTAL: 2   # PASS: 2   # FAIL: 0
alsa-lib/1.2.14 (test package): validated 11 independent ALSA test-package entries
```

**已知限制 / 说明**：
1. 注册用例仅 2 项是上游既有事实——上游 `test/` 下 19 个程序均为 build-only，未注册进 `TESTS`；本适配不虚增注册数。
2. `test/pcm-multi-thread.c` 的改动是唯一一处上游测试源码改动（见上节），且该程序不属注册用例。
3. 静态形态下构建 18 个 build-only 程序（不含 `oldapi`，其依赖 `ALSA_0.9` 版本符号），如实记录不虚报。
4. 原始 `conan create` 完整日志为本地复现产物，**不随本 PR 提交**；其 SHA256 与关键结论已内联记录在 `reports/test-report.md`、`reports/upstream-test-inventory.md`、`reports/conan-verify-report.md` 中，便于复现核对。
5. 本包未附带新增知识草稿（按"仅当前软件与当前版本文件"的提交口径，草稿保留在本地，另行提交）。
6. **本地预检（PF）误报留痕**：① `PF9 分支/路径闸` 只拦到软件级三件套 `archives/a/alsa-lib/{README.md,commands.json,manifest.yaml}` —— 这正是仓库规范要求的位置（`manifest.yaml` 12287 例、`commands.json` 2978 例、`README.md` 5107 例先例），非真实缺陷；② `PF3 测试实质闸` 要求 `test()` 内直接出现 `self.run()`，本包 `test()` 经 `_attempt_build → _run_entry` 间接执行，日志中有 `RUN: /system/bin/timeout 180 …` 与逐条 `PASS` 实证（该启发式严于 CI 的 L0c，CI 只要求 `test_package/` 存在测试源文件）；③ `PF5 补丁平台宏闸` 命中补丁 0001 / 0008 新增的 `__OHOS__`，属 R8 允许的 libc 与三元组识别例外（见上表）。以上仅作说明，不影响交付内容与测试结论。
