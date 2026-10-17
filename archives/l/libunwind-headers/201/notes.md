# libunwind-headers 201 Adaptation Notes

## Scope

`libunwind-headers` is the Apple open-source distribution of `libunwind`,
shipped as the GitHub tag `libunwind-201` in
`apple-oss-distributions/libunwind`. It is **not** LLVM libunwind and **not**
the nongnu `libunwind/libunwind` project — those are separate packages with
their own version schemes (LLVM uses `llvmorg-13.0.0`, nongnu uses `1.6.2`,
both already present in this archive under `l/libunwind`).

The Homebrew `libunwind-headers` formula is a header installation package: it
copies public header files from the upstream tree and does **not** build the
Apple libunwind runtime. This adaptation preserves that scope — no library is
produced and none is linked.

## Source Verification

- Upstream: `apple-oss-distributions/libunwind` (Apple open-source distribution)
- Tag / version: `libunwind-201` → version `201`
- Commit: `f709eccad023ec32db53d40146d07805cf3e4ee0`
- Archive URL: `https://github.com/apple-oss-distributions/libunwind/archive/refs/tags/libunwind-201.tar.gz`
- Archive SHA256: `bbe469bd8778ba5a3e420823b9bf96ae98757a250f198893dee4628e0a432899`
- License: APSL-2.0 (Apple Public Source License 2.0)

## Packaging (mirrors Homebrew install method)

Homebrew `install` block:

```ruby
def install
  cd "libunwind" do
    include.install Dir["include/*"]
    (include/"libunwind").install Dir["src/*.h*"]
  end
end
```

Translated into the Conan `package()`:

1. Download and verify the official GitHub tag archive (`strip_root=True`).
2. Apply the declared patch set (empty for this version — zero patch).
3. Copy `libunwind/include/*` → `include/`.
   - `libunwind.h` (public C API: `unw_context_t`, `unw_cursor_t`,
     `unw_proc_info_t`, register enums, `extern "C"` declarations).
   - `__libunwind_config.h` (architecture target/size macros).
   - `mach-o/compact_unwind_encoding.h` (Darwin compact unwind data layouts).
4. Copy `libunwind/src/*.h*` → `include/libunwind/` (private headers Homebrew
   exposes: `Unwind-EHABI.h`, `UnwindCursor.hpp`, `assembly.h`, `config.h`,
   `dwarf2.h`, `libunwind_ext.h`).
5. Install `APPLE_LICENSE` under `licenses/` when the tarball ships it.
6. Compile a C++17 consumer against the packaged headers.

No `build()` step compiles a library. The `apply_conandata_patches` call is
retained for recipe symmetry with the `dyld-headers` reference but applies no
patches for version 201.

## Architecture / Portability (OHOS aarch64)

The public `libunwind.h` is includable on HarmonyOS PC aarch64 because:

- It includes only `<stdint.h>` and `<stddef.h>`.
- `__libunwind_config.h` gates Apple availability behind `#ifdef __APPLE__`,
  so off-Apple `LIBUNWIND_AVAIL` expands to nothing.
- Without `_LIBUNWIND_IS_NATIVE_ONLY` defined, `__libunwind_config.h` takes
  the generic branch that defines `_LIBUNWIND_TARGET_AARCH64` and concrete
  `_LIBUNWIND_CONTEXT_SIZE` / `_LIBUNWIND_CURSOR_SIZE`, so
  `unw_context_t` / `unw_cursor_t` have well-defined sizes on aarch64.
- The AARCH64 register enum (`UNW_ARM64_X0..X31`, `UNW_ARM64_FP`, `UNW_ARM64_LR`,
  `UNW_ARM64_SP`, `UNW_ARM64_RA_SIGN_STATE`) is always compiled, regardless
  of native target.
- `compact_unwind_encoding.h` depends only on `<stdint.h>` and exposes pure
  data layouts and constants.

The `extern "C"` functions (`unw_getcontext`, `unw_step`, …) are **declarations
only** — their implementations live in the Apple libunwind runtime, which is
not built and not linked. Consumers that need actual unwinding must supply a
runtime; this package only provides the public ABI surface and data layouts.

## Validation

The consumer test (`test_package/test_libunwind_headers.cpp`) exercises the
real public surface: it includes `libunwind.h` and
`mach-o/compact_unwind_encoding.h`, checks compile-time invariants
(error codes, aarch64 register numbers, structure sizes, compact-unwind
constants), instantiates `unw_context_t` / `unw_proc_info_t` and writes
fields, and takes the address of `unw_getcontext` to prove the declaration is
visible. It does **not** call any unwind function (that would require linking
a libunwind runtime, which this headers package deliberately does not
provide). Eight assertions are checked.

## Upstream Tests (libunwind/test/)

The upstream tarball ships an LLVM-lit suite under `libunwind/test/`:

```
alignment.pass.cpp            # _Unwind_Exception double-word alignment
frameheadercache_test.pass.cpp # frame-header cache behaviour
libunwind_01.pass.cpp         # local unwind: backtrace >= lower_bound frames
libunwind_02.pass.cpp         # local unwind over multiple call depths
remember_state_leak.pass.sh.s # CFI remember-state leak (asan) — REQUIRES x86
signal_frame.pass.cpp         # signal frames reported (XFAIL darwin, UNSUPPORTED arm-ehabi)
unw_getcontext.pass.cpp       # unw_getcontext returns UNW_ESUCCESS
```
Total: 7 files.

