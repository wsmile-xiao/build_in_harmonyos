# indi-beefocus 0.1-20221222010828 适配笔记

## 任务与结论

- 软件: indi-beefocus（Bee Focuser 的 INDI 驱动，经 TCP/IP 控制开源望远镜调焦器）
- 版本: 0.1-20221222010828（上游快照 0.1+20221222010828）
- 分支: feat/indi-beefocus-0.1-20221222010828（W2 PR 原子性）
- 构建系统: cmake（PROJECT(indi_beefocus CXX C)）
- 依赖: libindi/2.2.2.1（已发布）+ gtest/1.17.0（test_requires，仅上游单元测试用）
- 产物: bin/indi_beefocus + share/indi/indi_beefocus.xml + licenses/LICENSE
- 结论: **published-able（built）**。`conan create` 全绿：上游 8/8 gtest 通过，
  test_package 4 用例 / 31 检查 0 失败。
- 语言预检（R47）: detected_language=cpp（CMakeLists PROJECT 显式 CXX C；12 个 .cpp 主体 100%）

## 版本号与源码来源

上游 `indilib/indi-3rdparty` **不为单个 3rdparty 驱动打 tag**，且该子项目在
v2.2.x 系列中已不再随 monorepo tarball 发布。本仓库既有先例（libplayerone
3.1.0）对同类情况采用 Debian Astronomy Team 在 salsa 上维护的官方上游 tag
快照，本配方沿用同一来源与同一模式：

```
https://salsa.debian.org/debian-astro-team/indi-beefocus/-/archive/upstream/0.1+20221222010828/indi-beefocus-upstream-0.1+20221222010828.tar.gz
sha256 00b4d372db38bd30e873594a18c043773e0740e38c9a489017c9cc4d5f5bee95
```

### 源码来源核验（与 Debian orig.tar.gz 逐字节比对）

担心 salsa 快照与 Debian 归档快照是否存在差异，实际做了全量比对：

| 比对项 | 结果 |
|---|---|
| 文件清单（`find -type f | sort`，95 个文件） | **完全一致**（diff 无输出） |
| 每个文件 sha256（`find -print0 | sort -z | xargs -0 sha256sum`） | **完全一致**（diff 无输出） |

即 salsa 的 `upstream/0.1+20221222010828` tag tarball 与 Debian 归档的
`orig.tar.gz` 内容完全相同（后者因 R39/PF7 的“Debian 下游重打包源”判定不可
直接使用）。因此该来源可信，且与分支版本号一一对应。

> R39/PF7 说明：`deb.debian.org` 等 pool 源被 PF7 判为“Debian 下游重打包源”
> 而拦截（实测 `check_source_urls()` 对 libfli 的 conandata 返回该告警）；
> salsa.debian.org 的官方上游 tag 不在拦截名单内（与 libplayerone 先例一致）。

## W0 依赖发布检查（R35：用 conan download 判定，禁用 conan list）

```
$ conan download libindi/2.2.2.1 -r=ohpcd --only-recipe   → rc=0（revision 9847189a…）
$ conan download libusb/1.0.27   -r=ohpcd --only-recipe   → rc=0（revision 0e6a7c47…）
$ conan download gtest/1.17.0    -r=ohpcd                  → 下载成功（binary 存在）
```

libindi 的传递依赖（cfitsio/4.6.4、libnova/0.16、libusb/1.0.27、curl/8.15.0.1、
gsl/2.8、libjpeg/10、zlib/1.3.1.1、fftw/3.3.11、libev/4.33）在 `conan create`
的依赖解析中全部命中 `Cache`，无需从源码构建。**无待适配的底层依赖**。

## W0b 历史经验核验 + CI 能力矩阵

