# FEX-Emu 2608 HarmonyOS PC adaptation

## Scope

This entry packages upstream tag `FEX-2608` as `fex-emu/2608`. The package
contains the AArch64 user-mode x86/x86-64 emulator core (SSA IR + Arm64 JIT),
the Linux syscall emulation layer and the command line tooling: `FEX`,
`FEXServer`, `FEXBash`, `FEXGetConfig`, `FEXOfflineCompiler`, `FEXRootFSFetcher`
and `FEXpidof`.

Upstream tag: `FEX-2608` (annotated tag `cc88edf0…`) → commit
`e869aa644a16e4332cdc15c1ea0b4d13d482385d`, released 2026-08-05.

## Path C difficulty rationale

FEX-Emu is not a glue library: it is a dynamic binary recompiler. The AArch64
host binary translates guest x86/x86-64 instructions into an SSA intermediate
representation and then emits AArch64 machine code at run time, including x87,
MMX, SSE/AVX and 128-bit atomic semantics, Linux syscall emulation, guest
signal delegation and virtual memory layout mirroring. Building it exercises a
compiler-like code base (generated instruction tables, JIT, emitters), and a
meaningful validation has to execute JIT-generated code rather than just link
it. The full test matrix crosses the host/guest boundary.

## Dependencies: the release tarball has no submodules

`https://github.com/FEX-Emu/FEX/archive/refs/tags/FEX-2608.tar.gz` is a GitHub
source archive and **intentionally omits git submodules**. Nine submodules that
FEXCore needs at configure/build time are therefore pinned individually at the
exact commit recorded by the FEX-2608 tag and fetched as separate, checksum
verified sources (the recipe reproduces `git submodule update --init` without a
git checkout):

| submodule | repository | pinned commit |
|---|---|---|
| External/vixl | FEX-Emu/vixl | 5f418449c48f6ca3ad37c47ec632f17a561c0580 |
| External/fmt | fmtlib/fmt | 1be298e1bd68957e4cd352e1f676f00e07dcfb57 |
| External/xxhash | Cyan4973/xxHash | e626a72bc2321cd320e953a0ccf1584cad60f363 |
| External/range-v3 | ericniebler/range-v3 | ca1388fb9da8e69314dda222dc7b139ca84e092f |
| External/unordered_dense | martinus/unordered_dense | 3234af2c03549bc85656bfd3a86993bf1cd8aef1 |
| External/rpmalloc | FEX-Emu/rpmalloc | 1d85c246cd827ead6865f4f880d4fef53f2b1864 |
| External/Catch2 | catchorg/Catch2 | b3fb4b9feafcd8d91c5cb510a4775143fdbef02f |
| External/drm-headers | FEX-Emu/drm-headers | 3e49836995c1dcb3df709440ad2f270b569c6a5f |
| Source/Common/cpp-optparse | Sonicadvance1/cpp-optparse | 9f94388a339fcbb0bc95c17768eb786c85988f6e |

`nasm/2.16.03` is declared as a `tool_requires`; FEXCore's ASM regression suite
assembles guest x86-64 snippets with NASM.

Deliberately **not** fetched, because they are not needed for the headless
build: `External/zydis` (x86 disassembler, `ENABLE_ZYDIS=OFF`),
`External/tracy` (profiler backend, `ENABLE_FEXCORE_PROFILER=OFF`),
`External/Vulkan-Headers` (thunks, `BUILD_THUNKS=OFF`), `External/tiny-json`
(vendored in-tree, shipped by the tarball), `External/fex-*-tests-bins` (guest
x86 binaries that need a Linux rootfs) and `External/jemalloc_glibc` (see the
feature boundary below).

### vendored vs artifact repository

The artifact repository does publish `fmt`, `range-v3`, `unordered_dense`,
`xxhash` and `catch2`, and FEXCore's CMake does try `find_package()` for
several of them first. They are nevertheless vendored here because upstream
pins *exact commits* (some ahead of any release) and because `vixl`,
`rpmalloc`, `drm-headers` and `cpp-optparse` have no artifact repository
equivalent at all. Vendoring the pinned revisions keeps the build faithful to
the upstream tag.

