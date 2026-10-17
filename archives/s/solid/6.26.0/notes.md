# solid 6.26.0 notes

- 状态: built
- 构建系统: cmake（KDE ECM / KDECompilerSettings 驱动）
- 编译器: clang/clang++ 15.0.4（os=OHOS 6.0, arch=armv8, C++20, Release）
- 适配日期: 2026-09-14

## Scope

This package upgrades the Solid dependency needed by KIO 6.26.0 to KDE
Frameworks 6.26.0 on HarmonyOS PC (os=OHOS 6.0, arch=armv8, clang 15, C++20).
It replaces the 6.18.0 recipe of the same package and keeps the OHOS baseline
on the fake-hardware backend.

## Upstream test inventory (R51 step 1)

`autotests/CMakeLists.txt:3,7-28` registers four `ecm_add_test()` targets
(Qt Test / `QTEST_MAIN`), all of which are built and executed when
`BUILD_TESTING=ON`:

| CTest target | Source | QtTest cases |
|---|---|---|
| `fakehardwaretest` | autotests/fakehardwaretest.cpp | 3 |
| `solidhwtest` | autotests/solidhwtest.cpp | 38 |
| `solidmttest` | autotests/solidmttest.cpp | 16 |
| `predicatetest` | autotests/predicatetest.cpp | 3 |

Total: 4 CTest binaries / 60 QtTest cases. The tests need `Qt6::Test` and
`Qt6::Concurrent` (`autotests/CMakeLists.txt:3`), both provided by
qtbase/6.11.1 (`FEATURE_testlib=ON`). There is no other upstream test entry in
the tarball (no pytest/rust/JS suites); `docs/` and `cmake/` contain no tests.

## Adaptations

1. **`cppstd=20`** (`configure()`): `src/solid/devices/frontend/device.cpp:226`
   uses `std::map::contains` (C++20). `conan_toolchain.cmake` sets
   `CMAKE_CXX_STANDARD 17` *before* `project()`, which defeats ECM
   `KDECompilerSettings`'s `if (NOT CMAKE_CXX_STANDARD)` auto-detection
   (C++20), so the standard must be overridden in the recipe.
2. **`BUILD_DEVICE_BACKEND_fstab=OFF`**: `CMAKE_SYSTEM_NAME` is `HarmonyOS`,
   which does not match `CMAKE_SYSTEM_NAME MATCHES Linux`, so upstream takes
   the `else()` "BSDs and other Unix like systems" fallback branch that adds the
   `fstab` backend. `fstabwatcher.h:12` unconditionally includes `<libmount.h>`
   (not available on OHOS: `fatal error: 'libmount.h' file not found`).
   Disabled through upstream's own per-backend option
   (`cmake/SolidBackendsMacros.cmake:29`) — no source patch needed. The 6.18.0
   recipe solved the same problem with a source patch; the option is minimal
   and upstream-supported.