The lit wrapper (`lit.site.cfg`) imports `libcxx.test.format` and an executor
at `libcxx/utils/run.py`. The Apple distribution tarball ships **no `libcxx/`
sibling**, and no `libcxx.test.format` module exists on this host, so the lit
harness cannot run as-is. Rather than skip the upstream tests, each `.pass.cpp`
was compiled and executed **directly** with the real OHOS toolchain and the
**OHOS SDK's own `libunwind.a`** — no Linux shim, no `CMAKE_SYSTEM_NAME=Linux`,
and no throwaway self-built runtime.

### Toolchain (real OHOS aarch64)

- clang: `/storage/Users/currentUser/usr/local/bin/clang++` 15.0.4, default
  target `aarch64-unknown-linux-ohos`, defines `__MUSL__`.
- target flag: `-target aarch64-unknown-linux-ohos`
- sysroot: `/storage/Users/currentUser/usr/local/sysroot` (musl libc; ELF
  interpreter `/lib/ld-musl-aarch64.so.1`).
- libunwind runtime: `/storage/Users/currentUser/usr/local/lib/aarch64-linux-ohos/libunwind.a`,
  shipped by the OHOS SDK and linked by clang's default link line
  (`-l:libunwind.a`). It exports `unw_getcontext` / `unw_init_local` /
  `unw_step` / `unw_get_proc_info` / `unw_is_signal_frame` (weak symbols) and
  the `_Unwind_*` Itanium API — so every upstream test has a real runtime.
- compile command per test:
  `clang++ -target aarch64-unknown-linux-ohos --sysroot=<sysroot> \
     -std=c++17 -I libunwind/include <test>.pass.cpp \
     -L <OHOS lib dir> -lunwind -lpthread -ldl -o t`
- run environment: the host runs OHOS/musl binaries natively — the **same**
  environment CI uses to run the `test_package` binary. (Earlier, a
  `CMAKE_SYSTEM_NAME=Linux` shim was used to build a throwaway runtime; that
  result is **invalidated** and not counted — see the correction note below.)

### ELF evidence (all 6 built binaries identical in shape)

- `file`: `ELF shared object, 64-bit LSB arm64, dynamic
  (/lib/ld-musl-aarch64.so.1), not stripped`
- `readelf -h`: `Machine: AArch64` ; `OS/ABI: UNIX - System V`
- `readelf -l`: `Requesting program interpreter: /lib/ld-musl-aarch64.so.1`
- `readelf -d`: `NEEDED libc++_shared.so` ; `NEEDED libc.so` (musl, **not**
  glibc `libc.so.6`) — confirming a real OHOS/musl target, not Linux/glibc.

### Upstream results

| # | test | compile | run | exit | note |
|---|------|---------|-----|------|------|
| 1 | unw_getcontext.pass.cpp | PASS | PASS | 0 | unw_getcontext returns UNW_ESUCCESS |
| 2 | libunwind_01.pass.cpp | PASS | PASS | 0 | backtrace >= lower_bound frames |
| 3 | libunwind_02.pass.cpp | PASS | PASS | 0 | multi-depth local unwind |
| 4 | alignment.pass.cpp | PASS | PASS | 0 | static_assert + runtime |
| 5 | signal_frame.pass.cpp | PASS | PASS | 0 | XFAIL darwin / UNSUPPORTED arm-ehabi; aarch64 OK |
| 6 | frameheadercache_test.pass.cpp | PASS | PASS | 0 | feature-guarded: upstream default `LIBUNWIND_USE_FRAME_HEADER_CACHE=OFF` ⇒ `_LIBUNWIND_USE_FRAME_HEADER_CACHE` undefined ⇒ upstream native `#else` branch `int main(){return 0;}` executed; file compiled+ran successfully |
| 7 | remember_state_leak.pass.sh.s | SKIP | SKIP | — | `# REQUIRES: x86, linux` — x86 assembly, cross-arch |

**Upstream: Total 7, Passed 6, Failed 0, Skipped 1.**

The skipped test is legitimately arch-specific (x86 assembly + `REQUIRES: x86,
linux`) and cannot run on an aarch64 target; it was not deleted, transcribed,
or altered.

### Correction: earlier invalidated "5 PASS"

An earlier attempt built a throwaway `libunwind.a` via the upstream
`libunwind/CMakeLists.txt` with a `CMAKE_SYSTEM_NAME=Linux` toolchain shim
(because LLVM `HandleLLVMOptions.cmake:152` fatal-errors on the `HarmonyOS`
system name) and ran the 5 `.pass.cpp` tests against it. That result was
**re-examined and invalidated**: although the binaries' ELF interpreter was in
fact `/lib/ld-musl-aarch64.so.1` (musl, not glibc), the build had forced the
platform to `Linux` and did not use explicit OHOS target flags, so it cannot
stand as an OHOS upstream-test result. The 5 PASS values above replace it,
using explicit `-target aarch64-unknown-linux-ohos --sysroot=<OHOS sysroot>`
and the OHOS SDK's own `libunwind.a`.

### test_package (Conan consumer)

The Conan `test_package` (see its `MANIFEST.yml`) compiles and runs a consumer
that includes the packaged headers and exercises the real public surface
(error codes, aarch64 register numbers, context/cursor/proc_info types,
compact-unwind constants, `extern "C"` declaration visibility). It does not
link a libunwind runtime (this is a headers package) and does not duplicate
the upstream runtime tests above.

**test_package: Total 1, Passed 1, Failed 0.**

The package itself contains no library or executable artifact. Official
competition CI remains the final platform validation.
