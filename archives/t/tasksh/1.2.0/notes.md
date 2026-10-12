# tasksh 1.2.0 适配笔记

## 软件信息

| 项 | 值 |
|---|---|
| 名称 | tasksh 1.2.0 |
| 上游 | GothenburgBitFactory/taskshell（Taskwarrior 官方组织），tag `v1.2.0` |
| 许可证 | MIT |
| 构建系统 | CMake（`cmake_minimum_required (VERSION 2.8)`） |
| 语言 | C++（C++11；本次实测以 C++17 通过） |
| 产物 | `bin/tasksh`（单个可执行文件） |
| 依赖 | `readline/8.3`（REQUIRED）、`ncurses/6.6` |
| 运行时同伴 | `task`（Taskwarrior）需在 PATH 中；制品仓已有 `task/2.6.2` |

## 源码来源（R39）

```
https://github.com/GothenburgBitFactory/taskshell/releases/download/v1.2.0/tasksh-1.2.0.tar.gz
sha256: 6e42f949bfd7fbdde4870af0e7b923114cc96c4344f82d9d924e984629e21ffd
```

官方 GitHub release 资产，非镜像 / 非个人 fork。归档共 93 个条目。

## 零 patch

本次适配**未打任何补丁**（`conandata.yml` 的 `patches: {}`）。所有平台适配
都在 `conanfile.py` 的 CMake 配置变量层面完成：

1. `CMAKE_POLICY_VERSION_MINIMUM=3.5` —— 根 `CMakeLists.txt` 声明
   `cmake_minimum_required (VERSION 2.8)`。CI 侧 CMake ≥ 3.31 会告警、
   ≥ 4.0 直接 `Compatibility with CMake < 3.5 has been removed` 硬失败。
   与 `archives/t/task/2.6.2`（Taskwarrior 同项目、同 `2.8` 声明）做法一致。

2. `READLINE_INCLUDE_DIR` / `READLINE_readline_LIBRARY` ——
   上游 `find_package (Readline REQUIRED)` 走自带的
   `cmake/Modules/FindReadline.cmake`，该模块用无约束的 `FIND_PATH` /
   `FIND_LIBRARY`。用 CMakeToolchain 把 Conan 产物的头文件与
   `libreadline.a` 绝对路径直接喂给它，避免误命中系统路径。

3. `READLINE_ncurses_LIBRARY` + `CMAKE_EXE_LINKER_FLAGS=-lncursesw` ——
   **本次适配唯一的实质性技术点**。`readline/8.3` 在本仓是静态库
   （`default_options = {"shared": False}`），其光标 / terminfo 符号
   （`tputs`、`tgetent`、`tgoto` …）由 ncurses 提供。而上游 FindReadline
   只探测名字恰好为 `ncurses` 的库：
   ```cmake
   FIND_LIBRARY (READLINE_ncurses_LIBRARY NAMES ncurses)
   ```
   本仓 `ncurses/6.6` 是 wide-character 静态构建，只产出
   `libncursesw.a` / `libformw.a` / `libmenuw.a` / `libpanelw.a`，
   **不存在 `libncurses.a`**。若不补这一项，`FindReadline` 会把
   `READLINE_LIBRARIES` 只填成 `libreadline.a`，最终链接阶段报
   `undefined reference to tputs` 一类错误。
   同仓先例：`archives/a/aeolus/0.10.4/conanfile.py` 的 docstring 已记录
   同一现象（"the published readline recipe builds static libs and its
   terminal-cursor symbols (tputs/tgetent ...) resolve to ncurses"）。

## 平台探测模块的落空分支（无需处理）

`cmake/CXXSniffer.cmake` 按 `CMAKE_SYSTEM_NAME` 穷举分支：

```cmake
if (${CMAKE_SYSTEM_NAME} MATCHES "Linux")
  set (LINUX true)
elseif (${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
...
else (${CMAKE_SYSTEM_NAME} MATCHES "Linux")
  set (UNKNOWN true)
endif (...)
```

OHOS 工具链下 `CMAKE_SYSTEM_NAME` 既不是 `Linux` 也不是其它任何一个，
于是落到末尾 `else()` 置 `UNKNOWN`。**这不是缺陷**：
- `set (CMAKE_CXX_FLAGS "-std=c++11" …)` 等关键设置在分支**之前**已经执行，
  与平台无关；
- `LINUX` / `UNKNOWN` 等变量的唯一消费者是 `cmake.h.in` 里的
  `#cmakedefine`，编译期宏缺失；
