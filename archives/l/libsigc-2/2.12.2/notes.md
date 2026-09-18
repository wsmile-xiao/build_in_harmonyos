# libsigc++ 2.12.2 adaptation notes

## Scope

- Conan reference: `libsigc-2/2.12.2` (task naming; upstream project
  `libsigc++`, library `libsigc-2.0.so`, pkg-config module `sigc++-2.0`)
- Target: HarmonyOS/OHOS armv8 using the SDK Clang 15 toolchain
- Build system: Meson + Ninja
- Third-party Conan dependencies: none
- Delivery: shared library, headers, pkg-config metadata, and license
- C++ standard: C++17 (upstream `cpp_std=c++17`, matching the CI profile)

## Source

The official GitHub release asset is
`https://github.com/libsigcplusplus/libsigcplusplus/releases/download/2.12.2/libsigc++-2.12.2.tar.xz`
with SHA256 `7d4cdf1e4332ebfee8085ad960075045e7763cb291b3ccf4744d7cbf08a22b75`.
The release tarball contains generated headers under `untracked/`, so
maintainer mode and its m4/mm-common requirements remain disabled. The
license is LGPL-2.1-or-later (COPYING in the tarball).

## Static / shared

`-Ddefault_library=shared|static` covers both variants. The static build
has no SONAME or alias handling; the shared build materializes the linker
and SONAME alias names next to `libsigc-2.0.so.0.0.0` (Meson cannot create
Unix symlinks when staging from Windows, and copies are equivalent for the
linker and loader). `cpp_info.libs = ["sigc-2.0"]` plus the two includedirs
(`include/sigc++-2.0` for the API headers and `lib/sigc++-2.0/include` for
the generated `sigc++config.h`) apply to both variants.

## Windows-to-OHOS Meson cross build

Conan 2.29.1 initially generated `--prefix=C:/` from the Windows build machine
and a Meson cross file containing only SDK compiler paths. Meson rejected the
prefix, then identified Clang as `x86_64-w64-windows-gnu` because the machine
file omitted the OHOS target and sysroot.

The recipe now:

1. uses `/` as the target prefix while Meson install keeps staging isolated
   with `--destdir=<package_folder>`;
2. derives `native/sysroot` from `tools.build:compiler_executables`;
3. adds `--target=aarch64-linux-ohos` and the sysroot to C/C++ compile and link
   arguments; and
4. writes the absolute SDK `llvm-ar.exe` and `llvm-ranlib.exe` paths into the
   generated Meson cross file.

This reusable pattern is documented as E219.

The first native HarmonyOS CI run failed before Meson because the Windows SDK
sysroot completion was applied unconditionally to `/data/service/hnp/bin/clang`.
The recipe now applies E219 only when `settings_build.os=Windows`; native OHOS
uses the worker compiler and Meson machine file directly.

## Shared-library names

Following E050/E073, the recipe copies the real `libsigc-2.0.so.0.0.0` file to
both the linker name `libsigc-2.0.so` and SONAME name `libsigc-2.0.so.0` when
those names are absent. All three files are identical AArch64 ELF64 objects;
the SONAME is `libsigc-2.0.so.0`.

## Upstream tests

The 2.12.2 tarball defines exactly 32 test executables in `tests/meson.build`
(`test_*.cc`, listed in test_package/MANIFEST.yml). The recipe runs
`meson.test()` inside `build()` whenever `can_run(self)` is true, so all 32
targets compile and execute during `conan create` on the native OHOS worker.
Test logic is unmodified. On the Windows-to-OHOS cross path (can_run=false)
the 32 targets are still compiled, and the consumer links against the package.

## Verification

- Recipe revision: `af82afa5e0eba50c698539f2bd565213`
  (package ids: shared `01d92cf349a0dd98ff915f4bd99a04430171517f`,
  static `21b17f8b2bc0e9511e276e3d57a23893067cefe5`)
- All 32 upstream tests compiled and passed via `meson test` on OHOS armv8
  (both shared and static `conan create` runs, `Ok: 32 / Fail: 0` each)
- Real Conan consumer compiled and linked signal, slot, ptr_fun, mem_fun,
  bind, disconnect, trackable, lambda-slot, void-signal, and exception-path
  operations with 20 assertions
- test_ohos delivery checks: 16/16 on the shared delivery (ELF64/LE/AArch64
  on library + consumer, musl interpreter on the consumer, SONAME
  `libsigc-2.0.so.0` plus `.so.0`/`.so` aliases, NEEDED closure including
  `libc++_shared.so` against the real libc++/libc, `.codesign` section on
  both artifacts, no RPATH/RUNPATH, no host paths in strings, and a real
  signal/slot execution on the target); 15/15 on the static delivery
  (shared-only checks reported as TAP skips, numbering preserved)

## OHOS clang wrapper `-Wl,--code-sign` workaround

The local OHOS SDK toolchain wrapper (`usr/local/bin/clang++` sh wrapper
around `clang-15`) reads `aarch64-unknown-linux-ohos.cfg`, which prepends
`-Wl,--code-sign` to every driver invocation.  Meson's compile-only probes
(`gcc_template_specialization_operator_overload` et al.) run with
`-Werror=unused-command-line-argument`, so the injected linker flag is
diagnosed as `'linker' input unused` and the probe fails; without
`SIGC_TEMPLATE_SPECIALIZATION_OPERATOR_OVERLOAD` defined, lambda slots fall
back to the `sun_forte_workaround` branch and break `base.h` /
`adaptor_trait.h`.  The recipe therefore appends `-Qunused-arguments` to
`tc.extra_cflags` / `tc.extra_cxxflags` for every OHOS build (generate()).
It only silences the driver diagnostic: the flag does not touch source-level
warnings, upstream test conditions, or the link step — the final `.so`
still carries `.codesign` and `.note.ohos.ident` (see knowledge E050-era
wrapper notes and libdav1d notes.md platform table for the same pattern).
CI's `/data/service/hnp` clang has no cfg injection; the flag is a no-op
there.
