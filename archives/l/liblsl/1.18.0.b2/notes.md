# liblsl 1.18.0.b2 — OHOS 适配记录（notes.md）

## 1. 包与源码

| 项 | 值 |
|---|---|
| 包名/版本 | `liblsl/1.18.0.b2` |
| 上游仓库 | https://github.com/sccn/liblsl |
| 上游 tag | `v1.18.0.b2`（sccn/liblsl 的预发布 tag 形如 `v1.18.0.bN`） |
| 源码 URL | `https://github.com/sccn/liblsl/archive/refs/tags/v1.18.0.b2.tar.gz` |
| sha256 | `a68367cabc35f7842daa2decb264e00b6821e56f343de598ba6b3ba6ec75dffd` |
| 构建系统 | CMake（上游要求 ≥3.23，设备为 CMake 4.1.2） |
| 语言 | C++17（含 C API 与 C++ RAII 头） |
| 许可证 | MIT |
| 下载体积/解压 | 1 042 424 B / 约 4.3 MB |

liblsl 是 Lab Streaming Layer（LSL）协议的 C/C++ 参考实现：跨设备、带时钟同步的
实时数据流传输（EEG/眼动/行为标记等采集场景的事实标准）。

## 2. 交付面（包内产物）

```
include/lsl_c.h                      C API 总头
include/lsl_cpp.h                    C++ API 总头
include/lsl/{common,inlet,outlet,resolver,streaminfo,types,xml}.h
lib/liblsl.so                        -> liblsl.so.2
lib/liblsl.so.2                      -> liblsl.so.1.18.0      （SOVERSION=2）
lib/liblsl.so.1.18.0                 实体（SONAME=liblsl.so.2）
lib/cmake/lsl/LSLConfig.cmake        CMake 包配置（find_package(LSL) + LSL::lsl）
lib/cmake/lsl/LSLConfigVersion.cmake
lib/cmake/lsl/LSLCMake.cmake         上游提供的消费者辅助函数
bin/lslver                           版本查询工具（R38 → software 级 commands.json）
```

- **集成方式**：`find_package(LSL CONFIG REQUIRED)` + `target_link_libraries(app LSL::lsl)`。
  上游**不产出 pkg-config `.pc` 文件**（`cmake/Installation.cmake` 只 install
  `LSLConfig.cmake`/`LSLConfigVersion.cmake`/`LSLCMake.cmake`），故本包也没有 `.pc`。
- 头文件是 C 与 C++ 双份；C++ 头要求消费者用 **C++17**（`-DCMAKE_CXX_STANDARD=17`）。
- `lslboost`（Boost 子集，header-only，109 个文件）与 `thirdparty/{asio,loguru}`
  随上游源码包内嵌，均已静态编入 `liblsl.so`，**不产生额外运行时依赖**。
- `liblsl.so` 的 `DT_NEEDED` 只有 `libc++_shared.so` / `libc.so`（均在
  `/system/lib64`，默认加载路径内）。

## 3. OHOS 适配要点（**不改上游源码**）

本版本在 OHOS/clang15/CMake 4.1.2 上编译**无需任何源码补丁**（`patches_applied: []`）；
平台差异全部在 `conanfile.py` 的 `generate()` 里以 CMake 变量解决。

### 3.1 SONAME / RUNPATH 链接标志全空（必须补）

`conan` 的 `CMakeToolchain` 把 `os=OHOS` 映射成 `CMAKE_SYSTEM_NAME=HarmonyOS`，
而 **CMake 4.1.2 没有 `Modules/Platform/HarmonyOS.cmake`**
（只有 `Platform/OHOS.cmake`，不被这个 system name 命中），于是平台模块回落成
generic，下列变量全部为空：

```
CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG
CMAKE_SHARED_LIBRARY_RUNTIME_{C,CXX}_FLAG / _FLAG_SEP
CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN
CMAKE_EXECUTABLE_RUNTIME_{C,CXX}_FLAG
```

后果（两者都实测到）：

1. 产出的 `liblsl.so` **没有 SONAME** → 消费者链接时 `DT_NEEDED` 退化成路径；
2. **根本写不进 RUNPATH** → `bin/lslver` 在裸环境找不到 `../lib/liblsl.so.2`
   （`readelf -d` 无 RUNPATH，运行报 `Error loading shared library liblsl.so.2`）。

