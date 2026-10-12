# weechat 4.9.4 — HarmonyOS PC 适配

WeeChat 是模块化、轻量级的可扩展聊天客户端（curses 终端界面 + headless
两种运行形态）：内置 alias、buflist、charset、exec、fifo、fset、irc、
logger、relay、script、trigger、typing、xfer 共 13 个插件，另外提供
perl/python/ruby/lua/tcl/guile/php 等脚本语言扩展（本归档关闭，见「适配要点」）。
配置全走 `/set` 命令体系，配合 relay 插件可作远程聊天后端。

本归档是上游 4.9.4 在 HarmonyOS PC（aarch64-linux-ohos）上的适配。Conan 包
类型为 application：安装 `bin/` 的 `weechat`（curses）与 `weechat-headless`
两个命令、`lib/weechat/plugins/*.so` 的 13 个插件与配套共享库，因此软件级
目录提供 `commands.json`。

上游地址：https://weechat.org/ （源码
https://weechat.org/files/src/weechat-4.9.4.tar.xz）

## 适配要点

- **pthread_cancel 特性检测**：OHOS musl 不提供 `pthread_cancel` 符号，
  上游 hook-url 的传输线程停止在链接期失败。适配以构建期特性检测替代
  平台宏：CMake `check_symbol_exists(pthread_cancel ...)` →
  `config.h.cmake` 的 `#cmakedefine HAVE_PTHREAD_CANCEL` → C 侧
  `#ifdef/#ifndef HAVE_PTHREAD_CANCEL` 条件编译。符号缺失时以协作式停止
  替代硬取消：置 `stop_transfer` 标志、轮询 `thread_running` 短等待，
  线程随后由 `hook_url_free_data()` 的 `pthread_join()` 回收；传输循环在
  调用方已记录错误（如超时）时不覆盖原始错误。经典平台行为不变
  （`patches/0001` + `patches/0002`）。
- **weechat-curses 兼容符号链接跳过**：HMDFS 不支持符号链接（symlink
  返回 EPERM），curses 目标的后置构建 `weechat-curses` 兼容链接与安装
  规则在 OHOS 上跳过（以 `CMAKE_SYSTEM_NAME` MATCHES 双串条件判断，
  POSIX 兼容形态，`patches/0003`）。
- **平台判断串（适配版 conan 映射）**：适配版 Conan 的 CMakeToolchain 将
  `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`（真机 CMakeSystem.cmake
  实测；OHOS SDK 工具链自身写 `OHOS` 串）。CMake 侧平台条件统一用
  `MATCHES "OHOS|HarmonyOS"` 兼容双串——写死 `STREQUAL "OHOS"` 恒为假，
  真机实证会致符号链接跳过与 SKIP_RPATH 豁免双双失效。
- **version_git 脚本执行**：设备用户文件系统 HMDFS 拒绝脚本文件的直接
  execve（chmod 亦被拒，ELF 二进制不受影响），上游 `version_git` 目标以
  `tools/set_git_version.sh` 为 COMMAND 会失败（make Error 127）。补丁
  `0005` 将该目标改为 `/bin/sh <script>` 解释器调用（sh 逐行读取脚本，
  不触发脚本本身的 execve）。
- **configure 期 version.sh 执行（`patches/0008`）**：同一 HMDFS 限制也命中
  顶层 CMakeLists 的 configure 期版本探测——`execute_process(COMMAND
  version.sh devel-major …)` 三处直接执行脚本被拒后取回空串，
  `PACKAGE_VERSION` 退化为 `.`（构建、单元测试、打包签名全过，仅消费者
  `--version` 校验失败，形态隐蔽）；补丁同 0005 模式改 `/bin/sh` 调用。
  configure 期 execute_process 与 build 期 custom target 是两条独立路径，
  须逐一改造。
- **RPATH 保留（linker flag 直注）**：上游顶层 CMakeLists 无条件
  `set(CMAKE_SKIP_RPATH ON)`；OHOS 上运行时依赖库位于 conan 包缓存/包内
  路径，不可跳过 RPATH。`CMAKE_SKIP_RPATH` 改为仅对非 OHOS/HarmonyOS
  生效（同平台串条件）；且设备 cmake（4.1.2，OHOS 版）不产出其自身计算的
  任何 rpath 链接标志（`CMAKE_INSTALL_RPATH`/`CMAKE_BUILD_RPATH`/
  `CMAKE_BUILD_WITH_INSTALL_RPATH` 最小工程实测全部无效），配方改以
  `-Wl,-rpath,<冒号连接的全部依赖 libdir>` 直注
  `CMAKE_EXE/SHARED/MODULE_LINKER_FLAGS`（含 conan home 与 cache 两种
  布局；产物 DT_RUNPATH 实测在位）。消费者用例显式清除 `LD_LIBRARY_PATH`
  验证自寻址（`patches/0002` + 配方）。
- **测试执行（ctest 直调）**：`conan create` 内由配方在构建目录直接运行
  `ctest --output-on-failure`（注册的 `unit` 测试即全套 CppUTest 二进制
  `tests -v`）；不用 conan `cmake.test()`——其 `cli_args` 会拼进
  `cmake --build` 命令行而非 ctest 参数（真机构建全过后首次执行即报
  `Unknown argument --output-on-failure`）。
