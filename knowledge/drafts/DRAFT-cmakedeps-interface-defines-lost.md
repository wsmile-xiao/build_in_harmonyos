# DRAFT-cmakedeps-interface-defines-lost - Conan CMakeDeps 重建依赖配置不携带上游 INTERFACE_COMPILE_DEFINITIONS

> **Status**: VERIFIED DRAFT | **Updated**: 2026-09-19
> **Severity**: medium | **Category**: conan / cmake / build-system / compile-definition
> **Slug**: `cmakedeps-interface-defines-lost`（最终编号由知识库主编确认）

## Usage

Use this pattern when a Conan consumer that relies on CMakeDeps-regenerated
dependency configs fails to compile with macro-gated API errors ("no member
named ... in namespace ...", "unknown type name ...") while the dependency
itself built fine, and the missing API is known to be selected by compile
definitions that the dependency's **native, installed** CMake config sets via
`INTERFACE_COMPILE_DEFINITIONS`.

Typical trigger: building a Qt5/KF5 project's upstream autotests
(`BUILD_TESTING=ON`) against `qt5-qtbase` consumed through CMakeDeps, or
compiling a consumer of `xdelta3.h` / pinocchio headers.

## Scope

- Any project whose dependency's upstream CMake config expresses an ABI/API
  contract through `INTERFACE_COMPILE_DEFINITIONS`:
  the Qt5 `QT_*_LIB` family (`QT_CORE_LIB`/`QT_GUI_LIB`/`QT_WIDGETS_LIB`/
  `QT_TESTLIB_LIB` — controls which headers QtTest pulls in and which
  application class `QTEST_MAIN` instantiates),
  `xdelta3` `SIZEOF_*`/`XD3_USE_LARGESIZET` (controls `usize_t`/`xoff_t`
  typedefs), pinocchio `BOOST_MPL_LIMIT_*`/`PINOCCHIO_ENABLE_TEMPLATE_INSTANTIATION`
  (controls template instantiation branches).
- Any Conan 2 build where CMakeDeps regenerates the dependency's config from
  `cpp_info` (including aggregated configs created via
  `set_property("qt5-qtbase", "cmake_file_name", "Qt5")`).
- Not applicable when the native config is consumed directly (no CMakeDeps
  shadowing), or when the failure is a link error / runtime error rather than
  header-level API disappearance.

## Symptom

The dependency package builds cleanly, but consumer translation units fail to
compile with "API missing" errors. Signatures observed (kwidgetsaddons5
5.116.0, `BUILD_TESTING=ON`, 29 errors → `ConanException: Error 2` →
`CONAN_RC=1`):

```text
autotests/ktooltipwidgettest.cpp:174:20: error: no member named 'qWaitForWindowExposed' in namespace 'QTest'
autotests/ktooltipwidgettest.cpp:185:20: error: no member named 'qWaitForWindowExposed' in namespace 'QTest'
error: no member named 'keyClick' in namespace 'QTest'
error: variable has incomplete type 'QWindow'
```

Same-family signatures from the in-tree precedents:

- xdelta3 3.2.0: `xdelta3.h` fails to typedef `usize_t`/`xoff_t`
  (`SIZEOF_*` all evaluate to 0).
- pinocchio 4.1.0/4.1.0.2: `mpl::non_sequence_tag` has no member named
  `apply`; `using declaration refers into 'Base::', which is not a base
  class`.

The silent part: `QTEST_MAIN` does not error out — it **degrades** to a
`QCoreApplication` main without any GUI test API, so a project that merely
links and runs (without GUI test API calls) appears fine, which makes the
root cause non-obvious.

## Root Cause

Conan CMakeDeps treats the dependency recipe's `cpp_info` as the single
source of truth and regenerates the CMake config from it; interface
properties that exist only in the package's installed (native) config files
are **not** inherited. Mechanism chain (Qt5 case, verified first-hand):

1. **Native config hardcodes the definitions** (tool implementation
   evidence). In the qt5-qtbase package:

   ```text
   lib/cmake/Qt5Core/Qt5CoreConfig.cmake:149     INTERFACE_COMPILE_DEFINITIONS QT_CORE_LIB
   lib/cmake/Qt5Gui/Qt5GuiConfig.cmake:149       INTERFACE_COMPILE_DEFINITIONS QT_GUI_LIB
   lib/cmake/Qt5Widgets/Qt5WidgetsConfig.cmake:149 INTERFACE_COMPILE_DEFINITIONS QT_WIDGETS_LIB
   lib/cmake/Qt5Test/Qt5TestConfig.cmake:149     INTERFACE_COMPILE_DEFINITIONS QT_TESTLIB_LIB
   ```

2. **CMakeDeps regeneration derives the same property from cpp_info**, which
   declares no defines for qt5-qtbase. In the consumer's
   `<build>/<build_type>/generators/Qt5-Target-release.cmake`:

   ```cmake
   set_property(TARGET Qt5::Widgets APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS
                $<$<CONFIG:Release>:${qt5-qtbase_Qt5_Widgets_COMPILE_DEFINITIONS_RELEASE}>)
   ```

   The variable is empty (`grep -c QT_GUI_LIB Qt5-Target-*.cmake` → 0), so
   the regenerated `Qt5::Gui`/`Qt5::Widgets` targets carry no defines.

3. **Header dispatch degrades** (failure point). QtTest's `qtest.h`
   (qt5-qtbase `src/testlib/qtest.h:460-504`) dispatches on the macros:

   ```text
   #if defined(QT_WIDGETS_LIB)   → includes qtest_widgets.h; QTEST_MAIN_IMPL uses QApplication
   #elif defined(QT_GUI_LIB)     → includes qtest_gui.h;    QTEST_MAIN_IMPL uses QGuiApplication
   #else                         → QCoreApplication only; no GUI test API at all
   ```

   Without the macros, `QTest::keyClick`/`QTest::qWaitForWindowExposed` are
   never declared and `QTEST_MAIN` instantiates a bare `QCoreApplication` —
   whole categories of autotests stop compiling.

4. **Classification**: build-system semantics (Conan generator contract vs
   upstream installed-config contract), not a quirk of the ported library.
   Recurrence is guaranteed by generator behavior: any new Qt5/KF5 consumer
   hits it. In-tree precedents fixed the same mechanism at two different
   positions: producer-side `cpp_info.defines`
   (pinocchio `4.1.0` conanfile.py:190, `4.1.0.2`:254 — copied verbatim from
   upstream `pinocchioTargets.cmake`'s `INTERFACE_COMPILE_DEFINITIONS`;
   xdelta3 `3.2.0`:142 — `SIZEOF_SIZE_T=8`, `SIZEOF_UNSIGNED_LONG=8`,
   `XD3_USE_LARGESIZET=1`, ...) and consumer-side toolchain injection
   (kwidgetsaddons5 5.116.0, this run).

## Solution Space

### 1 (recommended): consumer-side toolchain append — `rec_consumer`

In the consuming recipe's `generate()`, after `CMakeToolchain.generate()`,
append the upstream-native macro set to the generated
`conan_toolchain.cmake` (this run's validated precedent):

```python
toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
with open(toolchain_file, "a", encoding="utf-8") as f:
    f.write("add_compile_definitions(QT_CORE_LIB QT_GUI_LIB QT_WIDGETS_LIB QT_TESTLIB_LIB)\n")
```

- Scope: the whole build (every target links the corresponding Qt5 module
  anyway, so this is semantically equivalent to the native
  `INTERFACE_COMPILE_DEFINITIONS` propagation).
- Does not touch the shared base package (`qt5-qtbase`), so no ecosystem
  rebuild.
- Use the upstream-native macro names — for Qt5Test that is
  `QT_TESTLIB_LIB` (see notes below on the `QT_TEST_LIB` naming slip in the
  kwidgetsaddons5 recipe: harmless, kept as-is in the engineering files).

### 2 (structural, producer-side): dependency recipe `cpp_info.defines` — `rec_producer`

The dependency recipe's `package_info()` copies the interface definitions
verbatim from the upstream installed config (pinocchio / xdelta3
precedents):

```python
# values copied from upstream lib/cmake/.../*Config.cmake INTERFACE_COMPILE_DEFINITIONS
self.cpp_info.defines = ["SIZEOF_SIZE_T=8", "SIZEOF_UNSIGNED_LONG=8", "XD3_USE_LARGESIZET=1"]
```

- Structurally correct: every CMakeDeps consumer benefits.
- Trade-off: modifying a shared base package such as `qt5-qtbase` requires
  assessing the ecosystem-wide rebuild impact; for componentized packages
  the defines must be attached to the right component (`QT_TESTLIB_LIB`
  belongs on the Test component, not globally).

### 3 (last resort): target-scoped definitions — `fallback_target_scope`

`target_compile_definitions(<only-test-targets> PRIVATE QT_WIDGETS_LIB ...)`
is narrower than a build-wide toolchain append but requires patching the
upstream CMakeLists (test target properties) and masks the config-contract
gap. Use only when neither the consumer toolchain nor the dependency recipe
can be changed. Not the default.

### Forbidden

- **Copying the native `Qt5*Config.cmake` files into the CMakeDeps
  `generators/` directory.** Reason: CMakeDeps resolves configs through its
  own naming/path wiring; native configs double-define the imported targets
  and compute prefixes outside the Conan environment. Consequence: failures
  move from compile time to configure time (target redefinition / wrong
  paths), harder to diagnose and drifting across Conan versions.
- **Injecting `-DQT_*_LIB` through global `CMAKE_CXX_FLAGS`.** Reason: masks
  the `cpp_info` contract gap; `-D` strings have no dedup/ordering
  guarantees and are lost when the generator switches to the
  `CMakeToolchain` variables path. Consequence: a surface fix that is not
  reproducible across profiles/generators and recurs downstream.

## Verification

Self-contained three-segment sequence (any fresh shell on an OHOS PC
builder device with the ohos-aarch64 profile; executed 2026-09-19 on the
kwidgetsaddons5-5.116.0 run device, scratch probe under
`/storage/Users/currentUser/tmp/oh-device-porting-v2/kwidgetsaddons5-5.116.0/qtestmain-probe/`).

### (a) Native config hardcodes the definitions

```sh
qt5p=$(ls -d ~/.conan2/p/qt5-*/p | head -1)
for m in Core Gui Widgets Test; do
  grep -n INTERFACE_COMPILE_DEFINITIONS $qt5p/lib/cmake/Qt5$m/Qt5${m}Config.cmake | head -1
done
```

Observed: each of the four files hits at line 149 with
`QT_CORE_LIB` / `QT_GUI_LIB` / `QT_WIDGETS_LIB` / `QT_TESTLIB_LIB`.

### (b) Regenerated configs carry none of them

In any CMakeDeps consumer build of qt5-qtbase:

```sh
grep -c QT_GUI_LIB <build>/<build_type>/generators/Qt5-Target-*.cmake      # → 0
grep -A1 "APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS" \
  <build>/<build_type>/generators/Qt5-Target-release.cmake                  # → ${qt5-qtbase_Qt5_<C>_COMPILE_DEFINITIONS_RELEASE}, empty
```

Observed in the probe's own generators: count 0; the `set_property` lines
reference the (unset) cpp_info variables for every component.

### (c) Directed reproduction: minimal QTEST_MAIN consumer

Probe files (inline so the sequence is self-contained):

`conanfile.py`:

```python
import os
from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout

class QTestmainProbeConan(ConanFile):
    name = "qtestmain-probe"
    version = "1.0"
    settings = "os", "compiler", "arch", "build_type"
    requires = "qt5-qtbase/5.15.2.2"

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()
        tc = CMakeToolchain(self)
        qt5 = self.dependencies["qt5-qtbase"]
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = os.path.join(
            qt5.package_folder, "bin", "moc")
        # Phase A: intentionally NO QT_*_LIB compile definitions here.
        tc.generate()
```

`CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.16)
project(qtestmain_probe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_AUTOMOC ON)
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Widgets Test)
add_executable(qtestmain_probe qtestmain_probe.cpp)
target_link_libraries(qtestmain_probe PRIVATE Qt5::Core Qt5::Gui Qt5::Widgets Qt5::Test)
enable_testing()
add_test(NAME qtestmain_probe COMMAND qtestmain_probe)
```

`qtestmain_probe.cpp`:

```cpp
#include <QtTest/QtTest>
#include <QtWidgets/QWidget>

class QTestmainProbe : public QObject
{
    Q_OBJECT
private slots:
    void guiApiProbe();
};

void QTestmainProbe::guiApiProbe()
{
    QWidget widget;
    widget.show();
    QVERIFY(QTest::qWaitForWindowExposed(&widget));
    QTest::keyClick(&widget, Qt::Key_Escape);
}

QTEST_MAIN(QTestmainProbe)
#include "qtestmain_probe.moc"
```

Sequence and observed output:

```sh
conan install . -pr:h ci/conan/profiles/ohos-aarch64 \
                -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
cmake --preset conan-release
cmake --build --preset conan-release
```

Phase A (no defines) — **fails** exactly like the run's blocking log:

```text
qtestmain_probe.cpp:22:20: error: no member named 'qWaitForWindowExposed' in namespace 'QTest'
qtestmain_probe.cpp:23:12: error: no member named 'keyClick' in namespace 'QTest'
make[2]: *** [CMakeFiles/qtestmain_probe.dir/build.make:99: ...] Error 1
make: *** [Makefile:101: all] Error 2          # build RC=2
```

Phase B — append the native macro set and rebuild:

```sh
printf '\nadd_compile_definitions(QT_CORE_LIB QT_GUI_LIB QT_WIDGETS_LIB QT_TESTLIB_LIB)\n' \
  >> build/Release/generators/conan_toolchain.cmake
cmake --preset conan-release && cmake --build --preset conan-release   # → Built target qtestmain_probe (RC=0)
qt5p=$(ls -d ~/.conan2/p/qt5-*/p | head -1)
env QT_QPA_PLATFORM=offscreen \
    QT_QPA_PLATFORM_PLUGIN_PATH=$qt5p/plugins/platforms \
    LD_LIBRARY_PATH=$qt5p/lib ./build/Release/qtestmain_probe
```

Observed run output:

```text
********* Start testing of QTestmainProbe *********
Config: Using QtTest library 5.15.2, Qt 5.15.2 (arm64-little_endian-lp64 shared (dynamic) release build; ...)
PASS   : QTestmainProbe::initTestCase()
PASS   : QTestmainProbe::guiApiProbe()
PASS   : QTestmainProbe::cleanupTestCase()
Totals: 3 passed, 0 failed, 0 skipped, 0 blacklisted, 17ms
********* Finished testing of QTestmainProbe *********    # RUN RC=0
```

`guiApiProbe` passing proves `QTEST_MAIN` took the `QApplication` branch and
both macro-gated APIs exist — i.e. the appended definitions fully restore
the native interface contract for this consumer.

In-run blocking evidence (pre-fix): 29 compile errors across the autotests,
`ConanException: Error 2`, `CONAN_RC=1`
(`.../kwidgetsaddons5-5.116.0/local-create-1.log`); post-fix:
`local-create-2.log` all PASS, authoritative CI PASS (RC=0, all gates).

## Dedup (differentials)

- **E216** (glib/libxml2 CMakeDeps component `INTERFACE_INCLUDE_DIRECTORIES`
  propagation loss): same "regenerated config drops an interface property"
  family, but a different field (include dirs vs compile definitions), a
  different error signature (header not found vs macro-gated API missing),
  and a different fix (GLOB fallback vs defines restoration).
- **E221** (CLI + library contract modeling): same "package contract not
  fully stated" motif, but about `package_type`/libs modeling, not
  generator-regeneration semantics.
- **DRAFT-sophus-1.22.10-fmt-basic-logging-macro** (in tree): the macro
  being lost there is the ported library's own optional-dependency
  degradation macro (`SOPHUS_USE_BASIC_LOGGING`) expressed by the library's
  exported targets; here the loss is on the **dependency's native config**
  side (`QT_*_LIB`/`SIZEOF_*`/`BOOST_MPL_LIMIT_*`) and manifests as
  macro-gated API disappearance rather than a missing optional-dep header.
  Producer-side fix is shared, which corroborates L2.
- **DRAFT-conan2-cmakedeps-transitive-include-strip** (in tree):
  transitive include dirs generated empty for non-direct requirements;
  different field and different trigger topology (direct requires here).
- This entry is the first to cover the **compile-definitions** field of the
  family, to document the covert QTEST_MAIN degradation fingerprint, to document
  both fix positions (producer `cpp_info.defines` / consumer toolchain
  append) with three-library generalization (Qt5/xdelta3/pinocchio).

## Notes

- Sibling phenomenon (`qt_wrap_ui`): the regenerated Qt5 config also omits
  upstream macros. Consumer-side provisioning works by appending to
  `conan_toolchain.cmake`:
  `set(QT_DEFAULT_MAJOR_VERSION 5)` + `set(Qt5Widgets_UIC_EXECUTABLE <pkg>/bin/uic)`
  + `include(<pkg>/lib/cmake/Qt5Widgets/Qt5WidgetsMacros.cmake)`.
  Do **not** hand-write a `conan_cmakedeps_paths.cmake` for this: its mere
  existence makes the Conan toolchain skip its own dependency path wiring
  (the paths live in the else-branch of the toolchain's find_paths block).
- Native macro naming: Qt5Test's native define is `QT_TESTLIB_LIB`
  (`Qt5TestConfig.cmake:149`). The kwidgetsaddons5 5.116.0 recipe injects
  `QT_TEST_LIB` — not the native name; harmless (the QTEST dispatch only
  checks `QT_WIDGETS_LIB`/`QT_GUI_LIB`), engineering files kept unchanged;
  knowledge uses the native name.
- Principle proposal (for the knowledge-base owner, not self-numbered):
  "dependency config contract completeness" — when a dependency is
  regenerated through a generator, interface properties (compile
  definitions / macros / include dirs) must be equivalent to the upstream
  installed config; gaps must be closed explicitly in the dependency's
  `cpp_info` or the consumer's toolchain.
- Quota: this run (kwidgetsaddons5 5.116.0) files 1/2 knowledge entries
  (this entry only).

## Validated Example

`kwidgetsaddons5/5.116.0` (KF5/Qt5): upstream autotests failed to compile
under `BUILD_TESTING=ON` (29 errors, `no member named 'keyClick' in
namespace 'QTest'` etc.); the recipe's `generate()` appends
`add_compile_definitions(QT_CORE_LIB QT_GUI_LIB QT_WIDGETS_LIB QT_TEST_LIB)`
to `conan_toolchain.cmake` (see the naming note above for `QT_TEST_LIB`).
Post-fix local `conan create` all PASS, upstream ctest 24/24 real execution
(offscreen), `test_package` 1/1, authoritative CI RC=0 with all gates
(G0/G0e/L0/KC/JC/L1/L4/L5). The (c) probe in this draft re-validated the
mechanism in isolation with the native macro set.
