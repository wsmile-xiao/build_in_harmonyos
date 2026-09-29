# tmx 1.10.1 适配笔记

## 上游信息

- 上游：https://github.com/baylej/tmx（tag `tmx_1.10.1`，2026-01-25，BSD-2-Clause）
- 语言/构建：C + CMake（`cmake_minimum_required(VERSION 3.10)`，CMake 4.x 可直接配置）
- 源码包：`https://github.com/baylej/tmx/archive/refs/tags/tmx_1.10.1.tar.gz`
- sha256：`05a141abb5e1a6464242a888041bc81a8e1a032baf0f30a00e350f441f162c08`（实拉 136347 字节核验）
- 依赖：LibXml2（强制，`find_package(LibXml2 REQUIRED)`）、zlib（`WANT_ZLIB` 默认 ON）、zstd（`WANT_ZSTD` 默认 OFF，本配方保持关闭）

## 依赖发布检查（W0）

- `libxml2/2.15.3.1`：仓内已有归档（`archives/l/libxml2/2.15.3.1`，状态 built，备注制品仓已锁定 2.15.3），为带 `export_sources` 修复的新配方；多配方以 `self.requires("libxml2/2.15.3.1")` 引用。
- `zlib/1.3.1.1`：仓内独有版本（conancenter 无同版本，可避开 CCI 配方劫持及无 OHOS 条目的 cmake tool_requires 问题）；多已合入配方以 `self.requires("zlib/1.3.1.1")` 引用。
- 最终以真机预检 PF4（制品仓探测）与 `conan create` 图求解为准；若任一依赖未发布则按 R36 先补依赖。

## 上游测试清点（R51）

- 上游**无自动化测试**：tarball 共 61 条目，仅 `src/`、`examples/`、`doc/`、`.github/`；无 `tests/` 目录、无测试源文件；`CMakeLists.txt` 无 `enable_testing`/`add_test`（ctest 口径总数 0）。
- 唯一含 `test` 字样的文件是 `.github/workflows/buildandtest.yaml`，内容仅为：构建库、构建并运行 `dumper` 演示程序（无断言、无通过/失败判定）、把 `tmx.h` 当 C++ 编译一次。属于演示型 CI，非测试套件。
- `examples/` 下 allegro/sdl/raylib 为游戏引擎渲染演示（需三方游戏库），`dumper` 为地图转储演示，均无断言。
- 因此申报 `upstream_tests_exist: false`，`upstream_test_total: 0`，验证全部由 test_package 承担。

## 平台适配要点

- **工具链**：标准 `CMakeToolchain` + `CMake` helper（ADAPTATION_GUIDE 4.2，不依赖外部 `ohos.toolchain.cmake` 文件；首轮的自发现裸 cmake 路线在预检 worker 上硬失败 `ohos.toolchain.cmake not found`，profile 未配 user_toolchain 且 `OHOS_NDK_HOME` 为空、SDK glob 无命中——与 tvm-ffi 已记录的失败同源，故切回标准链路）；`CMAKE_INSTALL_LIBDIR=lib`（64 位默认装 `lib64/`，须改回 `lib`）。
- **依赖定位**：`CMakeDeps` 把 `zlib→ZLIB/ZLIB::ZLIB`、`libxml2→LibXml2/LibXml2::LibXml2` 映射并设 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=True`，让上游模块模式 `find_package(ZLIB)`/`find_package(LibXml2)` 走 Conan 生成的 config，避免 SDK sysroot 内宿主库漏入（taglib 2.3/1.13.1 同法）。
- **`tmx.h` 仅包含 `<stddef.h>`/`<stdint.h>`**，无须 `transitive_headers`；但上游以 PUBLIC 方式链接两依赖，故 `package_info.requires = ["libxml2::libxml2", "zlib::zlib"]`（静态链接消费者时自动补 `-lxml2 -lz`）。
- **开关**：`WANT_ZLIB=ON`（默认行为，test 第 12 项断言覆盖 base64+zlib 解码）、`WANT_ZSTD=OFF`（上游默认，不引入 zstd 依赖）、`BUILD_SHARED_LIBS` 跟随 `shared` 选项（默认静态；R26 不适用，tmx 非系统同名库）。
- **签名**：`package()` 对 `.so` 产物执行 llvm-objcopy 去 `.codesign` + binary-sign-tool 自签；默认静态构建时无 `.so`，函数直接返回。
- **文档目录**：上游 `add_subdirectory(doc)` 在 `DOC_HTML`/`DOC_SINGLEHTML` 全关（默认）时直接 `return()`，无需 Sphinx，无补丁。
- **补丁**：零补丁（`patches: {}`）。
- **类型**：纯库，无可执行产物，不建 `commands.json`（R38）。

## test_package 设计（R34）

- `test_tmx.c`：15 项确定性检查——CSV 夹具经 `tmx_load` 解析（维度/图块集名/图层 id 与 gids/GID 查块）、`tmx_load_buffer` 复检同一文档、缺失文件以 `E_NOENT` 干净失败且 `tmx_strerr()` 非空、畸形 XML 以非零 `tmx_errno` 失败、base64+zlib 图层解码（证伪 WANT_ZLIB 链路：zlib 未链接时会报 `E_ZDATA`/`E_FONCT` 而非静默通过）、ARGB 颜色转换、`find_layer_by_id` 与按名查找一致。任一失败即非零退出，不存在空文件比空文件的通过。
- test 夹具为源码内嵌字符串（无外部文件依赖）；`test()` 用 `VirtualRunEnv` 运行（libxml2 默认 shared，需 runenv 找到 `.so`）。

## 真机失败修复记录（2026-09-29，preflight compile：CMAKE_C_COMPILER 校验失败）

- 失败证据：标准链路已生成 `conan_toolchain.cmake`，但 `cmake.configure()` 在 `CMakeLists.txt:3 (project)` 报 `The CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 后配置中断（`-- Configuring incomplete, errors occurred!`，`build()` line 94 `cmake.configure()`）。
- 根因判断：profile 把编译器钉死在 `/data/service/hnp/bin/clang(++)`，该绝对路径在当前预检 worker 上不可用，`project()` 内编译器自检随即失败；与上一轮的 toolchain 文件缺失不同维度（上一轮是外部 SDK 文件依赖，本轮是工具链文件内烘焙的编译器路径）。
- 本轮改动（`conanfile.py`，仅换编译器可执行文件，不改标志与链接）：新增 `_compiler_executable()`（conf 有文件用 conf，否则 `shutil.which` 回退）与 `_patch_cmake_toolchain_compilers()`；`generate()` 在 OHOS 下把解析结果同时写入 `tc.cache_variables["CMAKE_C_COMPILER/CXX_COMPILER"]` 并在 `tc.generate()` 后改写 `conan_toolchain.cmake` 中的钉死路径（bzrtp 同法）。
- 待 HMBS 真机预检验证。

