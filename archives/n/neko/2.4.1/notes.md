# Neko 2.4.1 adaptation notes

## Build approach

The recipe uses Neko's CMake build and disables optional integrations that are
not needed for the VM, compiler, tools, or C API. Zlib is supplied by Conan.
BoehmGC and libatomic_ops remain the fixed versions bundled by upstream.

## OpenHarmony changes

| Problem | Root cause | Resolution |
|---|---|---|
| BoehmGC configure fails | Its 2014 `config.guess` does not recognize HarmonyOS | Build the bundled source with its CMake project |
| Nested libatomic_ops download intermittently loses its GitHub HTTP/2 connection | ExternalProject performs a single build-time download | Fetch the official codeload archive in Conan `source()` with retries and give ExternalProject the local source directory |
| Nested BoehmGC download intermittently loses its GitHub HTTP/2 connection | ExternalProject can spend the build timeout retrying a release asset | Fetch the official codeload archive in Conan `source()` with checksum verification and retries |
| New CMake rejects BoehmGC's 2.6 policy baseline | Compatibility below CMake 3.5 has been removed | Set `CMAKE_POLICY_VERSION_MINIMUM=3.5` for the bundled project |
| `neko_thread_register` declaration conflicts with its definition | A libc header imported by `gc.h` defines a `bool` macro after Neko declares its public `int bool` typedef | Undefine only the macro after `gc.h`, preserving Neko's public ABI |
| GC cancellation code may reference a missing function | POSIX thread cancellation support varies by libc | Detect `pthread_setcancelstate`; define `NO_CANCEL_SAFE` only when unavailable |
| BoehmGC links an unavailable cancellation wrapper | OHOS libc does not export `pthread_cancel` | Detect the symbol and define BoehmGC's upstream `GC_NO_PTHREAD_CANCEL` fallback |
| Dynamic segment enumeration may be unavailable | `dl_iterate_phdr` is not exported by every libc | Define `HAVE_DL_ITERATE_PHDR` only when the symbol check succeeds |
| Build and installed tools need different library paths | All build outputs share `bin/`, while installation separates `bin/` and `lib/` | Use `$ORIGIN` for `BUILD_RPATH` and `$ORIGIN/../lib` for `INSTALL_RPATH` |
| Installed ELF files fail signature validation | CMake rewrites RPATH during installation after the linker has signed the files | Remove stale `.codesign` sections and self-sign installed tools, shared libraries, and NDLL modules |
| Upstream CMake target omits public include directories | Its exported `libneko` target cannot compile a consumer including `neko.h` | Export the Conan-native `neko::neko` target through CMakeDeps |
| Consumer cannot resolve `libneko.so.2` from the package cache | The Conan package libdir is outside the system loader paths | Match successful repository tests by running through `CONFIG_SHELL` bash with the package's absolute libdir |
| Compiler bootstrap files race in parallel Make builds | Several upstream custom rules generate shared bootstrap outputs | Match Homebrew's `deparallelize` build behavior by setting Conan's build jobs to one |

## Patches

- `0001-boehmgc-configure-build.patch`: uses CMake for bundled BoehmGC and applies
  its two capability patches.
- `0002-preserve-neko-bool-typedef.patch`: prevents a later libc `bool` macro
  from changing the type of `neko_thread_register`.
- `0003-fix-neko-runtime-link.patch`: sets target-specific build and install
  RPATH values.
- `boehmgc-0001-ohos-cancel.patch`: detects `pthread_setcancelstate` and
  `pthread_cancel`, selecting BoehmGC's upstream `NO_CANCEL_SAFE` and
  `GC_NO_PTHREAD_CANCEL` fallback paths when required.
- `boehmgc-0002-ohos-dl-iterate-phdr.patch`: detects `dl_iterate_phdr` after
  thread configuration is enabled.

## Tests

`build()` runs all four upstream CTest entries through Conan's `cmake.test()`.
`test_package` compiles and links a C API consumer with 11 explicit checks,
then runs the installed `neko -version` command. The CI result remains pending
for this revision; this file does not claim a pass before the pipeline reports
one.

## CI evidence

- Build 7066 compiled Neko, passed all four upstream CTest entries, and created
  the package; its consumer then exposed the incomplete upstream CMake target.
- Build 7085 confirmed the Conan `neko::neko` target compiles and links the C
  API consumer; its runtime then exposed the missing shared-library run trait.
- Build 7107 did not reach the updated consumer test because GitHub closed the
  libatomic_ops HTTP/2 download with a transient TLS `unexpected eof` error.
