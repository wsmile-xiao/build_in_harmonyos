# attica5 5.116.0 适配笔记（KDE Frameworks 5 / Qt5）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-22
- 目标平台: HarmonyOS PC (arm64, OHOS 6.0, clang 15, libc++)
- 编译器: clang/clang++ (OHOS 工具链)
- 状态: published
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`

## 依赖
| 依赖 | 版本 | 用途 |
|------|------|------|
| qt5-qtbase | 5.15.2 | Qt5 Core/Network/Test 运行时与 moc/rcc |
| ecm | 6.26.0 | Extra CMake Modules（KDEInstallDirs、ECMGenerateHeaders 等） |

## 编译步骤

1. 源码: `https://download.kde.org/stable/frameworks/5.116/attica-5.116.0.tar.xz`
   sha256 `681107c4dd989999cecd002c58c01ec3af8317bb9da5267809ad465750d21fea`
2. 上游是标准 KF5 CMake 工程: `find_package(ECM 5.116.0 NO_MODULE)` +
   `find_package(Qt5 5.15.2 NO_MODULE REQUIRED Core Network)`，产物 libKF5Attica。
3. `conan create`（干净构建）→ `cmake.configure()` → `cmake.build()` → `ctest`。
   - 配置参数: `QT_MAJOR_VERSION=5`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、
     `BUILD_TESTING=ON`、`BUILD_SHARED_LIBS=ON`、`ATTICA_STATIC_BUILD=OFF`。
   - ctest 运行环境: `QT_QPA_PLATFORM=offscreen`、`HOME=<build>/test-home`、
     `QT_PLUGIN_PATH=<qt5-qtbase>/plugins`。

## 关键适配点（CMakeDeps Qt5 方案）

- **qt5-qtbase 原生 Qt5 cmake config 不可用**: 包内只有分模块 config
  （Qt5CoreConfig / Qt5NetworkConfig / …），没有聚合的 `Qt5Config.cmake`，
  而 attica 上游调用 `find_package(Qt5 … REQUIRED Core Network)`。
  解法（与 quazip/1.4 同款）: `CMakeDeps(self).set_property("qt5-qtbase", "cmake_file_name", "Qt5")`
  → CMakeDeps 在 generators 目录重新生成干净的 `Qt5Config.cmake`，并连带
  Qt5Core/Qt5Network 的分模块 config。
- **ECM_MODULE_PATH**: attica 的根 CMakeLists 依赖
  `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})`。ecm 是 tool_requires（build
  context），CMakeDeps 只把 host context 依赖的 builddir 放进
  `conan_cmakedeps_paths.cmake`；因此手动在 conanfile generate() 里设置
  `ECM_MODULE_PATH=<ecm>/share/ECM/{modules,find-modules,kde-modules}`，
  并把 `<ecm>/share/ECM/cmake` 追加进 `CMAKE_PREFIX_PATH`/`CMAKE_MODULE_PATH`
  （`find_package(ECM 5.116.0 NO_MODULE)` 需要 ECMConfig.cmake 在 config 搜索路径上）。
- **AUTOMOC / AUTORCC**: CMakeDeps 不导出 `Qt5::moc` / `Qt5::rcc` 可执行目标，
  通过 `CMAKE_AUTOMOC_EXECUTABLE=<qt5-qtbase>/bin/moc` 与
  `CMAKE_AUTORCC_EXECUTABLE=<qt5-qtbase>/bin/rcc` 注入。
- **CMakeDeps 与手动路径文件**: 主配方保留 CMakeDeps 生成的
  `conan_cmakedeps_paths.cmake`（追加 ECM 路径），保证 `find_package(Qt5)` 与
  `find_package(ECM)` 都命中。
- **ELF SONAME（W3 CI L5 门禁）**: HarmonyOS 不映射到 Linux CMake 平台，
  `CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG` 未被定义，产物 `.so` 无 DT_SONAME
  （L5 soname gate 报 `libKF5Attica.so 缺少 DT_SONAME`）。参照
  expat/2.8.2.1.1 验证过的模式修复:
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"`
  → 产出无版本号 `libKF5Attica.so` 但带可重定位 SONAME `libKF5Attica.so`，
  L5 门禁通过。

## 源码修改（补丁）

- `tests/projecttest/CMakeLists.txt`:
  `find_package(Qt${QT_MAJOR_VERSION}Widgets … CONFIG REQUIRED)` 在无
  Qt5Widgets 时必挂。改为 `CONFIG QUIET` + `if(NOT Qt…Widgets_FOUND) message(…); return() endif()`
  （qt5-qtbase 不含 Qt5Widgets，projecttest 只是手动 GUI 测试程序，
  跳过不影响 configtest/persontest）。
  补丁由 `ohc-run.py refresh-patch --auto` 生成:
  `patches/0001-tests-projecttest-CMakeLists.txt.patch`。

## 上游测试（CTest）

- 注册的 autotests: configtest、persontest、providertest（autotests/CMakeLists.txt）。
- 执行命令:
  `ctest --test-dir <build_folder> --output-on-failure --no-tests=error -E "^providertest$"`
- **providertest 排除**: 依赖外部 OCS 服务端点，构建沙箱无外网 → `-E` 排除并如实记录。
- 结果: **2/2 通过**（configtest、persontest），详见 `reports/test-report.md`。

## 验证结果

- `ohc-run.py conan-verify attica5 5.116.0`（8 门禁 G0-G4 / L2/L4/L5）全部通过。
- `test_package`: 消费者用 `find_package(Qt5 COMPONENTS Core Network)` +
  `find_package(KF5Attica REQUIRED)` 链接 `KF5::Attica`，调用
  `Attica::Person` / `Attica::Config` 值对象 API 断言往返 → `PASS: Attica value objects OK`（1/1）。

## 注意事项

- KF5 系列后续适配可复用本配方骨架（CMakeDeps Qt5 + ECM_MODULE_PATH +
  AUTOMOC/RCC 注入 + cmake_find_mode=none + builddirs=lib/cmake）。
- `test_package` 必须手工覆盖 `conan_cmakedeps_paths.cmake`（KF 系验证过的
  唯一可靠路径），否则 `find_package(KF5Attica REQUIRED)` 大概率找不到
  `<attica5>/lib/cmake/KF5Attica`。
- R32/R33 已遵守: 配方未用 `os == "Linux"` 判断；编译参数全部来自 Conan
  toolchain/deps，无裸 `${CC}`/`${CFLAGS}`。
---

**编译结束**: 2026-08-22 11:26
**最终状态**: published
