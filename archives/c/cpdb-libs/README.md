# cpdb-libs

cpdb-libs provides the core and frontend libraries for OpenPrinting's Common Print Dialog Backends architecture.

## 功能概述

- Provides common CPDB data structures and utility APIs.
- Discovers and communicates with print backends over GDBus.
- Provides frontend APIs used by print dialogs.
- Includes the `cpdb-text-frontend` and `cpdb-pickle-print` reference tools.

## OHOS 适配

- Uses the HarmonyOS Clang toolchain through Conan's OHOS profile.
- Uses the packaged GLib/GIO dependency and its relocatable `gdbus-codegen` generator.
- Preserves the upstream Autotools build and complete `make check` test flow.
- Fixes an upstream invalid unref exposed when the session bus has no activatable print backend.

## 依赖关系

- Build and runtime: `glib/2.88.3` (GLib, GObject and GIO).
- System libraries: pthread, math and crypt.
- Test runtime: a D-Bus session daemon used by the upstream integration test.

## 参考资料

- Homepage and source: https://github.com/OpenPrinting/cpdb-libs
- CPDB project: https://openprinting.github.io/projects/05-common-print-dialog/
