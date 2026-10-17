# libyang 3.13.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (HarmonyOS 真机，conan profile `ci/conan/profiles/ohos-aarch64`)
- 状态: built（配方已完成，真机预检结论以 CI 为准）

## 编译步骤

1. 下载源码：`https://github.com/CESNET/libyang/archive/refs/tags/v3.13.6.tar.gz`
   （sha256 见 conandata.yml；从官方 GitHub tag 包实测，非估算）
2. 依赖：`pcre2/10.45.1.1`（运行依赖，上游 `find_package(PCRE2 REQUIRED)`；
   必须用 ohpcd 专属的 OHOS 适配版：`pcre2/10.40` 会命中 conancenter 配方，
   其 `with_zlib/with_bzip2` 默认 ON 把 `zlib`+`bzip2` 拉进闭包，而 conancenter
   `bzip2/1.0.8` 是 CMake 配方，在 OHOS 下 `System is unknown to cmake` 配置失败
   并写只读 `/tmp`，`--build=missing` 在 libyang 本体之前就倒下；
   `10.45.1.1` 只存在于 ohpcd（已发布），强制走 OHOS Autotools 配方且零传递依赖）、
   `cmocka/2.0.2`（`test_requires`，驱动上游 CTest 套件；缺它上游会静默关闭测试）
3. CMake 配置要点（见 conanfile.py `generate()`）：
   - `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(VERSION 2.8.12...3.28.1)` 与 CMake 4.x 不兼容）
   - `-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64`（E092：CMake 4.x 无
     `Platform/HarmonyOS` 模块，默认映射 `HarmonyOS` 报 `System is unknown to cmake` 且编译器
     检查失败；OHOS 走 Linux 兼容路径，主配方与 test_package 的 `generate()` 内同步注入，
     与 `cmocka/2.0.2`、`zxc/0.9.1`、`easyloggingpp/9.97.1` 同法）
   - `-DENABLE_TESTS=ON`（shared 构建；static 时上游强制 OFF）
   - `-DENABLE_VALGRIND_TESTS=OFF -DENABLE_COVERAGE=OFF -DENABLE_FUZZ_TARGETS=OFF`
   - `-DENABLE_TOOLS=ON`（构建 `yanglint`/`yangre`，随包发布）
   - `-DCMAKE_INSTALL_LIBDIR=lib`
   - `PCRE2_INCLUDE_DIR/PCRE2_LIBRARY`、`CMOCKA_INCLUDE_DIR/CMOCKA_LIBRARY` 由 conan 依赖位置显式注入
     （上游自带 Find 模块只搜固定系统路径）
4. `cmake --build` 后在真机执行 `ctest --output-on-failure --no-tests=error`（56 个 cmocka 单测），
   按 `libevent/2.1.13` 与 `boxes/2.3.1` 的既有惯例输出 `HMBS_UPSTREAM_TEST_RESULT` 机器标记并落盘
   `res/upstream_test_result.json` 供 test_package 复发。
5. test_package：编译 `test_libyang.c`（context→schema→JSON data→print 全链路 6 个断言）并执行，
   另执行打包的 `yanglint --version`；输出 `HMBS_TEST_PACKAGE_RESULT` 机器标记。

## 上游测试清点（R51 申报表，源码静态审计）

| 位置 | 内容 | ctest 注册数 |
|------|------|--------------|
| `tests/utests/`（types 22、basic 10、data 11、schema 5、extensions 5、restriction 2、node 1） | cmocka 单元测试（`ly_add_utest`） | 56 |
| `tests/plugins/`（invalid.c、simple.c） | 以 `MODULE` 库形式构建，供 `utest_plugins` 加载的插件夹具，非独立 ctest 用例 | 0 |
| `tests/yanglint/`（interactive/non-interactive `.tcl`） | 仅当 `tclsh`+`expect` 同时存在才注册；OHOS 真机无此二者，上游 CMake 自行跳过 | 0 |
| `tests/yangre/`（`all.tcl`） | 同上，需 `tclsh`+`expect`；OHOS 下上游自行跳过 | 0 |
| `tests/style/`、`tests/perf/`、`tests/fuzz/` | 格式/性能/模糊辅助目标，非 `add_test` 功能用例（fuzz 需 `ENABLE_FUZZ_TARGETS=ON`，本配方关闭） | 0 |

