# libcec-tools 7.1.1 adaptation notes

## Source and build

- Source: official Pulse-Eight `libcec-7.1.1` GitHub release archive.
- Build system: CMake; HarmonyOS PC aarch64 Conan profile.
- The source has no upstream CTest registration or standalone unit-test directory in this release. The source tree was checked for `enable_testing`, `add_test`, and test directories; none are present.
- This release predates the upstream `DISABLE_BUILDINFO` option. Setting `SOURCE_DATE_EPOCH=0` uses its reproducible-build branch and avoids the `whoami` probe that otherwise causes `string(STRIP)` to fail on OHOS.
- CMake's platform name is mapped to Linux so shared-library SONAME links match the name used by libcec's runtime loader. This setting does not replace the OHOS compiler or sysroot from the Conan profile.
- Build-time requirements: `p8-platform/2.1.0` and `eudev/3.2.14`. XRandR is disabled because it is optional and not part of this package's OHOS target.
- The Python binding cannot be generated without SWIG, and the upstream subproject installs a demo script whenever it finds Python even when the binding is absent. Python discovery is disabled so the package does not ship a script whose `cec` module is unavailable.
- The upstream CMake detects `libudev` through pkg-config but does not add `UDEV_INCLUDE_DIRS` or `UDEV_LIBRARY_DIRS` to compile/link commands. This works for system-wide `/usr/include` and linker paths but fails for the Conan package prefix; the portability patch adds both pkg-config directories so USB detection remains enabled.
- CMake's install step rewrites runtime paths on the installed ELF files after the SDK linker signs them. The `.codesign` section remains present but its signature is stale, and the HarmonyOS loader rejects the library with `Permission denied`; re-sign installed ELF files with `binary-sign-tool` after install, then restore their executable bit because the signing tool's output lacks it.

## Adaptation experience

Two reusable CMake behaviors apply to OHOS ports that embed build metadata or load a versioned shared library by name: prefer an upstream reproducible-build switch or `SOURCE_DATE_EPOCH` branch when optional host identity commands are missing, and verify the installed SONAME against the runtime loader's requested name. Existing libcec knowledge drafts document these general mechanisms; this package records the 7.1.1-specific switch availability and verification results.

## Verification

HarmonyOS PC aarch64 `conan create archives/l/libcec-tools/7.1.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` completed with exit 0.

- Upstream 7.1.1 declares no test target, `enable_testing`/`add_test`, or test directory: upstream cases 0, pass rate not applicable.
- `test_package` passed 3/3 runtime checks (100%): API consumer, `cec-client --help`, and `cecc-client --help`.
- The API consumer passed both assertions: `CECInitialise()` returned a live interface and `serverVersion` matched 7.1.1; it then destroyed the interface.
- Installed `libcec.so.7.1.1`, `cec-client`, and `cecc-client` were signed after `cmake --install`; the installed shared object was loaded by the API consumer.
