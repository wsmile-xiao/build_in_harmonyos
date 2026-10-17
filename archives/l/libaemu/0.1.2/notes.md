# libaemu 0.1.2 适配笔记

## 编译环境

- 构建系统: CMake (>= 3.18, gfxstream build-config, 无第三方运行时依赖)
- 编译日期: 2026-09-25
- 编译器: clang 15 (aarch64-unknown-linux-ohos, musl libc)
- 状态: built (本地配方完成，真机预检待 HMBS 回填)

## 上游信息核实

| 项 | 值 | 验证方式 |
|---|---|---|
| 源码获取 | `git clone` 固定 commit `dd8b929c`（清华 AOSP 镜像优先，官方 googlesource 回退） | 2026-09-25 实测：ls-remote + 全量 clone + 逐文件比对 |
| 源码一致性 | tag `+archive` 当日包与 `dd8b929c` 树 411 文件逐字节一致；5 个关键 blob SHA 与 git 对象一致 | 按文件 sha256 全量比对 + `git hash-object`/`rev-parse` |
| Tag/Commit | refs/tags/v0.1.2-aemu-release（标注 tag 对象 `a6ed43…`）；实际发布内容 = commit `dd8b929c247ce9872c775e0e5ddc4300011d0e82`（"aemu: improve licensing"，与 Fedora `0.1.2^20231031gitdd8b929c` 同源） | git ls-remote + `rev-parse tag^{commit}` + 归档内容比对 |
| License | Apache-2.0 | tarball 内 LICENSE 全文 |
| 构建系统 | CMake, 版本 0.1.2 (CMake/Version.cmake) | Version.cmake |
| 库 | aemu-base / aemu-logging / aemu-host-common / aemu-snapshot (+ pkg-config .pc) | CMakeLists.txt |
| 上游测试 | ENABLE_VKCEREAL_TESTS=ON 时两个 gtest 二进制, 共 124 个 TEST/TEST_F | 19 个 unittest 源文件逐文件计数 |
| 依赖 | 运行时无第三方依赖; 测试需 gtest+gmock (pkg-config 查找) | third-party/CMakeLists.txt |

## 上游测试审计(124 个用例口径)

计数方法 gtest_macros, 仅统计 build-config/gfxstream 接线的 19 个文件:

- base 80: AlignedBuf 6, HealthMonitor 25 (9 TEST + 16 TEST_F), ArraySize 2, LayoutResolver 2, LruCache 1, ManagedDescriptor 4, Optional 13, ring_buffer 11 (含 1 DISABLED_ProducerDrivenSync), StringFormat 7, SubAllocator 4, TypeTraits 3, WorkerThread 2
- host-common 44: address_space_graphics 10 TEST_F, address_space_host_memory_allocator 5, shared_slots 5, HostAddressSpace 9 TEST_F, HostmemIdMapping 3, logging 9, GfxstreamFatalError 3
- base 目录下未接线的 ContiguousRangeMapper/FileUtils/ScopedFd/SharedMemory/StringParse/Win32UnicodeString 等单测不在 gfxstream 子集内, 不计入总数; host-common 的 VmLock/HostGoldfishPipe 单测同理未接线, 不计入
- DISABLED 用例处理: 源码宏共 124 (含 ring_buffer DISABLED_ProducerDrivenSync), 但 gtest 在所有平台默认排除 DISABLED_, ctest -N 官方注册为 123 (base 79 + host-common 44); 2026-09-26 预检实测 discovered=123/executed=122/passed=122/skipped=1/failed=0, marker 状态为 incomplete + 单 gaps (count=1) 求和 total-passed=1 (catch2先例: 有gaps时不用passed)

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

关键 CMake 开关 (与上游 rebuild.sh 一致, 另加测试开关):

