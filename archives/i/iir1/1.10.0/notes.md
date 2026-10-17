# iir1 1.10.0 adaptation notes

## Scope

- Dependency Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1246
- Downstream DOSBox Staging Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1093
- Adaptation path: Path A (base adaptation) + Path B (knowledge innovation).
  This dependency PR carries four reusable knowledge drafts that were
  absent from the cloud project at the final pre-push search.
- Upstream tag: `1.10.0`
- Upstream commit: `0a331a85e2ef58e550bed58d2485eee9858f61b8`
- Source SHA-256:
  `13b53f14d276adf6cafd3564fcda1d4b3e72342108d1c40ec4b4f0c7fc3ac95a`

## Dependency audit

The upstream CMake project has no `find_package`, FetchContent, submodule, or
third-party link dependency. It needs only a C++11 compiler, CMake, and the
platform C++ runtime. `iir1` is absent from cmd-pkgs README blob
`5b7e201c84be715eb3993f07287406a9b649bd39`. The mandatory remote check
`conan download iir1/1.10.0 -r=ohpcd --only-recipe` returned non-zero with the
CNB generic missing-package response `system acceleration policy not enabled`;
the known control `zlib/1.3.1.1` downloaded successfully from the same remote.

The only historic same-name PR is merged PR #964. It contributed metadata and
legacy notes but no `conanfile.py`, `conandata.yml`, or `test_package`, so this
recipe is not a duplicate adaptation.

The original target-device release-evidence runs used two independent empty
Conan homes. The final post-review run used another empty home and built
`shared=True` followed by `shared=False` against one Conan source cache. The
cache's `CMakeLists.txt` SHA-256 remained the official
`9c18d9f60864465912f4064e480cab69c98cf9bf2712e05af914f4eb85ec3025`
after both builds. The recipe's `export_sources()` copied the declared patch
before `source()` applied it; no run used manually seeded or pre-patched
source.

## Build adaptation

Upstream hard-codes its installed main target as `SHARED` and also builds a
separate static test target. For every package build, the recipe creates a
clean source copy under that package ID's `build_folder`, changes only the
copy with exact `replace_in_file` calls, and configures CMake from the copy.
The installed main target follows `BUILD_SHARED_LIBS`; the auxiliary static
target remains available to upstream tests but is not installed. Conan's
default log already showed a per-package source copy; the nested copy makes
that isolation explicit without claiming the default behavior was defective.

The Butterworth shelf prototype passed a negative radius to `std::polar`.
That violates the function's non-negative-radius precondition: Linux
`libstdc++` happened to return a finite value, while HarmonyOS `libc++`
returned `nan,nan` and `LowShelf<2>::setup()` failed with
`Pole to add is NaN.` The generated source patch preserves the intended
complex number by constructing its real and imaginary components directly.
It was produced by `refresh-patch --auto` on the HarmonyOS PC and replays with
zero fuzz against the official source baseline. `export_sources()` calls
`export_conandata_patches()` so a clean Conan cache carries the patch into the
recipe before source acquisition and application.

Verified OHOS/arm64 outputs:

- `shared=True`: only `libiir.so`.
- `shared=False`: only `libiir.a`.
- Shared ELF: ELF64, little-endian, AArch64, SONAME `libiir.so`.
- Shared consumer: `DT_NEEDED` contains `libiir.so`, not a Conan cache path.
- Static consumer: no `libiir.so` dynamic dependency.

Conan's generated toolchain maps OHOS to `CMAKE_SYSTEM_NAME=HarmonyOS`, but
CMake 4.1.2 has no built-in `Platform/HarmonyOS` module. Without a module the
shared library had no SONAME and consumers embedded the package cache's
absolute path. The recipe supplies a generated `Platform/HarmonyOS.cmake` that
includes CMake's Linux linker rules. CMake then attempted the upstream
`VERSION`/`SOVERSION` symlink chain, which HMDFS rejected. On OHOS only, the
recipe removes those filename-version properties and keeps one real
`libiir.so` with SONAME `libiir.so`; other platforms retain upstream behavior.

## Tests and score boundary

- Upstream CTest: 8 independent executables, executed on HarmonyOS PC in both
  package modes, 8/8 each.
- Conan consumer tests: 46 independent case commands covering 45 distinct
  filter family/type/order combinations plus invalid-parameter behavior,
  executed on HarmonyOS PC in both package modes, 46/46 each.
- Shared/static reruns validate two artifact contracts but do not double the
  logical test count.
- Total independently executable logical cases: 54. The dependency therefore
  exceeds the 50-case threshold for the 1-point tier. Assertions and repeated
  shared/static builds are not counted as new cases.

## Knowledge

The in-flight E217 knowledge already covers hard-coded CMake library target
types ignoring Conan's `shared` option, so no duplicate entry is included.
Existing E050, E092, and E207 cover HMDFS symlinks, unknown CMake
platform modules, and missing SONAME effects. Cloud and active-branch searches
found no entry for Conan 2 CMake helper argument routing, so this PR carries
the E224 knowledge draft with the formally submitted software for the independently verified
`CMake.test(cli_args=...)` versus `CMake.ctest(cli_args=...)` distinction.
The final diff and device failure were also searched for `std::polar`, negative
radius/rho, and NaN equivalents across cloud graph/doc/operations with no
match. The E228 knowledge draft records the portable replacement for negative-radius
`std::polar` calls and the exact Linux-versus-HarmonyOS verification evidence.
The E236 knowledge draft records how to distinguish Conan's default per-package source copy
from a genuinely shared source tree, and when an explicit nested copy is useful.
The E239 knowledge draft records how a multi-case Conan `test_package` can run
every independent command, retain each case name and original `ConanException`,
and report explicit non-zero consumer results before failing once with an
aggregate diagnostic.
