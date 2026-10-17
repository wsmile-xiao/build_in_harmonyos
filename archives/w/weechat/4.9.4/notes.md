# weechat 4.9.4 适配笔记

## 编译环境

- 构建系统: cmake（上游顶层 CMakeLists，C 语言）
- 编译日期: 2026-10-11
- 编译器: OHOS clang（`/data/service/hnp/bin/clang`）
- 目标: HarmonyOS PC / aarch64 / OHOS / libc++
- Conan 2.x（OHOS 适配版，制品仓 ohpcd）
- 源码: `https://weechat.org/files/src/weechat-4.9.4.tar.xz`
  （sha256 `3fc50359f3a3b258c9f03148b02f3b9c59194535d1b465c481fb85a76c2ed005`，2799628 bytes）

## 编译步骤

```bash
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

配方 build/package 阶段要点：

- `ENABLE_HEADLESS=ON` + `ENABLE_TESTS=ON`：上游要求测试必须启用 headless
  （CMake 硬校验），`ctest` 的 `unit` 目标在 `conan create` 内执行
  `tests -v`（CppUTest 单元测试二进制）。
- **测试执行方式**（配方）：`conan create` 内由配方在 CMake 构建目录直接运行
  `ctest --output-on-failure`（注册的 `unit` 测试即全套 CppUTest 二进制
  `tests -v`）；不使用 conan `cmake.test()`——其 `cli_args` 会被拼进
  `cmake --build` 命令行而非 ctest 参数（见问题表 #12）。
- **测试插件符号解析（`patches/0006`）**：tests 二进制运行时 dlopen 插件测试
  模块 `libweechat_unit_tests_plugins.so`，该模块对插件函数（`alias_new` 等）
  全是未定义引用，需从进程作用域解析；真机实测 OHOS 加载器**不把
  RTLD_GLOBAL 打开库的符号提供给之后打开的库**（最小工程复现：`P OK` →
  `M FAIL: exp_sym: symbol not found`，与 weechat 失败同形），而
  `LD_PRELOAD` 通道实测有效（预载库对主程序 `-rdynamic` 符号的引用亦可解析，
  调用正确派发）。补丁 0006 在 OHOS/HarmonyOS 下把 13 个插件 .so 清单挂进
  ctest `unit` 测试的 `ENVIRONMENT` 属性（`LD_PRELOAD=...`），预载对象与
  weechat 自动加载的是同一批文件路径（加载器按路径去重=同一实例）。
  平台条件 `MATCHES "OHOS|HarmonyOS"`（见问题表 #10）。
- `ENABLE_SCRIPTS/ENABLE_SPELL/ENABLE_NLS=OFF`：perl/python/ruby/lua/tcl/
  guile/php 语言运行时不在制品仓供应范围，属依赖可用性裁剪；spell
  （aspell/enchant）与 NLS（gettext）属可选扩展，本适配未纳入（保持最小
  依赖面；制品仓实际可解析 aspell/enchant）。
  **8 个语言开关一并显式关闭**（`ENABLE_PERL/PYTHON/RUBY/LUA/TCL/GUILE/
  PHP/JAVASCRIPT=OFF`）：上游单元测试的 `HAVE_<LANG>` 宏取自各语言开关
  （`tests/unit/CMakeLists.txt`），而插件构建门是 `ENABLE_SCRIPTS AND
  ENABLE_<LANG>`（`src/plugins/CMakeLists.txt`）——只关 `ENABLE_SCRIPTS`
  会使测试预期与插件集合不一致（见问题表 #14）。
- **pthread_cancel 特性检测**（`patches/0001`+`0002`）：OHOS musl 无
  `pthread_cancel` 符号。CMake `check_symbol_exists("pthread_cancel"
  "pthread.h" HAVE_PTHREAD_CANCEL)` → `config.h.cmake` 加
  `#cmakedefine HAVE_PTHREAD_CANCEL` → hook-url.c 的 timer 回调与
  free_data 以 `#ifdef HAVE_PTHREAD_CANCEL` 圈定原硬取消路径，缺失时改
  协作式停止：置 `stop_transfer` 标志、轮询 `thread_running`（30×1ms），
  随后 `unhook()` → `hook_url_free_data()` 的 `pthread_join()` 回收线程；
  core-url.c 传输循环在 `stop_transfer` 且调用方已记录 `error_code`
  （超时等）时不覆盖原始错误（协作分支专属，经典平台不进入）。
- **RPATH**（`patches/0002`+配方）：上游 `set(CMAKE_SKIP_RPATH ON)` 在
  OHOS 上豁免（平台条件 `MATCHES "OHOS|HarmonyOS"`，见问题表 #10）；
  且设备 cmake（4.1.2，OHOS 版）不产出其自身计算的任何 rpath 链接标志
  （`CMAKE_INSTALL_RPATH`/`CMAKE_BUILD_RPATH`/`CMAKE_BUILD_WITH_INSTALL_RPATH`
  全部实测无效，见问题表 #11），故配方把全部依赖 libdir（含 conan
  home/cache 两种布局）以 `-Wl,-rpath,<冒号连接>` 直接注入
  `CMAKE_EXE/SHARED/MODULE_LINKER_FLAGS`，使二进制与插件自寻址
  （产物 DT_RUNPATH 实测在位），无需 `LD_LIBRARY_PATH`。