- 实测（`grep -rE '#if(def)?[[:space:]]+(LINUX|UNKNOWN|DARWIN|__OHOS__|_WIN32|FREEBSD)'`
  扫全部 33 个 `.cpp` / `.h`）**0 处** `#ifdef LINUX` / `#ifdef UNKNOWN` /
  `#ifdef DARWIN`；仅 `src/libshared/src/FS.cpp` 有 2 处 `#ifdef FREEBSD`
  （FreeBSD 专有路径处理），在 OHOS 下不进入正是期望行为。

因此**没有为它写补丁**——那会引入无谓的源码改动（并触碰 R8 平台宏红线）。

## `HAVE_COMMIT` 保持未定义

```cmake
if (EXISTS ${CMAKE_SOURCE_DIR}/.git/index)
```
Conan 的 source folder 里没有 `.git`，该分支不进入，`commit.h` 使用
release tarball 中随包发布的版本。这是预期行为，不是缺失。

## 上游 test/ 目录不在 release tarball 内（重要）

`tar tzf tasksh-1.2.0.tar.gz` 共 93 条，**0 条匹配 `test`**。但上游 git tag
`v1.2.0` 的 `test/` 确实存在：

| 文件 | 说明 |
|---|---|
| `test/version.t` | Python 冒烟测试，校验 `--version` |
| `test/template.t` | Python 模板测试 |
| `test/run_all` | 测试驱动（多线程跑 `*.t`） |
| `test/problems` | 失败汇总报告器 |
| `test/simpletap`、`test/basetest/` | simpletap / basetest 测试框架模块 |

根 `CMakeLists.txt` 用 `if (EXISTS ${CMAKE_SOURCE_DIR}/test)` 守卫引入，
tarball 里没有该目录，故被自动跳过。

**为什么不在适配中把 test/ 补进来**：官方 release 归档不含 test/，
从 git 拉取等于换源码来源，违反 R39（源码 URL 必须官方正式源）。
另外 `test/version.t`、`test/template.t` 的 shebang 是
`#!/usr/bin/env python2.7` 且脚本正文按 py2 写（驱动脚本 `run_all` 自身兼容
py2/py3，但它用 `Popen` 直接 exec 这些 `.t` 文件，因此在只有 python3 的
worker 上同样跑不起来）；测试套件还全程驱动交互式终端（readline/pty）
并要求已安装的 taskwarrior 与已初始化的 `TASKDATA`。

**结论**：上游测试「不可执行」，改为在 `test_package/` 补全等价的非交互式
真实测试，覆盖上游测试所验证的同一批行为（见下）。

## 补全测试设计（R34 / R51）

tasksh 是交互式 REPL：`promptCompose()` → `getResponse()` → 分发 → 循环，
直到 EOF / `exit` / `quit`。`getResponse()` 在 `HAVE_READLINE` 下调
`readline(prompt)`；stdin 为管道时 readline 同样逐行读取。因此**用管道喂
命令即可真实驱动整个命令循环**，无需 pty。

`test_package/test_tasksh.sh`（12 项功能断言）：

| 编号 | 断言 |
|---|---|
| T1 | `--version` 精确等于 `1.2.0`（`argc==2` 短路，不触碰 task） |
| T2 | `argc != 2`（`--version extra`）**不**短路，落到 REPL |
| T3 | `help` 渲染命令表，含 `review` / `diagnostics` / `exec` |
| T4 | `exec <cmd>` 逃逸到 shell 并回显输出 |
| T5 | `!<cmd>` 短形式逃逸到 shell |
| T6 | `diagnostics` 报出 `libreadline: 8.3` ← **静态 readline 链接成功的直接证据**（无 Readline 时该字段是 `n/a`） |
| T7 | 任意命令被改写为 `task <cmd>` 并透传（`[task add ...]` 回显） |
| T8 | （可选，需 `task` 在 PATH）经 tasksh 新建的任务能被 `task list` 读回 —— 真实端到端往返 |
| T9 | stdin 立即 EOF → 退出码 0 |
| T10 | `quit` → 退出码 0 |
| T11 | `exit` → 退出码 0 |
| T12 | `review` 正常分发，未落入 `catch (...)` 的 `Unknown error.` |

`test_package/test_ohos.sh`（7 项 HarmonyOS 特有断言）：