- 历史归档检索：`archives/i/` 下无 indi-beefocus 历史目录（首次适配）。
- 同源先例核验（可迁移性确认，非盲从）：
  - `archives/l/libindi/2.2.2.1`（INDI 核心库，**本包的直接依赖**）：E092 处理、
    `CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF`、以及 **E537 → test_package 全静态
    探针** 三项结论在本包逐条复现有效。
  - `archives/l/libfli/2.0-20221221182632`（**同为 indi-3rdparty 子项目、同一
    Debian orig.tar.gz 快照模式、同一版本号格式**）：FindINDI 版本正则回移、
    `CMAKE_POLICY_VERSION_MINIMUM` 必须走命令行 `-D`、私有 prefix 三项可直接复用。
- CI 能力矩阵对照：cmake/clang/make ✅；无 Rust/OCaml 需求 → 无阻断。

## 探索阶段定位的真实问题（4 个，均有实测证据）

### 问题 1：FindINDI.cmake 版本正则与 INDI 2.x 不兼容（致命，configure 阶段）

上游 cmake_modules/FindINDI.cmake 用

```cmake
MATCHES ".*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)"
```

而 INDI ≥2.0 的 indiversion.h 写的是 `#define INDI_VERSION "2.2.2"`（带引号），
正则中的 `.` 会匹配到引号，导致 `FATAL_ERROR failed to detect INDI version`。
→ **补丁 0001**：回移上游 indi-3rdparty master 的同一处修复（与 libfli 逐字相同），
改为 `INDI_VERSION[ ]+\"?([0-9]+)\\.([0-9]+)\\.([0-9]+)\"?`。不含平台宏。

### 问题 2：C++ 标准过低（致命，编译阶段）

供应商 `cmake_modules/CMakeCommon.cmake` 把 `CMAKE_CXX_STANDARD` 固定为 **14**：

```
error: C++ versions less than C++17 are not supported.   (gtest-port.h:273)
error: no type named 'any' in namespace 'std'            (libindi/defaultdevice.h:334)
```

gtest 1.17 与 INDI 2.x 头文件都要求 C++17。→ **补丁 0002**：提升到 17，与上游
master 顶层 `cmake_modules/CMakeCommon.cmake` 的值完全一致。

### 问题 3：驱动源码是 INDI 1.x 时代的属性 API（致命，编译阶段）

`driver/beefocus.cpp` 使用 `FocusAbsPosN[0].value` 等数组成员与 `.s = IPS_*`
状态赋值，INDI 2.x 已改为 `FocusAbsPosNP` 属性对象访问器：

```
error: use of undeclared identifier 'FocusAbsPosN'; did you mean 'FocusAbsPosNP'?
error: no member named 's' in 'INDI::PropertyNumber'
error: 'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'
```

→ **补丁 0003**：迁移到 `setValue/setMin/setMax/setStep` + `setState()/getState()`
+ `apply()`。**逐行等同上游 indi-3rdparty master 现已携带的同一处移植**（已用
`diff -w` 与 master 文件比对确认：真实改动 40 行，其余为缩进重排）。

### 问题 4：两处上游构建缺陷（致命，构建/测试阶段）

1. `cmake_minimum_required(VERSION 3.0)`：CMake ≥4 移除 <3.5 兼容，硬报错
   `Compatibility with CMake < 3.5 has been removed`（上游 master 已提升到 3.16，
   本补丁采用同一值）。
2. 单元测试的 POST_BUILD 步骤用裸 `COMMAND ${TEST}` 调用测试程序：
   `make[2]: test_driver: No such file or directory` → **Error 127**。
   改为 `$<TARGET_FILE:${TEST}>` 后正常执行。

→ **补丁 0004**（同时把 `find_package(INDI)` 收窄为 `COMPONENTS driver`，见下）。

### 附加：E537 —— OHOS 共享库在本平台不可加载（配方侧的关键决策）

`conan create` 首次全绿前的最后一环。现象（多角度实测）：

```
$ ./test_driver
Error loading shared library libindidriver.so.2: (needed by ./test_driver)
Error relocating ./test_driver: _ZNK4INDI10BaseDevice13getDeviceNameEv: symbol not found

$ python3 -c "ctypes.CDLL('.../libindidriver.so.2.2.2')"
OSError: ... libindidriver.so.2.2.2: Permission denied
```

关键对照实验（排除“是不是所有 .so 都加载不了”）：

