# networkmanager-qt 6.26.0 适配笔记（HarmonyOS PC / OHOS aarch64）

## 结论

`networkmanager-qt` 6.26.0 在 OHOS/aarch64 上 **无需任何源码补丁** 编译通过
（`patches: {}`），交付 `libKF6NetworkManagerQt.so` + camel-case 头 +
上游 CMake 包 + 一枚可重定位的 `KF6NetworkManagerQt.pc`。
上游 40 项 ctest 中 **37 项通过**，3 项依赖 D-Bus session bus 的集成测试在
本沙箱环境不可运行（原因见下，照实运行记录、不阻塞构建）。

## 编译环境

- 构建系统: cmake（上游）+ Conan 2.29.1
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0, arch=armv8,
  clang 15, libc++, cppstd=17, Release；native 构建）
- 编译日期: 2026-09-29
- 命令:
  ```bash
  conan create archives/n/networkmanager-qt/6.26.0 \
      -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
  ```

## 编译步骤（配方做了什么）

1. `source()`：官方 tarball
   `https://download.kde.org/stable/frameworks/6.26/networkmanager-qt-6.26.0.tar.xz`
   （sha256 `a5cfed06af6156161f7fee56efe1521a6e9e26119327069f1799986f90b432e5`，
   与官方 `.sha256` 一致）。
2. `generate()`：
   - `PkgConfigDeps` 生成 `libnm.pc` / `gio-2.0.pc`（包内自带 .pc 的
     `prefix=/` 不可重定位，不能用）；
   - 给生成的 `libnm.pc` 的 Cflags 追加 `-I<libnm>/include`（见问题 3）；
   - `CMakeToolchain`：`BUILD_SHARED_LIBS=ON`、`BUILD_TESTING=ON`、
     `BUILD_EXAMPLES=OFF`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、
     `PKG_CONFIG_EXECUTABLE`（显式钉死）、`ECM_MODULE_PATH`、
     `QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<qtdeclarative>`
     （Qt6Qml/QmlModels 由 qtdeclarative 提供）；
   - 手写 `conan_cmakedeps_paths.cmake`：qtbase 用 `cmake_find_mode=none`，
     CMakeDeps 不会贡献它的 `lib/cmake`，需自己把 qtbase-sql-dbus /
     qtdeclarative / 各依赖的 `lib/cmake`、`lib`、`include` 前置到
     `CMAKE_PREFIX_PATH` / `CMAKE_LIBRARY_PATH` / `CMAKE_INCLUDE_PATH` /
     `CMAKE_MODULE_PATH`（kconfig 6.26.0 先例）。