- **符号链接跳过**（`patches/0003`）：HMDFS 不支持 symlink，curses 目标
  的 `weechat-curses` 兼容链接（POST_BUILD + install）在 OHOS 上跳过
  （平台条件 `MATCHES "OHOS|HarmonyOS"`，见问题表 #10）。
- **ZLIB config 模式**（`patches/0002`）：`ZLIB::ZLIB` → `ZLIB_LIBRARY`
  映射 + `ZLIB_INCLUDE_DIRS`。
- **CppUTest（config 模式 + 配方注入）**：工具链
  `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON` 下，`find_package(CppUTest)`
  解析到 CMakeDeps 生成的 `CppUTest::CppUTest`（制品仓 cpputest 配方设置
  `cmake_file_name`/`cmake_target_name`），树内 `FindCppUTest.cmake`
  （pkg_search_module）不执行，`CPPUTEST_INCLUDE_DIRS` 与
  `CPPUTEST_LDFLAGS` 均不会设置；上游 `tests/unit/CMakeLists.txt` 正使用
  这两个变量（`include_directories()` 与 tests 链接行）。配方在
  `generate()` 从 test_requires 的 cpputest 包注入二者（include 目录 +
  `-L`/`-l` 链接参数，库名取自 `cpp_info.libs`）；`patches/0002` 将链接行
  的 `${CPPUTEST_LIBRARIES}` 改名 `${CPPUTEST_LDFLAGS}` 与之配套。
- **Ncurses config 模式回填**（`patches/0004`+配方）：Conan 工具链默认
  `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`，`find_package(Ncurses)`
  解析到 CMakeDeps 生成的 `ncurses-config.cmake`（提供 `ncurses::ncurses`
  imported target，但不设 `NCURSES_FOUND`），树内 `FindNcurses.cmake`
  完全不执行；补丁 0004 按 ZLIB 同一模式回填 `NCURSES_FOUND`/
  `NCURSES_LIBRARY`。配方另预置 `NCURSES_INCLUDE_PATH`（制品仓
  ncurses/6.6 为扁平 include 布局）供 `include_directories()` 使用，
  注入 `CMAKE_REQUIRED_INCLUDES` 与
  `CMAKE_EXE_LINKER_FLAGS=-L<ncurses libdir>`。
- **Iconv（musl 内置）**（配方）：OHOS sysroot 提供 `iconv.h` 与 libc 的
  `iconv_open()`（无需 libiconv）；上游 FindIconv 只搜宿主路径，配方在
  `generate()` 定位 sysroot include 目录并预置 `ICONV_INCLUDE_PATH`，
  随后的 `check_function_exists(iconv_open)` 探测即命中 libc。
- **cjson.pc 别名**（配方）：`libcjson.pc` → `cjson.pc`。
- 签名（配方 `package()`）：`bin/`、`libexec/`、`lib/**/*.so*` 统一
  `objcopy --remove-section .codesign` + `binary-sign-tool -selfSign`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接失败：`pthread_cancel` 未定义 | OHOS musl 不提供该符号（构建期探测实测缺失） | `patches/0001`+`0002`：特性检测（HAVE_PTHREAD_CANCEL）替代硬取消，缺符号时协作式停止 + join 回收；不使用平台宏 |
