# rnp 0.18.1 适配笔记

## 编译环境

- 构建系统: cmake（最低 3.18，上游要求；OHOS 预检使用真机 cmake）
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15（HarmonyOS aarch64 真机，/data/service/hnp/bin）
- 状态: built（待真机 rule4 预检回填实测数据后更新）

## 上游信息

- 上游仓库: https://github.com/rnpgp/rnp
- 上游版本: v0.18.1（2025-11-21 发布，修复 PKESK 全零会话密钥安全漏洞）
- 源码包: https://github.com/rnpgp/rnp/releases/download/v0.18.1/rnp-v0.18.1.tar.gz
- sha256: 423c8e32e1e591462f759adf8441b1c44bca96d9f5daff13b82e81a79f18ecfd（来源：FreshPorts 记录与 openSUSE Factory 同版本校验一致）
- 许可证: BSD-2-Clause（另含 MIT/BSD-3-Clause 组件）
- 适配路径: 路径 A（基础适配）

## 编译步骤

1. 选择 Botan3 后端（`CRYPTO_BACKEND=botan3`），复用仓库已有 `botan3/3.12.0`（名与 CCI `botan` 不冲突，直落 ohpcd）、`bzip2/1.0.8#3b49a968…`（ohpcd Makefile RREV）、`zlib/1.3.1.1`（仓内独有 OHOS 重建版，同 1.3.1 源码，直落 ohpcd），json-c 改为 vendored 静态（同 S3 0.18 归档，`SYSTEM_NAME=Linux`），测试期另用 `gtest/1.17.0.1` 提供 GTest，避免上游 `DOWNLOAD_GTEST=On` 在 CI/真机上直连 GitHub。
2. 关闭文档与附加项：`ENABLE_DOC=OFF`（免 adoc 依赖）、`ENABLE_COVERAGE=OFF`、`ENABLE_SANITIZERS=OFF`、`ENABLE_FUZZERS=OFF`，`SYSTEM_LIBSEXPP=OFF` 使用源码树内嵌 sexpp。
3. 标准 CMake 流程：`build()` 先 `_build_vendored_jsonc()`（S3 0.18 归档 → `jsonc-prefix` 静态 `-fPIC`，`SYSTEM_NAME=Linux`，经校验的 CC/CXX 与 HMBS cmake），经 `CMAKE_PREFIX_PATH`/`PKG_CONFIG_PATH` 暴露给 rnp 的 `FindJSON-C`，再 `cmake.configure()` → `cmake.build()` → `ctest --output-on-failure`（`build()` 内 `_run_upstream_tests` 运行并按 `ctest -N` 与 `LastTest.log` 计数 emit `HMBS_UPSTREAM_TEST_RESULT`）；`generate()` 另加 `PkgConfigDeps` 供 `FindBotan`（botan-3.pc）与 `FindJSON-C` 探测。
4. 打包：`cmake.install()` 安装 `librnp`（含 `rnp`/`rnpkeys` 可执行文件）与头文件、`rnp-config.cmake`、`librnp.pc`。

## 上游测试审计