3. `build()`：`cmake.configure()` + `cmake.build()`，随后运行上游 ctest。
4. `package()`：`cmake.install()` + 额外安装 `lib/pkgconfig/KF6NetworkManagerQt.pc`。
5. `package_info()`：`cmake_find_mode=none`（用上游自带 `KF6NetworkManagerQtConfig.cmake`）、
   `cmake_file_name=KF6NetworkManagerQt`、`cpp_info.libs=["KF6NetworkManagerQt"]`、
   `pkg_config_name=KF6NetworkManagerQt`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Qt6 ... DBus ...)` 找不到 Qt6DBus | 本仓 `qtbase/6.11.1` 以 `FEATURE_dbus=OFF` 构建，包内没有 `lib/cmake/Qt6DBus`（`qtbase/6.11.1` 的二进制 requires 为空） | 改用 `qtbase-sql-dbus/6.11.1`（`FEATURE_dbus=ON`，随包发布 Qt6DBus），Qt6 Qml 由 `qtdeclarative/6.11.1` 经 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 提供 |
| 2 | Conan 图解析报 `Version conflict: Conflict between dbus/1.14.10.2 and dbus/1.14.10` | `libnm/1.58.0` 钉 `dbus/1.14.10.2`；所有已发布 `FEATURE_dbus=ON` 的 Qt6（`qtbase-sql-dbus/6.11.1` 及 `qtbase/6.11.1.1/.2/.3`）钉 `dbus/1.14.10` | `self.requires("dbus/1.14.10", override=True)` 统一到 qtbase-sql-dbus 发布二进制所依赖的版本（其 package id `852eddc8…` 要求 `dbus/1.14.10:8f3067d8…`）；代价是 `libnm/1.58.0` 按 dbus/1.14.10 从源码重建（约 5 分钟，`libdbus-1.so.3` ABI 稳定）。反向覆盖到 1.14.10.2 会作废整个 Qt Base 二进制，不可取 |
| 3 | 编译报 `fatal error: 'libnm/NetworkManager.h' file not found`（`src/settings/setting.h:15` 等） | upstream 同时用 `<libnm/NetworkManager.h>`（10 处）与 `<NetworkManager.h>`/`<nm-version.h>`（直接位于 `include/libnm/`）；`libnm` 自己的 `libnm.pc` 与 PkgConfigDeps 生成的 `.pc` 都只有 `Cflags: -I${includedir}/libnm` | 在 `generate()` 中给生成的 `libnm.pc` 的 Cflags 追加 `-I<prefix>/include`（libnm 配方自身对 `gio-2.0.pc`/`glib-2.0.pc` 用的是同一手法）；`test_package` 同样处理 |
| 4 | ECM 6.26 `KDEInstallDirs6` configure 期执行 qtpaths 失败 | 沙箱 `LD_LIBRARY_PATH` 中 `/data/storage/el1/bundle/libs/arm64` 的不兼容 `libc++_shared.so` 遮蔽了兼容版本 | 在 configure/build/测试环境前置 `/system/lib64`（bluez-qt 6.28.0 先例，与 kconfig/kwindowsystem 6.26.0 同款修法）；同时前置 OHOS SDK `native/llvm/lib`（lld 的 libxml2.so.16） |
| 5 | 3 项上游集成测试跑不起来 | 它们通过 `src/fakenetwork` 把 fake NetworkManager 注册到 D-Bus **session** 总线；本沙箱禁止 AF_UNIX bind（`dbus-daemon` 实测报 `Failed to bind socket ... Operation not permitted`），唯一能起来的 TCP+ANONYMOUS 总线 QtDBus 用不了（实测 `connectivity() == UnknownConnectivity`、`addDeviceSpy.wait() == false`） | 照实运行记录、**不阻塞构建**（bluez-qt 6.28.0 同口径）；37 项不需要总线的值对象测试作为**阻塞闸门**必须全绿。证据写入 `test_package/MANIFEST.yml` 的 `excluded_upstream_tests` |
| 6 | upstream 不安装 pkg-config 文件 | KDE Frameworks 6 只装 CMake 包（`lib/cmake/KF6NetworkManagerQt/*.cmake`），**没有** `.pc`（已核实：源码树无任何 `.pc` 生成/安装语句） | 配方在 `package()` 额外安装可重定位的 `KF6NetworkManagerQt.pc`（`prefix=${pcfiledir}/../..`），`Requires:` 镜像上游 `KF6NetworkManagerQtConfig.cmake` 的依赖跟踪（Qt6Core/Qt6DBus/Qt6Network/libnm/gio-2.0），并声明 `pkg_config_name`，使下游可经 pkg-config 消费 |
| 7 | L5 产物门禁失败（3 项）：`libKF6NetworkManagerQt.so` 无 `DT_SONAME`、`DT_NEEDED` 含绝对路径、导出 targets 声明 `IMPORTED_NO_SONAME` | ① CMake 无 `Platform/HarmonyOS.cmake`（E092）→ `CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 未定义 → CMake **静默丢弃**上游 ECM 已算出的 `VERSION/SOVERSION`；② 静态 `dbus/1.14.10` 声明 expat → PkgConfigDeps 在 `dbus.pc` 里写 `Requires: expat` → CMake 按绝对路径链接**无 SONAME** 的 `libexpat.so` → 绝对路径落进 `DT_NEEDED` | ① `generate()` 补 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`/`..._CXX_FLAG = "-Wl,-soname,"`（与 Linux 平台模块同值），使上游 SOVERSION/VERSION 生效；② `_strip_unused_expat_require()` 从生成的 `.pc` 中删掉未被引用的 expat 模块。详见下节 |

## L5 产物质量修复（SONAME / DT_NEEDED / IMPORTED_NO_SONAME）

**症状（修复前，`reports/w3-local-ci.log`）**：

```text
[fail] L5a: libKF6NetworkManagerQt.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
[fail] L5b: libKF6NetworkManagerQt.so 的 DT_NEEDED 含绝对/相对路径:
       /storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so
[fail] L5c: 1 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE —
       .../KF6NetworkManagerQtTargets-release.cmake
[fail] L5: SONAME quality gate failed (3 errors)
L5_RESULT=fail: soname_gate_failed
```

对应实测（`llvm-readelf -d .../lib/libKF6NetworkManagerQt.so`）：动态段里**没有** `(SONAME)` 条目，
而 `NEEDED` 中有一条是绝对路径；`lib/` 下只有一个无版本的 `libKF6NetworkManagerQt.so`。

**根因（两项，均为平台/依赖侧，不是 upstream 的问题）**：

1. **SONAME（L5a + L5c）**——本机 `uname` 返回 HarmonyOS/HongMeng Kernel，conan 未写
   `CMAKE_SYSTEM_NAME`，于是 CMake 让 `CMAKE_SYSTEM_NAME=HarmonyOS`（E092），而 CMake
   没有 `Platform/HarmonyOS.cmake`。没有平台模块 = ELF 的
   `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` 从未定义，CMake 便**同时丢弃**了
   ① 自己的默认 `-Wl,-soname,`，② upstream `src/CMakeLists.txt`
   `set_target_properties(KF6NetworkManagerQt PROPERTIES VERSION ${NETWORKMANAGERQT_VERSION}
   SOVERSION ${NETWORKMANAGERQT_SOVERSION})`（ECM `ecm_setup_version(... SOVERSION 6)`
   已正确算出 6 / 6.26.0）。所以这不是"upstream 忘了设 SOVERSION"，而是平台能力缺失。
   最小验证：同一份 CMake 工程，`-DCMAKE_SYSTEM_NAME=HarmonyOS` 只产出
   `libfoo.so`（无 SONAME），改成 `Linux`（或仅补上两个 SONAME flag 变量）即产出
   `libfoo.so → libfoo.so.6 → libfoo.so.6.26.0` 且 `SONAME=libfoo.so.6`。
2. **绝对路径 DT_NEEDED（L5b）**——已发布的 `dbus/1.14.10` 是静态包（只有
   `libdbus-1.a`），其 recipe 声明了 expat，Conan 的 PkgConfigDeps 如实把
   `Requires: expat` 写进生成的 `dbus.pc`，`libnm.pc` 又能传递到它；`pkg-config --libs libnm`
   因此带出 `-lexpat`，CMake 的 PkgConfig 模块把它解析成 Conan 缓存里的绝对路径。
   而那个包里的 `libexpat.so` **没有 SONAME**，链接器无法记录 soname，只能把绝对
   构建机路径写进 `DT_NEEDED`（不可重定位）。expat 的配方属于另一个库节点，本归档
   不得触碰，因此在本配方内消除：`llvm-nm --undefined-only` 实测
   `libdbus-1.a` 与产物 `.so` 均**没有任何 expat 符号**（`xml_`/`expat` 命中 0），
   且链接带 `-Wl,--no-undefined`（真缺符号会直接链接失败），所以删掉这个模块是安全的。

**修复（全部在配方内，无源码补丁）**：

- `generate()` 新增两个 toolchain 变量（值取 Linux 平台模块的原值）：
  `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG = CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG = "-Wl,-soname,"`；
- 新增 `_strip_unused_expat_require()`：删除生成 `.pc` 中 `Requires:`/`Requires.private:`
  里的 `expat` 模块（与既有的 `_augment_libnm_pc()` 同一手法）。

**验证（修复后，`reports/w3-local-ci.log`，`conan create` 全新构建）**：

```text
$ ls -l <pkg>/lib/
libKF6NetworkManagerQt.so        -> libKF6NetworkManagerQt.so.6
libKF6NetworkManagerQt.so.6      -> libKF6NetworkManagerQt.so.6.26.0
libKF6NetworkManagerQt.so.6.26.0

$ llvm-readelf -d <pkg>/lib/libKF6NetworkManagerQt.so | grep -E 'SONAME|NEEDED'
  (NEEDED)  Shared library: [libQt6Network.so.6]
  (NEEDED)  Shared library: [libQt6DBus.so.6]
  (NEEDED)  Shared library: [libQt6Core.so.6]
  (NEEDED)  Shared library: [libnm.so.0]
  (NEEDED)  Shared library: [libgio-2.0.so.0]
  (NEEDED)  Shared library: [libgobject-2.0.so.0]
  (NEEDED)  Shared library: [libgmodule-2.0.so.0]
  (NEEDED)  Shared library: [libglib-2.0.so.0]
  (NEEDED)  Shared library: [libc++_shared.so]
  (NEEDED)  Shared library: [libc.so]
  (SONAME)  Library soname: [libKF6NetworkManagerQt.so.6]      ← 新增，且全部 NEEDED 均为裸 soname

$ cat <pkg>/lib/cmake/KF6NetworkManagerQt/KF6NetworkManagerQtTargets-release.cmake
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libKF6NetworkManagerQt.so.6.26.0"
  IMPORTED_SONAME_RELEASE   "libKF6NetworkManagerQt.so.6"      ← 由 IMPORTED_NO_SONAME TRUE 变为真 SONAME

L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content                              ← SONAME 门禁由 fail 转 pass
```

> 与 `manifest.yaml::test_results.l5` 的关系：修复前 manifest 写 `l5: pass` 而 W3 实测
> `L5_RESULT=fail`，二者矛盾；**本次修复后 W3 实测即为 pass**，manifest 的 `l5` 字段随之
> 与实测一致（并在字段里写明具体证据），矛盾消除，不靠改数字掩盖。

## 源码修改

无。`patches: {}`，未改动任何上游文件（含 `#ifdef` 守卫式改动）。

## 依赖版本

| 依赖 | 版本 | 角色 |
|------|------|------|
| qtbase-sql-dbus | 6.11.1 | Qt6 Core/Network/DBus（`FEATURE_dbus=ON`） |
| qtdeclarative | 6.11.1 | Qt6 Qml/QmlModels（`src/CMakeLists.txt` 无条件构建 QML 模块） |
| libnm | 1.58.0 | NetworkManager 客户端库（`libnm.pc`）；本图按 dbus/1.14.10 重建 |
| dbus | 1.14.10 (override) | 与 qtbase-sql-dbus 的发布二进制对齐 |
| dbus | 1.14.10.2 (tool_requires, build context) | 仅测试用：提供 `dbus-daemon`（1.14.10 构建时 `DBUS_BUILD_TOOLS=OFF`，无 daemon） |
| ecm (extra-cmake-modules) | 6.26.0 | `tool_requires`，KDE CMake 模块 |
| glib / expat / libndp / libudev-zero / uuid | 传递 | 经 libnm |

> libnm 之所以按 `dbus/1.14.10` 重建：其已发布二进制 `libnm/1.58.0:e89918d2…`
> 对应 `dbus/1.14.10.2`，而本图必须用 `dbus/1.14.10`（见问题 2）。重建耗时约
> 5 分钟，产物落在本地 Conan 缓存，`conan create` 后续复用。

## 验证结果

```text
$ conan create archives/n/networkmanager-qt/6.26.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
-- Configuring done
-- Generating done
...
networkmanager-qt/6.26.0: Running CMake.build()   → 100%
networkmanager-qt/6.26.0: RUN: ctest --test-dir ... -E "^(managertest|settingstest|activeconnectiontest)$"
1088/1144 Test ... 37/37 Passed            (settings/* 值对象测试)
networkmanager-qt/6.26.0: session bus for bus-level autotests: tcp:host=127.0.0.1,...
    （3 项 bus 级测试照实运行记录，不阻塞）
...
Testing package: test_networkmanager_qt
PASS: KF6NetworkManagerQt ConnectionSettings/WirelessSetting round-trip OK
======== Computing dependency graph ========  (test_package)
[test_package] 100% tests passed, 0 tests failed out of 1
```

- 上游 ctest：**37/37 通过**（排除的 3 项见上，逐项原因已记录）。
- `test_package`：1/1 通过（`PASS: KF6NetworkManagerQt ConnectionSettings/WirelessSetting round-trip OK`）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libKF6NetworkManagerQt.so` (+ `.so.6`, `.so.6.26.0`) | 主库 |
| `include/KF6/NetworkManagerQt/` | camel-case 头（`NetworkManagerQt/` 子目录）+ 导出头 |
| `lib/cmake/KF6NetworkManagerQt/` | 上游 CMake 包（`KF6NetworkManagerQtConfig.cmake` 等） |
| `lib/pkgconfig/KF6NetworkManagerQt.pc` | 配方补装（upstream 不提供） |
| `lib/qml/org/kde/networkmanager/` | 上游 `networkmanagerqtqml` QML 模块 |

## 消费者须知

- CMake 目标：`KF6::NetworkManagerQt`（`find_package(KF6NetworkManagerQt)`）。
- pkg-config：`KF6NetworkManagerQt`（`Libs: -lKF6NetworkManagerQt`）。
- 头文件搜索路径：`<prefix>/include/KF6/NetworkManagerQt`
  （`#include <NetworkManagerQt/SecretAgent>` 等）。
- 运行时需 `LD_LIBRARY_PATH` 指向包的 `lib/`（OHOS musl 不解析 RUNPATH）。
- 因为是 CMake 库包（无可执行文件），**不创建** `commands.json`（R38）。
---

**编译结束**: 2026-10-01 17:36
**最终状态**: built