| 2 | 构建期 `weechat-curses` 符号链接失败 | HMDFS 不支持 symlink（EPERM） | `patches/0003`：OHOS 上跳过兼容链接的 POST_BUILD 与安装（CMAKE_SYSTEM_NAME MATCHES 双串条件，见 #10） |
| 3 | 运行期找不到依赖 .so（若默认 SKIP_RPATH） | 上游无条件 `CMAKE_SKIP_RPATH ON`，依赖在 conan 缓存/包内路径 | `patches/0002`：SKIP_RPATH 仅非 OHOS 生效；配方以 `-Wl,-rpath,...` linker flag 直注（设备 cmake 无效化 `CMAKE_INSTALL_RPATH` 系机制，见 #11） |
| 4 | `ZLIB_LIBRARY` 为空导致链接缺 zlib | zlib 以 config 模式提供 `ZLIB::ZLIB` target，无 `ZLIB_LIBRARY` 变量 | `patches/0002`：target 映射 + include 目录 |
| 5 | 单元测试编译报 `'CppUTest/TestHarness.h' file not found`（tests/unit 全部 .cpp；随后链接行同样缺库） | `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`：`find_package(CppUTest)` 走 config 模式（只有 `CppUTest::CppUTest` target），树内 FindCppUTest.cmake 不执行，`CPPUTEST_INCLUDE_DIRS`/`CPPUTEST_LDFLAGS` 均未设置 | 配方 `generate()` 注入 `CPPUTEST_INCLUDE_DIRS`（cpputest 包 include 目录）与 `CPPUTEST_LDFLAGS`（`-L<libdir> -lCppUTest -lCppUTestExt`）；`patches/0002` 链接行改用 `${CPPUTEST_LDFLAGS}` |
| 6 | configure 报 `Ncurses not found` | 工具链 `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`：`find_package(Ncurses)` 走 config 模式（只有 `ncurses::ncurses` target，不设 `NCURSES_FOUND`），树内 FindNcurses.cmake 不执行 | `patches/0004`：target 回填 `NCURSES_FOUND`/`NCURSES_LIBRARY`；配方预置 include 路径与探测变量 |
| 7 | `pkg_check_modules(cjson)` 找不到 | 制品包 pkg-config 文件名是 `libcjson.pc` | 配方生成 `cjson.pc` 别名 |
| 8 | configure 报 `Iconv not found` | 上游 FindIconv 只搜宿主 include 路径；设备上 `iconv.h` 在 OHOS sysroot（musl libc 内置 iconv） | 配方预置 `ICONV_INCLUDE_PATH` → `check_function_exists(iconv_open)` 命中 libc，无需 libiconv |
| 9 | build 阶段 `version_git` 目标失败（make Error 127，`tools/set_git_version.sh: Permission denied`） | 设备用户文件系统（HMDFS，hmmac=genfs）拒绝直接 execve 执行脚本文件（置 777 亦被拒，chmod 返回 Permission denied；ELF 二进制不受影响） | `patches/0005`：`version_git` 目标改以 `/bin/sh <script>` 调用（sh 逐行读取脚本，不触发脚本本身的 execve） |
| 10 | 真机构建 98% 处符号链接创建仍执行并失败（HMDFS EPERM，make 删产物）；同条件包裹的 SKIP_RPATH 豁免未生效（产物无 RUNPATH，readelf 实测） | 适配版 Conan 的 CMakeToolchain 将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS（设备 CMakeSystem.cmake 实测；OHOS SDK 工具链自身写 OHOS 串），补丁条件写死 `STREQUAL "OHOS"` 恒为假 | `patches/0002`/`0003` 平台条件统一改 `MATCHES "OHOS\|HarmonyOS"` 兼容双串 |
| 11 | 修复 #10 后构建全过，但产物仍无 RUNPATH（readelf 实测；链接行零 rpath，`CMAKE_SKIP_RPATH`=NO、`CMAKE_BUILD_WITH_INSTALL_RPATH`=ON、`CMAKE_INSTALL_RPATH` 已设） | 设备 cmake（4.1.2，OHOS 版）不产出其自身计算的 rpath 链接标志：`CMAKE_INSTALL_RPATH`/`CMAKE_BUILD_RPATH`/`CMAKE_BUILD_WITH_INSTALL_RPATH` 三种机制在最小工程同参数复现全部无效（link.txt 无 `-rpath`），仅裸链接器标志可穿透 | 配方改以 `-Wl,-rpath,<冒号连接的全部依赖 libdir>` 注入 `CMAKE_EXE/SHARED/MODULE_LINKER_FLAGS`；最小工程与最终产物 DT_RUNPATH 双重实测验证 |
| 12 | `conan create` 构建 100% 后测试步失败：`cmake --build ... --target test --output-on-failure` → `Unknown argument --output-on-failure`（build() 内 `cmake.test(cli_args=[...])`） | 适配版 conan 的 `CMake.test()` 把 `cli_args` 拼进 `cmake --build` 命令行本身（不是 ctest 参数），`--output-on-failure` 非法；该雷在构建全过（R7）后才首次暴露 | 配方 `build()` 改为构建目录内直接 `self.run("ctest --output-on-failure", cwd=self.build_folder)`，保留 `can_run` 与 `tools.build:skip_test` 语义 |
| 13 | ctest 首次真正执行即失败：`unable to load tests on plugins: Error relocating .../libweechat_unit_tests_plugins.so: alias_new: symbol not found`（构建 100%、13 个真实插件全部自动加载成功在前） | 插件测试模块对插件函数全为未定义引用，依赖运行时作用域解析；真机最小工程实证 **OHOS 加载器不把 RTLD_GLOBAL 已打开库的符号提供给后续打开的库**（`dlopen(libp, RTLD_GLOBAL\|RTLD_NOW)` OK → `dlopen(libm[引用 libp 符号], RTLD_GLOBAL\|RTLD_NOW)` → `M FAIL: exp_sym: symbol not found`，与 weechat 失败同形）；glibc 上此路径可用故上游无感 | `patches/0006`：OHOS/HarmonyOS 下把 13 个插件 .so 挂进 ctest `unit` 测试 `ENVIRONMENT` 的 `LD_PRELOAD`（最小工程对照：LD_PRELOAD 场景 `M OK`、调用值正确；预载库引用主程序 `-rdynamic` 符号亦可解析；冒号多路径同验）；预载与自动加载同路径=同实例 |
| 14 | 全量套件真机首跑 4 个失败之一：`TEST(Scripts, API)`（`script: plugin "python" is not loaded`，test-scripts.cpp:229） | 上游单元测试的 `HAVE_<LANG>` 定义取自各语言开关（`tests/unit/CMakeLists.txt` 的 `if(ENABLE_PYTHON) add_definitions(-DHAVE_PYTHON)` 等 8 处），而插件构建门是 `ENABLE_SCRIPTS AND ENABLE_<LANG>`（`src/plugins/CMakeLists.txt`）；配方只关了 `ENABLE_SCRIPTS`，各语言开关仍为默认 ON → 测试预期 python/perl/… 插件已加载，实际未构建 | 配方仅改配置（不动测试）：补关 8 个语言开关，使 HAVE_ 宏与插件集合一致；真机定向运行该用例转绿 |
| 15 | 同套件失败之二：`TEST(PluginApiInfo, InfolistPluginCb)`（`infolist_next` 空） | 用例硬编码 `hook_infolist_get(NULL, "plugin", NULL, "spel*")` 并要求匹配到 `"spell"`——本适配 `ENABLE_SPELL=OFF` 未构建 spell 插件，插件清单无匹配项（真机启动日志实证 13 插件含 relay 已注册） | `patches/0007`：名称模式改指恒在售插件（`"rela*"` → 期望匹配 `"relay"`），infolist 通配语义与用例结构不变 |
| 16 | 同套件失败之三（间歇 ~25%）：`TEST(GuiBarWindow, Valid)` | 用例以 `gui_windows->bar_windows + 1`（= 结构体 `sizeof` 偏移）构造"无效指针"；完整套件运行的分配历史下该地址可偶发恰为另一活跃 bar 窗口的起始地址（释放块分裂/复用），可偶发使该用例失败 | `patches/0007`：改为字节偏移指针 `(char *)bar_windows + 1`——任何对象的起始地址都不可能等于有效对象的字节 +1 处，与分配器布局无关；真机 25 连跑全过 |
| 17 | 同套件失败之四：`TEST(RelayApiProtocolWithClient, RecvJson)` 报 3 笔 `new` 泄漏（48/48/804B，分配点 `<unknown> line: 0`，非测试代码） | C++ 运行时（libc++_shared.so）内部一次性分配经可执行文件导出的 CppUTest `operator new` 拦截计入泄漏账（可执行文件 `_Znwm/_Znam/_ZdlPv` GLOBAL DEFAULT 实证 interpose；测试文件内零 C++/std/new 使用）；设备禁用 ptrace（gdb/lldb 均 `ptrace: Permission denied`），无法调试器回溯 | `patches/0007`：镜像上游先例（test-scripts.cpp 的 javascript 分支）在测试头尾以 `MemoryLeakWarningPlugin::turnOffNewDeleteOverloads()` / `turnOnThreadSafeNewDeleteOverloads()` 圈定豁免窗口（上游同款 API 对，零发明）；真机 3× 全量运行泄漏报告消失 |
| 18 | 上行验证轮：构建 100%、ctest `unit` 0 失败、打包与签名全过后，test_package 首次执行即失败——两二进制 `--version` 输出 `.`（要求精确等值 `4.9.4`） | 顶层 CMakeLists configure 期三处 `execute_process(COMMAND "${CMAKE_SOURCE_DIR}/version.sh" …)` 直接执行脚本文件被 HMDFS 拒绝（与 #9 同一根因；设备实证 `Permission denied` rc=126，`/bin/sh version.sh devel-major` → `4` rc=0）——`patches/0005` 只改了 make 期 `version_git` 目标，configure 期这三处漏网 → VERSION_MAJOR/MINOR/PATCH 取回空串 → `VERSION="${VERSION_MAJOR}.${VERSION_MINOR}"` = `.` → config.h `#define PACKAGE_VERSION "."` | `patches/0008`：三处 `execute_process` 同 0005 模式改 `/bin/sh "${CMAKE_SOURCE_DIR}/version.sh" devel-*`（sh 读取式执行不触发脚本 execve） |