## Feature boundary: what is disabled and why

- **FEXConfig (Qt front-end)** — disabled because Qt is not published in the
  artifact repository. `FEXGetConfig` still provides the CLI configuration
  query used by the test package.
- **glibc allocator interposition (`ENABLE_JEMALLOC_GLIBC_ALLOC=OFF`)** — FEX's
  `External/jemalloc_glibc` subproject interposes the *glibc* allocator and is
  documented upstream as "required for thunks to work". OHOS uses musl, so the
  interposition is meaningless there, and thunk execution is disabled anyway.
  FEX's own rpmalloc-based allocator (`ENABLE_FEX_ALLOCATOR`) stays enabled.
- **LTO** — disabled to keep the build time of the JIT within the CI budget; it
  has no functional effect.

## Portability changes (26 per-file patches)

Grouped by root cause:

1. **Platform / toolchain (0001, 0026)**
   - `CMakeLists.txt` only accepted `Linux` and `Windows`. The OHOS Conan
     toolchain sets `CMAKE_SYSTEM_NAME=HarmonyOS`, so the platform check now
     accepts it too.
   - The OHOS libc++ hides the C++20 ranges algorithms behind
     `_LIBCPP_ENABLE_EXPERIMENTAL` (`__config` defines
     `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` otherwise); the macro is defined for
     HarmonyOS.
   - CMake has no `Platform/HarmonyOS`, so `CMAKE_SYSTEM_PROCESSOR` stays
     `unknown`; the architecture detection now falls back to the compiler's own
     target triple.
   - A failed `program_invocation_name` probe leaves the CMake variable empty,
     which produced a bare `-DHAS_PROGRAM_INVOCATION_NAME=` and broke the `#if`
     in `ELFCodeLoader.h`; the result is normalised to `0`.
   - The same missing `Platform/HarmonyOS` module means CMake never emits the
     linker flag that records a `DT_SONAME`, so `lib/libFEXCore.so` was
     packaged without one. `FEXCore_shared` now gets
     `-Wl,-soname,libFEXCore.so` explicitly on HarmonyOS.

2. **libc++ facility gaps (0002–0015)** — see
   `knowledge/drafts/DRAFT-fex-emu-2608-ohos-libcxx-missing-cxx-facilities.*`
   for the full write-up. In short:
   - `std::atomic_ref` (C++20) does not exist → a shim header backed by Clang
     `__atomic` builtins, guarded by `__cpp_lib_atomic_ref`. 128-bit CAS is
     inlined by clang (`ldaxp/stxp`), so no `libatomic` is required.
   - `<memory_resource>` / `std::pmr` (C++17) does not exist at all → a shim
     header guarded by `__has_include(<memory_resource>)`, providing
     `memory_resource`, `polymorphic_allocator` (including uses-allocator
     `new_object`) and the pmr container aliases.
   - `fextl::move_only_function` relied on libc++ ≥16's conditional noexcept on
     `std::function`'s converting constructor. Since libc++ 15 lacks it, the
     inline-buffer criterion (`sizeof(F) <= 3 * sizeof(void*)`) is used
     directly so that small callables stay allocation free, and the wrapper now
     uses `std::invoke` so member function pointers work too.

