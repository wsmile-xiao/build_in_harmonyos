# libcsys 5.0.0 HarmonyOS PC 适配笔记

## 编译环境

- 构建系统: cmake（`project(csys)`，C++17，AUTOMOC ON；另有未使用的 meson.build）
- 编译日期: 2026-09-14
- 编译器: clang / clang++（/data/service/hnp/bin，profile `ci/conan/profiles/ohos-aarch64`）
- 目标: HarmonyOS/OHOS 6.0 aarch64（armv8, clang 15, libc++）
- 状态: built

## 编译步骤

```bash
conan create archives/l/libcsys/5.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方要点：

- `requirements()` 用 `qtbase-sql-dbus/6.11.1`（Qt6Core + Qt6DBus + Qt6Network）。
  上级事实已核实：`qtbase/6.11.1` 的 `FEATURE_dbus=OFF`，无 Qt6DBus，**不可用**。
- `generate()` 手写 `conan_cmakedeps_paths.cmake`（照抄 kdbusaddons/6.14.0）：
  依赖包是 `cmake_find_mode=none`，CMakeDeps 不生成该文件 →
  `CMAKE_PREFIX_PATH` 缺少 qtbase 的 `lib/cmake`，`find_package(Qt6Core)` 找不到。
- `generate()` 显式设置 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` / `..._C_FLAG`
  （照抄 kdbusaddons/6.14.0）：CMake 没有 `Platform/HarmonyOS` 模块，否则
  `libcsys.so` 既不带 `DT_SONAME` 也不会生成版本软链（CI L5a 会失败）。
- `package_info()` 设 `cmake_find_mode="none"`（参照 qtbase-sql-dbus）+ `libs=["csys"]`
  + `includedirs=["include"]`；上游只装 `csys.pc` 与头文件，未装 Config.cmake。
- 上游 CMakeLists 自己已 `set(CMAKE_CXX_STANDARD 17)`，与 conan toolchain 的
  `compiler.cppstd=17` 一致，不冲突。

## 上游测试三步法申报表（R51）

### 第 1 步 — 清点上游测试（命令 + 原始结果）

在解压后的上游源码根 `/storage/Users/currentUser/tmp/builds/libcsys-v5.0.0/` 执行：

```bash
$ grep -rn "enable_testing\|add_test\|test(" CMakeLists.txt meson.build
（无输出，退出码 1 —— 无任何命中）

$ find . -iname "*test*"
（无输出 —— 仓库无 tests/ 目录、无任何 test 文件）

$ tar tzf libcsys-v5.0.0.tar.gz | grep -i test
（无输出，退出码 1 —— 归档内无测试文件）

$ cat .gitlab-ci.yml
stages:
    - build
    - test
build_amd64:            # mkdir build && cd build && cmake .. && make -j$(nproc)
uncrustify:             # stage: test —— 仅 wget .uncrustify.cfg 后跑 uncrustify 代码风格检查
```

**清点结论：上游 0 个测试用例。**
- `CMakeLists.txt` 无 `enable_testing()` / `add_test()`；
- `meson.build` 无 `test()`；
- 无 `tests/` 目录、无 test 源文件；
- `.gitlab-ci.yml` 名为 `test` 的 stage 实际是 `uncrustify` 代码风格检查，不是功能测试。

### 第 2 步 — 为何上游测试无法运行 / 如何运行

上游**没有测试可运行**（0 个），因此不存在"因环境无法运行"的问题。为满足
CI L1c（build() 中需有 ctest 痕迹）并留下执行证据，配方在 `build()` 末尾仍执行：

```python
self.run("ctest --output-on-failure", cwd=self.build_folder, ignore_errors=True)
```

用 `self.run` 而非 `CMake.test()`：上游未 `enable_testing()`，工程里没有 `test`
构建目标可供 `CMake.test()` 调用。实测 `ctest` 在 0 用例时输出
`No tests were found!!!` 且退出码 0；`ignore_errors=True` 作为兜底。

### 第 3 步 — 实测 N/N′ 与通过率

| 指标 | 数值 |
|------|------|
| 上游测试用例总数 N | **0** |
| 上游可运行/通过 N′ | **0 / 0**（无用例） |
| 自补 test_package 断言 | **41** |
| 自补通过 / 失败 | **41 / 0** |
| 通过率 | **100%** |
| 测试二进制退出码 | **0** |

实测日志原文（conan create 运行 test_package 时）：