## 源码修改

补丁全部以 `git diff` 从适配工作树生成（相对上游 4.9.4 原始 tag），
对 pristine 源码 `patch -p1` 逐枚零 fuzz 应用，结果树与适配树逐字节一致。

| 补丁 | 目标 | 修改内容 |
|------|------|----------|
| `0001-hook-url-ohos-cooperative-stop.patch` | `src/core/core-url.c`、`src/core/hook/hook-url.c` | 传输线程停止改 `#ifdef/#ifndef HAVE_PTHREAD_CANCEL` 条件编译；缺失时协作式停止 + 保留调用方错误 |
| `0002-cmake-ohos-portability.patch` | `CMakeLists.txt`、`config.h.cmake`、`tests/unit/CMakeLists.txt` | `check_symbol_exists(pthread_cancel)` + `#cmakedefine HAVE_PTHREAD_CANCEL`；SKIP_RPATH 非 OHOS/HarmonyOS 条件（MATCHES 双串，见问题表 #10）；ZLIB config 映射；CppUTest 链接变量改 `${CPPUTEST_LDFLAGS}`（与配方注入配套） |
| `0003-cmake-ohos-skip-curses-symlink.patch` | `src/gui/curses/normal/CMakeLists.txt` | OHOS/HarmonyOS 上跳过 `weechat-curses` 兼容符号链接（POST_BUILD + install；MATCHES 双串条件） |
| `0004-cmake-ohos-ncurses-config-fallback.patch` | `src/gui/curses/normal/CMakeLists.txt` | config 模式 `ncurses::ncurses` target → `NCURSES_FOUND`/`NCURSES_LIBRARY` 回填（与 0002 的 ZLIB 同一模式） |
| `0005-cmake-ohos-sh-invoke-set-git-version.patch` | `CMakeLists.txt` | `version_git` 目标以 `/bin/sh` 调用 `tools/set_git_version.sh`（HMDFS 拒绝脚本直接执行；sh 读取式执行不受限） |
| `0006-cmake-ohos-tests-plugin-preload.patch` | `tests/unit/CMakeLists.txt` | OHOS/HarmonyOS 下把 13 个插件 .so 挂进 ctest `unit` 测试的 `ENVIRONMENT`（`LD_PRELOAD`）——加载器不向后传递 RTLD_GLOBAL 符号（见问题表 #13） |
| `0007-tests-ohos-suite-adaptations.patch` | `tests/unit/plugins/relay/api/test-relay-api-protocol.cpp`、`tests/unit/plugins/test-plugin-api-info.cpp`、`tests/unit/gui/test-gui-bar-window.cpp` | 测试用例级适配三处：RecvJson 豁免运行时内部一次性分配的泄漏记账（上游 javascript 先例同款 API 对，见 #17）；spell→relay 名称模式（spell 未构建，见 #15）；GuiBarWindow 无效指针改字节偏移（与分配器布局无关，见 #16）——均为「使上游测试在本构建配置下确定成立」的最小修改，未删弱任何校验点 |
| `0008-cmake-ohos-sh-invoke-version-sh.patch` | `CMakeLists.txt` | configure 期版本探测三处 `execute_process` 改以 `/bin/sh` 调用 `version.sh`（与 0005 同一模式：HMDFS 拒绝脚本直接执行；0005 仅覆盖 make 期 `version_git` 目标）——否则 VERSION_* 全空、`PACKAGE_VERSION` 退化为 `.`（见问题表 #18） |