| 对象 | dlopen/mmamp PROT_EXEC | 说明 |
|---|---|---|
| `libusb-1.0.so.0.4.0`（Conan 缓存，133 KB） | **OK** | 第三方库正常 |
| `libfftw3.so.3`（Conan 缓存） | **OK** | 第三方库正常 |
| 本机新编 `libfresh.so` | **OK** | mmap RX 本身可用 |
| 本机新编 8 MB `libbig.so` | **OK** | 与体积无关 |
| `libindidriver.so.2.2.2`（Conan 缓存） | **FAIL Permission denied** | 仅 libindi 产物 |
| `libindiAlignmentDriver.so.2.2.2` | **FAIL Permission denied** | 仅 libindi 产物 |

排除项：非体积问题、非 xattr/权限位问题（`chmod 777` 无效、字节复制到别处同样
失败）、非 TEXTREL（`readelf -d` 只有 `BIND_NOW`，与能加载的 libusb 的 FLAGS_1
一致）。这与知识条目 **E537** 及 `archives/l/libindi/2.2.2.1/notes.md` 记录的
「本机 HMDFS 无法对 OHOS 共享库 mmap PROT_EXEC」完全吻合。

**配方侧解法（三步，均已实测）**：

1. **预置 FindINDI 的缓存变量**：FindINDI.cmake 把
   `_INDI_LIB_RELEASE_<component>` 交给 `find_library()`，该变量已是有效路径时
   `find_library` 会**直接跳过搜索**。配方因此传
   `-D_INDI_LIB_RELEASE_driver=<libindi>/lib/libindidriver.a`，强制解析到静态归档。
2. **收窄组件为 driver**（补丁 0004）：FindINDI 默认同时找 `driver` 与 `align`，
   而 align 上游**只发 .so**；收窄后不再引入不可加载的共享库。
3. **`-Wl,--allow-multiple-definition`**：`libindidriver.a` 内含
   `indidrivermain.o`（定义 `main`）与 `indidriver.o`（定义 `me`），与单元测试
   `test_helpers.cpp` 自带的 `main`/`me` 冲突：

   ```
   ld.lld: error: duplicate symbol: main   (test_helpers.cpp vs indidrivermain.c:297)
   ld.lld: error: duplicate symbol: me     (test_helpers.cpp vs indidriver.c)
   ```

   → 允许重复定义后链接通过。此模式与 `archives/l/libindi/2.2.2.1` 的 test_package
   全静态探针思路一致（该先例亦因 E537 改用静态链接）。

**验证**：上述设置下链接出的 `test_driver`（静态 INDI + 动态第三方）实测
**8/8 全过**（727–776 ms）。

### 附加：构建树内运行测试需要显式 RPATH（非配方缺陷）

补丁 0004 修好 POST_BUILD 调用后，`test_driver` 能被执行，但报：

```
Error loading shared library libusb-1.0.so.0: (needed by .../test_driver)
Error relocating .../test_driver: inflate: symbol not found
```

OHOS 加载器不会自动搜索 Conan 缓存目录。因构建树的驱动与单元测试会在构建期被
实际执行（POST_BUILD + ctest），配方通过 `tc.extra_exelinkflags` 注入
`_transitive_rpath_flags()` 生成的 `-Wl,-rpath,<dep libdir>`。仅影响构建树二进制，
不影响交付产物（消费者由自己的 Conan 环境解析依赖）。

### 附加：CMakeToolchain 的 shell 类标志不能拼进 `-D` cli_args

最初把 `-L... -l...` 直接拼成 `-DCMAKE_EXE_LINKER_FLAGS=...` 传给
`cmake.configure(cli_args=...)`，含空格时 CMake 把后续 token 当成独立参数：

```
CMake Error: Unknown argument -ldl
```

→ 改用 `tc.extra_exelinkflags`（Conan 会正确加引号写入 toolchain）。**后者是正确
API，前者是踩坑记录**。

## 补丁清单（4 个，全部 platform_only=false）