结论：OHOS 真机 ctest 应发现 56 个用例；`--no-tests=error` 保证 0 发现即失败，杜绝空跑误报。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试在 static 构建下消失 | 上游 `if(NOT BUILD_SHARED_LIBS)` 强制 `ENABLE_TESTS=OFF`（单测链接 `$<TARGET_OBJECTS:yangobj>`，该目标仅 shared 构建存在） | 配方默认 `shared=True`；static 时 `build()` 明确跳过 ctest 并告警，test_package 消费者测试照常覆盖 |
| 2 | `find_package(PCRE2/CMocka)` 找不到 conan 依赖 | 上游自带 Find 模块只搜 `/usr/lib` 等固定路径；且上游 `unset(PCRE2_LIBRARY CACHE)` 会丢弃单数缓存，CMocka 模块以 `CMOCKA_ROOT_DIR` 为主（本轮预检：配置通过但编译报 `pcre2.h file not found`、`Disabling tests because of missing CMocka`）。第 6 轮重读模块源码后确认：FindPCRE2 仅在复数对 `PCRE2_LIBRARIES AND PCRE2_INCLUDE_DIRS` 已缓存时短路，而 `unset()` 只清单数；FindCMocka 无短路且 `find_library PATHS ${CMOCKA_ROOT_DIR}/include` 注定找不到库（库不在 include/ 下），故 ROOT 通道必然失败 | `generate()` 从 `self.dependencies` 定位头文件与库文件并注入 `*_INCLUDE_DIR/*_LIBRARY`，再补 `CMOCKA_ROOT_DIR` + `CMAKE_INCLUDE_PATH/LIBRARY_PATH/PREFIX_PATH` 三路搜索输入；第 6 轮改为缓存直通绕过搜索：预置复数 `PCRE2_INCLUDE_DIRS/PCRE2_LIBRARIES` 触发短路（不受 `unset()` 影响），预置 `CMOCKA_LIBRARY/CMOCKA_LIBRARIES` 使 `find_*` 跳过坏 PATHS（CMake 缓存已存在即跳过搜索） |\n| 3 | CMake 4.x 配置失败风险 | 上游 `cmake_minimum_required(VERSION 2.8.12...3.28.1)` 下限低于 3.5 | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（与 `libyaml/0.2.5` 同法） |
| 4 | OHOS 真机执行需签名 | 未签名 ELF 无法执行 | `build()` 签名构建树产物、`package()` 签名 `lib/*.so*` 与 `bin/*`、`test_package` 签名消费者二进制（`libevent`/`lerc` 既有惯例） |
| 5 | 真机 `/tmp` 只读致编译器识别失败 | 预检设备 `/tmp` 只读，CMake 编译器探测临时文件无处可写 | `generate()` 将 HMBS 注入的任务私有 `TMPDIR/TMP/TEMP` 持久化为 `conanbuild` 环境脚本，主配方与 `test_package` 同步，测试侧 `test()` 入口同样重定向；仅换临时根目录，不跳过任何测试 |
| 6 | profile 钉死的编译器绝对路径在部分runner缺失或不可运行 | `tools.build:compiler_executables` 的绝对路径不存在或实际不可用（三轮复现：本轮 C/CXX 均 `--version` 失败已回退到 `.harmonybrew/bin/clang(+​+)`，但 CMake 仍见 `/data/service/hnp/bin/clang` 报 `identification is unknown`）；第 1 轮 `--version` 探测仍放行了该 C 路径 | 第 1 轮：可运行性探测 + 双向兄弟恢复 + `CC/CXX` 透传；第 2 轮（不同策略）：`--version` 通过后再加 `-c` 编译探针（头文件无关的最小源，临时文件强制进 HMBS 可写 `TMPDIR`），替换候选改走 basename 经 `PATH` 解析（`libequihash` 经验 1），兄弟恢复同样要求编译探针通过；第 3 轮（不同通道）：预检证明回退已打印但 CMake 仍见钉死路径——`conan_toolchain.cmake` 内 conf 编译器行覆盖用户 `tc.cache_variables`，故编译器覆盖改走 `tc.variables`（preset/CLI `-D`，`plutosvg:501` 与 cryptokit/faudio 同通道）；第 4 轮（本轮，不同交付）：预检证明仅 `tc.variables` 仍输给工具链文件，故 `tc.generate()` 后就地补丁所有 `conan_toolchain.cmake`（ stale→fresh 字符串替换并打 `HMBS toolchain patch` 日志），`build()` 内先重打补丁再 `cmake.configure(variables={CMAKE_C_COMPILER,CMAKE_CXX_COMPILER})` 经 CLI `-D` 显式传入，主配方与 test_package 双侧同步；两者皆无则抛明示环境故障 |
| 7 | 上轮缓存预置后 PCRE2 恢复但 CMocka 仍 missing，ctest 发现数为 0 | `tests/CMakeLists.txt` 只消费 `${CMOCKA_INCLUDE_DIR}/${CMOCKA_LIBRARIES}`，后者唯一来源是 `CMOCKA_LIBRARY`；而 `FindCMocka.cmake` 的 `find_library` 在 `${CMOCKA_ROOT_DIR}/include` 下找库（本轮预检：`HMBS dep roots` 已打印、`pcre2.h` 错误消失证明预置生效，仍 `Disabling tests because of missing CMocka` + `No upstream tests discovered`）——属模块源码级缺陷，变量注入无法根治 | 与上轮缓存预置不同的路线：`patches/0001-findcmocka-lib-path.patch` 把库 `PATHS` 改为 `lib`/`lib64`（保留 `include` 回退），让模块真正搜到 conan 包里的库；已有复数缓存预置保留为双保险 |
| 8 | 静态 PATHS 补丁后仍 `Disabling tests because of missing CMocka`（同指纹第 3 次） | 唯一在本机预检中被证实有效的注入是 PCRE2 的 early-exit（不经搜索即 FOUND）；CMocka 模块没有 early-exit，任何搜索都可能在受限交叉环境里落空；且导出日志里未见 `.patch` 拷贝行，补丁通道是否实际生效无法确认 | 与上轮不同的双路线：补丁追加 `FindPCRE2` 同款缓存 early-exit（预置复数对即 `FOUND TRUE`）；主配方 `build()` 新增 `_ensure_findcmocka_fix()` 在解包源码上强制同等修改（幂等）并打 `HMBS FindCMocka ...` 日志行，下轮日志可直接证明哪条通道生效 |
| 9 | `apply_conandata_patches` 直接抛 `Failed to apply patch: 0001-findcmocka-lib-path.patch`（`source file is different`，`actual: b')'`），编译前即中断 | 上轮静态补丁的上下文行与 3.13.6 发布包内 `CMakeModules/FindCMocka.cmake` 失配（conan 严格打补丁，行号/上下文差一行即整包失败）；且按策略连续三轮同指纹后必须换路线 | 与上轮不同的单通道路线：删除静态补丁（`conandata.yml` 去掉 `patches` 段，删 `patches/` 目录），只保留构建期 `_ensure_findcmocka_fix()`，并改为容错实现（CRLF 归一化、lib 修复仅作用于 `find_library` 块、early-exit 按锚点注入），`apply_conandata_patches` 变为空操作不再中断 |
| 10 | 删静态补丁后配置通过但仍 `Disabling tests because of missing CMocka`，`No upstream tests discovered`（同指纹第 2 次，`Configuring done` 但发现数为 0） | 上轮只修 `FindCMocka.cmake` 模块本身，但该模块仍受交叉 `find-root` 限制与 `find_package(CMocka 1.0.1)` 版本握手影响，任何残留 miss 都会在调用处把 `ENABLE_TESTS` 关掉；且若修完仍重跑模块，`find_package_handle_standard_args` 会覆盖 `FOUND` | 与上轮不同的调用方路线：`build()` 新增 `_ensure_cmocka_caller_fix()`，用 `_dep_layout` 定位的绝对路径直接改写顶层 `CMakeLists.txt`（`CMOCKA_INCLUDE_DIR/LIBRARIES/LIBRARY` + `CMOCKA_FOUND/CMocka_FOUND=TRUE`，注释掉原 `find_package` 使其不再覆盖），`Find` 模块修复保留为回退 |
| 11 | 本轮预检 60 用例中 `headers` 报 `env: exec bash: No such file or directory` 且解析器 `discovered=60 executed=51` 失配 | `compat/check_includes.sh` 首行为 `#!/usr/bin/env bash`，真机 PATH 无 bash；且脚本内 `--include=\*.{c,h}` 依赖 bash 花括号展开，直译到 sh 下会空匹配导致空断言通过；解析器对 `***Exception` 等非 Passed/Failed 行漏计 | 与上轮 CMocka 路线不同的新路线：`build()` 新增 `_ensure_check_includes_posix()`（改 shebang 为 `#!/bin/sh` 并展开为两个 `--include`，仅换解释器不断言删除），`_run_upstream_tests()` 新增 `_ensure_bash_shim()`（真 bash 优先，否则 symlink `bash`→`/bin/sh` 并前置 PATH，无需 chmod）；`_parse_ctest_output` 改为穷举（非通过非跳过一律计失败），主配方与 test_package 同步 |