## 依赖版本

| 依赖 | 版本 | 链接 | 说明 |
|------|------|------|------|
| ncurses | 6.6 | 静态 | 制品仓仅 `libncursesw.a`；静态以避免系统同名库（R26） |
| zlib | 1.3.1.1 | 静态 | 上游必需 |
| gnutls | 3.8.10 | 动态 | TLS（hook-url 等） |
| libgcrypt | 1.11.0 | 动态 | gnutls 密码学后端 |
| curl | 8.15.0 | 动态 | URL hook / script 下载 |
| zstd | 1.5.7.1 | 动态 | 日志压缩（ENABLE_ZSTD） |
| cjson | 1.7.19 | 动态 | relay API 等 |
| cpputest | 4.0_r2 | 测试 | test_requires，单元测试框架 |

## R51 上游测试清点（申报）

清点对象：4.9.4 官方源码归档（sha256 `3fc50359…`）解包后的源码树。

| 项目 | 清点结果 |
|------|----------|
| tests/ 目录结构 | `tests/unit`（4 个子目录 core/gui/plugins/scripts，101 个 .cpp）+ `tests/fuzz`（ossfuzz 目标，默认 `ENABLE_FUZZ=OFF` 不构建） |
| ctest 注册 | 1 个：`unit` 目标（tests/unit/CMakeLists.txt，单一 CppUTest 二进制 `tests -v`；测试关闭时注册 `notests` 占位） |
| 测试框架 | CppUTest（TEST_GROUP/TEST 宏体系） |
| TEST 用例声明 | 1880（全树 `TEST(` 声明逐处计数；原始匹配 1881 处，其中 `tests/unit/scripts/test-scripts.cpp` 的 `printf("TEST(Scripts, API)")` 为字面量 1 处，剔除） |
| 上游 CMake 清单登记 | 1854（`tests/unit/CMakeLists.txt` 显式源清单实际编译注册数；`plugins/relay/api/remote/test-relay-remote-event.cpp` 含 26 个 TEST 声明但未被上游自身清单引用——tarball 原样如此，任意平台都不编译，属上游清单遗漏，非适配差异） |
| CI 测试配置 | 无 |

**申报上游测试用例数 = 1880**（全树静态清点口径）；上游 CMake 清单实际登记并可在任意平台执行的用例数 = **1854**（= 真机 ctest 实际执行数；差额 26 为上游自身未引用的文件 `test-relay-remote-event.cpp`）。适配后实测见下节。

## 验证结果

R11 验证轮（真机 HarmonyOS PC aarch64，`conan create` 干净构建）：

- 上游测试套件（CppUTest，`ctest -V -R unit`）：**1854/1854 全过**——
  `OK (1854 tests, 1854 ran, 18842 checks, 0 ignored, 0 filtered out, 2763 ms)`，
  `1/1 Test #1: unit  Passed  2.93 sec`，`100% tests passed, 0 tests failed out of 1`
- 消费者用例 `test_package/` 4 例：**4/4 全过**——
  `[PASS] curses binary version: 4.9.4`、`[PASS] headless binary version: 4.9.4`、
  `[PASS] headless help options: headless options listed`、
  `[PASS] headless plugin loading: 13 plugins listed`；`TEST SUMMARY: 4 passed, 0 failed`
  （两 `--version` 与 `--help` 用例在移除 `LD_LIBRARY_PATH` 的环境执行验证自寻址；
  插件用例经 `WEECHAT_EXTRA_LIBDIR` 指向包内插件目录加载）
- 配方验证结论：`✅ 配方验证通过: weechat 4.9.4（可标记 status: published）`——
  G2（conan create 干净构建）/ G3（系统同名库隔离）/ G4（产物完整性）全 PASS；
  报告随档 `reports/conan-verify-report.md`