- 上游构建文件 `src/tests/CMakeLists.txt` 注册：`setupTestData`（fixture 数据拷贝）+ `rnp_tests`（GTest，`RNP_TEST_SOURCES` 共 50 个 `.cpp`，含 issues/fuzz 回归文件）+ `cli_tests-*`（`cli_tests.py -ls` 动态枚举的 python unittest 套件，需 Python3 与 GnuPG）。
- `test_package/MANIFEST.yml` 声明 `upstream_test_total: 282`，口径 `ctest_entries`（2026-09-24 真机 `ctest -N`=282：setupTestData 1 + rnp_tests 经 gtest_discover 展开约 271 + cli_tests 10；`RNP_TEST_SOURCES` 逾 50 源文件仅为源码级下限）。
- `build()` 中运行完整 `ctest`，计数只读 `ctest -N` 与 `LastTest.log`，不做字符串数数与算术修补。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出上游 main 失败：`invalid path 'archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??'` | 上游存在含 `?` 的文件名，Windows 文件系统非法 | 本地使用 sparse-checkout 排除 `archives/g/gama/` 后同步，不影响 rnp 配方；真机为 Linux 不受影响 |
| 2 | 上游默认 `DOWNLOAD_GTEST=On` 会 FetchContent 拉取 googletest | CI/真机网络受限且不可复现 | `DOWNLOAD_GTEST=OFF` + `test_requires gtest/1.17.0.1`，走 CMakeDeps 提供的 GTest |
| 3 | `archives/l/libXext` 与 `libxext` 大小写目录在 Windows 下冲突 | 上游 Linux 大小写敏感，Windows `ignorecase` 合并 | 本地不碰该目录，保持未提交；以真机/Linux 为准 |
| 4 | 真机 `bzip2/1.0.8` 构建失败：`System is unknown to cmake` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` broken（`cmake.configure(build_script_folder=...pardir)`，`build()` 第 62 行） | 依赖图命中 conancenter CCI CMake 配方，而非仓内 Makefile 配方（仓内 `archives/b/bzip2/1.0.8` 无 `generate()`/CMake 步骤——铁证）；CCI 配方在 `CMAKE_SYSTEM_NAME=HarmonyOS` 下配置失败 | `self.requires("bzip2/1.0.8#3b49a968338a1932917a5049fce54a4e")` pin 到 cataract/fceux 已验证的 ohpcd OHOS revision（Makefile 配方，不走 CMake）；rnp 本体不链接方式不变，仅做图手术 |
| 5 | 真机 `cmake/4.4.3` 源码构建失败：`Error in build() method, line 35`，`KeyError: 'OHOS'`（`conan_data["sources"][version][os][arch]` 无 OHOS 条目） | `build_requirements()` 的 `tool_requires("gtest/1.17.0")` 解析到 CCI 修订版，其 `tool_requires cmake` 把 CCI `cmake/4.4.3` 拉入闭包从源码构建；且 `tool_requires` 把 GTest 置于 build context，CMakeDeps 渲染不完整（openrct2 实证 `gtest.h not found`） | 改用仓内统一版本路线（与上轮 RREV pin 不同策略）：`self.test_requires("gtest/1.17.0.1")`——独有版本自动落 ohpcd（同上游 v1.17.0 源码 + OHOS tmpdir 补丁），零依赖不拉 CCI cmake；`test_requires` 使 GTest 留在 host context，CMakeDeps 生成完整 `GTest::` 目标 |
| 6 | 真机 `json-c/0.18` 构建失败：`System is unknown to cmake` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` broken（`conan_toolchain.cmake`，`build()` 第 61 行 `cmake.configure()`） | 依赖图命中 conancenter CCI CMake 配方，而非仓内 `archives/j/json-c/0.18`（后者强制 `CMAKE_SYSTEM_NAME=Linux`，不会报 `Platform/HarmonyOS`——铁证）；上一周期 RREV-pin 路线对 json-c 无效：仓内无已验证 json-c RREV 前例（全库扫描 0 条），且 libdatovka/0.7.3 已审计 `json-c/0.16-0.18` 在双远端同版本、无独有版本可强制 ohpcd，逐个 pin 是打地鼠 | 改用与上一周期不同的独有路线：json-c 去 conan 依赖、改为 vendored 静态（同 S3 0.18 归档/sha256，`SYSTEM_NAME=Linux` + `-fPIC` + 经校验 CC/CXX + SDK lld 守卫，libdatovka `_build_vendored_jsonc` 前例），经 `CMAKE_PREFIX_PATH`/`PKG_CONFIG_PATH` 供给 `FindJSON-C`；同步把 `zlib/1.3.1` 换为仓内独有 `zlib/1.3.1.1`（同源码，直落 ohpcd，fceux/sail 前例），`botan3` 保持直引（名与 CCI `botan` 不冲突）；另加 `PkgConfigDeps` 修复 `FindBotan` 探测 |

