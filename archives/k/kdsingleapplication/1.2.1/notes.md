# KDSingleApplication 1.2.1 HarmonyOS PC adaptation

## Source and scope

- Official release: `v1.2.1`
- Official archive SHA-256:
  `e3254ce9dc5ecf6d61ef83264bc61d486a307f0e3c9ed1bb2176f068cdbcbe09`
- Build system: CMake, C++14 upstream sources, Qt 6
- Package dependency: `qtbase/6.11.1.2`
- Qt identifies HarmonyOS as a Unix platform, so KDSingleApplication uses its
  existing POSIX local-socket path without a platform-specific source branch.

## Adaptation

The recipe enables the Qt 6 shared-library build, disables examples and
documentation, and enables the complete upstream test suite. It points CMake
at the relocatable Qt configuration shipped by the Conan dependency. Because
CMake does not yet provide a HarmonyOS platform module, the recipe also sets
the shared-library SONAME flags explicitly and avoids versioned symlinks.
The sole platform-neutral patch makes optional qmake `.pri` metadata generation
configurable; the recipe disables it so a target `qmake` is never executed by
host-side cross builds. The public CMake package remains installed unchanged.
For host-side verification, the recipe uses a profile-provided QEMU runner
when available and extends its loader path with Qt's library directory. When
no runner is configured, it uses a native Qt 6 `moc` from `QT_HOST_PATH`, the
host `PATH`, or standard Qt 6 host-tool locations. Native HarmonyOS builds use
the target Qt tools directly.

KDSingleApplication tests launch many child processes. Their runtime
environment therefore includes the `lib` directory of every Conan dependency,
not just Qt itself. HarmonyOS user-storage mounts do not necessarily support
Unix-domain socket nodes, so the recipe probes candidate temporary directories
and selects a writable socket-capable cache directory. This is an environment
adaptation only; upstream test sources and assertions remain unchanged.

CMake installation may rewrite an ELF while removing build-tree runtime paths.
Installed shared objects are consequently re-signed during native HarmonyOS
packaging with the system `binary-sign-tool` after removing any stale
`.codesign` section. Cross-build hosts do not attempt device-side signing.

## Validation

Native HarmonyOS PC aarch64 validation on 2026-09-23:

- Upstream CTest discovery: 4 test executables, containing 42 functional
  cases/data rows (QTest lifecycle hooks are not counted)
- Upstream results: 4/4 executables and 42/42 functional cases passed (100%)
  - `tst_simpletest`
  - `tst_stresstest`
  - `tst_namelengthtest`
  - `tst_disconnectduringreadtest`
- Consumer results: 2/2 passed (100%); adapted total 44/44
  - installed CMake package/public API test
  - HarmonyOS-specific cross-process local IPC test

The consumer tests use the installed `KDSingleApplication-qt6` package and the
upstream `KDAB::kdsingleapplication` target.
---

**编译结束**: 2026-09-23 14:41
**最终状态**: built