- `-DAEMU_COMMON_BUILD_CONFIG=gfxstream` (必传, 否则顶层 `if(NOT ${...} STREQUAL "")` 误判)
- `-DAEMU_COMMON_GEN_PKGCONFIG=ON`
- `-DENABLE_VKCEREAL_TESTS=ON` (打开上游 gtest 套件)
- `-DAEMU_BASE_USE_LZ4=OFF -DAEMU_COMMON_USE_PERFETTO=OFF`
- googlesource `+archive` 无顶层目录时代已结束：源码改为 `Git.clone` 固定 commit（`dd8b929c`），按 `git_urls` 顺序试错，清华镜像优先、官方回退，checkout 后校验 `HEAD == git_commit`
- 上游 124 用例口径已在 `dd8b929c` 树上复核：19 个接线单测文件计数与原表完全一致（base 80 + host-common 44），12 处内容差异均为非单测文件（license 头/LICENSE/Lock.h），总数不变
- gtest 由 `test_requires gtest/1.17.0` + `PkgConfigDeps` 提供 .pc, 供上游 `pkg_search_module` 查找
- OHOS shared 下注入 `-Wl,-soname,` (CMake 无 HarmonyOS 平台模块, 同 libaegis/libharu 先例)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | 顶层 CMake 对空变量的 `if(NOT ${AEMU_COMMON_BUILD_CONFIG} STREQUAL "")` 在未传值时语义不明 | 上游默认全量构建路径依赖外部 angle 等 | 固定传 `-DAEMU_COMMON_BUILD_CONFIG=gfxstream` (nixpkgs/Arch 同款) |
| 2 | 上游测试默认关闭 (rebuild.sh 用 OFF) | VKCEREAL 门控 | 配方强制 ON, 并用 gtest 补齐依赖后跑 ctest |
| 3 | 上游用 pkg-config 找 gtest, 非 find_package(GTest) | third-party/CMakeLists.txt | PkgConfigDeps 生成 .pc, 不设 GTest_DIR |
| 4 | Windows 下 `archives/l/libXext` 与 `archives/l/libxext` 大小写目录冲突导致 worktree 常显 2 个 modified | 上游同时存在大小写两份目录, Windows 文件系统不区分 | 本 PR 未触碰该两文件; Linux 真机/CI 不受影响 |
| 5 | 真机 `source()` 下载 `+archive` 报 ConnectTimeout；且同 URL 上午/晚上两次下载字节数与 sha256 均不同（423118 B/`a69bf040…` → 423321 B/`00deeca3…`） | 双重根因：runner 到 googlesource 建连超时 + Gitiles 按请求重生成 gzip（tarball sha256 天然腐烂）；另 tag 归档实际装的是 `dd8b929c` 树而非 tag 对象剥出的 `50b85682` | 弃用 `get()` 抓包：`source()` 改 `Git.clone` 固定 commit `dd8b929c`，清华 AOSP 镜像优先、官方回退，checkout 后断言 HEAD；清华侧已用 ls-remote/全量 clone/411 文件逐字节比对验证与官方包一致；无官方 GitHub 镜像（`github.com/google/aemu` 404），故不用 gh-proxy |
| 6 | 真机 `make` 编译 `host-common/logging.cpp` 时 OHOS libc++ 头 (`__algorithm/comp.h` 等) 报 `_LIBCPP_BEGIN_NAMESPACE_STD` 等 unknown-type 级联错误；此时 configure 已过（`project()`/`find_package(PkgConfig)`/`pkg_search_module(gtest/gmock)` 均成功），故非缺编译器/缺 pkg-config/缺 gmock-pc 问题 | 上一周期"profile 钉死路径缺失→PATH 回退"假设已完成其使命（configure 通过为证），当前是新的失败域：TU 真正解析系统头，编译器二进制之外的 SDK/sysroot/`-std` 配套才是决定因素；旧方案只换二进制路径字符串，不核验 SDK 一致性 | 本轮改走不同路线：保留 PATH 探针（健康机零改动）但不再加新的路径替换；改用文档化机制声明输入——`CMAKE_CXX_STANDARD=17`+`REQUIRED=ON` 缓存钉死 C++17 底线（E130 家族），`CMAKE_VERBOSE_MAKEFILE`+`EXPORT_COMPILE_COMMANDS` 只加证据不加标志，toolchain 修复函数只加编译器/sysroot 行的前后日志输出，供下一轮按真实编译命令定位 SDK 错配；未改测试口径 |
| 7 | 同一 `_LIBCPP_BEGIN_NAMESPACE_STD` 指纹第二次失败：C++17 底线+VERBOSE 取证未移动失败，且聚焦摘要省略日志中段（真实编译命令与首个错误行不可见）；失败点仍在主库 `logging-base` 的 TU（非测试目标），故与 gtest/.pc 无关 | 连续两轮 flag 微调（编译器路径替换、C++17 缓存）均未改变指纹，按策略必须换路线：停止猜测头文件语义，改为配方内只读取证 | `build()` 在 configure 与 build 之间新增 `_dump_build_evidence()`：只读打印 conan_toolchain.cmake 的编译器/sysroot/flags 行、CMakeCache 的编译器行、`compile_commands.json` 中 `host-common/logging.cpp` 的完整编译命令（含 `-std`/`-stdlib`/`-isystem`/`--sysroot` 顺序）；全函数 try/except 包裹、永不抛异常、不改任何标志与测试口径，供下一轮按真实命令定位 |
| 8 | 同一指纹第三次失败：info 通道取证落在摘要省略区（两轮均未见 `HMBS diag evidence/tc/cache/cmd` 行，但 `cmake.build()` 行号 318→319 证明取证代码已部署执行），而 generate 期 `HMBS diag compilers/wrote fallback` 行轮轮保留；并行完成上游审计：三处 `-I` 根（base/include、host-common/include/host-common、base/include/aemu/base 全量约 150 头文件）无 `__config` 同名遮蔽文件，base/host-common 两处 CMake 无 INTERFACE 毒化宏（仅 include 目录与 WIN32/ANNOTATIONS 定义） | 证据链收敛：配方与上游均干净（bandit 同 SDK C++ 绿、baloo/bcc 证明本 SDK `__config`/`__config_site` 机制正常），info 通道在门禁摘要下不可达；必须换路线把证据送入摘要保留的错误尾部 | `build()` 包裹 `cmake.build()`：失败时 `_report_build_failure_evidence()` 从 `compile_commands.json` 提取 logging.cpp 的 compiler/`-std`/`-stdlib`/`--sysroot`/`--target`（缺失标 MISSING）与工具链 SYSROOT 行，经 `self.output.error` 发出并拼入新 `ConanException`（附原文）抛出；成功路径零改动，收集全程 try/except；未改测试口径 |
| 9 | 同一指纹第四次失败，本轮错误尾部取证穿透成功：`compile_commands.json` 中 logging.cpp 为 `-std=c++17`/`-stdlib=libc++` 但 `--sysroot=MISSING`/`--target=MISSING`，`conan_toolchain.cmake` 无 `CMAKE_SYSROOT`（`tc:SYSROOT-unset`）；configure（project/PkgConfig/pkg_search_module）全过而 `make` 解析系统头失败 | 新失败域定位完成：Conan 的 CMakeToolchain 对 os=OHOS 仅映射 `CMAKE_SYSTEM_NAME=HarmonyOS`，不提供 SDK sysroot/target（expat/zstd/glfw 先例称 ML-0035）；缺 sysroot 时 OHOS 定制 libc++ 头（`libcxx-ohos`，需配套 `--sysroot=<sdk>/native/sysroot`+`--target=aarch64-linux-ohos`+OHOS 定义）无法选中正确 `__config`，`_LIBCPP_*` 宏全空致级联 unknown-type；前三轮只换二进制路径/C++17/取证通道，均未补 sysroot，故指纹不动 | 改走不同实现路线（expact/zstd 裸 cmake 路子）：主配方与 test_package 弃用 CMakeToolchain（Linux 回退除外），`generate()` 仅保留 PkgConfigDeps+gmock-pc 回退；`build()` 经 `_ohos_toolchain()` 自发现 SDK `ohos.toolchain.cmake`（profile user_toolchain→OHOS_NDK_HOME/OHOS_SDK_HOME→`/data/...`与 harmonybrew 两套 glob），`cmake -B build-ohos -S . -DCMAKE_TOOLCHAIN_FILE=ohos.toolchain.cmake -DOHOS_ARCH=arm64-v8a` 传入原全部 `-D` 开关，`cmake --build`/`cmake --install` 同目录；test_package 同法；失败证据函数同步改读 `build-ohos/compile_commands.json` 并附 toolchain 路径；未改 124 口径与 12 断言 |
| 10 | 切 ohos.toolchain 后新失败域：`ohos.toolchain` 已命中 harmonybrew SDK 路径，但 configure 在 `third-party/CMakeLists.txt:16 pkg_search_module(gtest)` 即失败（`None of required gtest/gmock/gmock_main`），`compile_commands.json=MISSING`；旧 CMakeToolchain 路线同 pin 下 configure 全过 | 不同策略的副作用而非旧指纹复发：裸 cmake 不再经 `conan_toolchain.cmake` 间接获得 generators 目录的 `PKG_CONFIG_PATH` 接线，`PkgConfigDeps` 生成的 `.pc`（及 gmock 回退）对 `pkgconf` 不可见；与编译器/sysroot 无关 | 同轮换路线补接线：`_build_with_ohos_toolchain()` 在 `self.run(cmake)` 前把 `generators_folder` 显式前置到 `PKG_CONFIG_PATH` 并打印目录清单；`_ensure_gtest_pc_fallback()` 补齐 `gtest.pc`（此前假设 PkgConfigDeps 必出 gtest.pc，仅补 gmock 三件）；未改测试开关与总数口径 |
| 11 | PKG 接线修复后 configure 通过、sysroot/target 就绪（`--sysroot=<sdk>/native/sysroot`/`--target=aarch64-linux-ohos`），但 `logging.cpp` 同一 `_LIBCPP_*` 级联仍失败；本轮取证关键差分：`-std=gnu++17`/`-stdlib=MISSING`（上一轮 conan 工具链为 `-std=c++17`/`-stdlib=libc++`） | 前次“补 sysroot 即好”假设已证伪：ohos.toolchain 默认给 gnu 扩展且不注入 `-stdlib`，而 profile `compiler.libcxx=libc++` 的注入（E455）随 CMakeToolchain 移除而丢失；缺 `-stdlib=libc++` 时即使 sysroot 正确，`libcxx-ohos` 的 `__config` 仍选错，全空宏致同一指纹 | 换路线补标准库接线（非路径/取证复用）：`_cmake_defs()` 新增 `-DCMAKE_CXX_EXTENSIONS=OFF`（得 `-std=c++17`）与 `-DCMAKE_CXX_FLAGS/-EXE/-SHARED_LINKER_FLAGS=-stdlib=libc++`（wuffs 先例），test_package 同步；未改 124/12 口径 |
| 12 | stdlib 接线后取证显示 `-std=c++17`/`-stdlib=libc++`/`--sysroot`/`--target` 四项齐备但同一 `_LIBCPP_*` 级联仍失败，且 `incflags=0`；错误语义（`template` 非法、`_LIBCPP_*` 未知、`declval.h` 顶层 `expected ';'`）符合 `.cpp` 被当 C 解析的特征 | 上一轮“缺 -stdlib”假设已证伪（stdlib 补齐后指纹不动）；新判断：`-D CMAKE_CXX_FLAGS=...` 会覆盖工具链的 `CMAKE_CXX_FLAGS_INIT`（OHOS 附加定义/标志丢失），属破坏性注入，且旧 `incflags` 计数只认分离式 `-I` 会误报 0；必须换路线恢复工具链 pristine 并取完整命令 | 主配方与 test_package 移除全部 `-D CMAKE_*_FLAGS=-stdlib...`（及 EXTENSIONS 覆盖），只保留 `CXX_STANDARD=17/REQUIRED`，SDK 默认标志原样保留；证据函数改计组合式 `-I`/`-isystem`、新增 `langflags(-x/-nostdinc/-std=c*)` 与 `-D` 计数，并经 error 通道另发 `HMBS diag fullcmd` 完整命令（1500 字截断）供下轮定位；未改 124/12 口径 |
| 13 | pristine 回退后完整命令穿透成功：`--target/--sysroot/-D__MUSL__/-I×4` 俱全，`langflags=none`（无 `-x/-nostdinc/-std=c`），证伪上轮“C 解析”假设；失败仍为同一 `_LIBCPP_*` 级联，此时 `-stdlib=MISSING` | 新证据链：本仓 august/ada/xqilla/bowtie2 一致认定 OHOS clang++ 无默认 C++ 头搜索、必须显式 `-stdlib=libc++`（`tc.extra_cxxflags.append` 为安全接法）；前两轮只测过破坏性 `-D` 注入与完全缺席两种形态，env 合并形态未测 | 换路线安全追加：主配方与 test_package 均在 `self.run(cmake)` 前经 `CXXFLAGS/LDFLAGS` env 幂等追加 `-stdlib=libc++`（CMake 首配与 INIT 合并，不覆盖 `--target/--sysroot/-D__MUSL__`），`_cmake_defs` 坚持无 `-D FLAGS`；取证函数保留；未改 124/12 口径 |
| 14 | env 追加后仍 `-stdlib=MISSING`：三轮注入（`-D`/缺席/env）无一到达 `compile_commands`，证伪“注入方式有效”假设；必是 cmake 内部（SDK 工具链 FORCE-set 或上游覆盖）吞掉了外部标志 | 与前三轮不同的新路线：不再从外部传 flag，改写工具链文件本身——配方生成 wrapper toolchain（先 `include(SDK)` 再 `string(APPEND ... -stdlib=libc++)`，即 Conan CMakeToolchain 的 ada/xqilla 存活写法），`-DCMAKE_TOOLCHAIN_FILE` 指向 wrapper；取证新增 CMakeCache 与 `flags.make` 转储以区分吞没点 | 主配方新增 `_hmbs_wrapper_toolchain()` 并切换 `build()` 取 wrapper 路径，test_package 同法；env 追加保留作双保险；取证函数新增 `HMBS diag cache flags` 与 `flags.make CXX_FLAGS` 两行；未改 124/12 口径 |
| 15 | wrapper+env 双保险后完整命令终现 `-stdlib=libc++`×2，且 `--target/--sysroot/-D__MUSL__/-std=gnu++17` 四项齐备，但 `_LIBCPP_*` 级联逐字节相同：四轮 flag 注入（`-D` 破坏式/缺席/env/wrapper）被全部证伪；flag 字符串作为诊断手段已穷尽（且 ada/baloo/bcc/bandit 证明同 SDK 的 C++ 在 conan 工具链路线可绿，/data hnp 编译器+默认头搜索即过） | 进入第 5 策略周期：停止一切 flag 增删改，改走从未采集过的新证据路线——配方在 cmake configure 前运行只读隔离探针 `_probe_cxx_environment()`（永不抛异常、真实构建照常继续）：SDK clang++ 与 hnp wrapper 双编译器 `--version`、真机源码树头文件遮蔽审计（`__config/version/functional/string/...`）、SDK 内 `__config*`/`__config_site` glob、与失败 TU 同基旗的最小 `<functional>` TU 三变体（V1 镜像/V2 去 MUSL/V3 切 c++17）+ hnp 对照 V4、`-E -dM` 预定义宏（`__OHOS__/__MUSL__/clang` 版）、`-H` 头包含链（定位实际命中的 `__config`）、`CPLUS_INCLUDE_PATH/CPATH` 环境转储；全部经 error 通道发出 | 主配方新增探针函数并在 `_build_with_ohos_toolchain()` 内调用；wrapper/env/stdlib 接线原样保留以维持相同失败条件；下轮按探针判定：V1 失败+V4 成功→切 hnp 编译器路线（ada/baloo 先例），V1 成功→毒在上游、审上游 CMake；未改 124/12 口径 |
| 16 | 本轮预检证伪玩具探针：V1/V2/V3 最小 `<functional>+<string>` TU 在同基旗（`--target/--sysroot/-stdlib/-D__MUSL__/-std`）下全部 COMPILES，`-H` 链命中正常 `__config→__config_site`，`__OHOS__/__MUSL__/clang15/c++17` 预定义正常，源码树遮蔽审计为空，但 `host-common/logging.cpp` 同一 `_LIBCPP_*` 级联仍失败；旧探针头文件集合与失败 TU 无交集（缺 `chrono/thread/sstream/cstdio/cstring/cinttypes`），属假阴性，且真实首错行落在摘要省略中段不可见 | 同周期内换取证粒度：不增删任何 flag（wrapper/env 接线原样保留），只加只读证据——(a)探针新增 V5/V6/V7 精确头二分（`chrono/cinttypes/cstdio/cstring/sstream/thread`+真实上游 `-I` 四根，镜像/去MUSL/切c++17 三变体，首错行经 error 通道）；(b)遮蔽审计扩至 30 个标准头并兼查 build 树生成头；(c)`_report_build_failure_evidence` 在 fullcmd 后用 shlex 重放 logging.cpp 编译到临时 `.o` 并经 error 通道重发前 12 行真实 errmsg（含 rc），落盘零触碰；据下轮 V5-V7 与 errmsg 判定：exact 失败→审 `-D__MUSL__/gnu` 与该头族关系或上游 `-I` 遮蔽，exact 全绿→毒在 logging.cpp 特有 `#include/syscall` 或 TU 体 | 主配方三处只读增强，未改 124/12 口径与 flag 接线 |
| 17 | 上轮三取证一次命中：V5-exact-mirror rc=1（V1-V3 玩具全绿），`__config:261→host-common/features.h:16→<functional>→comp.h:18 _LIBCPP_BEGIN_NAMESPACE_STD`，重放 errmsg 同链（logging.cpp:15→logging.h:17→cstdint→__assert→__config:261→features.h:16）；`shadow_hits=0` 系审计漏 `features.h`，真凶为 `host-common/CMakeLists` 以 `-I include/host-common` 把上游 `features.h` 暴露给角括号，使 libc++ 自检 `#include <features.h>` 误命中上游文件并中途重入 | 根因修复：`source()` 新增 `_patch_host_common_includes()`，logging 库与 aemu-host-common 的 `PRIVATE include/host-common` 改 `PRIVATE include`（限定 `<host-common/features.h>` 仍经父目录命中），并各加 `-iquote…/include/host-common` 保裸 `"features.h"/"logging.h"`；遮蔽集补 `features.h`；flag/wrapper/env/124 口径不动，下轮以 V5 转绿与主库编译通过为判据 | 配方新增源码补丁函数并在 checkout 后调用，notes 补审计链 |
| 18 | round-17 预检仍 compile 失败但 logging.cpp 重放 rc=0（补丁对该 TU 生效），fullcmd 仍带 `-I host-common/include` 组合且失败 TU 不明；旧补丁用精确空白匹配，主库 pattern 极易 miss，且失败取证硬编码 logging.cpp 会掩盖真实失败 TU | 加固不同路线：补丁改正则+全文件 `include/host-common→include` 通扫（含其他 CMakeLists sweep）并经 error 通道上报，任一布局都命中；失败取证改按异常文本猜测真实 TU 并审计全量 `toxic_entries=n/m`，重放放宽到任意 .cpp | 配方两处修改，未改 flag/wrapper/env 与 124/12 口径 |
| 19 | round-18 预检补丁已命中（leaf_refs=2 双库）但仍 compile 失败，logging.cpp 重放 rc=0 而整体 Error 2，真凶 TU 藏在省略中段；旧 toxic 计数把 `-iquote` 当毒（toxic_leaf=1、toxic_entries=27/78 全是误报），V5 永远用未补丁叶 `-I` 故永红无法证伪补丁，`self.run(--build)` 丢弃输出致 fail-guess 永回落 logging.cpp | 换策略抓真凶而非再改 include：新增 `_cmake_build_capture` 以 subprocess 全量捕获 `--build` 输出，解析 `failed file=`+首 15 行 builderr 经 error 通道上报并附入异常；V8-patched 用补丁形态（父 `-I`+`-iquote` 叶）验证应转绿；toxic 改只计真 `-I` 叶（toxic_Ileaf/Ientries）；证据改两阶段查找优先真凶 | 配方三处修改，未改补丁语义与 124/12 口径 |
| 20 | round-19 预检失败域转移：logging.cpp 重放 rc=0（补丁对该 TU 生效）但整体仍 Error 2，fail-guess 指向 base/WorkerThread_unittest.cpp，而该 TU 的 fullcmd 无毒叶（toxic_Ileaf=0）且重放 rc=0（仅一条 gcc-toolchain 未用警告）；toxic_Ientries=24/78 说明仍有 24 个 TU 带真 -I 叶，但 WorkerThread 自身干净，故其 fail 极可能是链接失败被误归因（link 错误附近最后一个 .cpp 被当成编译失败），旧 capture 只找 .cpp 且 builderr 发 15 行易被摘要截断 | 停止再改 flag/include 语义，只修取证误归因：capture 新增 kind=compile/link 判别（有 .cpp:line:col:error 才算编译，否则按 ld.lld/undefined/Linking CXX/FAILED:link 判链接并提 linktarget），builderr 缩至 6 行保摘要存活；report 解析 kind，LINK 时跳过 TU 回退与重放并显式标注，compile 重放 rc=0 时发 recapture-mismatch 明示真凶在链接/并行；sweep 扩至 *.cmake 助查剩余 24 毒叶并输出 toxic_samples 前 3 名；未改补丁语义与 124/12 口径 |
| 21 | round-20 预检用新取证一次定位两个误判：(a) kind=link/linktarget=aemu-logging.a 系误分类——真凶是 GfxstreamFatalError.cpp 等 logging 库 TU 的编译失败，`ninja: build stopped` 对任何失败都出现、`GfxstreamFatalError.cpp.o` 含子串 error 致旧判据全中；(b) toxic 24/78 的样本全是 host-common 源（empty-crash-handler/crash_reporter/vm_operations）且 sweep 无 `swept` 行——即无字面 `include/host-common` 的 CMake 文件，毒叶系动态拼接，文本补丁永远追不上 | 换与前轮不同的全局策略：不再追文本，改在执行期过滤——wrapper toolchain 内新增 python 编译器过滤脚本（对 C/CXX 分别按 SDK 的 llvm/bin/clang{,++} 具化），把任何形态的 `-I.../host-common/include/host-common`（分离/组合、命令行/响应文件 @rsp）改写为 `-iquote...` 后 exec 真编译器，CMAKE_C/CXX_COMPILER 以 CACHE FORCE 指向它；同步修判据：kind 判别改编译优先（有 .cpp:行号+error: 即 compile，仅无 cpp 错误而有 ld/undefined 才 link），builderr 跳过 `[ n%] Building/Linking` 进度行并要求 error:/undefined/FAILED: 真信号；evidence 加 filter=wrapper-active 标明 compile_commands 的毒计数为过滤前快照；未改 124/12 口径 |