| 编号 | 断言 |
|---|---|
| T13 | `param get const.ohos.fullname` 为 `OpenHarmony-*` |
| T14 | ELF64 + `EM_AARCH64` —— 证明没有静默回落到宿主 x86_64 工具链 |
| T15 | `ET_DYN`（PIE）—— OHOS 应用沙箱只加载位置无关可执行文件 |
| T16 | DT_NEEDED 全部在 OHOS 运行期可解析（conanrun LD_LIBRARY_PATH + 系统库目录） |
| T17 | `readline` / `ncurses` **不**出现在 DT_NEEDED —— 静态链接未被静默降级为动态 |
| T18 | 在 OpenHarmony 目标上真实执行 `--version` 成功 |
| T19 | `share/man/man1/tasksh.1` 与 `share/doc/tasksh/COPYING` 已随同一次 cmake install 落地（内置 help 文本指引用户 `man tasksh`） |

T14/T17 是本次适配的核心防线：若配方某天静默回落到宿主工具链或把静态库
悄悄改成动态链接，只有这两条会红。

`test_package/runner.sh` 被上面两个脚本 `source`，负责**怎么执行**产物：
按产物 ELF 头判断是直跑（CI 的 HarmonyOS PC aarch64 worker）还是走
`qemu-aarch64 -L <OHOS guest sysroot> -E LD_PRELOAD=<guest 侧 fortify shim>`
（本机 x86_64 WSL 交叉编译）。两个要点：

- **不能用 `cross_building()` 判断**：`ohos-aarch64` profile 对 `-pr:h` 与
  `-pr:b` 传同一个文件，Conan 认为 host == build，尽管产物是 aarch64 而宿主
  是 x86_64。只能读产物 ELF 头。
- **`LD_PRELOAD` 必须走 `qemu -E` 而不是 export**：guest musl 没有
  `__fd_chk`，不预载就 `Error relocating ...: __fd_chk: symbol not found`；
  但若 export 到环境里，宿主 x86_64 子进程（bash / grep / qemu 自己）也会去
  加载这个 aarch64 `.so`，每个都打一行
  `ERROR: ld.so: object '...' cannot be preloaded ...: ignored.`。
  `runner.sh` 只过滤这一行已知无害的告警；shim 真坏掉时 tasksh 自己会以
  `Error relocating ... __fd_chk: symbol not found` 失败，不会被过滤掉。

## 本地验证记录

> 本机是 x86_64 WSL，而产物是 aarch64/OpenHarmony。仓内 profile
> `ci/conan/profiles/ohos-aarch64` 的 `tools.build:compiler_executables` 指向
> `/data/service/hnp/bin/clang{,++}`（CI worker 上的 OHOS 设备编译器），
> 本机不存在。本地另建等价 profile：settings/`[buildenv]` 与仓内 profile
> 逐行一致，只把编译器换成 `/opt/lpk-fixed/clang{,++}`（本机的等价驱动 shim，
> 补上 OHOS libc++ 头与静态 libc++/libc++abi/libunwind），`CONFIG_SHELL`
> 换成 WSL 的 `/bin/bash`。**这是环境差异，不是配方差异。**

- `conan create . -pr:h=<local ohos-aarch64> -pr:b=<local ohos-aarch64>`：
  退出码 0，编译零错误、零补丁。依赖 `readline/8.3` 与 `ncurses/6.6`
  在本地 Conan 缓存中已有 OHOS 二进制，未触发从源码重建。
- 产物：`ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked,
  interpreter /lib/ld-linux-aarch64.so.1`，`DT_NEEDED` 仅 `libc.so`
  —— readline / ncurses 均已静态并入。打包内容：`bin/tasksh` +
  `share/man/man1/tasksh.1` + `share/doc/tasksh/{NEWS,ChangeLog,INSTALL,AUTHORS,COPYING}`。
- `conan test test_package tasksh/1.2.0 -pr:h=... -pr:b=...`：退出码 0，
  T1–T7 / T9–T19 全部 `[ok]`（T8 因 PATH 上无 `task` 二进制 `[skip]`），
  T13 在交叉模拟下降级为 `[skip]`（本机无 OHOS `param` 工具）。
- 交叉模拟实跑：`--version` → `1.2.0`；`help` / `exec` / `!` /
  `diagnostics`（报 `libreadline: 8.3`）/ 命令透传 / `exit` / `quit` /
  EOF 全部符合预期。

## 已知平台限制

`diagnostics` 的 `Configuration` 段会打印 `PATH:`，在 OHOS 上是设备真实
PATH —— 属预期行为，不做屏蔽。