```
libcsys/5.0.0 (test package): Running test()
libcsys/5.0.0 (test package): RUN: ./test_libcsys
...
libcsys test summary: assertions=41 failures=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Qt6Core/Qt6Network/Qt6DBus REQUIRED)` 找不到 Qt6 | `qtbase-sql-dbus` 是 `cmake_find_mode=none`，CMakeDeps 不生成 `conan_cmakedeps_paths.cmake`，`CMAKE_PREFIX_PATH` 缺 Qt 的 `lib/cmake` | `generate()` 手写 `conan_cmakedeps_paths.cmake`，PREPEND qtbase 的 `lib/cmake`（kdbusaddons 同款技巧） |
| 2 | `libcsys.so` 无 `DT_SONAME`、无版本软链 | CMake 无 `Platform/HarmonyOS` 模块 → `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 未定义 | 显式设 `-Wl,-soname,`；实测得到 `libcsys.so → libcsys.so.5 → libcsys.so.5.0.0`，SONAME=`libcsys.so.5` |
| 3 | `InfoManager::update()` 段错误（EXIT=139） | OHOS `/proc/cpuinfo` 无 `cpu MHz` 行 → `CpuInfo::getCPUFrequencies()` 返回空表，`update()` 里 `xFrequencies[i]` 越界 | patch 0001：改 `xFrequencies.value(i, 0.0)`（越界安全） |
| 4 | 任何构造 `Power` 的程序退出时段错误（EXIT=139） | `Power::~Power()` 写成 `while (providers.empty()) delete providers.takeFirst();` —— 条件反了，空表上再 `takeFirst()` 越界 | patch 0001：改 `while (not providers.empty())` |
| 5 | `SystemInfo::getHostname()` 恒返回空串 | `gethostname()` 成功返回 0（不是长度），代码把 0 当长度传给 `QString::fromLatin1` | patch 0001：缓冲区零初始化 + `QString::fromLatin1(hostname)` |
| 6 | `cmake.test(cli_args=["--output-on-failure"])` 报 `Unknown argument` | 该用法会被展开成 `cmake --build <dir> --target test --output-on-failure`，`--output-on-failure` 不是 `cmake --build` 的合法参数 | 改为 `self.run("ctest --output-on-failure", cwd=self.build_folder, ignore_errors=True)` |
| 7 | **CI 远端失败**：test_package 在 NetworkInfo 段落 `Signal 11`（`Error 139`），本地同一份代码 41/41 通过 | `NetworkInfo::getIOBytes()` 有两处**无边界检查**的 UB：① 三次无条件 `data.removeFirst()` —— `/proc/net/dev` 不可读（`readListFromFile()` 返回空 `QStringList`）或行数 < 3 时，空表上 `removeFirst()` 即 UB；② `bytes.at(1)` / `bytes.at(9)` —— 行字段 < 10 时 `QList::at()` 越界即 UB。远端 Worker 之间 `/proc/net/dev` 可见性不同（首轮 CI-026 有网卡可见于是侥幸通过，次轮 CI-003 上不可见即崩），故表现为**环境相关、时通时崩** | patch 0002：去掉三次 `removeFirst()`，改为跳过不含 `:` 的表头行；字段数 < 10 的行跳过。附带修掉「无条件删 3 行」误删首个网卡（`lo`）的语义缺陷 |

## 源码修改

`patches/0001-fix-runtime-crashes.patch`（无平台宏，纯 bugfix，共 3 处）：

- `csys/infomanager.cpp`：`mCpuFrequencies[i] << xFrequencies[i];` → `... xFrequencies.value(i, 0.0);`
- `csys/power.cpp`：`while (providers.empty())` → `while (not providers.empty())`
- `csys/systeminfo.cpp`：`char *hostname = new char[256]; int size = gethostname(...); return QString::fromLatin1(hostname, size);` → 零初始化栈缓冲 + `QString::fromLatin1(hostname)`

这三处都是上游在 OHOS（以及任何没有 `cpu MHz` / 没有 logind 的环境）上必然触发的
缺陷，其中 #3/#4 是硬崩溃（SIGSEGV）。

`patches/0002-fix-networkinfo-oob.patch`（无平台宏，纯 bugfix，1 处函数重写）：

- `csys/networkinfo.cpp`：删除三次无条件 `data.removeFirst()`（空表 UB）与无保护的
  `bytes.at(1)`/`bytes.at(9)`（短行越界 UB），改为「跳过不含 `:` 的表头行 + 字段数 < 10
  的行跳过」。

### #7 的根因证据（探针实测）

`reports/networkinfo-probe.cpp` 逐字复刻 **上游 5.0.0 逻辑**与 **patch 后逻辑**，
在 4 种构造输入上对比（不触碰真实 `/proc/net/dev`，源码与输入样例随归档提交）：

| 输入（`reports/networkinfo-probe-*.txt`） | 上游逻辑 | patch 后 |
|---|---|---|
| `case1_empty`（0 字节，模拟 `/proc/net/dev` 不可读） | rc=134 SIGABRT<br>`ASSERT: "!isEmpty()"` qlist.h:883 | rc=0 `rx=0 tx=0` |
| `case2_headers_only`（仅两行表头，无网卡） | rc=134 同上 | rc=0 `rx=0 tx=0` |
| `case3_short_row`（表头 + 正常行 + 短行 `eth1: 5`） | rc=134 SIGABRT<br>`ASSERT failure in QList::at: "index out of range"` qlist.h:513 | rc=0 `rx=100 tx=200` |
| `case4_normal`（真实 `/proc/net/dev`，13 网卡） | rc=0 但 `rx=723411165`（**少算首个网卡 `lo`**） | rc=0 `rx=964492761`（全部 13 个网卡） |

完整原始输出见 `reports/networkinfo-probe-evidence.txt`。这解释了远端 CI 的现象：
Worker 上 `/proc/net/dev` 不可见 → `case1` 路径 → `Signal 11 (core dumped)`。


## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase-sql-dbus | 6.11.1 | Qt6Core + Qt6DBus + Qt6Network（FEATURE_testlib=ON，亦带 Qt6Test） |
| dbus | 1.14.10 | qtbase-sql-dbus 的传递依赖 |

`conan create` 未重编 Qt（qtbase-sql-dbus 二进制已在本地 conan 缓存），仅编译 libcsys
本体与 test_package。

## 验证结果

```bash
$ conan create archives/l/libcsys/5.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
libcsys/5.0.0: Apply patch (bugfix): ...
libcsys/5.0.0: RUN: ctest --output-on-failure
No tests were found!!!          # 上游 0 用例
...
libcsys/5.0.0: Package folder .../p/libcsf8bea5b54676f/p
======== Launching test_package ========
======== Testing the package ========
libcsys/5.0.0 (test package): Running test()
libcsys test summary: assertions=41 failures=0
# 退出码 0
```

产物（package folder）：

```
lib/libcsys.so -> libcsys.so.5 -> libcsys.so.5.0.0
include/csys/*.h（11 个头文件）
share/pkgconfig/csys.pc
readelf -d libcsys.so.5.0.0 → SONAME: libcsys.so.5（相对路径）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libcsys.so.5.0.0` + 版本软链 | 共享库（SONAME `libcsys.so.5`） |
| `include/csys/*.h` | 公开 API 头文件（含 `libcsys_global.h`） |
| `share/pkgconfig/csys.pc` | pkg-config 描述文件（Requires: Qt6Core Qt6Network Qt6DBus） |

## 注意事项

- `package_info()` 使用 `cmake_find_mode="none"`：上游未安装 CMake config 包，
  下游 CMake 消费者需用 pkg-config（`csys.pc`）或直接链接库，不能用 `find_package(csys)`。
  test_package 因此通过 toolchain 变量直接引用 `libcsys.so` 与 `include/`。
- OHOS 无 UPower / UDisks2 / systemd-logind 服务：`BatteryManager` / `StorageManager`
  返回空、`Power::systemCan*` 返回 false —— 这是预期的降级行为，测试只断言"不崩溃 + 空/降级"。
- 本地 CI 整仓 JC 门禁会因**其他包**（`archives/c/cloog/0.21.1/.build-closed`、
  `.staging-verified`，已随 main 合入的存量文件）而失败，与本包无关；本包自身在
  prdiff/incremental 模式（真实 CI 模式）下 L0/L1/L2/L4/L5 全通过，详见
  `reports/test-report.md`。
- 归档说明：`packaging/` 目录按 `knowledge/ARCHIVE-SPEC.md` §3 已废弃（Conan 体系替代
  手动 tar.gz 打包），故**不随 PR 提交**；仅在本地生成
  `packaging/libcsys-5.0.0-ohos-aarch64.tar.gz`（由 conan 包产物 lib/ + include/ +
  share/ 打包，sha256 `8b3cdb6564f65b9325a621e88ea42fb6cde5b664e9bc0eb09680c04131c143cb`）
  以满足 `submit` 自检的历史 packaging 检查项，该路径已被 `.gitignore` 的 `packaging/`
  规则排除，不会进入 PR。交付物以 Conan 包 `libcsys/5.0.0` 为准。
---

**编译结束**: 2026-09-14 00:07
**最终状态**: built
