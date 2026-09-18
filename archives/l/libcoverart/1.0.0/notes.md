# libcoverart 1.0.0 编译笔记（HarmonyOS PC · arm64 · CMake）

## 上游审计

- 仓库：https://github.com/metabrainz/libcoverart ，tag `release-1.0.0`
  （2012-10-09，commit 8bd416e），LGPL-2.1。
- 源码包：GitHub tag archive（58 个条目，58600 字节），顶层目录
  `libcoverart-release-1.0.0`，`strip_root=True` 处理。
  sha256 `cc830e265fef0f77ed172705bb60ca705a4237d02c0454d3ee4952e1de98eb76`
  为本机实测下载值（GitHub 生成包哈希与 MusicBrainz 发布的旧 tarball MD5
  不同，属不同打包器所致，文件内容一致）。
- 构建系统：纯 CMake。根 `CMakeLists.txt` + `src/` + `tests/` + `examples/`。
  无 `enable_testing()`、无 `add_test()`、无 `make check` 目标——上游没有
  注册到 CTest 的测试（`cmake.test()` 会报 "No tests were found"，故配方
  不调用它，改为直接运行构建产物）。
- 产物：单个 `libcoverart`（C++ 核心 + C API 同一 target，
  `src/CMakeLists: ADD_LIBRARY(coverart SHARED ...)`，链接 neon + jansson；
  C API 由构建时工具 `make-c-interface` 从
  `src/cinterface.xml` + 5 个 `.inc` 生成 `caa_c.cc`/`caa_c.h`）、9 个头文件、
  单个 `libcoverart.pc`。

## 依赖（W0）

| 依赖 | 版本 | 在树内状态 | 用途 |
|------|------|-----------|------|
| neon | 0.34.0 | 有配方（`--without-ssl`，仅静态） | HTTP 传输（HTTPFetch.cc 直接 `#include <ne_*.h>`） |
| jansson | 2.15.1.1 | 有配方（与 2.15.1 同上游 v2.15.1 包，零 tool_requires） | JSON 解析 |
| libxml2 | 2.15.3.1 | built | 仅构建时：`make-c-interface` 生成器链接它 |
| zlib | 1.3.1.1 (override，经 neon) | 有配方，零 tool_requires | neon 传递依赖；裸 1.3.1 会撞 CCI 配方引入 cmake 工具边 |
| expat | 2.8.2.1 (override，经 neon) | 有配方，零 tool_requires | neon 传递依赖；裸 2.8.2 会撞 CCI 配方引入 cmake 工具边 |

- 三个依赖在树内均有对应版本配方；制品仓发布状态（published/built）以
  真机预检 `conan download` 实测为准（本机 Windows 无 conan，不做判断）。
- 已知功能降级：neon 以 `--without-ssl` 构建，在线抓取 https 资源时
  TLS 能力缺失（见 PR 正文“补充说明”）。离线 API 全不受影响。

## 上游测试清单（R51 三步法之清点）

| # | 程序 | 场景数 | 能否在真机门禁执行 |
|---|------|--------|--------------------|
| 1 | `tests/ctest`（tests/ctest.c，C API） | 1（new → get_version → delete，打印 `Version: 'libcoverart-v1.0.0'`，exit 0） | 能（纯离线）。build() 末尾运行并做字符串门禁 |
| 2 | `tests/cctest`（tests/test.cc，C++ API） | 6（ReleaseInfo + FetchFront + FetchBack + 3× FetchImage，均打到 Cover Art Archive 公网） | 否：需公网；且程序 catch 异常后仍 return 0，无断言语义。只编译验证，不 gated |
| 3 | `examples/example`、`example_c` | 演示程序，非测试 | 只编译验证 |

- `tests/ctest.c` 另含一个从未被调用的 `CompileTest()`（全 API 编译覆盖），
  其调用形状是本配方 test_package 断言设计的来源。
- 结论：门禁内可执行 1/7 上游场景；6 个在线场景缺公网依赖未运行，
  已在 PR 正文补充说明如实声明。

## 配方内可移植调整（无 patches/，全部经 replace_in_file 落盘前完成）

1. `cmake_minimum_required(VERSION 2.6)` → `3.5`：现代 CMake（≥4.0）
   直接拒绝 <3.5 的下限声明；不改任何构建逻辑。