| 补丁 | 内容 | 性质 |
|---|---|---|
| `0001-FindINDI.cmake.patch` | 版本正则回移上游 master（兼容 `INDI_VERSION "x.y.z"` 引号形式） | 上游同步，非平台相关 |
| `0002-CMakeCommon-cxx17.patch` | C++14 → 17 | 上游同步（master 已是 17） |
| `0003-beefocus-indi2-api.patch` | INDI 1.x → 2.x 属性 API 移植（40 行） | 上游同步（master 已移植） |
| `0004-CMakeLists.txt.patch` | cmake_minimum 3.0→3.16；POST_BUILD `$<TARGET_FILE:>`；INDI 收窄为 COMPONENTS driver | 上游缺陷修复 + 本平台 E537 需要 |

**R8 合规**：4 个补丁**均不含任何平台宏**（无 `__OHOS__`），无 `#ifdef` 平台分支，
全部为“上游 master 已有 / 与平台无关的构建缺陷修复”，PR 描述中逐条说明。
`patch_classification` 已在版本级 manifest.yaml 中逐项记录 `platform_only: false`
与 rationale。

## 配方关键决策

| 决策 | 理由 |
|---|---|
| `package_type = "application"` | 产物是驱动可执行文件，不是库 |
| `cpp_info.bindirs=["bin"]` / `resdirs=["share"]` / `libdirs=[]` / `includedirs=[]` | 显式声明产物形态，避免下游误当库链接 |
| `test_requires("gtest/1.17.0")` | gtest 仅上游单元测试用，不进交付依赖 |
| `validate()` 限定 Linux/OHOS（R32） | 非 Linux 家族不支持 |
| `CMAKE_SYSTEM_NAME=Linux` | E092：CMake 不识别 HarmonyOS |
| `CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF`（Block 末置） | 让供应商 FindINDI.cmake 的 legacy 变量生效 |
| `INDI_BUILD_UNITTESTS=ON` + `ctest --output-on-failure` | 层 1 上游测试嵌入 build()（TEST_QUALITY_SPEC §3） |
| `GTEST_ROOT=<gtest pkg>` | 供应商 CMakeLists 用 `find_package(GTest REQUIRED)` + legacy `${GTEST_*}`；PREFER_CONFIG=OFF 时走 CMake 自带 FindGTest，用 GTEST_ROOT 指向 Conan 包 |
| gtest 用 `dependencies.build.values()` 按名查 | `test_requires` 在本包被当依赖消费时不存在，`dependencies.build.get("gtest")` 会抛 KeyError（实测踩过） |
| 传递依赖从 Conan 依赖图动态生成 | FindINDI 无 CONFIG 感知，必须显式注入；硬编码易漂移 |
| 不设 `--disable-shared` / R26 | 产物非系统同名库；bin 可执行文件，无 .so 污染 `/lib`/`/lib64` 风险 |

### 依赖声明说明

`requirements()` 只声明 `libindi/2.2.2.1`。libindi 的传递依赖（cfitsio/nova/usb/
curl/gsl/fftw3/libev/jpeg/zlib）由 Conan 依赖图自动带入，配方经
`self.dependencies.host` 读取它们的 `libdirs`/`libs` 生成 `-L/-l`，**不硬编码**。

## 上游测试情况与补全（R51 三步法）

### 1. 清点（附证据）

上游源码树 `unit_tests/` 目录含：

```
unit_tests/test_driver.cpp      ← 8 个 gtest TEST() 用例（DEVICE.*）
unit_tests/test_helpers.h
unit_tests/test_helpers.cpp     ← 提供 main() + CStringWrap 等测试工具
```

CMakeLists.txt 第 54-71 行注册：

```cmake
SET(UNIT_TESTS test_driver)
...
add_test( run-tests ${TEST} )
```

| 测试类型 | 数量 | 来源 |
|---|---|---|
| CTest 注册用例 | **1** | `add_test(run-tests test_driver)` |
| 其中 gtest 用例 | **8** | `unit_tests/test_driver.cpp` 的 8 个 `TEST(DEVICE, …)` |
| 集成测试 | 0 | 上游无 |
| 其他测试 | 0 | 上游无 |