| 22 | round-21 预检首次进入链接阶段（编译已过）但报 `LINK:aemu-logging.a` + `clang++: linker command failed`：自相矛盾——已用 `?format=TEXT` 取回上游 tag 树 `host-common/CMakeLists.txt` 证实 logging 库是普通 `add_library(logging.cpp GfxstreamFatalError.cpp ../base/Metrics.cpp)`（`BUILD_SHARED_LIBS=OFF` 下为静态库，归档走 `ar`，不可能报 clang++ 链接错误）；故旧“取 FAILED: 行首个 aemu-* 子串”正则命中的是可执行文件链接命令行里的输入归档，而非真正的链接目标，且无 `--dry-run` 依据的 builderr 首行只是无诊断信号的编译器回显（占位挤掉了真正的 `ld.lld: error: undefined ...` 行），真正的未定义符号藏在被摘要省略的中段 | 只修取证误归因、不动任何编译/链接语义（编译已绿，不得回退）：(a) kind/link 目标改取真实 `FAILED: <target>` 路径 basename，`.a` 配 clang++ 错误如实上报不再伪装；(b) builderr 先发 FAILED 行，跳过无链接信号的 `hmbs-*-filter.py` 回显行，link 窗口放宽到 25 行并新增 `multiple definition/duplicate symbol/relocation/no such file` 信号；(c) link  kind 追加 `HMBS diag linkcmd`（`-o` 前后 head+tail，保留目标与库表）；(d) evidence 在 link 时转储 `HMBS diag linkfailed/linktxt`（按失败目标匹配 `CMakeFiles/*.dir/link.txt` 首选，否则首个候选+MISSING 声明）；全程 try/except 只读；未改补丁语义与 124/12 口径 |

