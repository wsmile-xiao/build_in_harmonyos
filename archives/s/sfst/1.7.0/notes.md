# sfst 1.7.0 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang/clang++
- 状态: built（待真机 rule4 门禁验证后由 HMBS 统一提交）

## 编译步骤

上游为 CMake 项目（top-level + src/ + python/）。配方流程：

1. `get` 获取 `https://github.com/santhoshtr/sfst/archive/refs/tags/1.7.0.tar.gz`
  （sha256 `e158fb22...`，与 Debian `.orig.tar.gz` 同值，证实为同一上游归档）。
2. 打补丁 `source() replace_in_file guard (no patch file)`：当 `pybind11/CMakeLists.txt`
   不存在时跳过 `add_subdirectory(pybind11/python)`（release tarball 的
   submodule 目录为空，无条件 descent 会报 `no CMakeLists.txt found`）。
3. `CMakeToolchain + CMakeDeps + VirtualBuildEnv` 生成后
   `cmake.configure()` / `cmake.build()` 编译 `libsfst`；`fst-*` 工具仅在
   原生 FLEX+BISON 均可用时由上游自动追加（`src/CMakeLists.txt` 的
   `if(BISON_FOUND AND FLEX_FOUND)` 守卫）。配方不声明任何
   flex/bison/m4 `tool_requires`：强制 conancenter 三件套会触发
   `m4/1.4.19` 源码构建，其 configure 硬编码
   `/data/service/hnp/bin/bash`，在 HMDFS 构建目录下不可执行
   （真机 2026-09-27 报 Error 127，sfst 自身尚未编译即失败）。
   `readline/8.3`（host，有 OHOS 二进制）仍由配方提供。
4. `cmake.install()` 后做 fallback 拷贝：上游仅声明
   `install(TARGETS libsfst RUNTIME ...)`，ELF 下共享库/头文件/工具可能
   遗漏，配方按 `libsfst.so*`、`*.h`、`fst-*` 补齐到 `lib/`、`include/sfst/`、`bin/`。
5. 上游测试证据：`ctest -N`（`Total Tests: 0`）确认零注册；输出
   `HMBS_UPSTREAM_TEST_RESULT`（`status:no_tests`）并落盘
   `build/upstream_test_result.json`，`package()` 转存入 `res/` 供
   `test_package` 重播。
6. `test_package` 构建 `test_sfst`（链接 `sfst::sfst`，调用
   `Alphabet::add_symbol/symbol2code/code2symbol` 与 `Label` 语义，共 2 断言，
   必跑）并在工具存在时运行已安装 `fst-infl -v`（+1 断言）；工具缺失时走
   上游支持的 library-only 形态，以 `gaps` 显式声明而不静默跳过。汇总输出
   `HMBS_TEST_PACKAGE_RESULT`（工具齐全时期望 `discovered:3/passedCount:3`，
   library-only 时 `discovered:2/passedCount:2 + gaps[environment]`，实际以真机为准）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 `add_subdirectory(pybind11)` 在 release tarball 下失败 | GitHub 自动 tarball 不含 submodule 内容，`pybind11/` 为空目录 | 补丁 guard：仅当 `pybind11/CMakeLists.txt` 存在时 descent；C++ 构建不受影响 |
| 2 | 上游无 C++ 可运行测试套件 | `src/` 无 `add_test()`，`python/` 仅 `enable_testing()` 零注册；唯一测试文件针对 pybind11 扩展 | 如实声明 `upstream_tests_exist:false` + 审计，`status:no_tests`，不虚构计数；新增消费者覆盖验证交付物 |
| 3 | 上游 `install()` 疑似漏装 ELF 共享库 | 仅 `RUNTIME DESTINATION`，Linux/OHOS 下 `LIBRARY` 未声明 | `package()` 增加 fallback `copy`（lib/headers/bin），幂等且不掩盖 `cmake.install()` |
| 4 | 真机预检卡在 `m4/1.4.19` 源码构建：`src/configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`（Error 127），sfst 自身未编译 | 配方曾 `tool_requires` flex/bison/m4，无 OHOS 二进制命中时 conan 从源码构建 m4；m4 configure 写死 hnp bash 路径，在 HMDFS 深路径构建目录下不可执行（含 getcwd/chmod 受限）；该失败在外部依赖 recipe 内，本配方无法注入 CONFIG_SHELL 修复 | 删除 flex/bison/m4 `tool_requires`，利用上游 `BISON_FOUND AND FLEX_FOUND` 可选语义：原生有 flex/bison 则全量构建，无则走上游支持的 library-only；`test_package` 的 CLI 检查改为条件式（有则 +1，无则 `gaps[environment]` 声明）。libsfst 本身不需 flex/bison（仅 `fst-compiler.yy`/`.ll` 生成需要），证据见上游 `src/CMakeLists.txt` |
| 5 | 真机 `source()` 报 `get() argument after ** must be a mapping, not list` | `conandata.yml` 的 `sources` 写成单元素列表，而配方用 `get(self, **self.conan_data["sources"])` 要求映射；此前被 m4 失败掩盖 | `sources` 改为 `url/sha256` 映射，URL 与校验值不变 |
| 6 | 真机 `build()` 报补丁应用失败（`source file is different - CMakeLists.txt`） | 补丁 hunk 头写成 `-18,6`，而 1.7.0 尾部实际为 5 行（`add_subdirectory(src)` 起至文件末），上下文长度不匹配 | hunk 头修正为 `-18,5 +18,9`，补丁内容不变 |
| 7 | build() apply_conandata_patches parse failure (extra lines for hunk / Failed to parse patch) | header-only recounts kept fragile patch_ng gate; correct header is -17,6 +17,10 for 22-line upstream file plus mail footer confuses parser | delete patches/ + conandata patches entry, guard in source() via replace_in_file with loud failure and re-verify (no hunk headers); conandata keeps mapping-only sources, manifest patches_applied:[] |
| 8 | 真机 cmake.configure 在 project() 失败：`System is unknown to cmake, create: Platform/HarmonyOS` + `CMAKE_C/CXX_COMPILER: /data/service/hnp/bin/clang(++)` 错误（2026-09-27 预检 compile 阶段） | CMake 无 HarmonyOS 平台模块，CMakeToolchain 默认下发 CMAKE_SYSTEM_NAME=HarmonyOS，vanilla CMake 4.4.3 无法识别，编译器自检连带失败；配方此前未覆盖 E092 平台绕过 | 主包与 test_package 的 generate() 在 os==OHOS 时统一下发 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` + `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（julius/oystr/jwt-cpp/adamstark-audiofile 先例）；test_package 由 generators 属性改为显式 generate() 以便注入（CMakeDeps 保留为 generators）；仅影响 OHOS 配置，Linux 本地行为不变 |