3. **OHOS SONAME for `lib/libKF6Solid.so`**: HarmonyOS has no CMake platform
   module (`configure` prints "System is unknown to cmake, create:
   Platform/HarmonyOS"), therefore `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` is never
   set. Consequences observed in the first successful build:
   - `libKF6Solid.so` had **no `DT_SONAME`** (CI gate L5a fail);
   - `bin/solid-hardware6` recorded the link path as its dependency:
     `DT_NEEDED ../../../bin/libKF6Solid.so` (L5b class defect).
   Fixed in the toolchain (`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` plus both
   `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG`), the verified pattern of
   `knowledge/DRAFT-libharu-2.3.0-missing-dt-soname.md`. Result: a single
   unversioned `libKF6Solid.so` with `SONAME = libKF6Solid.so` and
   `bin/solid-hardware6 → NEEDED libKF6Solid.so`.
4. **`USE_DBUS=OFF`**: on HarmonyOS `UNIX` is unset, so upstream already
   defaults `USE_DBUS` to OFF; set explicitly for determinism. This keeps the
   DBus-based `udisks2`, `upower` and the new-in-6.26.0 `kdeconnect` backend
   out of the build (no `Qt6::DBus` dependency, no qtbase-sql-dbus chain).
5. **`UDEV_DISABLED=ON`**, `CMAKE_DISABLE_FIND_PACKAGE_IMobileDevice=ON`,
   `CMAKE_DISABLE_FIND_PACKAGE_PList=ON`: Linux-only (UDev) and iOS-only
   (IMobileDevice/PList) backends.
6. **`KF_SKIP_PO_PROCESSING=ON`**: the qtbase package used by this repository
   ships no `Qt6LinguistTools`; ECM's `ecm_process_po_files_as_qm()` returns
   early when this option is set (`ECMPoQmTools.cmake:88,134`), so
   `ecm_install_po_files_as_qm(poqm)` degrades gracefully without a patch.
7. **`KF_IGNORE_PLATFORM_CHECK=TRUE`**: OHOS is not in KDE's platform allowlist
   (metainfo.yaml lists Linux/FreeBSD/Windows/macOS/Android).
8. **Upstream CTest embedded in `build()`** (`_run_upstream_tests()`), the same
   pattern used by the published sibling kcoreaddons/6.26.0, so CI also gets an
   upstream test signal. `SOLID_FAKEHW` is pointed at the in-tree
   `src/solid/devices/backends/fakehw/fakecomputer.xml`, because on OHOS only
   the fakehw backend exists while `solidmttest::testDeviceMatching`
   (`autotests/solidmttest.cpp:185`) requires a non-empty
   `Solid::Device::allDevices()`. On Linux CI the real udev/udisks2 backends
   provide devices, hence upstream needs no such variable.

## Source patches

None. `conandata.yml` declares no patches and the 6.26.0 source is used
unmodified.

## Dependencies

- `qtbase/6.11.1` (Qt6::Core, Qt6::Xml, Qt6::Gui; Qt6::Test/Concurrent for the
  autotests) — verified consumable.
- `tool_requires`: `ecm/6.26.0`, `bison/3.8.2`, `flex/2.6.4.2`, `m4/1.4.19`.
  `bison` invokes `m4` at build time and its compiled-in data directory does not
  match the Conan package path, so `_tool_environment()` sets
  `BISON_PKGDATADIR` and `M4` (inherited from the 6.18.0 recipe).
- `flex/2.6.4.2` is required (not 2.6.4): the older package lacks `bin/flex`,
  which broke the 6.18.0 CI builds.

## Verification

- Source: `solid-6.26.0.tar.xz`,
  sha256 `85cfab9b0787f59478661140997c485fadab62cec535ffcef2953d312f736c4a`.
- `conan create` (host/build profile `ci/conan/profiles/ohos-aarch64`,
  Release, `--build=missing --build='solid/*'`): **exit 0**, 103 s;
  `Signed 2 OHOS package ELF file(s)`; packaged 19 `.h`, 18 files,
  1 `.so` (`libKF6Solid.so`), 4 `.cmake`, 1 `.categories`.
- Upstream CTest inside `build()`: `100% tests passed, 0 tests failed out of 4`.
- Upstream CTest manually, verbose (`ctest -V`): 60 QtTest cases
  (3 + 38 + 16 + 3) **passed / 0 failed / 0 skipped**, exit 0.
  Log: `/storage/Users/currentUser/tmp/builds/logs/07-ctest-with-fakehw.log`.
- `conan-verify solid 6.26.0`: verdict PASS (G0, G1, G2, G3, G4).
- L2 smoke: `bin/solid-hardware6 --version` → `solid-hardware 0.1a` exit 0;
  `SOLID_FAKEHW=…/fakecomputer.xml bin/solid-hardware6 list` prints the fake
  device UDI list (54 `udi = '…'` lines).
- L4: `libKF6Solid.so` and `bin/solid-hardware6` are PIE/DYN with
  `GNU_STACK RW` (NX), `GNU_RELRO` and `BIND_NOW` (full RELRO).
- L5a/L5b: `SONAME = libKF6Solid.so`; no `DT_NEEDED` entry containing an
  absolute or `../` path.

## Notes / follow-ups

- `bin/solid-hardware6` is installed by upstream (`src/tools/solid-hardware/
  CMakeLists.txt:1-7`) but the recipe declares `package_type = "library"` and no
  `bindirs`, so the software-level `commands.json` is intentionally absent,
  matching the 6.18.0 baseline and the sibling KF6 packages (kio, kcoreaddons).
- The 6.26.0 KDE Connect backend (new in this release) is not built because it
  requires DBus.
- Real-device hardware discovery on OHOS still depends on a future udev/sysfs
  backend; this package intentionally ships the fakehw backend like 6.18.0.

## 对话记录

### 对话 #1 [2026-09-14]

- 问题: 真实构建（上游默认 + OHOS 设置、未打补丁）首轮 `make` 失败：
  `bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory`
  （`predicate_parser.c` 生成失败，Error 1）
- 操作: 根因是手工构建环境未注入 Conan 工具包的编译期数据目录（bison 二进制内
  编译死的 pkgdatadir 为 `/share/bison`）；按配方 `_tool_environment()` 口径注入
  `BISON_PKGDATADIR=<bison>/share/bison`、`M4=<m4>/bin/m4` 并前置 PATH
- 结果: bison/flex 生成通过，构建推进到真正的源码编译阶段

### 对话 #2 [2026-09-14]

- 问题: `src/solid/devices/frontend/device.cpp:226:19: error: no member named
  'contains' in 'std::map<...>'`
- 操作: 根因是 conan_toolchain.cmake 在 `project()` 前设置
  `CMAKE_CXX_STANDARD 17`，使 ECM `KDECompilerSettings` 的
  `if (NOT CMAKE_CXX_STANDARD)`（C++20 自动判定）失效；实测
  `-DCMAKE_CXX_STANDARD=20` 被覆盖无效 → 在配方 `configure()` 中覆盖
  `self.settings.compiler.cppstd = "20"`
- 结果: toolchain 变为 `C++ Standard 20`，编译推进（沉淀为知识草稿
  DRAFT-solid-6.26.0-conan-toolchain-cppstd17-blocks-ecm-cpp20）

### 对话 #3 [2026-09-14]

- 问题: `src/solid/devices/backends/fstab/fstabwatcher.h:12:10: fatal error:
  'libmount.h' file not found`
- 操作: 根因是 HarmonyOS 的 `CMAKE_SYSTEM_NAME` 不匹配 Linux，上游落入
  "BSDs and other Unix like systems" 兜底分支并加入 fstab 后端，而该后端的
  fstabwatcher.h 无条件 `#include <libmount.h>`；用上游自带后端开关
  `BUILD_DEVICE_BACKEND_fstab=OFF` 关闭（不改源码、不打补丁）
- 结果: 配置特性只剩 `fakehw` 后端，构建通过；与 6.18.0 的补丁意图等价

### 对话 #4 [2026-09-14]

- 问题: 产物 `lib/libKF6Solid.so` 无 `DT_SONAME`（CI L5a 门禁），且
  `bin/solid-hardware6` 的 `DT_NEEDED` 退化为 `../../../bin/libKF6Solid.so`
- 操作: 根因是 HarmonyOS 无 CMake 平台模块（configure 提示 "System is unknown
  to cmake, create: Platform/HarmonyOS"），`CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`
  为空；按知识 E383 / DRAFT-libharu-2.3.0-missing-dt-soname 方案在 toolchain 层
  设置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` 与两个 SONAME 标志
- 结果: `readelf -d` 显示 `SONAME = libKF6Solid.so`，可执行文件
  `DT_NEEDED = libKF6Solid.so`；L5a/L5b 口径通过

### 对话 #5 [2026-09-14]

- 问题: 上游 ctest 4 个目标中 `solidmttest::testDeviceMatching` 失败
  （`'!deviceList.isEmpty()' returned FALSE`，solidmttest.cpp:185），
  其余 59 个用例通过
- 操作: 根因是 OHOS 只构建 fakehw 后端，而 `Solid::Device::allDevices()`
  需要 `SOLID_FAKEHW` 指向 fake 计算机 XML（managerbase.cpp:58）；
  在配方 `_run_upstream_tests()` 中注入该变量（上游 Linux CI 由真实
  udev/udisks 后端提供设备）
- 结果: 复跑 `Totals: 16 passed, 0 failed`；全套件 4/4 CTest、60/60 用例通过，
  `conan create` exit 0
---

**编译结束**: 2026-09-14 03:31
**最终状态**: built