修法：用 `CMAKE_USER_MAKE_RULES_OVERRIDE_{C,CXX}` 注入一份规则文件补齐这些变量
（先例 `archives/c/curl/8.15.0.1`）。自证：

```
readelf -d lib/liblsl.so.1.18.0 | grep -E 'SONAME|RUNPATH'
  (SONAME)  Library soname: [liblsl.so.2]
  (RUNPATH) Library runpath: [$ORIGIN;$ORIGIN/../lib]
readelf -d bin/lslver | grep RUNPATH
  (RUNPATH) Library runpath: [$ORIGIN;$ORIGIN/../lib]
```

### 3.2 RUNPATH 需要显式给（CMake 的 `UNIX` 变量在 HarmonyOS 下不存在）

上游 `cmake/CompilerSettings.cmake` 只在 `elseif(UNIX AND NOT ANDROID)` 分支里设
`CMAKE_INSTALL_RPATH`。CMake 的 `UNIX` 由平台模块
`Platform/<system>-Initialize.cmake` 设置，**没有 `Platform/HarmonyOS-Initialize.cmake`
就没人 `set(UNIX 1)`**（实测 build 目录 `CMakeCache.txt` 里根本没有 `UNIX` 条目），
于是该分支不执行、`CMAKE_INSTALL_RPATH` 保持为空。

修法：配方显式 `tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN;$ORIGIN/../lib"`
（取值与上游 Linux 分支一致）。

### 3.3 `cmake --install` 不得改写 ELF（会破坏 OHOS 代码签名）

install 阶段做 RPATH_CHANGE 改写会把 ELF 的 `.note.ohos.ident` 签名弄失效，
装出来的可执行文件 exec 直接报 `Operation not permitted`（EACCES/rc=126，
**不是** not found）——实测在探针工程上复现（改写前后 sha256 变化 + exec 失败）。

修法：`CMAKE_BUILD_WITH_INSTALL_RPATH=ON`，让构建产物直接带上最终 RUNPATH，
构建/安装两侧 RPATH 相同 → 不再触发改写。自证：**安装前后逐文件 sha256 一致**
（见 `reports/conan-verify-supplement.md`）。

### 3.4 上游 FetchContent 的 git 依赖改为 tarball

上游 `cmake/Dependencies.cmake` 用
`FetchContent_Declare(pugixml GIT_REPOSITORY ... GIT_TAG v1.15)`，
`testing/CMakeLists.txt` 用 `FetchContent_Declare(Catch2 ... GIT_TAG v3.4.0)` ——
这是 **configure 期的 `git clone`**，worker 的 configure 阶段不保证有 git/可访问
github.com。

修法：`source()` 里用 conan `get()` 下载**同一版本**的 tag tarball 到
`<source_folder>/_vendor/{pugixml,Catch2}`，`generate()` 里写
`FETCHCONTENT_SOURCE_DIR_{PUGIXML,CATCH2}` + `FETCHCONTENT_FULLY_DISCONNECTED=ON`。
两个 URL/sha256 登记在 `conandata.yml`，因此 CI 的 conandata 预下载与镜像回退
（`build_and_test.sh` 的 `get_mirrors`）能覆盖到它们。

### 3.5 版本号：tag tarball 不含 `.git`

上游 `cmake/ProjectVersion.cmake` 用 `git describe --tags` 定版本，并声明
「A version can be forced (e.g. from CI) by passing `-DLSL_VERSION_OVERRIDE=...`」。
GitHub tag tarball 没有 `.git`，不覆盖就会退化成内置 fallback（**1.17.7**，
实测产出 `liblsl.so.1.17.7`、`lsl_library_version()` 返回 117）。

修法：`tc.cache_variables["LSL_VERSION_OVERRIDE"] = "1.18.0.b2"`。
**必须用 `cache_variables` 而不是 `variables`**：上游在 `project()` **之前**就调用
`lsl_version_from_git()`，而 toolchain 文件要到 `project()` 里才被读 —— 只写
`tc.variables` 会静默退化（本轮实测踩到）。同时显式给
`lslgitrevision=v1.18.0.b2` / `lslgitbranch=conan`，否则 `lsl_library_info()`
是 `git:/branch:/...`。

自证：

```
$ conan cache path liblsl/1.18.0.b2:<pkgid>     # 包目录
$ ./bin/lslver
LSL version: 118
git:v1.18.0.b2/branch:conan/build:Release/compiler:Clang-15.0.4/link:SHARED
```

### 3.6 并行度自限

