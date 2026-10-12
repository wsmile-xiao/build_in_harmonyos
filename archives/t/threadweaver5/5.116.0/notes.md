# threadweaver5 5.116.0 适配笔记（KDE Frameworks 5 / Qt5）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-06
- 目标平台: HarmonyOS PC (arm64, OHOS 6.0, clang 15, libc++)
- 编译器: clang/clang++（OHOS 工具链）
- 状态: built（本地 conan create + 上游 ctest + test_package 待实测回填）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（host==build，原生轨）

## 依赖
| 依赖 | 版本 | 用途 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Qt5 Core/Test 运行时与 moc/rcc/uic（含 widgets/network/xml，examples 全量可构建） |
| ecm | 6.26.0 | Extra CMake Modules（KDEInstallDirs、KDECMakeSettings、ECMAddTests、ECMGenerateHeaders 等，tool_requires） |

ThreadWeaver 是 KF5 Tier 1 functional 库，运行时仅依赖 QtCore——
本链最轻的 KF5 配方（无 ki18n/kcoreaddons 等间接依赖）。

## 编译步骤

1. 源码: `https://download.kde.org/stable/frameworks/5.116/threadweaver-5.116.0.tar.xz`
   sha256 `9723dc652df9a2df8b6b9909af5bf0de3b3eb3aaed260a6419df2b0ddbe8eae0`
   （本地实测，且与官方 .sha256 sidecar 文件逐字节一致）
2. 上游是标准 KF5 CMake 工程: `find_package(ECM 5.116.0 NO_MODULE)` +
   `find_package(Qt5Core 5.15.2 REQUIRED NO_MODULE)`。
   本地构建命令:
   `conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2`
   流程: `cmake.configure()` → `cmake.build()` → `ctest`（build 内执行上游测试）
   → `cmake.install()` → `binary-sign-tool` 签名 → test_package。
   配置参数: `QT_MAJOR_VERSION=5`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、
   `KF_SKIP_PO_PROCESSING=ON`、`BUILD_TESTING=ON`、`BUILD_QCH=OFF`、
   `BUILD_SHARED_LIBS=ON`、`CMAKE_SYSTEM_NAME=Linux`、
   `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + SONAME flags。
   ctest 运行环境: `QT_QPA_PLATFORM=offscreen`、`HOME=<build>/test-home`、
   `XDG_RUNTIME_DIR=<build>/xdg-runtime`、`LD_LIBRARY_PATH` 含依赖 lib 与
   `/system/lib64`。

## 关键适配点

- **CMAKE_SYSTEM_NAME=Linux（UNIX-like 原生目标）**: OHOS 的 Conan toolchain 把
  `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 对其无 platform module
  且不置 `UNIX`，并把构建判定为 cross-compiling。7 个上游测试由 `ecm_add_test()`
  注册，而 ECM 仅在非 cross 构建时 `add_test()`；同时 ECM 的 POSIX 编译标志/RPATH
  处理在 `if(UNIX)` 下生效。显式固定为 Linux（同 libc/同 clang 驱动的 Linux-like
  目标）既恢复 `UNIX=1` 又让测试真正注册与构建，是本链通用做法
  （kcoreaddons5/kitemviews5）。
- **KF_SKIP_PO_PROCESSING=ON**: qtbase 不含 Qt5LinguistTools（lrelease/lconvert）；
  threadweaver 本身无 po/ 目录（该开关为链统一惯例，对本库是 no-op）。
- **使用 qt5-qtbase 原生 Qt5 CMake 配置**: `find_package(Qt5 ... NO_MODULE)` 需要
  原生 Qt5 config 提供的 `Qt5::Core/Qt5::Test` 与 CMake 宏；CMakeDeps 生成的
  configs 会被 `cmake_find_mode=none` 抑制，Qt 安装前缀手动加入
  `CMAKE_PREFIX_PATH`。
- **AUTOMOC/AUTORCC/AUTOUIC 指向 qt5-qtbase bin 工具**: CMakeDeps 不导出
  Qt5::moc 等 target；examples/ 树（HelloInternet 带 .qrc、ThumbNailer 带 .ui）
  需要它们。
- **mkspecs 兼容树重建**: `Qt5CoreConfigExtrasMkspecDir.cmake` 硬编码构建树路径
  `<prefix>/../b/mkspecs/linux-clang`，打包缓存里不存在；generate() 从包内
  `mkspecs/` 整树复制过去（kcoreaddons5 先例）。
- **签名（本链 2026-10 新增）**: CMake 安装期会改写共享库 RUNPATH，使 OHOS
  构建期 `.codesign` 段失效，加载器拒绝加载（"Permission denied"）。安装后用
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
  对包内每个 ELF 重签名（kitemmodels 6.18.0.1 / kirigami 6.26.0 / ki18n
  6.26.0.1 先例）。
- **E537**: OHOS 拒绝 mmap PROT_EXEC 一个链接后被改写 ELF 的共享库；
  `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` 使链接器直接写入最终安装 RPATH。