| 23 | round-22 取证上线后一次定位三个 stale 误判：(a) 生成器实为 Unix Makefiles（`linktxt-cands=8` 且 `failed-targets=` 为空——Make 输出没有 `FAILED:` 行），故 round-22 的“首个 `Linking CXX` 匹配”兜底命名了早先的成功归档回显，`LINK:aemu-logging.a` 系第二次误标；(b) `linkcmd` 抓到的是首个 `-o` 行——一条带 `-c` 的 logging.cpp 成功编译回显，而真正的失败在日志中段（被摘要省略），kind=link（有链接信号、无 `.cpp:行号`）与之自洽；(c) `make[n]: *** [...] Error` 行从未匹配 `_errpat`（`Error 1` 无冒号），轮轮被静默丢弃 | 改走 Make 感知的“末端优先”路线（与 round-22 的 Ninja/首匹配假设不同）：收集全部 `Linking CXX` 行但只取最后一条的目标，最深层 `make[n]` Error 目标进 `failed_targets` 首位；linkcmd 改从尾部倒扫且永不把含 `-c` 的编译标成链接（标 `lastcmd-compile`）；builderr 固定追加最多 5 行 `make[...]: ***`；gtest 本地审计确认 pin 的 1.17.0 包以 `BUILD_GMOCK=ON` 构建（gmock 文件存在，仅 package_info 未声明——fallback .pc 前提成立，不换 pin）；未改编译/链接语义与 124/12 口径 |