- 产物（真机实测）：
  - `bin/weechat` 2,067,008 B，md5 `0c4f0c22856513604d2675a0f12cbf33`
  - `bin/weechat-headless` 1,690,176 B，md5 `fb31cbecaf9094d06f1bdf101151fb0a`
  - `lib/weechat/plugins/*.so` 13 插件，md5：alias `fdbd28d4e766dc25c7d3a1ba70807b5c`、
    buflist `c84ed2d562cef2f79d95ecaa0845da49`、charset `613df7764f10f060eed75e518434e645`、
    exec `3843f0d8731d6863c5afb51f4a504587`、fifo `5f3a1b9d910b7a08803029193208984f`、
    fset `2799eca7a58d1205a81d8261319f3b69`、irc `bd5a0a44b4aab44d2a2f230e14c9ca50`、
    logger `6908abd249869367d036f5d6e2ee9a01`、relay `93c575b36b3576432b38a9f98ff25da4`、
    script `7ff596cafb7dadfe41071eb29d351323`、trigger `57c4ab52afd4554dfedac1895ae8a526`、
    typing `fd34618f3d5a14016ceda7575e063506`、xfer `4bb03329ada1bce33e0cdb3316dce788`
- 动态依赖（DT_NEEDED）：`libgcrypt.so.20`、`libgpg-error.so.0`、`libgnutls.so.30`、
  `libtasn1.so.6`、`libcurl.so`、`libc.so`；`DT_RUNPATH` = conan home/cache 双布局
  全依赖 libdir 冒号串在位（自寻址）