| 12 | 预检 `discovered=60 executed=51 skipped=0` 对账失配（9 个用例无结果行）且 fuzz  harness 未签名、`--include` 转义丢失 | 清点确认 60=56 utests+headers+3 fuzz 回归；`_sign_build_artifacts` 仅签名 `tests/*` 顶层，`tests/fuzz/*/*/regress_fuzz_*` 未签名导致 OHOS 上无法执行；listing 与 run 均用 `self.build_folder`，而真实二进制目录为 `build/Release` 子目录，两处 cwd 不一致可致发现与执行漂移；`_parse_ctest_output` 只计数不记名，缺失的 9 个无法定位；`check_includes` 改写把 `--include=\*.c` 写成无转义的 `--include=*.c`，sh 下会 glob 展开导致空匹配假通过 | 与上轮不同的 harness 路线：新增 `_ctest_dir()`（搜最深 `CTestTestfile.cmake`，listing 与 run 同目录并打 `HMBS ctest dir` 日志）；`LD_LIBRARY_PATH` 补 `ctest_dir/tests`；解析器返回用例名并在失配时打 `HMBS ctest missing results` 明细；`_sign_build_artifacts` 改为递归签名全构建树 ELF（含 fuzz）；`--include` 改写保留反斜杠转义；仅换目录/签名/日志，不删任何测试 |