| 7 | 真机 `rnp/0.18.1` 本体构建失败：`System is unknown to cmake` + `Platform/HarmonyOS`，`CMakeLists.txt:47 project()` 处 `CMAKE_C/CXX_COMPILER: /data/service/hnp/bin/clang` 报错（`build()` 第 127 行 `cmake.configure()`） | 默认 OHOS profile 经 CMakeToolchain 发射 `CMAKE_SYSTEM_NAME=HarmonyOS`，真机 cmake 4.4.3 无该平台文件而中断；与上轮 json-c 依赖失败同指纹但不同域：上轮 vendored json-c 已成功（日志 `Configuring done (33.2s)` 后才进 rnp 本体），证 vendoring 路线对依赖域有效，不可再对 rnp 本体套用 vendoring | 与上轮不同的独有路线：主配方 `generate()` 照 hardened `json-c/0.18` 前例加 `if os in (Linux, OHOS): tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"`（仅改系统名 token，仍用 OHOS clang 编译；vendored json-c 同法已在同机成功），不改测试口径与依赖图 |

| 8 | 真机 `rnp/0.18.1` 本体仍失败（第 3 次同指纹）：`-- The C/CXX compiler identification is unknown`，`CMakeLists.txt:47 project()` 处 `CMAKE_C/CXX_COMPILER: /data/service/hnp/bin/clang` 报错（`build()` 第 134 行） | 上轮仅强制 `CMAKE_SYSTEM_NAME=Linux` 消除了 `Platform/HarmonyOS` 平台报错，但 Conan OHOS 工具链的 sysroot/linker 标志与 Linux 名混合后 try_compile 链接可执行文件失败，致编译器识别 unknown；vendored json-c 因直调 cmake（不走工具链文件）不受影响，故本体不能原样重复 SYSTEM_NAME 单补丁 | 与上轮不同的独有路线：照 `adamstark-audiofile/1.1.4`（C++ CMake）前例加 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（try_compile 只编静态库不链接）+ `CMAKE_SYSTEM_PROCESSOR=aarch64`（OHOS 工具链该值为空，abpoa 前例），全局（含 Linux/OHOS）先生效；仍用 OHOS clang，不改测试口径与依赖图 |

| 9 | 真机 `rnp/0.18.1` 本体第 4 次仍 `compiler identification is unknown`（C/CXX 双未知，`build()` 第 134 行后）：STATIC_LIBRARY 免链接后依然未知，证失败不在链接阶段 | 上轮假设“混合 sysroot 链接失败”是根因并加 STATIC_LIBRARY，但免链接后识别仍双未知，假设被证伪；vendored json-c（纯 C、直调 cmake、自带 SDK llvm/lib 的 LD 作用域）同机成功，而主包走 CMakeToolchain + profile 硬编码 `ohos-sdk_26.0.0.18` 的 LD，若真机 SDK 版本漂移则 clang 启动即 loader 失败，且 C++ 识别另需 libc++ 头/sysroot，主包无任何启动期证据 | 与上两轮不同的环境/证据路线（不改 SYSTEM_NAME/TRY_COMPILE 假设）：`build()` 先经 `_sdk_llvm_lib` 定位真机实际 SDK llvm/lib 并前置 `LD_LIBRARY_PATH`，再对 CC/CXX 跑 `--version` 留启动证据并快照 `conan_toolchain.cmake` 关键行，`cmake.configure()` 失败时转储 `CMakeError/Output.log` 尾部再抛；保留原 Linux/STATIC 缓存，仅补启动环境与诊断，不伪造 `*_WORKS`，不跳测试 |