3. **musl / uapi / userland differences (0016–0025)** — see
   `knowledge/drafts/DRAFT-fex-emu-2608-ohos-musl-uapi-runtime-differences.*`.
   In short: OHOS `sigevent` has no `SIGEV_THREAD_ID`/`_sigev_un`; `UNAME26`
   and `MREMAP_DONTUNMAP` are missing from the headers; the OHOS uapi
   `linux/socket.h` redefines `sockaddr_storage` without a guard; the kernel
   rejects `MAP_FIXED_NOREPLACE` with `ENOSYS`; `sed` is toybox (whose `a\`
   command turns `\ret` into CR + `et`); and `/tmp` is a read-only filesystem
   while the tests hardcode `P_tmpdir`.

## Verification

A formal Conan build with the OHOS clang 15.0.4 profile (`os=OHOS`,
`arch=armv8`, `build_type=Release`) completes, all 26 patches apply, and
`conan create` exits 0. The resulting binaries are AArch64 ELF executables; the
`test_package` smoke test verifies the `FEXGetConfig` and `FEXOfflineCompiler`
CLIs and the AArch64 ELF headers of `FEX`, `FEXServer`, `FEXBash` and
`FEXpidof`.

### Upstream tests: 7861 CTest cases

`BUILD_TESTING=ON` builds FEXCore's own suites. `ctest -N` reports **7861**
cases:

| suite | cases | executed | result |
|---|---|---|---|
| `FEXCore/unittests/Emitter` (AArch64 emitter, checked via vixl disassembler) | 273 | 273 | pass |
| `FEXCore/unittests/APITests` + remaining host suites (allocator, file loading, bit sets, futex spin lock, ilog2, string utils, wildcard matcher, interruptable condvar, pmr/Filesystem) | 66 | 66 | 65 pass / 1 environment-limited |
| `unittests/ASM` + `unittests/32Bit_ASM` (guest x86-64/x86 instruction tests) | 7482 | 0 | documented runtime boundary |
| `Scripts/StructPackVerifier.py` struct layout verifier | 40 | 0 | missing Python `clang` bindings on the worker |
| guest x86 loads (`POSIX`, `gvisor-tests`, `gcc-target-tests-*`) | – | 0 | need an x86 Linux rootfs |

Measured host-side result: **338 of 339 executed cases pass (99.7%)**.

Two documented non-passes:

1. `ParentPath.Filesystem.APITest` — `FHU::Filesystem::ParentPath("//.")` returns
   `"/"` while this libc++'s `std::filesystem::path("//.").parent_path()` returns
   `"//"`. The test asserts equality with libc++, and libc++ 15 treats a leading
   `//` as a root name. This is a libc++ version behaviour difference, not
   something introduced by the adaptation; FEX only uses the hand-rolled
   implementation on non-Windows. (The other 23 cases in that file pass.)
2. `Test_verify_*` (40 cases) — `Scripts/StructPackVerifier.py` imports
   `clang.cindex`; the worker has no `clang` Python bindings, and installing
   them is not an option (the bindings must match the toolchain's libclang:
   bindings 21.x against libclang 15.0.4 fail with
   `clang_CXXMethod_isDeleted` missing). These are static analysis checks and
   do not affect the built artifacts.

### Documented runtime boundary: guest execution

Every ASM test case is assembled and linked, but executing it requires FEX's
in-process harness (`TestHarnessRunner`) to JIT the guest code and finish.
On OHOS the harness stops in a single-threaded FUTEX wait during the first
guest `mmap` tracking call:

```
TRACE  before MapMemory
T-MAP  a                      → GuestMmap(0xe0000000, 40 KiB, MAP_FIXED|MAP_ANON)
G-mmap mutex acquired
G-mmap host mmap result=0xe0000000
G-mmap before TrackMmap       ← hangs here
/proc/<pid>/wchan = FUTEX     (State: S, Threads: 1, 0% CPU)
```

The first guest mapping is performed before any guest thread exists, so the
deferred-signal handshake FEX uses around VMA tracking
(`FEXCore::GuardSignalDeferringSection` → `InterruptableConditionVariable`, a
futex condvar that waits for the signal handler to notify) has nothing to
complete it. This is consistent with OHOS's libc multiplexing signals for its
own purposes (its `<signal.h>` defines `MUSL_SIGNAL_HOOK`/
`MUSL_SIGNAL_NATIVE_REMOTE` etc.), which conflicts with FEX's assumption of
owning guest signal delivery.

Consequently the ASM suite (and, for the same reason, any in-process guest
execution) cannot be exercised on OHOS today; the same applies to the
`binfmt_misc`/rootfs based end-to-end path, which additionally needs the FEX
rootfs and mount privileges. `FEX --help` correspondingly ends in
`FEXServerClient: Failure to setup client` (the FEXServer side needs the rootfs
mount). The packaged tooling that does not require guest execution
(`FEXGetConfig`, `FEXOfflineCompiler`) works and is covered by `test_package`.

This boundary is reported as-is; no test is weakened, skipped or stubbed to
make the suite look green.