| 13 | 上轮 `_ctest_dir` 取最深匹配落到 `.../build/Release/tests/yanglint`，`discovered=0` 直接失败 | 最深目录是叶子子集而非测试全集；不同策略：枚举全部 `CTestTestfile.cmake` 目录并逐个 `ctest --show-only=json-v1` 探测试数，选用例数最多的顶层二进制目录（`.../b/build/Release`，60 用例） | 与上轮不同的选择策略：按用例数投票而非按路径深度，并打 `HMBS ctest probe` 日志；仅换目录选择，不删任何测试 |

| 14 | 上轮按名对账定位到缺失 `utest_uint8..utest_string` 前 9 个，但仍整包对账失败 | 缺失集合确定性地固定为前 9 个 types 单测（两轮均为 51/60），属执行侧无结果行而非发现侧问题；不同策略：主跑后对每个缺失用例 `ctest -R ^name# libyang 3.13.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (HarmonyOS 真机，conan profile `ci/conan/profiles/ohos-aarch64`)
- 状态: built（配方已完成，真机预检结论以 CI 为准）

## 编译步骤

1. 下载源码：`https://github.com/CESNET/libyang/archive/refs/tags/v3.13.6.tar.gz`
   （sha256 见 conandata.yml；从官方 GitHub tag 包实测，非估算）
2. 依赖：`pcre2/10.45.1.1`（运行依赖，上游 `find_package(PCRE2 REQUIRED)`；
   必须用 ohpcd 专属的 OHOS 适配版：`pcre2/10.40` 会命中 conancenter 配方，
   其 `with_zlib/with_bzip2` 默认 ON 把 `zlib`+`bzip2` 拉进闭包，而 conancenter
   `bzip2/1.0.8` 是 CMake 配方，在 OHOS 下 `System is unknown to cmake` 配置失败
   并写只读 `/tmp`，`--build=missing` 在 libyang 本体之前就倒下；
   `10.45.1.1` 只存在于 ohpcd（已发布），强制走 OHOS Autotools 配方且零传递依赖）、
   `cmocka/2.0.2`（`test_requires`，驱动上游 CTest 套件；缺它上游会静默关闭测试）