| 10 | 真机 `rnp/0.18.1` 本体第 5 次仍双未知（`build()` 第 190 行），且诊断报 `no CMakeError/Output.log under .../b/build/Release` | 上轮 LD 作用域假设未被证实：同机 vendored json-c（同 clang、无工具链）成功而主包（同 clang、有工具链）双未知，LD 仅影响启动但探针输出被摘要省略无法定论；且日志转储搜错根（仅搜 `build_folder` 单层），`roots` 逻辑漏掉 `base_build_folder`/CMakeFiles 散落日志，工具链快照亦缺 scrub 前后对照 | 与上轮不同的工具链净化路线：`generate()` 后对 `conan_toolchain.cmake` 做 Linux-native scrub（注释含 ohos/harmonyos/linux-ohos/--sysroot/SYSROOT/FIND_ROOT 的行，保留 `SYSTEM_NAME=Linux` 本行，botan3 `--os=linux` 前例），并记录被注释行；重写 `_dump_cmake_logs` 多根（build/base_build/base_source/source）递归收 `CMakeError/Output.log` 及 CMakeFiles 下 `.log`，上报 roots/found；保留 LD 探针与原缓存，不伪造通过 |

| 11 | 真机第 6 次仍双未知且 `rnp scrub: no OHOS/sysroot lines`、`found=0`（`build()` 第 267 行）：scrub 无行可删仍失败，日志多根仍为 0 | 上轮净化假设被证伪：工具链文件本身已无 OHOS/sysroot 行，说明破坏识别的不是文件文本，而是 CMakeToolchain 在 OHOS 下的整体行为（ML-0035 同类）；且失败点恒为 `project()` 首行双未知，与文件内容无关；vendored json-c（无工具链裸 cmake）同机恒成功 | 与上轮不同的弃用路线（fceux/2.6.6、expat、zstd 前例）：主包与 test_package 均不再生成 CMakeToolchain，改用 SDK `ohos.toolchain.cmake`（conf user_toolchain/OHOS_NDK_HOME/双路径 glob 自发现）+ 裸 cmake（`HMBS_CMAKE`）；主包传 `OHOS_ARCH=arm64-v8a`、`CXX_STANDARD=20`（botan3 头需 C++20，上游默认 11）、`PREFIX_PATH=jsonc-prefix;generators`、`FIND_ROOT_MODE_PACKAGE=BOTH`，`package()` 改裸 `cmake --install`；另加 `cmake/version.cmake` 缺失离线 stub（上游首行 `file(DOWNLOAD)` 无网必挂）；test_package 同步同路线并按 bdir 寻二进制；保留确定性计数与诊断转储 |

| 12 | 真机第 7 次 `Invalid configuration: rnp: cannot find ohos.toolchain.cmake; searched: [...ohos-sdk.org...]`（`build()` 内 `_ohos_toolchain` 硬抛） | 上轮“改用 SDK 工具链”假设被证伪的不是方向而是路径：同机证据显示真机 SDK 已漂移（`CC=/storage/.../.harmonybrew/bin/clang`、`llvm/lib` 在 `Cellar/ohos-sdk/26.0.0.18_1/native/llvm/lib`），而 `_ohos_toolchain` 仅搜 `conf user_toolchain`（本轮为空）+ `OHOS_NDK_HOME`（空）+ 两条 `ohos-sdk.org` 旧 glob，必然搜空后硬抛，连 configure 都没进；与 fceux/zstd 前例同指纹但不同根（前例真机仍有 `/data/service/hnp/ohos-sdk.org`） | 与上轮硬抛不同的鲁棒降级路线：`_ohos_toolchain(cc_hint)` 新增多源自发现（`OHOS_SDK_HOME/ROOT/NATIVE/SDK_HOME`、clang realpath 向上 6 层、`_sdk_llvm_lib` 反推 native、`~/.harmonybrew/Cellar/ohos-sdk/*/native/...` 与 `ohos-sdk/*` 新 glob），找不到时返回空而非抛错；`build()` 有工具链走 `TOOLCHAIN_FILE+OHOS_ARCH`，无工具链走 Linux-native 降级（`SYSTEM_NAME=Linux` + `PROCESSOR=aarch64` + 显式 CC/CXX，同机 vendored json-c 已证可 configure）；test_package 同步新增两条新 glob；保留计数口径与日志转储，不跳测试 |