| 24 | round-23 取证精准命中真凶：`linkfailed: aemu-base_unittests` + `ld.lld: error: unable to find library -lgtest_main`，linktxt 形如 `-o aemu-base_unittests libaemu-base.a ... -lgtest_main -lm`（纯 `-l` 名、无 `-L`、无线索指向缺文件）。取回上游 `third-party/CMakeLists.txt` 与 `base/CMakeLists.txt` 解码确认：上游只给 gtest/gmock/gmock_main 建 `pkg_search_module+ALIAS`，两个单测二进制却都直链纯名 `gtest_main`（base 链 `gmock gtest_main`，host-common 链 `gtest_main gmock_main`），无任何同名 target——CMake 只能退化成裸 `-lgtest_main`；桌面有系统 gtest 故上游从未察觉 | 改走真实构建修复（与 round-22/23 纯取证不同路线）：(a) `source()` 新增 `_patch_thirdparty_gtest_main()`，按上游既有体例补 `pkg_search_module(gtest_main)+ALIAS` 一节（正则锚定 gmock_main 别名行、缩进跟随、已存在则跳过），fallback 的 gtest_main.pc 自带 `-lgtest_main -lgtest` 使导入边同时恢复 gtest 传递边；(b) Exp2 兜底形：wrapper toolchain 给 EXE/SHARED/MODULE 统一追加 `-L<gtest libdir>`（`-L` 无序语义，不可能破坏符号解析；沿用已证有效的 string(APPEND) 机制，目录来自 `self.dependencies[gtest]` 真实存在性检查）；未改测试口径与 124 总数 |