设备 `os.cpu_count()`=20 而 affinity=8，且 `conan create` 没有 jobs 旋钮。
配方用 `self.conf.get("tools.build:jobs", default=2)` 自限并显式
`cmake.build(build_tool_args=["-j2"])`，避免在共享设备上真开 20 路。

## 4. 上游测试（R51 三步法）

### 4.1 清点（N）

上游测试框架 = **Catch2 3.4.0**（`testing/` 目录，7 个 `add_test` 可执行文件）。

三种候选数法实测（决定 N 取最大值）：

| 候选数法 | 取值 | 取数命令 |
|---|---|---|
| A. 源码宏数（`TEST_CASE` 字样，含 `TEMPLATE_TEST_CASE`） | 66 | `grep -rho 'TEST_CASE' testing/ --include=*.cpp \| wc -l` |
| B. **框架注册数（Catch2 `--list-tests` 汇总行，`LSL_BENCHMARKS=ON`）** | **78** | `for t in lsl_test_*; do ./testing/$t --list-tests \| tail -1; done` |
| C. 框架注册数（默认 `LSL_BENCHMARKS=OFF`） | 67 | 同上；该档少 11 个 benchmark 用例（`ext/bench_{bounce,common,pushpull}.cpp` 7 + `int/bench_{sleep,timesync}.cpp` 3 + `int/network.cpp` 里被 `#ifdef CATCH_CONFIG_ENABLE_BENCHMARKING` 包住的 "streambuf throughput" 1） |

**声明 N = 78 = max(A,B,C) = B**（本次验证用 `-o liblsl/*:with_benchmarks=True`，
即 B 这一档；78 个用例全部注册、全部执行）。

`78 - 66 = +12` 的**逐项归因**：

| 项 | 增减 | 说明 |
|---|---|---|
| `TEMPLATE_TEST_CASE` 展开 | **+13** | 4 个模板宏按类型参数各展开成多个 Catch2 用例：`ext/DataType.cpp` "datatransfer"(6 类) 、`ext/sync_outlet.cpp` "sync_outlet_datatypes"(6 类)、`ext/bench_pushpull.cpp` "pushpull"(3 类) 与 "stringconversion"(2 类) → 4 个宏 = 17 个用例 |
| `int/loguruthreadnames.cpp` 从未被编译 | **−1** | **上游 `testing/CMakeLists.txt` 的变量名笔误**：`if(NOT MINGW) LIST(APPEND LSL_INTERNAL_SRCS int/loguruthreadnames.cpp)` 写的是 `LSL_INTERNAL_SRCS`，而 `add_executable(lsl_test_internal ${LSL_TEST_INTERNAL_SRCS})` 用的是 `LSL_TEST_INTERNAL_SRCS` —— 该文件在任何平台上都不进 `lsl_test_internal`（实测 `build.ninja` 中 0 处引用），其唯一用例 `loguru_thread_local_storage` 因此**在任何平台都不注册**（不是 OHOS 特有问题，上游缺陷如实登记） |

按可执行文件（`--list-tests` 汇总行实测，benchmarks ON）：

| 可执行文件 | 注册用例数 | 源文件 |
|---|---|---|
| `lsl_test_exported` | 38 | ext/{DataType,discovery,move,streaminfo,sync_outlet,time}.cpp + ext/bench_{bounce,common,pushpull}.cpp |
| `lsl_test_internal` | 35 | int/{inireader,network,stringfuncs,streaminfo,samples,postproc,serialization_v100,sync_endian,tcpserver,sendbuffer}.cpp + int/bench_{sleep,timesync}.cpp |
| `lsl_test_runtime_config` | 1 | int/runtime_config.cpp |
| `lsl_test_resolve_bad_interface` | 1 | int/resolve_bad_interface.cpp |
| `lsl_test_resolve_query_port` | 1 | int/resolve_query_port.cpp |
| `lsl_test_resolve_machine` | 1 | int/resolve_machine.cpp |
| `lsl_test_resolve_over_tcp` | 1 | int/resolve_over_tcp.cpp |
| **合计** | **78** | |

另有 4 个**未注册进 CMake** 的独立程序目录
（`testing/{BounceTest,SpeedTest,StressTest,SyncTest}/`）：上游 `testing/CMakeLists.txt`
里没有为它们 `add_executable`、不参与 `ctest`，**不计入 N**（其中 3 个是手工 `main()`
程序、不含 Catch2 `TEST_CASE`）。