3. CMake 配置要点（见 conanfile.py `generate()`）：
   - `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(VERSION 2.8.12...3.28.1)` 与 CMake 4.x 不兼容）
   - `-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64`（E092：CMake 4.x 无
     `Platform/HarmonyOS` 模块，默认映射 `HarmonyOS` 报 `System is unknown to cmake` 且编译器
     检查失败；OHOS 走 Linux 兼容路径，主配方与 test_package 的 `generate()` 内同步注入，
     与 `cmocka/2.0.2`、`zxc/0.9.1`、`easyloggingpp/9.97.1` 同法）
   - `-DENABLE_TESTS=ON`（shared 构建；static 时上游强制 OFF）
   - `-DENABLE_VALGRIND_TESTS=OFF -DENABLE_COVERAGE=OFF -DENABLE_FUZZ_TARGETS=OFF`
   - `-DENABLE_TOOLS=ON`（构建 `yanglint`/`yangre`，随包发布）
   - `-DCMAKE_INSTALL_LIBDIR=lib`
   - `PCRE2_INCLUDE_DIR/PCRE2_LIBRARY`、`CMOCKA_INCLUDE_DIR/CMOCKA_LIBRARY` 由 conan 依赖位置显式注入
     （上游自带 Find 模块只搜固定系统路径）
4. `cmake --build` 后在真机执行 `ctest --output-on-failure --no-tests=error`（56 个 cmocka 单测），
   按 `libevent/2.1.13` 与 `boxes/2.3.1` 的既有惯例输出 `HMBS_UPSTREAM_TEST_RESULT` 机器标记并落盘
   `res/upstream_test_result.json` 供 test_package 复发。
5. test_package：编译 `test_libyang.c`（context→schema→JSON data→print 全链路 6 个断言）并执行，
   另执行打包的 `yanglint --version`；输出 `HMBS_TEST_PACKAGE_RESULT` 机器标记。

## 上游测试清点（R51 申报表，源码静态审计）

| 位置 | 内容 | ctest 注册数 |
|------|------|--------------|
| `tests/utests/`（types 22、basic 10、data 11、schema 5、extensions 5、restriction 2、node 1） | cmocka 单元测试（`ly_add_utest`） | 56 |
| `tests/plugins/`（invalid.c、simple.c） | 以 `MODULE` 库形式构建，供 `utest_plugins` 加载的插件夹具，非独立 ctest 用例 | 0 |
| `tests/yanglint/`（interactive/non-interactive `.tcl`） | 仅当 `tclsh`+`expect` 同时存在才注册；OHOS 真机无此二者，上游 CMake 自行跳过 | 0 |
| `tests/yangre/`（`all.tcl`） | 同上，需 `tclsh`+`expect`；OHOS 下上游自行跳过 | 0 |
| `tests/style/`、`tests/perf/`、`tests/fuzz/` | 格式/性能/模糊辅助目标，非 `add_test` 功能用例（fuzz 需 `ENABLE_FUZZ_TARGETS=ON`，本配方关闭） | 0 |