- **无版本 DT_SONAME**: `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
  SONAME flags → 可重定位、无版本号的 DT_SONAME（W3 CI L5 门禁）。
- **HMDFS 并行限制**: make jobserver fifo 创建被拒（EPERM），
  `CMAKE_BUILD_PARALLEL_LEVEL=1`。

## 上游测试（rule4 口径）

上游构建系统注册的测试目标数 **N=7**（autotests/CMakeLists.txt 中 7 个
`ecm_add_test`，TEST_NAME 分别为）:

| # | ctest 名 | main 宏 | 覆盖 |
|---|----------|---------|------|
| 1 | ThreadWeaverJobTests | QTEST_MAIN | Job 执行/失败/装饰器/依赖（上游最全） |
| 2 | ThreadWeaverSequencesTests | QTEST_MAIN | Sequence 顺序与失败中止 |
| 3 | ThreadWeaverQueueTests | QTEST_MAIN | Queue 优先级/资源限制/线程 |
| 4 | ThreadWeaverDeleteTest | QTEST_MAIN | 运行中删除 Job 的安全性 |
| 5 | ThreadWeaverLifecycleTest | QTEST_APPLESS_MAIN | Queue 生命周期状态机 |
| 6 | ThreadWeaverShutdownOnQApplicationQuitTest | QTEST_APPLESS_MAIN | QCoreApplication 退出时关闭 |
| 7 | ThreadWeaverQueueFactoryTest | QTEST_APPLESS_MAIN | QueueFactory/QueueStreams |

- benchmarks/QueueBenchmarks: `add_test` 在上游被注释（构建但不注册，不计 N）。
- examples/（HelloWorld/HelloWorldRaw/HelloInternet/ThumbNailer）: demo 程序，
  无任何测试注册（不计 N）。
- 全部 7 个测试均为无头 QCoreApplication/QTest 事件循环（库仅链 QtCore），
  无 GUI、无 D-Bus、无外部 fixture——OHOS PC runner 原生可跑，无豁免项。

实测结果: **7/7 通过（100%）**，无豁免项（本地 conan create 全量日志
`100% tests passed, 0 tests failed out of 7`，总耗时 1.40s；干净缓存重跑
`conan remove threadweaver5/* -c` 后复跑同样 7/7 全绿）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libKF5ThreadWeaver.so` | 主库，`DT_SONAME=libKF5ThreadWeaver.so`，含 RUNPATH，安装后 binary-sign-tool 重签名 |
| `include/KF5/ThreadWeaver/*.h` + `ThreadWeaver/` CamelCase 头 | 公开头（含 threadweaver_export.h） |
| `lib/cmake/KF5ThreadWeaver/*` | CMake 包配置（KF5::ThreadWeaver 目标，find_dependency(Qt5Core)） |
| `mkspecs/modules/qt_ThreadWeaver.pri` | qmake .pri（KDE_INSTALL_USE_QT_SYS_PATHS=OFF → 包内相对路径） |

## 注意事项

- 本配方骨架与 kcoreaddons5/kconfig5/kitemviews5 同源，可复用于后续 KF5（Qt5）
  库（同 qt5-qtbase/5.15.2.2 + ecm/6.26.0）。
- 若下游出现 `Error loading shared library ... Permission denied`，优先检查是否
  触发了 install 期 RPATH 原地改写（E537 类）与 .codesign 失效（本配方已双双
  处理：install-RPATH 链接 + 安装后重签名）。
- **已知限制（RPATH，本配方不单独处理）**: `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`
  使安装产物的 RUNPATH 固化为构建机 Conan cache 绝对路径，产物本身非
  relocatable；消费者场景由 Conan RPATH / conanrun（LD_LIBRARY_PATH）兜底。
  此为链上普遍现象（kcoreaddons5 等同），不在本配方单独处理。
- R32/R33 已遵守：未用 `os == "Linux"` 做 Conan 平台判断（配方用
  `str(self.settings.os) == "OHOS"`）；编译参数全部来自 Conan toolchain/依赖，
  无裸 `${CC}`/`${CFLAGS}`。
- R8/R49 已遵守：无源码补丁；未向共享 `/usr/local` 注入。
- R38：纯库包（无 `bin/`、`package_type="library"`），不建 `commands.json`
  （PF8 反向门禁）。
- R39：conandata 只写官方单条 URL（download.kde.org），未加任何镜像前缀。

## test_package 实测

16/16 断言通过（详见 reports/test-report.md）:
- API: 全局 stream() 按序执行、Sequence 失败中止、Collection 全量执行、
  make_job() lambda + enqueue()、QObjectDecorator started/done 信号、
  ResourceRestrictionPolicy(1) 并发上限、Job 状态机 New→Success/Failed。
- OHOS 特有: 无版本 DT_SONAME、DT_RUNPATH、.codesign 段（安装后
  binary-sign-tool 重签名）三断言全过。

## 干净重跑

`conan remove "threadweaver5/*" -c` 清缓存后全量重建: 上游 7/7（100%）+
test_package 16/16 + 签名 1 ELF，RC=0 全部复现（防"本地过 CI 挂"）。

---

**编译结束**: 2026-10-06 02:0x（本地时间）
**最终状态**: built（conan create 全绿，上游 7/7 + test_package 16/16）