| 13 | 真机第 9 次 `Could NOT find BZip2 (missing: BZIP2_LIBRARIES BZIP2_INCLUDE_DIR)`（`src/lib/CMakeLists.txt:29 find_package`，`build()` 第 173 行 exit 1；此时 toolchain 已定位、configure 跑 35.6s） | 上两轮“工具链/format”假设均已证伪通过（toolchain 路径与 `{cmake}` 占位符问题解决，configure 真进且跑完依赖探测）；新根在裸 cmake 无 CMakeToolchain 时 `find_package(BZip2)` 走模块模式，而 `CMakeDeps` 只产小写 `bzip2-config.cmake`，`PREFIX_PATH=generators` 无法满足 `FindBZip2.cmake` 的全大写模块变量；bzip2 依赖本身是 Makefile 配方（`package_info libs=[bz2]`），头/库真实存在于 conan 包内 | 与上轮不同的依赖透传路线（osrm-backend/osmcoastline 前例）：新增 `_dep_prefix/_dep_lib_file/_dep_hints`，从 `self.dependencies` 真实包路径取 `include` 与 `libbz2.a/.so`，以 `-DBZIP2_INCLUDE_DIR/LIBRARIES/LIBRARY`（及 ZLIB 同理 `ZLIB_INCLUDE_DIR/LIBRARY/LIBRARIES`）显式注入 configure；缺失仅警告不硬抛；不改测试口径与工具链逻辑 |

## 依赖版本

- botan3/3.12.0（Botan 3 后端，需 C++20，上游要求 Botan >= 3.0.0；名与 CCI `botan` 不冲突，直落 ohpcd）
- json-c/0.18 vendored 静态（上游要求 >= 0.11；同 S3 归档/sha256 `876ab046…`，`SYSTEM_NAME=Linux`，不走 conan 图）
- bzip2/1.0.8#3b49a968338a1932917a5049fce54a4e（ohpcd Makefile RREV）
- zlib/1.3.1.1（独有 OHOS 重建版，同 1.3.1 源码/sha，直落 ohpcd）
- gtest/1.17.0.1（仅测试期 `test_requires`；仓内统一测试版本，零依赖，不拉 CCI cmake）

## 验证结果

```bash
# 待 HMBS 真机预检回填：
# - conan create archives/r/rnp/0.18.1（ohos-aarch64 profile）
# - build() 内 ctest 输出与 HMBS_UPSTREAM_TEST_RESULT
# - test_package 内消费者测试与 HMBS_TEST_PACKAGE_RESULT
```

首轮本地仅完成工作树搭建，未做真机编译；以上实测数据待预检日志返回后如实回填，不估算、不照抄上游 README。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/r/rnp/0.18.1/conanfile.py | 主配方（CMake + Botan3 后端 + ctest 接入） |
| archives/r/rnp/0.18.1/conandata.yml | 官方源码 URL + sha256 |
| archives/r/rnp/0.18.1/manifest.yaml | 版本级 manifest |
| archives/r/rnp/0.18.1/test_package/ | 消费者测试（真实调用 librnp FFI）+ MANIFEST.yml |
| archives/r/rnp/commands.json | rnp/rnpkeys 命令行工具声明 |
| .hmbs/pr-body.md | PR 正文草稿（测试数待真机回填） |

## 注意事项

- rnp 会同时产出 `rnp` 与 `rnpkeys` 可执行文件，已按 R38 在软件级目录声明 `commands.json`。
- `manifest.yaml` 状态暂标 `built`；通过真机 rule4 与 CI 后再由 HMBS 改为 `published`。
- 本轮严禁 commit/push/建 PR；工作树保持未提交，等待 HMBS 后台真机验证。
- 第 8 轮补记：真机已定位到 `Cellar/ohos-sdk/.../ohos.toolchain.cmake`（多源发现生效），但 `build()` 拼出的 `RUN: ... "{cmake}" -B "{b}" ...` 原样残留占位符，`/bin/sh: {cmake}: inaccessible`（exit 127）。系 `ld + '...' + tc_defs + '...'.format(...)` 中 `.format` 只作用于最后一段，首段 `{cmake}/{b}/{s}` 未展开；已改为首段独立 `.format(cmake,bdir,source)`，`py_compile` 通过。