2. 去掉三处 `CMakeLists.txt`（src/tests/examples）的 `-Werror`
   （保留 `-Wall -Wextra`）：2012 年代码在 clang 15 下的新警告会被转成硬错误。
3. 经 tarball 实测确认**不需要**改 `xmlParser.cc → xmlParser.cpp`
  （1.0.0 tag 内已是 `xmlParser.cpp`；写错的是 master 分支）。
   `xmlParser.h` 的 `<tchar.h>` 在 `_XMLWINDOWS` 守卫内，OHOS 不触发。

## 关键构建决策

- **默认静态**（`shared=False`）：neon/0.34.0 只产出非 PIC 静态库，
  动态链接 libcoverart 会在 aarch64 报 relocation 错误。jansson 取共享/静态
  均可（generate() 按实际产物 glob 定位）。
- **依赖定位三保险**：`NEON_INCLUDE_DIR/NEON_LIBRARIES`、
  `JANSSON_INCLUDE_DIR/JANSSON_LIBRARIES`、`LIBXML2_INCLUDE_DIR/LIBXML2_LIBRARY`
  全部显式 pin 到 Conan 包路径（glob 实测文件名），外加 PkgConfigDeps +
  CMakeDeps。上游 FindNeon/FindJansson 的 `/usr` 回退在干净 worker 上永不命中。
- **test_c 用 C++ 链接器**（`LINKER_LANGUAGE CXX`）：静态 C++ 核心经由 C API
  被 C 程序链接时需要 C++ 标准库（上游 README 原话：C API 链接加 `-lstdc++`）。
- `package_info().libs = ["coverart"]`（单库；1.0.0 无 coverartcc）；OHOS/Linux 下
  `system_libs = ["m"]`（R32 写法）。

## 证据标记语义

- `HMBS_UPSTREAM_TEST_RESULT`（build()）：`framework=custom`，
  `command=./tests/ctest (offline C-API: new/get_version/delete)`，
  `discovered=1/executed=1`。证伪门：输出必须含
  `Version: 'libcoverart-v1.0.0'`，否则 build 直接失败（空输出/错二进制
  混入会被抓住；上游该程序 exit 恒 0，字符串门是唯一的真实信号）。
- `HMBS_TEST_PACKAGE_RESULT`（test()）：`./test_c` 8 个 + `./test_cc` 8 个
  `PASS:` 行计数，`discovered=16`。二进制任一返回非零或出现 `FAIL:` 即失败。
  离线断言依据：`Version()=="libcoverart-v1.0.0"`（config.h `PACKAGE-VERSION`
  实测源码）、构造后 `LastResult==Success`/`LastHTTPCode==200`/
  `LastErrorMessage` 为空（CoverArt.cc 私有成员初值实测源码）。

## 状态

built（配方工作树完成，待 HMBS 真机预检：conan create + test_package +
上游离线测试；通过前不提交、不推送）。

## 2026-09-16 真机失败修复（cmake/4.4.3 KeyError: 'OHOS'）

- 现象：预检在 Computing dependency graph 后构建 `cmake/4.4.3` 工具包，
  `build() line 35 ... KeyError: 'OHOS'`（CCI cmake 配方的 conandata 无
  OHOS 源码条目），libcoverart 主包尚未进入 configure。
- 根因：裸版本 `jansson/2.15.1` 与经 neon 引入的 `zlib/1.3.1` /
  `expat/2.8.2` 在 conancenter 与 ohpcd 双 remote 共存，预检先查
  conancenter 即命中 CCI 配方，其 `tool_requires` 拉入无 OHOS 条目的
  cmake 工具包。同仓 ayatana-ido/0.10.4-v2 notes 第五至七轮记载同机制
  同指纹（gtest 换版本→vendor 仍复现，证伪后收敛到 CCI 工具边）。
- 改动：`jansson/2.15.1` → `jansson/2.15.1.1`（同上游 v2.15.1 包，
  仓内独有、零 tool_requires，已本地 grep 核验）；新增
  `zlib/1.3.1.1` + `expat/2.8.2.1` `override=True`（同上游源码的仓内
  独有版本，零 tool_requires），neon/libxml2 保持不变。
- 未采用：RREV pin（ohpcd RREV 无法在本地合规查询，属编造）；vendor
  上游源码（本轮父链明确在直接/传递依赖版本选择，无需删边重构）。
