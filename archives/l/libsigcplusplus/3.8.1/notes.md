# libsigcplusplus 3.8.1 adaptation notes

## Scope

- Conan reference: `libsigcplusplus/3.8.1` (task naming for the upstream
  `libsigc++` 3.x line; coexists with the archived 2.x packages
  `libsigc/2.x`, `libsigc++/2.10.8`, `libsigc-2/2.12.2` — different
  package name and different major ABI line, kitemmodels5/KF6 style)
- Target: HarmonyOS/OHOS armv8 using the SDK Clang 15 toolchain
- Build system: Meson + Ninja (upstream reference build system)
- Third-party Conan dependencies: none (`sigcxx_build_dep = []` upstream)
- Delivery: shared library, headers, pkg-config metadata, and license
- C++ standard: C++17 (upstream `cpp_std=c++17`, matching the CI profile)

## Naming map

| item | value |
|---|---|
| Conan package | `libsigcplusplus` |
| library file | `libsigc-3.0.so` (SONAME `libsigc-3.0.so.0`) |
| headers | `include/sigc++-3.0/sigc++/*.h` |
| generated config | `lib/sigc++-3.0/include/sigc++config.h` |
| pkg-config | `sigc++-3.0` |
| CMake | `libsigcplusplus` / `libsigcplusplus::libsigcplusplus` |

## Source

The official GitHub release asset is
`https://github.com/libsigcplusplus/libsigcplusplus/releases/download/3.8.1/libsigc++-3.8.1.tar.xz`
with SHA256 `4ff41d1474e501d3baeced4c989d154338206ac16471e614376496b63fe252d1`.
The release tarball contains generated files under `untracked/`, so
maintainer mode and its mm-common requirements stay disabled (the default
`if-git-build` never activates on a tarball; the recipe pins `false`
explicitly). The license is LGPL-3.0-or-later (COPYING in the tarball).

## Static / shared

`-Ddefault_library=shared|static` covers both variants. The shared build
materializes the linker and SONAME alias names next to
`libsigc-3.0.so.0.0.0` (copied rather than symlinked, same as the
archived libsigc-2 recipe — copies are equivalent for linker and loader).
`cpp_info.libs = ["sigc-3.0"]` plus the two includedirs
(`include/sigc++-3.0` for the API headers and `lib/sigc++-3.0/include`
for the generated `sigc++config.h`) apply to both variants.

## OHOS specifics

- The OHOS clang wrapper injects `-Wl,--code-sign`, which breaks Meson's
  `-Werror=unused-command-line-argument` compile probes; the recipe
  appends `-Qunused-arguments` to `tc.extra_cflags`/`tc.extra_cxxflags`
  for OHOS builds (same pattern as libsigc-2/2.12.2, knowledge E050/E219).
- The Meson machine file gets SDK `llvm-ar`/`llvm-ranlib` injected from
  `tools.build:compiler_executables` (archiver injection, same pattern as
  libsigc-2/2.12.2).
- `wrap_mode=nodownload` prevents Meson subproject downloads; sigc++ has
  no required external dependencies so this is purely defensive.

## Upstream tests

The 3.8.1 tarball defines exactly 42 test executables in
`tests/meson.build` (`test_programs`, from test_accum_iter to
test_weak_raw_ptr; the set is identical to 3.8.0). The recipe runs
`meson.test()` inside `build()` whenever `can_run(self)` is true, so all
42 targets compile and execute during `conan create` on the native OHOS
worker. Test logic is unmodified.

## Verification

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
  exit 0 (2026-09-25, native OHOS worker)
- Upstream tests: `meson test` inside build() — **Ok: 42 / Fail: 0**
  (all 42 test executables from tests/meson.build compiled and passed;
  full log meson-logs/testlog.txt inside the build folder)
- Package id `01d92cf349a0dd98ff915f4bd99a04430171517f` (shared=True),
  recipe revision recorded in local cache after `conan create`
- Artefacts: `lib/libsigc-3.0.so.0.0.0` + `.so.0`/`.so` aliases,
  `include/sigc++-3.0/sigc++/*.h`, `lib/sigc++-3.0/include/sigc++config.h`,
  `lib/pkgconfig/sigc++-3.0.pc`, `licenses/COPYING`
- Consumer test: `test_libsigcplusplus` ran on target with bash -c +
  explicit LD_LIBRARY_PATH (dependency libdirs + SDK libc++_shared.so
  dir) — "all checks passed" (10 checks)

## Consumer test

test_package/test_package.cpp is a C++17 consumer that links against the
packaged library via CMakeDeps and runs on the target with
`self.run(bash -c "... export LD_LIBRARY_PATH=... && ./test_libsigcplusplus")`.
It checks: lambda slot emit, default last-value collector with two slots,
connection disconnect semantics, ptr_fun free-function slot invocation
count, mem_fun slot on a trackable receiver, trackable auto-disconnect on
receiver destruction, bind adaptor, scoped_connection release on scope
exit, exception_catch adaptor keeping an emit alive when one slot throws,
and empty-signal value-initialized return (10 checks).