**上游 N = 8 个 gtest 用例（1 个 CTest 条目）**。驱动走**软件模拟固件**
（`beesimfirmware` 复用 `firmware/` 同一套代码，含 `AdvanceTimeForward` 加速时间），
**不需要真实硬件**，因此可在干净 CI 环境实跑 —— 不存在“没环境”的情况。

### 2. 运行（实测）

在 `build()` 内 `cmake.build()` 之后执行 `ctest --output-on-failure`；
上游 CMakeLists 另有 POST_BUILD 步骤（补丁 0004 修复后）会先跑一遍。

```
[==========] Running 8 tests from 1 test suite.
[  PASSED  ] 8 tests.
[----------] 8 tests from DEVICE (776 ms total)
```

| 测试类型 | 实测数 | 通过 | 通过率 | 说明 |
|---|---|---|---|---|
| 上游 CTest（8 个 gtest 用例） | 8/8 | 8 | **100%** | 证据落盘 [reports/r51-upstream-tests.log](reports/r51-upstream-tests.log) |

**上游测试未做任何修改**（0 处）：8 个用例原样保留并通过。

### 3. 回填

见 PR 描述统计表（N=8，N′=8，通过率 100%）。

### 补全测试用例（test_package，4 个具名用例）

上游是**驱动可执行文件**而非库，`test_package` 必须真正执行包内二进制（R34）。
本适配新增 4 个消费者端到端用例：

| 用例 | 类型 | 内容 |
|---|---|---|
| HC-1 | consumer_e2e | 包内 `bin/indi_beefocus` 是 ELF64/EM_AARCH64 且可执行；按上游 `indidrivermain.c` 契约，未知选项打印 "Usage: … INDI Device driver framework." 并以状态 1 退出 |
| HC-2 | consumer_e2e | 真实向包内驱动 stdin 写入 `<getProperties version="1.7" />`，断言驱动经 INDI 协议路径消费该请求（`-v` 回显）并发出自身诊断；`nm` 断言 7 个驱动自有入口 + 4 个 INDI 协议入口（newLilXML/readXMLEle/delXMLEle/dispatch）确实编入交付 ELF |
| HC-3 | consumer_e2e | 包内 `share/indi/indi_beefocus.xml` XML 良构、注册 `indi_beefocus`、标签 Bee Focuser、归入 Focusers 组 |
| HC-4 | **harmony_specific** | `readelf` 检查交付 ELF：DT_NEEDED 非空且**不含绝对路径**（E537 教训：机器私有 Conan 缓存路径泄漏 = 制品不可跨机消费）；确认上游 CMakeCommon 请求的 BIND_NOW/RELRO 硬化仍然可见 |

### 统计口径：按「具名端到端用例数」，不按断言数

PR 描述「适配后测试用例统计」表的「鸿蒙特有测试」行填 **4**（HC-1..HC-4），
「合计」填 4；用例内部的 ok/FAIL 行（共 31 条）只是各用例的检查项，不单独计数。

### HC-2 的诚实说明（重要）

HC-2 最初写成“捕获 `<def>` 输出并断言设备名/属性名”，实测**不成立**，已在适配
过程中修正为可观测断言。原因（有实测证据，非猜测）：

上游 `libs/indibase/indidrivermain.c` 的 `clientMsgCB()` 把收到的 XML 交给
`deferMessage()` 排队，真正的 `dispatch()` 由 `addImmediateWork(flushDeferredMessages)`
在**事件循环迭代**时触发；而 `read()` 返回 0（管道 EOF）时驱动直接
`fprintf(stderr, "%s: EOF\n", me); exit(1);`。因此一次性管道喂入请求后驱动
在 flush 之前就退出：

```
$ printf '<getProperties version="1.7" />\n' | ./indi_beefocus   → stderr: indi_beefocus: EOF（stdout 为空）
$ ./indi_beefocus -v  （保持 stdin 打开，写请求）                 → stderr: <getProperties version="1.7"/>（驱动已消费）
```