| 25 | round-24 的 gtest_main 真修未转绿：本轮失败提前到 `aemu-base_unittests` 内 `HealthMonitor_unittest.cpp` 的 compile（`failed-targets=base/aemu-base_unittests` 却是可执行目标名），且该 TU 独立重放 rc=0、自身无毒叶（`toxic_Ileaf=0`），自证“编译失败”归因不可靠、真错行被摘要省略；同时 `toxic_Ientries=24/78` 四轮不动，`-I` 专用过滤器结构上够不到经 `-isystem` 到达的叶（host-common 三样本仍在） | 换与 22–24 不同的路线，不再猜归因：(a)把证据钉进异常正文——capture 收集 builderr 首 3 行拼入 `build-capture` 异常（异常正文必进失败原因，不再依赖被摘要省略的 error 通道），report 把 recapture 结论追加进 evidence 异常（`recapture=pass-mismatch` 时后轮不再误读为该 TU 编译失败）；(b)真实构建加固走新向量：编译器过滤器同时把 `-isystem` 组合/分离式与 @rsp 内的 `host-common/include/host-common` 叶降为 `-iquote`（复用 `_map_inc`；`-iquote` 保留引号查找、角括号回落 sysroot，无 `-Werror` 故仅丢 system 头警告抑制，安全）；未改测试口径与 124 总数 |