结论：OHOS 真机 ctest 应发现 56 个用例；`--no-tests=error` 保证 0 发现即失败，杜绝空跑误报。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试在 static 构建下消失 | 上游 `if(NOT BUILD_SHARED_LIBS)` 强制 `ENABLE_TESTS=OFF`（单测链接 `$<TARGET_OBJECTS:yangobj>`，该目标仅 shared 构建存在） | 配方默认 `shared=True`；static 时 `build()` 明确跳过 ctest 并告警，test_package 消费者测试照常覆盖 |
| 2 | `find_package(PCRE2/CMocka)` 找不到 conan 依赖 | 上游自带 Find 模块只搜 `/usr/lib` 等固定路径；且上游 `unset(PCRE2_LIBRARY CACHE)` 会丢弃单数缓存，CMocka 模块以 `CMOCKA_ROOT_DIR` 为主（本轮预检：配置通过但编译报 `pcre2.h file not found`、`Disabling tests because of missing CMocka`）。第 6 轮重读模块源码后确认：FindPCRE2 仅在复数对 `PCRE2_LIBRARIES AND PCRE2_INCLUDE_DIRS` 已缓存时短路，而 `unset()` 只清单数；FindCMocka 无短路且 `find_library PATHS ${CMOCKA_ROOT_DIR}/include` 注定找不到库（库不在 include/ 下），故 ROOT 通道必然失败 | `generate()` 从 `self.dependencies` 定位头文件与库文件并注入 `*_INCLUDE_DIR/*_LIBRARY`，再补 `CMOCKA_ROOT_DIR` + `CMAKE_INCLUDE_PATH/LIBRARY_PATH/PREFIX_PATH` 三路搜索输入；第 6 轮改为缓存直通绕过搜索：预置复数 `PCRE2_INCLUDE_DIRS/PCRE2_LIBRARIES` 触发短路（不受 `unset()` 影响），预置 `CMOCKA_LIBRARY/CMOCKA_LIBRARIES` 使 `find_*` 跳过坏 PATHS（CMake 缓存已存在即跳过搜索） |\n| 3 | CMake 4.x 配置失败风险 | 上游 `cmake_minimum_required(VERSION 2.8.12...3.28.1)` 下限低于 3.5 | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（与 `libyaml/0.2.5` 同法） |
| 4 | OHOS 真机执行需签名 | 未签名 ELF 无法执行 | `build()` 签名构建树产物、`package()` 签名 `lib/*.so*` 与 `bin/*`、`test_package` 签名消费者二进制（`libevent`/`lerc` 既有惯例） |
| 5 | 真机 `/tmp` 只读致编译器识别失败 | 预检设备 `/tmp` 只读，CMake 编译器探测临时文件无处可写 | `generate()` 将 HMBS 注入的任务私有 `TMPDIR/TMP/TEMP` 持久化为 `conanbuild` 环境脚本，主配方与 `test_package` 同步，测试侧 `test()` 入口同样重定向；仅换临时根目录，不跳过任何测试 |
| 6 | profile 钉死的编译器绝对路径在部分runner缺失或不可运行 | `tools.build:compiler_executables` 的绝对路径不存在或实际不可用（三轮复现：本轮 C/CXX 均 `--version` 失败已回退到 `.harmonybrew/bin/clang(+​+)`，但 CMake 仍见 `/data/service/hnp/bin/clang` 报 `identification is unknown`）；第 1 轮 `--version` 探测仍放行了该 C 路径 | 第 1 轮：可运行性探测 + 双向兄弟恢复 + `CC/CXX` 透传；第 2 轮（不同策略）：`--version` 通过后再加 `-c` 编译探针（头文件无关的最小源，临时文件强制进 HMBS 可写 `TMPDIR`），替换候选改走 basename 经 `PATH` 解析（`libequihash` 经验 1），兄弟恢复同样要求编译探针通过；第 3 轮（不同通道）：预检证明回退已打印但 CMake 仍见钉死路径——`conan_toolchain.cmake` 内 conf 编译器行覆盖用户 `tc.cache_variables`，故编译器覆盖改走 `tc.variables`（preset/CLI `-D`，`plutosvg:501` 与 cryptokit/faudio 同通道）；第 4 轮（本轮，不同交付）：预检证明仅 `tc.variables` 仍输给工具链文件，故 `tc.generate()` 后就地补丁所有 `conan_toolchain.cmake`（ stale→fresh 字符串替换并打 `HMBS toolchain patch` 日志），`build()` 内先重打补丁再 `cmake.configure(variables={CMAKE_C_COMPILER,CMAKE_CXX_COMPILER})` 经 CLI `-D` 显式传入，主配方与 test_package 双侧同步；两者皆无则抛明示环境故障 |
| 7 | 上轮缓存预置后 PCRE2 恢复但 CMocka 仍 missing，ctest 发现数为 0 | `tests/CMakeLists.txt` 只消费 `${CMOCKA_INCLUDE_DIR}/${CMOCKA_LIBRARIES}`，后者唯一来源是 `CMOCKA_LIBRARY`；而 `FindCMocka.cmake` 的 `find_library` 在 `${CMOCKA_ROOT_DIR}/include` 下找库（本轮预检：`HMBS dep roots` 已打印、`pcre2.h` 错误消失证明预置生效，仍 `Disabling tests because of missing CMocka` + `No upstream tests discovered`）——属模块源码级缺陷，变量注入无法根治 | 与上轮缓存预置不同的路线：`patches/0001-findcmocka-lib-path.patch` 把库 `PATHS` 改为 `lib`/`lib64`（保留 `include` 回退），让模块真正搜到 conan 包里的库；已有复数缓存预置保留为双保险 |
| 8 | 静态 PATHS 补丁后仍 `Disabling tests because of missing CMocka`（同指纹第 3 次） | 唯一在本机预检中被证实有效的注入是 PCRE2 的 early-exit（不经搜索即 FOUND）；CMocka 模块没有 early-exit，任何搜索都可能在受限交叉环境里落空；且导出日志里未见 `.patch` 拷贝行，补丁通道是否实际生效无法确认 | 与上轮不同的双路线：补丁追加 `FindPCRE2` 同款缓存 early-exit（预置复数对即 `FOUND TRUE`）；主配方 `build()` 新增 `_ensure_findcmocka_fix()` 在解包源码上强制同等修改（幂等）并打 `HMBS FindCMocka ...` 日志行，下轮日志可直接证明哪条通道生效 |
| 9 | `apply_conandata_patches` 直接抛 `Failed to apply patch: 0001-findcmocka-lib-path.patch`（`source file is different`，`actual: b')'`），编译前即中断 | 上轮静态补丁的上下文行与 3.13.6 发布包内 `CMakeModules/FindCMocka.cmake` 失配（conan 严格打补丁，行号/上下文差一行即整包失败）；且按策略连续三轮同指纹后必须换路线 | 与上轮不同的单通道路线：删除静态补丁（`conandata.yml` 去掉 `patches` 段，删 `patches/` 目录），只保留构建期 `_ensure_findcmocka_fix()`，并改为容错实现（CRLF 归一化、lib 修复仅作用于 `find_library` 块、early-exit 按锚点注入），`apply_conandata_patches` 变为空操作不再中断 |
| 10 | 删静态补丁后配置通过但仍 `Disabling tests because of missing CMocka`，`No upstream tests discovered`（同指纹第 2 次，`Configuring done` 但发现数为 0） | 上轮只修 `FindCMocka.cmake` 模块本身，但该模块仍受交叉 `find-root` 限制与 `find_package(CMocka 1.0.1)` 版本握手影响，任何残留 miss 都会在调用处把 `ENABLE_TESTS` 关掉；且若修完仍重跑模块，`find_package_handle_standard_args` 会覆盖 `FOUND` | 与上轮不同的调用方路线：`build()` 新增 `_ensure_cmocka_caller_fix()`，用 `_dep_layout` 定位的绝对路径直接改写顶层 `CMakeLists.txt`（`CMOCKA_INCLUDE_DIR/LIBRARIES/LIBRARY` + `CMOCKA_FOUND/CMocka_FOUND=TRUE`，注释掉原 `find_package` 使其不再覆盖），`Find` 模块修复保留为回退 |
| 11 | 本轮预检 60 用例中 `headers` 报 `env: exec bash: No such file or directory` 且解析器 `discovered=60 executed=51` 失配 | `compat/check_includes.sh` 首行为 `#!/usr/bin/env bash`，真机 PATH 无 bash；且脚本内 `--include=\*.{c,h}` 依赖 bash 花括号展开，直译到 sh 下会空匹配导致空断言通过；解析器对 `***Exception` 等非 Passed/Failed 行漏计 | 与上轮 CMocka 路线不同的新路线：`build()` 新增 `_ensure_check_includes_posix()`（改 shebang 为 `#!/bin/sh` 并展开为两个 `--include`，仅换解释器不断言删除），`_run_upstream_tests()` 新增 `_ensure_bash_shim()`（真 bash 优先，否则 symlink `bash`→`/bin/sh` 并前置 PATH，无需 chmod）；`_parse_ctest_output` 改为穷举（非通过非跳过一律计失败），主配方与 test_package 同步 |