> **口径提醒（本轮实际踩到）**：只用 `grep -c TEST_CASE` 会**把 N 报小 12 个**
> （66 而非 78）—— `TEMPLATE_TEST_CASE` 一行会展开成多个用例。清点必须同时用
> 「源码宏数」和「框架注册数」两种候选法并取最大值。

### 4.2 实际运行

```sh
# 槽位限流；with_tests/with_benchmarks 打开上游全套
conan create <pkg> -pr:h=<profile> -pr:b=<profile> \
  --build=missing -c tools.build:jobs=2 \
  -o 'liblsl/*:with_tests=True' -o 'liblsl/*:with_benchmarks=True'
# recipe 的 build() 在 cmake.build() 之后直接 ctest
```

**`ctest` 的目录必须是 `<build>/testing`**：上游只在 `testing/CMakeLists.txt` 里
`enable_testing()`，`CTestTestfile.cmake` 因此只生成在 `build/testing/` 下。在
`<build>` 跑 `ctest` 会打印

```
No tests were found!!!
```

并且 **rc=0**（实测）——这是一条「零用例假绿」，会让「上游测试全绿」变成空话。
本配方的处置：`ctest --test-dir <build>/testing --output-on-failure --no-tests=error`
（`--no-tests=error` 让空套件直接硬失败）。同类缺陷已有条目
`DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass`。

结果与计数（由最终日志复算）见 `reports/test-report.md`。

### 4.3 消费者侧（单独计数，不并入上游 N）

`test_package/` 两个程序（C 与 C++）**真跑**被测包：库标识、streaminfo + XML 往返、
本机回环 outlet→inlet 真实传样本，外加裸环境 `lslver` smoke。
断言数由程序自打印的 `ASSERTIONS:` 行复算，见 `reports/test-report.md`。

### 4.4 上游测试必须**串行**跑：它们共用同一段端口带（本机实测踩到假失败）

liblsl 的监听端口默认从 **16572** 起（`ports.BasePort`），7 个测试可执行文件全部在这个
端口带上创建 outlet/resolver。**并发运行两个 liblsl 测试进程会互相抢占端口**，而
`ports.AllowRandomPorts` 默认为 `true` → 抢不到时 outlet 静默改用随机端口（实测
`491xx`/`60xxx`），而 `resolve_over_tcp` 用例的 TCP 探测目标**固定**为
`127.0.0.1:{BasePort..BasePort+PortRange-1}`（该用例把 PortRange 设为 4）→ 探测打空 →
`REQUIRE(found.size() == 1)` 报 `0 == 1`。

- **实测证据**（本任务 2026-09-20 23:35–23:41）：
  - 与另一个 `lsl_test_exported` 进程并发时：`lsl_test_resolve_over_tcp` **连续 3/3 失败**，
    同时用 Python 探测 16572–16575 得到 `BUSY(errno 98 = EADDRINUSE)`；
    带日志的等价探针显示 acceptor 落到随机端口（60241/60777）后 `FOUND=0`；
  - 停掉并发进程、等端口释放后（Python 探测 16572–16581 全部 `FREE`）：同一序列
    **连续 3/3 全绿**，`lsl_test_resolve_over_tcp` rc=0。
- **判据**：`ctest` 必须串行（不加 `-j`）；本配方的 `build()` 里 `ctest` 未传 `-j`，
  天然串行。**本任务在跑上游测试期间本机不得同时跑任何其它 liblsl 进程**。
- 佐证：上游自带 CI（`.github/workflows/cppcmake.yml`）也是顺序执行两个测试可执行文件。

### 4.5 结果与计数

**实测 N = N′ = 78，PASS = 78，FAIL/SKIP/NOT_RUN = 0**（耗时约 14.5 分钟）：

| 可执行文件 | 注册用例 | 断言数 | 耗时 | rc |
|---|---|---|---|---|
| `lsl_test_exported` | 38 | 2161 | 9m01s | 0 |
| `lsl_test_internal` | 35 | 3763736 | 5m25s | 0 |
| `lsl_test_runtime_config` | 1 | 6 | <1s | 0 |
| `lsl_test_resolve_bad_interface` | 1 | 2 | <1s | 0 |
| `lsl_test_resolve_query_port` | 1 | 2 | 1s | 0 |
| `lsl_test_resolve_machine` | 1 | 1 | 1s | 0 |
| `lsl_test_resolve_over_tcp` | 1 | 4 | <1s | 0 |

