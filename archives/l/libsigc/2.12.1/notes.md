# libsigc++ 2.12.1 adaptation notes

## Scope

- Conan reference: `libsigc/2.12.1`
- Target: HarmonyOS/OHOS armv8 using the SDK Clang 15 toolchain
- Build system: Meson + Ninja
- Third-party Conan dependencies: none
- Delivery: shared library, headers, pkg-config metadata, and license

## Source

The official GitHub release asset and the GNOME release checksum both resolve
to SHA256 `a9dbee323351d109b7aee074a9cb89ca3e7bcf8ad8edef1851f4cf359bd50843`.
The release tarball contains generated headers under `untracked/`, so
maintainer mode and its m4/mm-common requirements remain disabled.

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

Meson cannot create Unix symlinks in the Windows staging directory. Following
E050/E073, the recipe copies the real `libsigc-2.0.so.0.0.0` file to both the
linker name `libsigc-2.0.so` and SONAME name `libsigc-2.0.so.0` when those names
are absent. All three files are identical AArch64 ELF64 objects; the SONAME is
`libsigc-2.0.so.0`.

## Verification

The forced source build completed Meson steps 103/103 and compiled all 32
upstream test targets. The real Conan consumer compiled and linked signal,
slot, ptr_fun, mem_fun, bind, disconnect, trackable, lambda-slot, and void-signal
operations with 12 assertions.

- Recipe revision: `b05085d169b1707ec27a790653d05e80`
- Package revision: `a99ecb781a6c94ae3b204a3fb51c5580`
- Build log SHA256: `3D154456AA12CFAEC6260B283D0025BD63EC952F5C341B004CD15C5EC2C5B8D4`
- Packaged library SHA256: `4a2faa9b2473a179c8f6dc42db92137608e32dd245694274da52a1e4b1033764`

The Windows-to-OHOS build had `can_run=false`, so its log proves only
cross-compilation and linking. Buildbot #9207 later ran 32/32 upstream tests
and the real Conan consumer on a native HarmonyOS worker with L0/L1 pass and
exit code 0.

On 2026-07-24, the same 32 AArch64 upstream test executables and the Conan
consumer were transferred to a HarmonyOS PC over SSH. The library, its
materialized SONAME/linker aliases, and all executables were stripped of any
old `.codesign` section, signed in place at their final HMDFS paths, and run
with the packaged library on `LD_LIBRARY_PATH`. All 33 tests returned 0.

- Device result: upstream 32/32, Conan consumer 1/1, 12/12 consumer assertions
- Payload SHA256: `57f0f30c9492bf9c29464591b0b562b6c3b505ff2367cf7f1ca4418d73211bec`
- Signed library SHA256: `f898919e3b668357703b410be4c5c498bbd180f4e67b061d90ba496f425fc9a2`
- Signed consumer SHA256: `7e4690637e99468404512567d8eb8fcb71b1c99e497267024785627bc88937e7`