| 14 | 真机 compile 期 Signal 9（stdout/stderr 尾部均空，preflight 判 failed，阶段 compile，上游 0/0/0） | 日志无 TU/命令定位，只能判定为大库单编期峰值资源被杀：librnp + rnp_tests（50 个 GTest 源 + Botan3 C++20 重模板）在 Unix Makefiles 下每 TU 派生 shell、单作业吞吐慢，峰值内存/时长最先触顶；此前同机 botan3 已缓存、configure 曾跑 35.6s，依赖域已排除 | 与之前改优化/工具链文本不同的降压路线：主配方与 test_package 新增 _cmake_generator_arg（HMBS_NINJA/conf ninja/PATH 探测 + --version 存活校验），可用时 configure 加 -G Ninja（zstd/1.5.7.1 与 eigenpy OHOS 前例），所有 cmake --build 保持 -j1；不改优化等级、不改测试口径与依赖图 |

| 15 | 真机 `Could NOT find JSON-C (missing: JSON-C_LIBRARY JSON-C_INCLUDE_DIR JSON-C_VERSION)`（`src/lib/CMakeLists.txt:33 find_package`，configure 已跑完 BZip2/ZLIB 探测） | BZip2/ZLIB 显式 hints 已生效（日志 `BZ2_bzCompressInit - found`、`Found ZLIB ... libz.a`），证依赖透传路线对 conan 包有效；唯独 JSON-C 仍走 `FindJSON-C.cmake` 的 pkg-config+find 路径：vendored 前缀仅经 `CMAKE_PREFIX_PATH`/`PKG_CONFIG_PATH` 暴露，而 `ohos.toolchain.cmake` 的 `FIND_ROOT_PATH_MODE_INCLUDE/LIBRARY=ONLY` 把前缀挡在 sysroot 外（BZip2/ZLIB 因显式 `-D*_INCLUDE_DIR/_LIBRARY` 绕过 find 而不受影响），pkg-config 缺失或环境被 `conanbuild` 覆盖时无回退 | 与上轮 conan 包 hints 不同的 vendored 显式路线：`_dep_hints(jsonc_prefix)` 从 `jsonc-prefix` 真实产物取 `include/json-c/json_c_version.h` 与 `lib/libjson-c.a/.so`，以 `-DJSON-C_INCLUDE_DIR/LIBRARY` 显式注入（模块据此头文件解析出 0.18 版本满足 >=0.11），另加 `-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH`（保留 PACKAGE=BOTH），不改测试口径与工具链逻辑 |

| 16 | Zhenji compile Signal 9, empty stdout/stderr tail, phase compile, upstream 0/0/0 (2026-09-24 preflight) | No TU/log location; huge librnp + rnp_tests (60 TUs incl Botan3 C++20 heavy headers, single rnp_tests link) peak RSS killed even at -j1 + Ninja; deps excluded (botan3 cached, configure once ran 35.6s) | Memory-slim only, no -O change, no test change: CMAKE_C/CXX_FLAGS append -g0 -fno-lto, EXE/SHARED_LINKER_FLAGS add -Wl,--no-keep-memory; Ninja + -j1 kept; json-c vendored untouched |

| 17 | Zhenji Could NOT find Botan (missing BOTAN_LIBRARY/BOTAN_INCLUDE_DIR, require >=3.0.0) at src/lib/CMakeLists.txt:35, configure passed ZLIB/JSON-C probes | BZip2/ZLIB/JSON-C explicit hints proven effective (log Found ZLIB/Found JSON-C); Botan alone still uses FindBotan.cmake pkg-config+find path: hardened botan3 headers live at <pf>/include/botan-3 with no botan-3.pc installed, PkgConfigDeps output hidden by ohos.toolchain FIND_ROOT=ONLY, and _dep_hints never passed BOTAN_* vars | Same dep-hint route, missing domain filled: new botan3 block in _dep_hints reads real package folder (include/botan-3 verified via botan/version.h, libbotan-3.a/.so) and injects -DBOTAN_ROOT_DIR/-DBOTAN_INCLUDE_DIR/-DBOTAN_LIBRARY; FIND_ROOT BOTH kept; no test/toolchain change |