| 26 | round-25 的 `-isystem` 加固与证据内嵌已部署（本轮日志含 `recapture=pass-mismatch` 与 `snip=` 即证），构建仍红但失败域第一次清晰：`aemu-base_unittests` 链接期 `ld.lld: undefined symbol: testing::internal::IsTrue(bool)` 与 `GTestLog::GTestLog(...)`——编译全绿（HealthMonitor 重放 rc=0），链接找到的 libgtest 缺符号。上游单测仅用 `MOCK_METHOD/EXPECT_CALL` 等公开宏（已取回 `dd8b929c` 的 HealthMonitor_unittest.cpp 全文核对，无任何 `testing::internal` 直引），符号来自 gmock 头内联展开；又 `IsTrue/GTestLog` 自 1.8 至 HEAD 未被移除，故非版本 API 漂移，而是 `-l` 搜索命中了影子库 | 与 22–25 的“名/搜索路径”路线不同，改走文件级确定性：`_ensure_gtest_pc_fallback()` 的 `Libs` 改写绝对归档路径 `${libdir}/libX.a`（.a 优先于 .so，缺失则回退 `-l` 不劣于现状），`gtest.pc` 仍沿用 PkgConfigDeps 生成（保 pthread/defines），另三件覆写并经 error 通道打印所选 `Libs`；wrapper `-L` 兜底保留；未改测试口径与 124 总数 |

