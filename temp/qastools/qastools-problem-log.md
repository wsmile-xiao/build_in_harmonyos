# qastools 1.4.0 适配问题日志

> 实时记录：每个问题的现象 / 根因 / 解法 / 验证 / 对同类问题的影响。
> 适用库类：Qt6 CMake 项目 + 非 Qt 第三方库（alsa/udev）混链。

## P1：Qt6LinguistTools 组件在制品仓 qtbase 变体中缺失

- **现象**：CMake configure 阶段 `FIND_PACKAGE(Qt6 REQUIRED COMPONENTS LinguistTools)` 报 `Failed to find required Qt component "LinguistTools"`。
- **根因**：ohpcd 制品仓所有已发布 qtbase 变体（qtbase/6.11.1、qtbase-sql-dbus/6.11.1 等）均未构建 Qt6LinguistTools 模块（lupdate/lrelease 工具链）。
- **解法**：patch 0001 把 i18n 子目录包进 `FIND_PACKAGE(Qt6 QUIET COMPONENTS LinguistTools)` 守卫，缺失时跳过（翻译 .qm 运行时加载，跳过安全，回退英文字符串）。
- **验证**：conan create 全通过，应用正常安装。
- **同类影响**：**高** — 任何依赖 `Qt6 LinguistTools` 的上游 CMake 项目都会命中（如 kde/、qt/ 系大量应用）；翻译若为运行时加载，守卫跳过是通用安全降级。

## P2：Qt6Svg 找不到（多 Qt 包目录 CMAKE_PREFIX_PATH 问题）

- **现象**：`Could NOT find Qt6Svg (missing: Qt6Svg_DIR)`。
- **根因**：Qt6 基础组件在 qtbase-sql-dbus 包，Svg 组件在独立的 qtsvg 包；CMake 默认只从 CMAKE_PREFIX_PATH 找 Qt6Config.cmake，不会自动把 qtsvg 包目录纳入。
- **解法**：conanfile `generate()` 同时把 qtbase 与 qtsvg 包目录拼进 CMAKE_PREFIX_PATH，并显式设置 `Qt6_DIR` / `Qt6Svg_DIR` 缓存变量。
- **验证**：qasmixer/qashctl 链接 Qt6::Svg 成功。
- **同类影响**：**高** — 任何依赖「qtbase + qtXxx 独立包」组合的 CMake 项目（qtsvg、qt5compat、qttools 等）都需同样处理；E438 只覆盖单包场景，此条目是 E438 的扩展（多 Qt 包目录桥接）。

## P3：libudev.h / alsa 头文件在子目录 CMakeLists 不继承

- **现象**：`fatal error: 'libudev.h' file not found`（子目录编译单元）。
- **根因**：qastools 顶层 CMakeLists 的 `INCLUDE_DIRECTORIES` 不向子目录 CMakeLists 传递；子目录的 `INCLUDE_DIRECTORIES` 也只在子目录生效。
- **解法**：patch 0002 在顶层 `PROJECT()` 之后注入 `INCLUDE_DIRECTORIES(${UDEV_INCLUDE_DIRS} ${ALSA_INCLUDE_DIRS})`（由 conanfile 通过 CMake cache 传入绝对路径）。
- **验证**：所有编译单元正常。
- **同类影响**：**高** — 任何「上游 CMake 用 `SET()` 而非 `target_link_libraries()` 管理依赖路径」的项目在 Conan 下都会命中；CMakeDeps 生成的导入 target 不会自动替换裸 `SET()` 变量。

## P4：子目录 `SET(UDEV_LIBRARIES udev)` 覆盖 conanfile 传入的绝对路径

- **现象**：链接阶段 `ld.lld: error: unable to find library -ludev` / `undefined symbol: udev_new`。
- **根因**：qashctl/qasmixer 子目录 CMakeLists 有 `SET(UDEV_LIBRARIES udev)`，把顶层 `-DUDEV_LIBRARIES=<绝对路径>` 覆盖成裸名 `-ludev`；libudev-zero 是静态库，`-ludev` 在 HMDFS 上没有搜索路径。
- **解法**：conanfile 改用 `UDEV_LIBRARIES_CACHE`（绝对路径 libudev.a）；patch 0004/0005 在子目录用 `IF(DEFINED UDEV_LIBRARIES_CACHE)` 守卫重新赋回 `UDEV_LIBRARIES`。
- **验证**：qasmixer/qashctl 链接通过，NEEDED 表正确。
- **同类影响**：**中** — 上游用裸 `SET()` 而非 find_package 的库（老项目常见）在 Conan 下都会命中；解法模式（`_CACHE` 后缀 + 子目录守卫）可迁移。

## P5：musl/libc++ 下 `std::basic_ostringstream` 未隐式包含

- **现象**：`states_db.cpp:64: error: implicit instantiation of undefined template 'std::basic_ostringstream<char>'`。
- **根因**：OHOS 的 libc++ 头文件依赖链比 glibc/libstdc++ 短，`<sstream>` 未被其他已包含的头间接引入。
- **解法**：patch 0003 显式 `#include <sstream>`。
- **验证**：编译通过。
- **同类影响**：**中** — 任何在 glibc 下能编、在 musl 下报 `implicit instantiation`/`undeclared identifier` 的 C++ 项目都需逐一显式补头文件；无法自动化，属 musl 移植常规成本。

## P6：HMDFS 不可执行 conan 缓存中的二进制

- **现象**：test_package 直接 `subprocess.run(.../bin/qasmixer --version)` 报 `PermissionError: [Errno 1] Operation not permitted`。
- **根因**：HMDFS 对 conan 缓存目录中的 ELF 可执行文件不给执行权限（与文件系统属性无关，是平台限制）。
- **解法**：test_package 改为 ELF magic + NEEDED 表静态校验（`readelf -d` 等价），不实际执行 GUI 二进制。
- **验证**：TP-001..006 全 PASS。
- **同类影响**：**高** — 所有 HMDFS 上「conan 缓存中直接执行可执行文件」的 test_package 都会命中；CI 的 L2 smoke（`--version`）走的是安装目录，不受此限制；本地 test_package 应优先用静态断言。