| 18 | Zhenji Could NOT find GTest (missing GTEST_LIBRARY/GTEST_INCLUDE_DIR/GTEST_MAIN_LIBRARY) at src/tests/CMakeLists.txt:47, configure passed Botan/ZLIB/JSON-C probes (Configuring done 30.2s) | Botan hints proven effective (configure now passes FindBotan); GTest alone still uses module-mode FindGTest.cmake: test_requires gtest/1.17.0.1 is host-context but bare cmake + ohos.toolchain cannot see CMakeDeps GTestConfig.cmake, and _dep_hints never passed GTEST_* vars; upstream links GTest::Main (module target, not CMakeDeps GTest::gtest_main) so config mode alone would still mismatch | Same dep-hint route, next missing domain: new gtest block in _dep_hints reads real gtest package folder (include verified via gtest/gtest.h, libgtest.a + libgtest_main.a) and injects -DGTEST_ROOT/-DGTEST_INCLUDE_DIR/-DGTEST_LIBRARY/-DGTEST_MAIN_LIBRARY; no test/toolchain change, PkgConfig warning is non-fatal |

| 19 | Zhenji 2026-09-24: main build reached [157/157] Linking rnp_tests but `RUN: .../usr/local/bin/ctest --output-on-failure` failed `/bin/sh: .../ctest: inaccessible or not found` (marker discovered/executed 0/0) + test_package `find_package(rnp)` failed `By not providing Findrnp.cmake` | ctest: old `_resolve_tool(cmake_path)` blindly rewrote `.../bin/cmake` to `.../bin/ctest` without existence check, but HMBS only probes cmake/make/ninja/python3 and its cmake dir ships no ctest sibling (HMBS_BUILD_TOOLS lists cmake 4.4.3 with no ctest); test_package: `gens = build_folder/generators` is wrong under cmake_layout (generators live in `self.generators_folder`, sail/simage precedent), so CMAKE_PREFIX_PATH missed CMakeDeps rnp-config; echo marker also read `build_folder/Testing` instead of bdir | Existence-checked `_resolve_ctest()` in both recipes (PATH which first, cmake sibling only if exists+executable, then conf sibling + /data/service/hnp/bin/ctest + /usr/local/bin/ctest, fallback bare `ctest`; missing binary now warns with searched paths instead of silent 0); test_package `gens` switched to `self.generators_folder` (fallback old path) and echo marker switched to `_test_bdir()`; main `gens` likewise; `py_compile` passed |

| 20 | 真机 2026-09-24：ctest 282 跑完但标记 executed/passed/failed=0/0/0，且 test_package find_package(rnp) 缺失；另 12 项失败（178 test_rnp_access、185 HomeDirNoPermission、273-282 cli_tests 十套件 GPG_EXECUTABLE-NOTFOUND） | 计数根因：_parse_last_test_log 只读 build-ohos/Testing/Temporary/LastTest.log 并匹配 Test #N 行，但该文件不含此类行（状态行只在 ctest stdout），故恒返回 0；test_package 根因：CMAKE_PREFIX_PATH 只给 generators 未含包目录，且 ohos.toolchain FIND_ROOT=ONLY 挡住查找，另缺 home harmonybrew 新路径 | 主配方改 subprocess 捕获 ctest stdout 为主数据源逐行解析 N/M Test #K 行，LastTest.log 改递归搜索仅作回退，加恒等式自检与失败 gaps（2 权限 ohos_feature + 10 GPG environment）；test_package PREFIX_PATH=gens;pkg_folder + 三项 FIND_ROOT=BOTH + 补 home 路径；MANIFEST 口径改 ctest_entries/282；不删断言不跳测试 |