- 证伪信号（下轮预检判定）：cmake KeyError 消失即命中；若仍在则父节点
  在剩余裸版本（neon/libxml2）或基线侧工具二进制缺失，不再重复换版本。

## 2026-09-16 第二轮：E092 平台别名 + 可写临时目录（待验证）

- 上一方案是否有效：有效——cmake/4.4.3 工具边消失，
  zlib/1.3.1.1、expat/2.8.2.1、jansson/2.15.1.1 均落到 ohpcd 配方，
  失败指纹转移到主包 `cmake.configure()`。
- 新失败根因：conan_toolchain 生成 `CMAKE_SYSTEM_NAME=HarmonyOS`，
  cmake 4.4.3 无 `Platform/HarmonyOS.cmake`，`project()` 报
  "System is unknown to cmake" 并连带
  `/data/service/hnp/bin/clang/clang++` sanity 失败。
- 改动：`generate()` 新增 `CMAKE_SYSTEM_NAME=Linux` +
  `CMAKE_SYSTEM_PROCESSOR=aarch64`（E092，同 julius/1.0.0 与 ayatana-ido
  在仓先例；本库为纯 POSIX 网络/JSON 客户端，无 Linux 专有平台逻辑，
  只替换平台名）；`CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4.x
  版本门；`generate()` 经 Environment 落盘 `hmbs_tmpdir` 脚本 +
  `build()` 进程级兜底，确保 cmake/编译器子进程走任务级可写目录
  （只替换临时根，不删测试）。
- 上游测试与 test_package 口径不变（离线 ctest 1 用例 + 新增 16 断言）。

## 2026-09-16 第三轮：NDK ohos.toolchain + 裸 cmake（待验证）

- 上一方案是否有效：无效——`CMAKE_SYSTEM_NAME=Linux` 别名后，
  `project()` 不再报 unknown，但 `-- The C/CXX compiler identification
  is unknown` 仍在，`/data/service/hnp/bin/clang/clang++` 识别失败。
  结论：conan_toolchain 提供的编译器调用缺 NDK 目标三元组/sysroot，
  换平台名不够，需换工具链（同指纹第 3 次，必须换策略）。
- 新路线（同 libxml2/2.15.3.1 与 zstd/1.5.7.1 在仓先例）：主配方删除
  CMakeToolchain/CMakeDeps/PkgConfigDeps/VirtualRunEnv，`generate()`
  仅保留可写临时目录脚本；新增 `_ohos_toolchain()`（conf/OHOS_NDK_HOME
  优先，`/data/service/hnp/ohos-sdk.org/*` glob 兜底）与 `_cmake_bin()`
 （HMBS_CMAKE/conf/PATH 顺序）；`build()` 用裸 cmake
  `-DCMAKE_TOOLCHAIN_FILE=ohos.toolchain -DOHOS_ARCH=arm64-v8a` 配置构建，
  依赖 pin（NEON/JANSSON/LIBXML2 cache 变量）原样保留；
  `package()` 用 `cmake --install` + 共享库自签（静态默认下无操作）。
- test_package 同步去掉 CMakeToolchain：改用 NDK C++ 驱动直接编译
  test_c.c/test_cc.cpp（全依赖 include/libdir 自动收集，
  `--start-group` 消除静态链接顺序依赖），`test()` 计数与
  HMBS_TEST_PACKAGE_RESULT 口径不变（16 断言）。
- 上游离线 ctest 1 用例与证伪门（版本字符串）不变。
- 证伪信号：unknown/identification 双错消失即命中；若 NDK glob 落空
  则报错指明缺 ohos.toolchain.cmake，属环境基线问题。

## 2026-09-16 第四轮：NDK 缺失时降级备用工具链（待验证）

- 上一方案是否有效：无效——预检 compile 门报 `Invalid configuration: 找不到 ohos.toolchain.cmake`，主包未进入 configure。结论：预检 worker 的 SDK 挂载路径与 CI 不同（CI profile 引用的 ohos-sdk_26.0.0.18 路径在预检侧 glob 落空），硬报错路线不可行，需换策略（第 2 策略周期）。
- 新路线：`_ohos_toolchain()` 改为返回 None（扩大搜索：OHOS_SDK_HOME 等环境变量 + 多 glob 模式），`build()` 在 NDK 存在时沿用它（含 -DOHOS_ARCH），缺失时降级到本配方生成的 `hmbs-fallback-toolchain.cmake`（CMAKE_SYSTEM_NAME=Linux + STATIC_LIBRARY try-compile，同 lapack/3.12.1 在仓先例；编译器取自 profile conf tools.build:compiler_executables，同 libcello/2.1.0 先例；llvm-ar 兄弟路径自动探测）。
- 上游测试与 test_package 口径不变（离线 ctest 1 用例 + 16 断言）。
- 证伪信号：compile 门进入 configure 即命中；若备用链仍报 compiler identification unknown，则需进一步补 sysroot/target 标志，不再重复加 glob。

## 2026-09-16 第五轮：交叉生成器两阶段导入（待验证）

- 上一方案是否有效：有效——备用链使 configure 进入（编译器识别通过，Neon/Jansson 均 Found），失败指纹转移到 `src/CMakeLists.txt:16 INCLUDE IMPORTFILE-NOTFOUND`。
- 新失败根因：上游以 CMAKE_CROSSCOMPILING 决定 make-c-interface 策略，交叉时 INCLUDE（\${IMPORT_EXECUTABLES}）（缺省即 IMPORTFILE-NOTFOUND），非交叉时原生构建并 EXPORT；本机 NDK/备用链均落入交叉分支，而配方从未提供该文件。
- 改动：build() 先无工具链原生配置、只构建 make-c-interface 目标，产出 native-gen/ImportExecutables.cmake，再经 -DIMPORT_EXECUTABLES 传入主构建；生成器仅由 xmlParser.* 自举不链接 neon/jansson。测试口径不变。
- 证伪信号：configure 通过并进入构建即命中；若原生配置本身失败，则需检查 host 编译器选择，不再动主工具链。

## 2026-09-16 第六轮：展开src通配符DEPENDS（待验证）

- 上一方案是否有效：有效——原生两阶段使两次 configure 均 Configuring done，失败指纹转移到构建期 `make: No rule to make target src/*.inc`。
- 新失败根因：上游 src/CMakeLists 的 ADD_CUSTOM_COMMAND 写了字面 `DEPENDS ... *.inc`，现代 CMake 原样生成字面 make 目标故无规则；经 GitHub tag 实测 src 下恰为 5 个 .inc（c-int-coverart-defines/source、c-int-imagedata-defines/source、c-int-source-funcs）。
- 改动：_portability_fixes 新增第 3 项，把该 DEPENDS 展开为 5 个显式文件名；其余（NDK优先/备用链、两阶段导入、测试口径）不变。
- 证伪信号：构建进入编译链接即命中；若再报缺其他字面目标，则同法继续展开，不回退两阶段路线。


## 2026-09-16 第七轮：E012/E429 归档器覆盖（待验证）

- 上一方案是否有效：有效——原生两阶段 + DEPENDS 展开后两次 configure 均 Configuring done，9 个 .o 全编译通过，失败指纹转移到 `[57%] Linking CXX static library libcoverart.a` + `Error running link command: no such file or directory`（CI #48596）。
- 新失败根因：ohos.toolchain.cmake 把 CMAKE_AR/RANLIB 指向 SDK native/llvm/bin 内不存在的二进制（geos/joltphysics/crunch-dxtc/googletest/draco 在仓同法证明；CI worker PATH 仅含 /data/service/hnp/bin，ar 不可见），.o 全对、唯造 .a 时 ENOENT，且报错不说是哪个程序缺失。真机预检通过是因 HMBS 前置了工具目录，CI 侧未覆盖故复现。
- 改动：新增 `_ohos_llvm_bin()`（从 toolchain 推导 <ndk>/llvm/bin，落空时 glob 通用 SDK 路径）+ `_archiver_defs()`（SDK llvm/bin → /data/service/hnp/bin → PATH 顺序探测 llvm-ar/ranlib；CMAKE_AR:FILEPATH + C/CXX_CREATE_STATIC_LIBRARY=`<ar> rcs` 覆盖，找到 ranlib 则 pin，否则 `-DCMAKE_RANLIB=:` 绕过默认规则中的失效调用），build() 在 NDK/备用链均接入；`_fallback_toolchain()` 同样用多候选重写 CMAKE_AR/RANLIB，避免文件内 set() 覆盖命令行缓存值。测试口径不变。
- 证伪信号：.a 归档通过并进入 install/test 即命中；若仍同指纹，则需打详日志先查 CMAKE_AR/RANLIB 实际解析值，不再重复换链。