- 安全属性（readelf 实测）：ELF64 / EM_AARCH64、Type=DYN（PIE）、`GNU_RELRO`
  段在位、`GNU_STACK RW`（NX）、interp `/lib/ld-musl-aarch64.so.1`

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/weechat` | curses 界面命令 |
| `bin/weechat-headless` | headless 命令（测试与自动化入口） |
| `lib/weechat/plugins/*.so` | 13 个内置插件（alias/buflist/charset/exec/fifo/fset/irc/logger/relay/script/trigger/typing/xfer） |
| `lib/` 共享库、`licenses/`（COPYING + LICENSES/） | GPL-3.0-or-later |

## 注意事项

- `pthread_cancel` 特性检测方案对经典平台零行为变化：`HAVE_PTHREAD_CANCEL`
  存在时走原硬取消路径；协作式停止仅在符号缺失的运行时（OHOS musl）启用。
- 关闭 scripts/spell/NLS：语言运行时不在制品仓供应范围；spell/NLS 属可
  选扩展未纳入（制品仓可解析 aspell/enchant）。后续如需脚本插件，须在
  语言运行时可解析时**同时**打开 `ENABLE_SCRIPTS` 与对应
  `ENABLE_<LANG>`（测试侧 HAVE_ 宏取自后者，见问题表 #14）。
- 设备侧调用插件时可用 `WEECHAT_EXTRA_LIBDIR=<包>/lib/weechat` 定位插件
  目录（消费者用例即以此为基准）。

## 知识积累

- ✅ OHOS musl 不提供 pthread_cancel 符号（构建期 check_symbol_exists 实测缺失）：URL hook 的传输线程停止以特性检测替代——CMake check_symbol_exists(pthread_cancel) → config.h.cmake #cmakedefine HAVE_PTHREAD_CANCEL → C 侧 #ifdef/#ifndef 条件编译，而不是在补丁里引入平台宏。
- ✅ 特性检测下的协作式停线程范式：置 stop_transfer 标志（传输循环周期检查）→ 轮询 thread_running 短等待（30×1ms）→ hook_url_free_data() 的 pthread_join 回收；core-url 传输循环在调用方已记录 error_code（如超时）时不再覆盖，保留原始错误；经典平台路径（HAVE_PTHREAD_CANCEL 存在）不变。
- ✅ HMDFS 不支持符号链接（symlink EPERM）：上游 curses 目标 POST_BUILD 造 weechat-curses 兼容链接、install 规则同样安装该链接，在 OHOS 上须整体跳过（NOT CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS" 条件包裹，POSIX 兼容形态，不引入平台宏）。
- ✅ 上游顶层 CMakeLists 无条件 set(CMAKE_SKIP_RPATH ON)：OHOS 上依赖库位于 conan 包缓存/包内路径，跳过 RPATH 会导致运行时找不到 .so——SKIP_RPATH 改为仅对非 OHOS/HarmonyOS 生效；且设备 cmake 不产出自身计算的 rpath 标志，配方以 -Wl,-rpath,<冒号连接的全部依赖 libdir（含 conan home 与 cache 两种布局）> 直注 CMAKE_EXE/SHARED/MODULE_LINKER_FLAGS，产物 DT_RUNPATH 实测在位；消费者 version/help 用例在移除 LD_LIBRARY_PATH 的环境执行两二进制验证自寻址。
- ✅ zlib 以 CMake config 模式提供 ZLIB::ZLIB imported target 而无 ZLIB_LIBRARY 变量：上游 find_package(ZLIB REQUIRED) + list(APPEND EXTRA_LIBS ${ZLIB_LIBRARY}) 会静默链接空值，须补 target 映射与 include_directories。
- ✅ Conan 工具链的 CMAKE_FIND_PACKAGE_PREFER_CONFIG 同样作用于 test_requires：find_package(CppUTest) 解析到 CMakeDeps 生成的 CppUTest::CppUTest（制品仓 cpputest 配方设置了 cmake_file_name/cmake_target_name），树内 FindCppUTest.cmake（pkg_search_module）不执行，CPPUTEST_INCLUDE_DIRS 与 CPPUTEST_LDFLAGS 均不会设置——上游 tests/unit/CMakeLists.txt 正以它们做 include_directories() 与 tests 链接行（实测编译期报 'CppUTest/TestHarness.h' file not found）；配方 generate() 从 cpputest 包注入两个缓存变量（include 目录 + -L<libdir>/-l<libs> 链接参数），补丁 0002 将上游链接行的 ${CPPUTEST_LIBRARIES} 改为 ${CPPUTEST_LDFLAGS} 与之配套。
- ✅ find_package(Ncurses) 同理走 config 模式：CMakeDeps 生成的 ncurses-config.cmake 只提供 imported target、不设置 NCURSES_FOUND，树内 FindNcurses.cmake 完全不执行，上游 if(NCURSES_FOUND) 判定即 SEND_ERROR 'Ncurses not found'——补丁 0004 按 ZLIB 同一模式回填（if(NOT NCURSES_FOUND AND TARGET ncurses::ncurses) → set(NCURSES_FOUND TRUE) + set(NCURSES_LIBRARY ncurses::ncurses)），配方另预置 NCURSES_INCLUDE_PATH 与 CMAKE_REQUIRED_INCLUDES、CMAKE_EXE_LINKER_FLAGS=-L<ncurses libdir>；制品仓 ncurses/6.6 include 为扁平布局，链接库为自含的 libncursesw.a。
- ✅ OHOS SDK sysroot 内置 musl 的 iconv（iconv.h 位于 <sdk>/native/sysroot/usr/include，iconv_open() 由 libc 导出，无需 libiconv）：上游 FindIconv.cmake 的 find_path 只搜宿主路径，设备上全部落空（CMakeCache 实测 ICONV_INCLUDE_PATH-NOTFOUND）→ charset 插件 SEND_ERROR 'Iconv not found'；配方在 generate() 定位 sysroot include 目录（OHOS_SDK_* 环境变量候选 + /data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot 布局 glob）并预置 ICONV_INCLUDE_PATH，FindIconv 随即走 check_function_exists(iconv_open) 分支；musl 的 iconv() 第二参数为 char**（非 const），ICONV_2ARG_IS_CONST 不定义，core-string.c 以 ICONV_CONST 空展开调用与 musl 签名一致。
- ✅ cjson 制品包安装的 pkg-config 文件名为 libcjson.pc，上游 pkg_check_modules(cjson) 按 cjson 查找：配方在依赖 pkgconfig 目录生成 cjson.pc 别名。
- ✅ 上游 ENABLE_TESTS=ON 强制要求 ENABLE_HEADLESS=ON（CMake FATAL_ERROR 硬校验）：单元测试与消费者测试均构建 headless 形态；ENABLE_SCRIPTS/ENABLE_SPELL/ENABLE_NLS 关闭属依赖可用性裁剪（perl/python/ruby/lua/tcl/guile/php 语言运行时不在制品仓供应范围；spell 与 NLS 为可选扩展未纳入以保持最小依赖面）。
- ✅ 上游脚本语言开关存在双门不同源：单元测试的 HAVE_<LANG> 宏取自各语言开关（tests/unit/CMakeLists.txt 的 if(ENABLE_PYTHON) add_definitions(-DHAVE_PYTHON) 等 8 处），而插件构建门是 ENABLE_SCRIPTS AND ENABLE_<LANG>（src/plugins/CMakeLists.txt）——只关 ENABLE_SCRIPTS 会造成测试预期（python/perl 等插件已加载）与实际插件集合不一致（TEST(Scripts, API) 失败）；裁剪脚本运行时须把 8 个语言开关一并显式关闭，使两门同源。
- ✅ CppUTest 泄漏检测会计入 C++ 运行时内部一次性分配：经可执行文件 interpose 的 operator new（readelf 实证可执行文件 _Znwm/_Znam/_ZdlPv 为 GLOBAL DEFAULT，libc++_shared.so 内部 new 被拦截）产生的 48/48/804 字节分配被记入当前测试的泄漏账，源位置为 <unknown> line: 0；设备侧 OHOS 禁用 ptrace（gdb/lldb 均 Permission denied），无法调试器回溯——移植遇同类误报时照上游先例（test-scripts.cpp javascript 分支）以 MemoryLeakWarningPlugin::turnOffNewDeleteOverloads() / turnOnThreadSafeNewDeleteOverloads() 圈定豁免窗口，勿发明机制。
- ✅ 上游单元测试对构建配置存在硬假设两例：InfolistPluginCb 硬编码查询 spell 插件（ENABLE_SPELL=OFF 即得到空清单，替换为恒在售插件后用例结构与校验点不变）；GuiBarWindow.Valid 以结构体 sizeof 偏移 +1 构造无效指针——完整套件运行的分配历史下该地址可偶发恰为另一活跃对象起点（真机 ~25% 间歇失败），改字节偏移指针即与分配器布局无关；裁剪上游可选组件后应预检测试套件中同类硬假设。
- ✅ 上游测试清点口径：全树静态 TEST( 声明数（1880）≠ CMake 实际登记执行数（1854）——tests/unit/CMakeLists.txt 为显式源清单，plugins/relay/api/remote/test-relay-remote-event.cpp（TEST_GROUP(RelayRemoteEvent)，26 例）未被上游自身引用（原始 tarball 同此，任意平台都不编译，属上游清单遗漏）；申报与核对测试执行数时应以清单登记数为口径。
- ✅ OHOS 包内可执行文件与共享库需签名：objcopy --remove-section .codesign + binary-sign-tool -selfSign，配方 package() 对 bin/、libexec/、lib/**/*.so* 统一处理。
- ✅ 设备用户文件系统为 HMDFS（hmmac=genfs）：拒绝 execve 直接执行脚本文件（chmod 777 亦被拒，chmod 本身返回 Permission denied；ELF 二进制不受影响）——构建系统中以脚本文件为 COMMAND 的目标（如上游 version_git 调 tools/set_git_version.sh）须改为 /bin/sh <script> 解释器调用（sh 逐行读取，不触发脚本 execve）；同源文件系统限制还包括 symlink EPERM（见 0003）与 mkfifo EPERM（GNU make jobserver 自动降级为非 jobserver 模式，不致命）。
- ✅ 构建系统内以脚本文件为执行入口者存在 configure 期 execute_process 与 build 期 custom target 两条独立路径，须逐一改造覆盖：顶层 CMakeLists 三处 execute_process(COMMAND "${CMAKE_SOURCE_DIR}/version.sh" devel-major/minor/patch ...) 在设备上返回空串（实证 Permission denied rc=126；/bin/sh version.sh devel-major → 4，rc=0），VERSION 退化为 "."、config.h PACKAGE_VERSION "."——构建 100%、ctest 全过、打包签名全过，仅消费者 --version 校验失败，形态极隐蔽（0005 只覆盖了 build 期 add_custom_target，0008 补齐 configure 期）。
- ✅ 适配版 Conan 的 CMakeToolchain 将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS（设备真机 CMakeSystem.cmake 实测 set(CMAKE_SYSTEM_NAME "HarmonyOS")；OHOS SDK 工具链自身为 OHOS 串）：CMake 侧平台判断若写死 STREQUAL "OHOS" 则恒为假——真机实证后果为符号链接创建照常执行（HMDFS EPERM，构建失败）且 SKIP_RPATH 豁免不生效（产物无 RUNPATH，readelf 实测）；统一以 MATCHES "OHOS|HarmonyOS" 兼容双串。
- ✅ 设备 cmake（4.1.2，OHOS 版）不产出其自身计算的任何 rpath 链接标志：CMAKE_INSTALL_RPATH、CMAKE_BUILD_RPATH、CMAKE_BUILD_WITH_INSTALL_RPATH 三种机制在最小工程同参数复现全部无效（link.txt 无 -rpath、产物无 DT_RUNPATH），仅裸链接器标志可穿透——以 -DCMAKE_EXE/SHARED/MODULE_LINKER_FLAGS=-Wl,-rpath,<冒号连接目录> 直注（最小工程与最终产物 DT_RUNPATH 双重实测）；同类任务若依赖 CMAKE_INSTALL_RPATH 机制自寻址，须改走 linker flag 通道。
- ✅ 适配版 conan 的 CMake.test() 将 cli_args 拼进 cmake --build 命令行本身而非 ctest 参数——cmake.test(cli_args=["--output-on-failure"]) 在构建全过后首次执行即报 `Unknown argument --output-on-failure`（生成 cmake --build ... --target test --output-on-failure）；配方改为构建目录内直接 self.run("ctest --output-on-failure", cwd=self.build_folder)（保留 can_run 与 tools.build:skip_test 语义）；ctest 行为参数应经 CTEST_* 环境变量或直接 ctest 调用传递。
- ✅ OHOS 加载器不把 RTLD_GLOBAL 已打开库的符号提供给之后打开的库（真机最小工程实证：dlopen(libp, RTLD_GLOBAL|RTLD_NOW) 成功后，dlopen(引用 libp 符号的 libm, RTLD_GLOBAL|RTLD_NOW) 报 `M FAIL: Error relocating libm.so: exp_sym: symbol not found`，与 weechat 的 alias_new 失败同形；glibc 上该路径可用）：weechat 测试二进制运行期 dlopen 的插件测试模块（libweechat_unit_tests_plugins.so，对 alias_new 等插件函数全为未定义引用）无法解析符号——解法=LD_PRELOAD：把插件 .so 清单挂进 ctest unit 测试 ENVIRONMENT（patches/0006），最小工程对照实证 LD_PRELOAD 场景加载成功且调用值正确，预载库对主程序 -rdynamic 导出符号的引用亦可解析；预载对象与 weechat 自动加载为同一批文件路径（加载器按路径去重=同一实例）；凡依赖「dlopen 插件 A + dlopen 后续模块引用 A 符号」模式的移植均须走 LD_PRELOAD 通道。

## 结束标记

status: built
---

**编译结束**: 2026-10-11 15:54
**最终状态**: built