| 21 | 真机 2026-09-24 Signal 9 复现（compile 期、stdout/stderr 均空，上游 0/0/0）：上一轮 -g0/-fno-lto/--no-keep-memory + Ninja -j1 已生效仍被杀 | 上轮去调试信息+LTO 关闭+no-keep-memory 假设被证伪：同等 flags 下再次 Signal 9 且无 TU 定位，证峰值不在调试信息/LTO 全程序分析，而在巨型 rnp_tests 链接期符号/节保留；与之前改优化/工具链文本不同的正交方向 | 本轮保留 -O 等级、测试口径与上轮 flags，新增编译期 -ffunction-sections/-fdata-sections 与链接期 -Wl,--gc-sections/--exclude-libs,ALL/--as-needed（另补 MODULE_LINKER 同组），只做节级死代码回收与静态归档符号隐藏，不动可见性（保 librnp 对外 API 导出）、不动测试；py_compile 通过 |

| 22 | 真机 2026-09-24 test_package 链接失败：ld.lld undefined symbol typeinfo/vtable/std::bad_array_new_length/std::out_of_range/std::exception（test_package build() 第 172 行 exit 1）；上游 cli_tests 10 套件 FileNotFoundError GPG_EXECUTABLE-NOTFOUND | test_package CMakeLists 仅 project(C)，链接 librnp.a（C++ 静态归档）时用 C 驱动，未链 C++ 运行时；主配方 package_info 仅 libs=[rnp]，未声明 botan/bzip2/zlib 传递依赖，vendored json-c 未随包发布 | 经验1适配：test_package 改 project(C CXX)+LINKER_LANGUAGE CXX 强制 C++ 链接；package_info 加 requires=[botan3::botan3,bzip2::bzip2,zlib::zlib]，package() 追加 vendored libjson-c.a 进包并按存在性加入 libs；GPG 缺失属环境缺口，已由 gaps 上报，不改测试口径 |
| 23 | 真机 rule4 incomplete：上游标记 discovered=1/executed=0/skipped=1（命令 ctest --output-on-failure），与 MANIFEST 声明 282 严重不符 | 本轮证实该标记并非主包 build() 的 282 项全量运行，而是 test_package/conanfile.py 的 _echo_upstream_marker 在消费者构建目录（仅 1 个 test_rnp）内做 ctest -N=1 + 只读 LastTest.log（该文件无 Test #N Passed 行恒得 0）并发射第二个 HMBS_UPSTREAM_TEST_RESULT，把主包的真实全量标记覆盖（取最后一条）；属标记源污染而非上游测试本身失败 | test_package 删除 _echo_upstream_marker 调用与方法（不再发射任何 HMBS_UPSTREAM_TEST_RESULT，只保留 HMBS_TEST_PACKAGE_RESULT）；主包 _run_upstream_tests 按经验1收紧 passed 判定（仅 failed==0 且 skipped==0 且 executed==discovered 时 passed，否则 failed+reason+gaps 但构建不抛错），12/0 失败时保留 2 权限+10 GPG 既有 gaps，其余未完成形态走诚实 fallback（count=discovered-passed，category=test_failure，evidence 指向上方 ctest 捕获行）；不删断言不跳测试 |
| 24 | CI 2026-09-25 #60615 编译失败：`[12/157] Linking CXX static library src/libsexpp/libsexpp.a` 后 `llvm-ranlib: inaccessible or not found`（exit 127，SDK 路径 `ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ranlib`） | ohos.toolchain.cmake 把 CMAKE_RANLIB 固定为 SDK 内 `llvm/bin/llvm-ranlib`，但当前 SDK 只提供同目录 `llvm-ar`（zstd/brotli/flac 已实证）；llvm-ar 的 `qc` 步骤成功，`ranlib` 步骤 ENOENT，且报错不指明缺哪个程序；真机预检曾过是因为其 SDK/工具链布局不同，CI 的 `ohos-sdk.org` 旧路径无此文件 | 与之前改优化/依赖透传不同的工具链补齐路线：新增 `_llvm_ranlib_defs`（SDK 有则不覆盖；缺失则定位 `llvm-ar` 并在 `build_folder/llvm-ranlib-shim` 生成 `exec <ar> s` 包装器，`py_compile` 通过），主包 `build()` 仅在 `ohos.toolchain` 分支追加 `-DCMAKE_RANLIB=<shim>`；不改测试口径与依赖图，不跳测试 |