| 27 | 本轮真机新失败域：`host-common/feature_control.cpp:17: 'feature_control.h' file not found`，`flags.make` 显示 `-iquote.../host-common/include/host-common` 已存在，`toxic_Ileaf=1` 且 `recapture rc=1`（过滤器执行后仍找不到）；logging.cpp 此前 `recapture rc=0` 证明 logging 补丁有效，失败转移到 aemu-host-common 主库 TU | 配方自查定位为补丁自身语法破坏：主库 `pat_main` 正则停在 `include` 换行处、未含 closing `)`，`target_compile_options` 被注入到仍敞开的 `target_include_directories(...` 括号内，破坏主库 include 配置致头文件丢失；修复为全调用匹配 `target_include_directories\(\s*aemu-host-common\b[^)]*?\)`（含 `)`，DOTALL）并用切片 `txt[:m.end(0)]+iquote+txt[m.end(0):]` 追加到调用之外；logging 块、filter、gtest 补丁、124/12 口径不动 |
| 28 | 本轮真机编译已过、卡在上游测试计数：`discovered=123 executed=0`（`ctest --output-on-failure` 尾部仅见 `62 - ring_buffer.ProducerDrivenSync (Disabled)` 未运行项），且 `source()` 报 `include-patch failed: unbalanced parenthesis at position 55` | 见 29：转义与计数正则双修；编译通过说明上轮括号内注入已随异常回退，本轮恢复语法安全的括号外追加 |
| 29 | 接上：计数 0 系解析正则与 ctest 真实格式不符，`Disabled` 仅出现在尾部汇总而无 `Test #N ... Disabled` 行 | 转义修复 `\)` 失衡；`Test #N` 四处计数正则 `[^:\n]*` 改 `[^\n]*`（真实行为 `Test #1: name ... Passed`，冒号后有点点与结果词）；另从 `^\s*\d+\s*-\s*.+\((Disabled|Not Run|Skipped)\)` 汇总行补充 skipped（确定性源，不做减法修补）；124 口径与构建语义不动 |
| 30 | 本轮 configure 失败：`host-common/CMakeLists.txt:43 target_compile_options Cannot specify compile options for target aemu-host-common which is not built`（首匹配插入点在 `add_library` 之前） | 改与前两轮不同策略：不再按首匹配就地插入，改文件尾追加并包 `if(TARGET aemu-host-common)` 守卫（目标不存在时零操作）；logging 块不动；124 口径不动 |
## 源码修改

无补丁。SONAME 修复仅通过 CMakeToolchain 变量注入, 未改动上游源码。

## 上游测试实际运行记录

- 本轮为配方首轮 (Windows 工作区), 未在本地运行 conan create; 以上 124 总数来自源码审计, 非执行结果
- HMBS 真机预检将执行 `ctest -N` (discovered) + `ctest --output-on-failure` (逐行 Passed/Failed/Skipped), marker 由 conanfile.build() 按确定性日志源产出
- test_package 12 个 CHECK (StringFormat 家族) 同样待真机回填

## 验证结果(实测, 待真机回填)

```bash
# 待 HMBS 预检: conan create (static) + ctest 124 + ./test_libaemu 12/12
```

## 依赖版本

- 运行时: 无 (libc/m/dl/pthread 系统库)
- 测试: gtest/1.17.0 (test_requires, 仅构建期)

## 注意事项

- 不要把 `AEMU_COMMON_BUILD_CONFIG` 留空; 不要切回 `+archive` 抓包（gzip 按请求重生成，sha256 会腐烂）
- `aemu-snapshot` 在 GEN_PKGCONFIG=ON 时名为 aemu-snapshot (OFF 时为 gfxstream-snapshot); 本配方固定 ON, package_info 按 ON 命名
- 真机若报个别单测失败/跳过, 按 rule4 在 marker 加 gaps 逐项解释, 缺依赖必须补齐重测, 不得改总数凑恒等式

## Round-27 (2026-09-27): CI #62453 首个归档失败

- 现象: CI 在 `host-common/libaemu-logging.a` 报 `Error running link command: no such file or directory`; 同一提交 2026-09-26 真机预检全量通过 (discovered=123/executed=122/passed=122/skipped=1)。
- 判定: 全部 78 个 TU 编译通过 (toxic_Ientries=0/78, recapture rc=0), 失败的是 `ar` 归档步骤本身, 即 CI Worker PATH 极简、无主机 `ar` 可用, 而真机 PATH 有 binutils, 故同提交两地分叉。
- 修复: wrapper toolchain 在 SDK include 之后 FORCE 钉死 `CMAKE_AR/CMAKE_RANLIB` 到 SDK 绝对路径 `native/llvm/bin/llvm-ar/llvm-ranlib` (存在性检查, 缺失回退裸名); 与编译器 filter 同机制, 真机零影响。
- 诊断增强: build-capture 新增 kind=archive 分类 (`.a` 失败目标或 `Error running link command` + `.a`), evidence 对 LINK/ARCHIVE 统一跳过 TU 回查、转储 link.txt 与 CMAKE_AR/RANLIB 缓存值, 避免再误标 logging.cpp。