断言数（3 765 912）属**另一单位**，只披露不并入 N。

完整报告见 `reports/test-report.md`；原始日志逐字留档见 `reports/upstream-tests.md`
（`reports/` 被 `.gitignore` 覆盖，不进 PR）。

## 5. 复现命令（设备可直接执行）

```sh
TASK_DIR=/storage/Users/currentUser/tmp/liblsl-1.18.0.b2
PACKAGE_DIR=/storage/Users/currentUser/ws/worktrees/liblsl-1.18.0.b2/archives/l/liblsl/1.18.0.b2
HOST_PROFILE=/storage/Users/currentUser/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64

# 1) 完整构建 + 上游测试 + 消费者测试
HOME="$TASK_DIR/test-home" conan create "$PACKAGE_DIR" \
  -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" --build=missing \
  -c tools.build:jobs=2 -o 'liblsl/*:with_tests=True' -o 'liblsl/*:with_benchmarks=True'

# 2) 取出包目录并逐条核 ELF
PKG=$(conan cache path liblsl/1.18.0.b2)
readelf -d "$PKG/lib/liblsl.so.1.18.0" | grep -E 'SONAME|RUNPATH|NEEDED'
readelf -d "$PKG/bin/lslver" | grep -E 'RUNPATH|NEEDED'
readelf -lW "$PKG/lib/liblsl.so.1.18.0" | grep -A1 GNU_STACK      # RW（NX 生效）

# 3) 裸环境 smoke（不注入 LD_LIBRARY_PATH）
env -u LD_LIBRARY_PATH "$PKG/bin/lslver" --version
```

## 6. 与上游的差异清单

| 项 | 上游默认 | 本包 | 原因 |
|---|---|---|---|
| 源码 | — | 未改动 | 无补丁 |
| SONAME/RUNPATH 链接标志 | 由平台模块给 | 配方注入规则文件 | §3.1 |
| `CMAKE_INSTALL_RPATH` | Linux 分支设 | 配方显式设 | §3.2 |
| install 期 RPATH 改写 | 开 | `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` | §3.3 |
| pugixml/Catch2 | FetchContent git clone | conan `get()` + `FETCHCONTENT_SOURCE_DIR_*` | §3.4 |
| 版本号 | git tag / fallback 1.17.7 | `LSL_VERSION_OVERRIDE=1.18.0.b2` | §3.5 |
| `LSL_UNITTESTS` | OFF（顶层工程默认 OFF） | 默认 OFF，`with_tests=True` 可开 | 保持 CI 精简；上游测试单独一轮验证 |
| `lslver` | 默认随库安装 | 保留 | R38 → `commands.json` |

## 7. 遗留与未验证项

- `shared=False`（静态 `liblsl.a`）路径未做设备验证：本轮验证的是默认
  `shared=True`（上游默认）。选项与 `LSL_BUILD_STATIC` 已正确映射，但静态消费者
  的链接行为未实测，**不声称通过**。
- `LSL_LEGACY_CPP_ABI`（legacy ABI 静态库）、`LSL_TOOLS=ON`（blackhole 工具）、
  macOS/Windows 分支均未验证（与 OHOS 无关，保持上游默认关闭）。
- 上游 4 个未注册测试程序目录（BounceTest/SpeedTest/StressTest/SyncTest）
  未编译未运行（上游 CMake 未注册它们）。
- **`with_tests=True` 的 conan 路径**：已验证到
  `conan install -o 'liblsl/*:with_tests=True' -o 'liblsl/*:with_benchmarks=True'`
  （generate 正确产出 `LSL_UNITTESTS=ON`/`LSL_BENCHMARKS=ON`/
  `FETCHCONTENT_SOURCE_DIR_CATCH2` 指向 `_vendor/Catch2`），且 `build()` 里的
  `ctest` 调用形状（`--test-dir <build>/testing`、串行、`--no-tests=error`、
  显式 `LD_LIBRARY_PATH`）已在本机同一工具链的构建树上实测跑通全部 78 个用例；
  但**未再用一次完整 `conan create -o with_tests=True` 端到端复跑**（设备槽位受限：
  一次完整 ctest 约 14.5 分钟 + 构建约 10 分钟）。默认路径（`with_tests=False`，
  即 CI 与采信轮走的路径）已完整验证。此项**不声称 conan 路径下已实测**。