## 源码修改

- `patches/source() replace_in_file guard (no patch file)`：守卫 python 绑定 descent（POSIX 兼容 CMake 条件，无平台宏，PF5 合规）。

## 依赖版本

- `readline/8.3`（host）+ `ncurses/6.6`（静态 readline 的 tools 链接需要 ncursesw 符号，与 readline 自身依赖同版本）
- flex/bison/m4：无 `tool_requires`（原生 PATH 探测；缺失即 library-only，见 #4）

## 验证结果

待 HMBS 真机预检（conan create）返回后如实回填：`ctest -N` 输出、上游 `no_tests` 标记、`test_sfst` 与条件式 `fst-infl -v` 日志、`HMBS_*` 两行标记。

## 注意事项

- 本轮仅完成未提交工作树；严禁 commit/push/建 PR（由 HMBS 在 rule4 通过后统一提交）。
- `fst-*` 工具仅在 FLEX/BISON 均找到时生成；真机 library-only 时 `test_package` 以 `gaps` 显式声明，不算缺依赖（配方侧已无强制工具依赖，上游原生可选语义）。
- Windows 检出说明：本机 `archives/l/libXext` 大小写冲突与 `archives/g/gama` 非法文件名导致工作树常驻脏状态（`M libXext` + `D gama patch`），与本次 sfst 改动无关，不得提交。

| 9 | Round-3: same project() failure persisted after SYSTEM_NAME=Linux (compiler identification is unknown for both C and CXX, build() line 186) | Profile absolute compiler /data/service/hnp/bin/clang(++) not executable in preflight sandbox; cache_variables alone cannot move baked toolchain value (leatherman R18 / zydis class) | Sandbox-first resolve in main + test_package generate(): keep existing profile path when file exists, else PATH lookup (clang/clang++, cc/c++, CC/CXX env); pin CMAKE_C/CXX_COMPILER and rewrite stale absolute path in conan_toolchain.cmake only when old missing and new exists |

| 10 | Round-4: cmake.install fails with file INSTALL cannot find build/Release/src/fst-compiler.h although libsfststatic built OK | Upstream src/CMakeLists.txt lists BISON-generated fst-compiler.h in HEADERS unconditionally, but the file only exists when BISON_FOUND; library-only build (FLEX/BISON/READLINE absent) has no such file so install aborts before fallback copy | source() gains _fix_library_only_install(): whitespace-tolerant split of the HEADERS line into static names plus if(BISON_FOUND) list(APPEND HEADERS ...) guard; no platform macro, tools-enabled behavior unchanged |

| 11 | CI #63222: 原生 FLEX+BISON 存在时 tools 构建被启用，`fst-compiler(-utf8)` 链接字面 `readline` 无 `-L<conan>/lib`，lld 报 `unable to find library -lreadline`；此前真机 library-only 掩盖了该路径 | 上游 `src/CMakeLists.txt` 用 `target_link_libraries(... readline)` 从未使用自带 Findreadline 生成的 `READLINE::READLINE`；且该模块仅凭 `HINTS ${READLINE_ROOT}` 找不到 `include/readline/readline.h` 与 `lib/libreadline.a`（需 `include/`/`lib/` 后缀），故报 `Readline not found` 却仍进 `BISON AND FLEX` 块尝试链接 | `requirements()` 显式追加 `ncurses/6.6`；`generate()` pin `READLINE_INCLUDE_DIR/READLINE_LIBRARY`（探测 `libreadline.a/.so` 实际文件）与 `SFST_NCURSES_LIBS`（`libncursesw/formw/menuw/panelw.a` 绝对路径）；`source()` 新增 `_fix_readline_link()` 将两处 `readline` 改为 `READLINE::READLINE → ${READLINE_LIBRARY} → readline` 三级回退并条件追加 `${SFST_NCURSES_LIBS}`，library-only 与系统 readline 行为不变 |