这不是本适配引入的缺陷（上游行为），也不影响交付产物可用性（真实使用由
`indiserver` 常驻拉起驱动，stdin 不关闭）。因此 HC-2 改为断言**可观测事实**：
驱动确实经 INDI 协议路径消费了请求 + 交付 ELF 确实含驱动与框架符号。原“冒烟式
断言”的写法被弃用，避免出现“形式通过、实质空转”的假测试（R34）。

### 防空壳的结构性保障（R34 / L1e）

- `test_package/conanfile.py` 的 `test()` 用 `self.run` 真正执行包内二进制；
  `can_run()` 为假时**直接抛 AssertionError**（不允许静默跳过）。
- 缺任一包内制品（`bin/indi_beefocus` / `share/indi/indi_beefocus.xml`）时直接
  失败，不跳过。
- L1e 负向预期：`mv` 走包内 `bin/` 后 HC-1.1 找不到可执行文件 → 立即失败。

## 验证结果

```console
$ python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight indi-beefocus 0.1-20221222010828 --src <src>
  ✅ 语言匹配: task=cpp, detected=cpp — 继续适配主流程

$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
  ...
  [==========] Running 8 tests from 1 test suite.
  [  PASSED  ] 8 tests.
  ...
  == 4 cases, 0 failed ==
  == 31 checks, 0 failures ==
  RESULT: PASSED
  rc=0
```

| 项 | 结果 |
|---|---|
| `conan create` 退出码 | **0** |
| 上游 8 个 gtest 用例 | **8/8 通过（100%）** |
| 上游测试修改 | **0 处** |
| test_package 用例 | **4/4 通过** |
| test_package 检查项 | **31/31 通过** |
| 产物 | `bin/indi_beefocus`、`share/indi/indi_beefocus.xml`、`licenses/LICENSE` |

## 复现命令

```sh
# W3 本地编译验证
cd archives/i/indi-beefocus/0.1-20221222010828
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable

# 单独查看上游测试日志（ctest 详细输出）
#   conan create 日志中 "Running 8 tests from 1 test suite." / "[  PASSED  ] 8 tests."
```

## 踩坑与注意事项

1. **`dependencies.build.get("gtest")` 会抛 KeyError**：`test_requires` 在本包作为
   依赖被消费时不存在。改为遍历 `dependencies.build.values()` 按名匹配。
2. **`-DCMAKE_EXE_LINKER_FLAGS=<含空格>` 不能用 cli_args 传**：CMake 把后续 token
   当独立参数（`Unknown argument -ldl`）。用 `tc.extra_exelinkflags`。
3. **`CMAKE_POLICY_VERSION_MINIMUM` 必须走命令行 `-D`**：写进
   `tc.variables` → `conan_toolchain.cmake` 是普通变量，CMake 在内部 system scope
   求值它，不跨到 project directory scope（libfli 同款教训，本包复现）。
4. **静态链接 INDI 归档会引入 `main`/`me`**：需 `--allow-multiple-definition`，
   否则单元测试链接报 duplicate symbol。
5. **构建树内运行测试需 RPATH**：OHOS 加载器不自动搜 Conan 缓存目录。
6. **`make -j` 的 jobserver fifo 在 HMDFS 上偶报 `Operation not permitted`**：
   非致命（make 回退串行继续），与配方无关。

## 遗留与后续

- 无待办阻断项。
- 上游 indi-3rdparty master 的 beefocus 已带 INDI 2.x 移植；本包补丁 0002/0003
  与其等价，待上游为子项目打 tag 后可直接切换官方源并弃用补丁。
- 潜在路径 B 素材：本包与 libfli/libindi 共同构成「indi-3rdparty 系子项目适配
  模式」（E092 + FindINDI 收窄 + E537 静态链接 + 传递依赖注入四件套），具备提炼
  为通用新 SKILL 的形态；本轮先完成路径 A，不牺牲 A 的通过率。
---

**编译结束**: 2026-10-03 21:17
**最终状态**: built