| 12 | 预检 `discovered=60 executed=51 skipped=0` 对账失配（9 个用例无结果行）且 fuzz  harness 未签名、`--include` 转义丢失 | 清点确认 60=56 utests+headers+3 fuzz 回归；`_sign_build_artifacts` 仅签名 `tests/*` 顶层，`tests/fuzz/*/*/regress_fuzz_*` 未签名导致 OHOS 上无法执行；listing 与 run 均用 `self.build_folder`，而真实二进制目录为 `build/Release` 子目录，两处 cwd 不一致可致发现与执行漂移；`_parse_ctest_output` 只计数不记名，缺失的 9 个无法定位；`check_includes` 改写把 `--include=\*.c` 写成无转义的 `--include=*.c`，sh 下会 glob 展开导致空匹配假通过 | 与上轮不同的 harness 路线：新增 `_ctest_dir()`（搜最深 `CTestTestfile.cmake`，listing 与 run 同目录并打 `HMBS ctest dir` 日志）；`LD_LIBRARY_PATH` 补 `ctest_dir/tests`；解析器返回用例名并在失配时打 `HMBS ctest missing results` 明细；`_sign_build_artifacts` 改为递归签名全构建树 ELF（含 fuzz）；`--include` 改写保留反斜杠转义；仅换目录/签名/日志，不删任何测试 |