## 验证结果

- 本轮为首轮工作树（未提交），真机预检（`conan create` 全量门禁 + 双 HMBS 标记）由 HMBS 后台执行后回填：
  - `HMBS_TEST_PACKAGE_RESULT` 期望 `discovered:15/passedCount:15`
  - `HMBS_UPSTREAM_TEST_RESULT` 期望 `status:no_tests/discovered:0/executed:0`
- 若预检报依赖未发布（PF4）或构建失败，下一轮按结构化日志修复。

## 交付物

- 库：`libtmx.a`（默认静态；`shared=True` 时为 `libtmx.so` + 已签名）+ 头文件 `tmx.h` + `lib/cmake/tmx/` 包配置
- 许可证随包：`licenses/COPYING`

## 真机失败修复记录（2026-09-29，preflight compile：Signal 9）

- 失败证据：compile 阶段 Signal 9（SIGKILL），stdout/stderr 尾部为空，上游测试计数全 0；即库编译期被 kill，与 OOM/fork 压力一致。
- 根因判断：上游仅 6 个小 C 文件（src/tmx.c 等，无 examples/tests 子目录），单 TU 超限可能性极低；更可能是共享真机瞬时 fork/内存压力。hmbs 虽注入 tools.build:jobs=1，配方内未显式串行，若该 conf 在某环节未生效即出现并行 fork 风暴。
- 本轮改动（最小化，不碰测试口径与优化等级）：`conanfile.py:build()` 与 `test_package/conanfile.py:build()` 均改为 `cmake.build(cli_args=["-j1"])`，显式串行封顶峰值压力；库源码、编译选项、测试断言均不变。
- 待 HMBS 真机预检验证（Signal 9 轮）。

## 真机失败修复记录（2026-09-29，preflight compile：test_package CMAKE_C_COMPILER 校验失败）

- 失败证据：主包工具链已打补丁并进入 build，但 `tmx/1.10.1 (test package)` 在 `CMakeLists.txt:2 (project)` 报 `The CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 后 `-- Configuring incomplete, errors occurred!`（`test package: Error in build() method, line 24 cmake.configure()`）。
- 根因判断：主配方上一轮的 `_compiler_executable()+_patch_cmake_toolchain_compilers()` 只覆盖了库 generate；test_package 仍用声明式 generators，其工具链文件原样烘焙了 profile 钉死的绝对路径，在该路径缺失的 worker 上 project() 自检直接失败。`System is unknown to cmake` 仅为警告级。
- 本轮改动（test_package/conanfile.py，仅换编译器可执行文件，不改标志与测试口径）：generators 收敛为 VirtualRunEnv，新增与主配方同逻辑的 helpers，并以显式 generate() 手工生成 CMakeDeps+CMakeToolchain，OHOS 下把解析结果同时写入 tc.cache_variables 并在 tc.generate() 后改写 conan_toolchain.cmake 中的钉死路径。
- 待 HMBS 真机预检验证（test_package 编译器轮）。

## 真机失败修复记录（2026-09-29，preflight evidence：FAIL 11 + 标记计数矛盾）

- 失败证据：test_package 输出 ok 1-10、FAIL 11、ok 12-15（PASSED 14/15），标记却为 discovered:14/passedCount:0（passedCount 被异常分支硬置 0，与日志自相矛盾）；rule4 判 incomplete（新增测试不足 100% 且无 gaps）。
- 根因确认（源码级）：CHECK 11 断言 tmx_errno == E_NOENT，但上游 src/tmx_xml.c 的 parse_xml() 在打不开文件时走 tmx_err(E_UNKN, "xml parser: unable to open %s")，E_NOENT 在该版本源码中从未被设置；期望值本身与上游行为相悖，必失败。另有计数笔误：test_tmx.c 实际 15 个 CHECK（宏定义除外），配方/MANIFEST/notes 均误写 14。
- 本轮改动：test_tmx.c 的缺失文件断言改为 missing==NULL 且 tmx_errno != E_NONE 且 tmx_strerr() != NULL（失败闭环不断言从未出现的码值，桩库仍失败）；全仓 14→15 对齐（conanfile、MANIFEST、notes）；test() 改为把二进制输出重定向到 test_tmx_output.log 后解析唯一 PASSED x/y 汇总行作为 discovered/passedCount 单一来源，失败时附 test_failure gaps（FAIL 行原文）再抛错，不再硬置 passedCount=0。
- 待 HMBS 真机预检验证（期望 PASSED 15/15，双标记一致）。