- **测试插件符号预载（`patches/0006`）**：tests 二进制运行期 dlopen 插件
  测试模块（`libweechat_unit_tests_plugins.so`），模块对插件函数
  （`alias_new` 等）的未定义引用需从进程作用域解析；真机最小工程实证
  **OHOS 加载器不把 RTLD_GLOBAL 已打开库的符号提供给之后打开的库**
  （glibc 上此路径可用故上游无感），而 `LD_PRELOAD` 通道有效。补丁在
  OHOS/HarmonyOS 下把 13 个插件 .so 清单挂进 ctest `unit` 测试的
  `ENVIRONMENT`（`LD_PRELOAD=...`）；预载对象与 weechat 自动加载为同一批
  文件路径（加载器按路径去重=同一实例）。
- **测试套件适配（`patches/0007`，三处用例级）**：`RecvJson` 以
  `MemoryLeakWarningPlugin::turnOffNewDeleteOverloads()` /
  `turnOnThreadSafeNewDeleteOverloads()`（上游 test-scripts.cpp javascript
  分支同款 API 对）豁免 C++ 运行时内部一次性分配的泄漏记账；
  `InfolistPluginCb` 名称模式改指 relay（spell 插件未构建）；
  `GuiBarWindow.Valid` 无效指针改字节偏移（与分配器布局无关，消除间歇
  失败）。三处均为「使上游测试在本构建配置下确定成立」的最小修改，
  未删弱任何校验点；真机 3× 全量 + 定向验证全过。
- **ZLIB config-mode 兼容**：平台的 zlib 以 config 模式提供 `ZLIB::ZLIB`
  imported target 而不提供 `ZLIB_LIBRARY` 变量，上游
  `find_package(ZLIB REQUIRED)` + `list(APPEND EXTRA_LIBS ${ZLIB_LIBRARY})`
  会链接空值；补 target 映射与 `include_directories(ZLIB_INCLUDE_DIRS)`
  （`patches/0002`）。
- **CppUTest（config 模式 + 配方注入）**：Conan 工具链 config 模式下
  `find_package(CppUTest)` 解析到 CMakeDeps 生成的 `CppUTest::CppUTest`
  （只提供 imported target），树内 `FindCppUTest.cmake` 不执行，
  `CPPUTEST_INCLUDE_DIRS`/`CPPUTEST_LDFLAGS` 均不会设置；上游
  tests/unit/CMakeLists.txt 正使用这两个变量（include 与链接）。配方在
  `generate()` 注入这两个缓存变量（cpputest 包 include 目录与
  `-L`/`-lCppUTest`/`-lCppUTestExt` 链接参数）；`patches/0002` 将链接行
  改用 `${CPPUTEST_LDFLAGS}` 与之配套。
- **Ncurses config 模式回填**：Conan 工具链默认
  `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON`，`find_package(Ncurses)` 解析到
  CMakeDeps 生成的 `ncurses-config.cmake`（提供 `ncurses::ncurses`
  imported target，但不设 `NCURSES_FOUND`），树内 `FindNcurses.cmake`
  不执行；`patches/0004` 按 ZLIB 同一模式回填 `NCURSES_FOUND`/
  `NCURSES_LIBRARY`。配方另预置 `NCURSES_INCLUDE_PATH` 缓存变量（制品仓
  ncurses/6.6 为扁平 include 布局）供 `include_directories()` 使用，并注入
  `CMAKE_REQUIRED_INCLUDES` 与
  `CMAKE_EXE_LINKER_FLAGS=-L<ncurses libdir>`（header probe 与链接探测
  都需要）。
- **Iconv（musl 内置）**：OHOS sysroot 提供 `iconv.h` 与 libc 的
  `iconv_open()`（无需 libiconv）；上游 FindIconv 只搜宿主路径，配方在
  `generate()` 定位 sysroot include 目录并预置 `ICONV_INCLUDE_PATH`，
  随后的 `check_function_exists(iconv_open)` 探测即命中 libc。
- **cJSON pkg-config 别名**：制品仓 cjson 包安装的 pkg-config 文件名为
  `libcjson.pc`，上游 `pkg_check_modules(cjson)` 按 `cjson` 查找；配方
  在依赖的 pkgconfig 目录生成 `cjson.pc` 别名。
- **功能开关**：`ENABLE_HEADLESS=ON`（上游要求开启测试必须启用 headless）、
  `ENABLE_TESTS=ON`；`ENABLE_SCRIPTS=OFF` 且 8 个语言开关显式 OFF
  （`ENABLE_PERL/PYTHON/RUBY/LUA/TCL/GUILE/PHP/JAVASCRIPT`——上游单元
  测试的 `HAVE_<LANG>` 宏取自这些开关，仅关 `ENABLE_SCRIPTS` 会使测试
  预期与插件集合不一致；语言运行时不在制品仓供应范围）、
  `ENABLE_SPELL=OFF`、`ENABLE_NLS=OFF`（可选扩展未纳入，保持最小依赖面）。
- **同名库隔离（R26）**：ncurses 静态链接（避免运行时解析到系统同名
  库）；zstd 采用制品仓动态库。

## 依赖

- `ncurses/6.6`（静态）、`zlib/1.3.1.1`、`gnutls/3.8.10`、
  `libgcrypt/1.11.0`、`curl/8.15.0`、`zstd/1.5.7.1`（动态）、
  `cjson/1.7.19`
- 测试依赖：`cpputest/4.0_r2`（test_requires）

## 构建与验证

- `conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`
- 上游测试套件：`tests/unit`（CppUTest，ctest `unit` 目标；上游 CMake
  清单登记 1854 例 = 实际执行口径，另有 26 例位于上游自身未引用的文件，
  见 `4.9.4/notes.md`），真机 `conan create` 内自动执行
- 消费者用例：`4.9.4/test_package/`（4 例：curses/headless
  `--version`、headless `--help` 选项、13 插件加载）