| 13 | 上轮 `_ctest_dir` 取最深匹配落到 `.../build/Release/tests/yanglint`，`discovered=0` 直接失败 | 最深目录是叶子子集而非测试全集；不同策略：枚举全部 `CTestTestfile.cmake` 目录并逐个 `ctest --show-only=json-v1` 探测试数，选用例数最多的顶层二进制目录（`.../b/build/Release`，60 用例） | 与上轮不同的选择策略：按用例数投票而非按路径深度，并打 `HMBS ctest probe` 日志；仅换目录选择，不删任何测试 |

 单独重跑并合并 verdict，恢复真实结果或输出显式失败，同时 stat 缺失二进制存在性 | 与上轮不同的执行策略：缺失重跑+结果合并+二进制存在性取证；不跳过不删除任何测试 |

## 源码修改

- 无静态补丁（第 9 轮已删除 `patches/0001-findcmocka-lib-path.patch`：其上下文与发布包失配致 `apply_conandata_patches` 在编译前中断）。
  上游 `CMakeModules/FindCMocka.cmake` 把 `find_library(CMOCKA_LIBRARY ...)` 的
  `PATHS` 写成 `${CMOCKA_ROOT_DIR}/include`，库文件不可能出现在 `include/`
  下，交叉编译时 `find_package(CMocka)` 永失败，上游静默 `ENABLE_TESTS=OFF`。
  修复走两层构建期改写（均幂等、容错，CRLF 归一化）：（1）`_ensure_findcmocka_fix()`
  修 `FindCMocka.cmake`（lib 路径只改 `find_library` 块为 `lib`/`lib64`/`include`，
  另按锚点注入 `FindPCRE2` 同款 early-exit）；（2）第 10 轮新增
  `_ensure_cmocka_caller_fix()` 直改顶层 `CMakeLists.txt` 调用处，用 conan 绝对
  路径 pin 住 `CMOCKA_*` 并跳过原 `find_package`（重跑模块会覆盖 `FOUND`），
  输出 `HMBS CMocka caller fix ...` 日志行证明生效。
  OHOS 兼容点其余均为上游已处理：工具链自带 `compat/`（`use_compat()` 自动探测），
  `yanglint` 交互模式缺 `sys/ioctl.h` 时上游自行降级为非交互构建。

## 依赖版本

- `pcre2/10.45.1.1`（制品仓 `published`，ohpcd 专属 OHOS 适配版，零传递依赖）
- `cmocka/2.0.2`（`test_requires`，仅测试期使用，不进运行闭包）

## 验证结果

配方工作树已完成，待 HMBS 真机预检（`conan create`：上游 56 用例 ctest + test_package 2 用例）后回填实测数字。
退出码为 0 不等于真跑：配方内 ctest 解析器按 `Test #N:` 结果行逐个分类统计，
`--no-tests=error` + 发现数/执行数对账（`executed + skipped == discovered`）双重防空跑；
参照文件均为真机实测产物，非空校验在预检日志中可查。

---

**编译结束**: 2026-09-16（工作树，待真机验证）
**最终状态**: built
