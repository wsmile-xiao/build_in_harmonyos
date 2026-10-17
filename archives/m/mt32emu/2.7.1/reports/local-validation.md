# mt32emu 2.7.1 local validation

Status: fresh Conan W3 r10 and target execution passed.

This report will record static recipe checks and the available local OHOS SDK
cross-build. It will not be used to claim W3 or target-device execution.

## First configure attempt

Both shared and static configurations stopped before compiler detection with:

```text
Compatibility with CMake < 3.5 has been removed from CMake.
```

Root cause: upstream declares `cmake_minimum_required(VERSION 2.8.12)` while
the local CMake is 4.3.3. Existing project knowledge `E187` prescribes
`CMAKE_POLICY_VERSION_MINIMUM=3.5`; the recipe now applies that cache value.

## Environment

- CMake: `4.3.3`, `D:\tools\cann_env\cmake\bin\cmake.exe`
- Ninja: `1.13.2`, `D:\tools\cann_env\ninja\ninja.exe`
- OHOS SDK: `D:\OpenHarmony\Sdk\12`
- Compiler: OHOS Clang `15.0.4`
- Toolchain: `D:\OpenHarmony\Sdk\12\native\build\cmake\ohos.toolchain.cmake`
- Source: official tag archive with SHA-256
  `e4524d52d6799a4e32a961a2e92074f14adcb2f110a4e7a06bede77050cfdaf4`

No compiler, CMake, Ninja, Conan, or other program was installed during this
validation. Conan is not available in the local Python environment, so no
`conan create` result is claimed.

## Successful configure and build

Both variants used the standalone upstream `mt32emu/` directory with:

```text
-DCMAKE_TOOLCHAIN_FILE=D:\OpenHarmony\Sdk\12\native\build\cmake\ohos.toolchain.cmake
-Dlibmt32emu_WITH_INTERNAL_RESAMPLER=ON
-Dlibmt32emu_C_INTERFACE=ON
-Dlibmt32emu_CPP_INTERFACE=ON
-DBUILD_SNAPSHOTS=OFF
-DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

Variant-specific settings and results:

| Variant | `BUILD_SHARED_LIBS` | `libmt32emu_SHARED` | Build result |
| --- | --- | --- | --- |
| shared | `ON` | `ON` | PASS, 30 Ninja steps |
| static | `OFF` | `OFF` | PASS, 29 Ninja steps |

The shared ELF has only `libc++_shared.so` and `libc.so` as external
`DT_NEEDED` entries. No SOXR or SampleRate library was linked.

## Installed artifacts

| Check | Shared | Static |
| --- | --- | --- |
| Primary library | `libmt32emu.so.2.7.1` | `libmt32emu.a` |
| Size | 519400 bytes | 698984 bytes |
| SHA-256 | `df62d95fabf2c304073fcac1c87b4d1ab40c0994eac26600128d00ca6a6a7df4` | `f4a2f9fb3e784b4582a338678965a4afbc3f12d856aa453b78ae74e635ec928c` |
| Architecture | ELF64 AArch64 | 28 AArch64 object members |
| Public headers | 15 | 15 |
| CMake package files | 4 | 4 |
| pkg-config files | 1 | 1 |

The direct upstream shared install has SONAME `libmt32emu.so.2` and creates
`libmt32emu.so -> libmt32emu.so.2 -> libmt32emu.so.2.7.1`. This confirms the
source-audit risk. The Conan recipe removes `VERSION`/`SOVERSION` from its
OHOS-only build copy. A temporary source copy with the exact same block
removed completed another 29-step OHOS arm64 build and installed exactly one
real `libmt32emu.so`, with no link members and SONAME `libmt32emu.so`. Its
SHA-256 is
`c38c9077f26d8c66e0dd84aebb34d0162d34ebedec603dbe5aba50bf69525c50`.
This validates the proposed output shape on the local filesystem; fresh Conan
W3 verification on HMDFS is still required.

Both shared and static libraries define:

```text
mt32emu_get_library_version_int
mt32emu_get_library_version_string
```

Installed metadata reports version `2.7.1` in `mt32emu.pc`,
`MT32EmuConfig.cmake`, and `include/mt32emu/config.h`.

## Consumer compile and link

The tracked `test_package.cpp` was configured against each installed
`MT32EmuConfig.cmake` and linked successfully for OHOS arm64.

| Variant | Consumer SHA-256 | mt32emu `DT_NEEDED` |
| --- | --- | --- |
| shared | `b38e723a4dcb29231848bc6ccf418e59acbd6523f7960451e4c29397e1b70451` | `libmt32emu.so.2` |
| static | `855994a2c9e95fc4f7f369a2535a0acdffea99f7672ae42385b111e38c6ac79f` | none |

Both consumers are ELF64 AArch64 executables. The shared direct-validation
consumer contains an E-drive staging RUNPATH; this is not acceptable as final
package evidence and must be rechecked with Conan's generated package target
and target runtime environment.

The first direct consumer configure used only `CMAKE_PREFIX_PATH`; the OHOS
SDK root-path policy did not search the E-drive staging prefix. Setting the
absolute `MT32Emu_DIR` to the installed CMake package directory resolved the
diagnostic. The formal Conan test uses `CMakeDeps` and `CMakeToolchain`, which
generate their own package discovery path. Its OHOS toolchain also sets
`CMAKE_SKIP_RPATH=ON`, so fresh W3 must confirm that the shared consumer uses
the generated Conan runtime environment without a cache `RPATH` or `RUNPATH`.

The tracked consumer revision retains one logical process and validates nine
semantic conditions: the integer and string versions, non-empty machine and
ROM inventories, context creation, initial closed state, renderer selection,
the missing-ROM return code, and unchanged closed state after that expected
failure. A strict Windows/x86_64 build using `-Wall -Wextra -Werror -pedantic`
ran successfully against the installed static package and printed
`PASS mt32emu consumer version=2.7.1 context=validated`; its SHA-256 is
`809fe72c12d8dd1a11482e84f2f68fc461b085cbc1d71c37205372a723653ab9`.
The refreshed OHOS/AArch64 shared and static consumers above both compiled and
linked successfully but were not executed on the Windows host.

## Test-accounting boundary

- Upstream CMake-registered tests: 0.
- Independently declared consumer flows: 1.
- Consumer flows executed on OHOS: 0.
- Shared/static compile-link repetitions do not increase the logical flow
  count.
- The consumer binary was not executed on the Windows build host because it
  targets AArch64 OHOS.

## Fresh W3 r5 candidate

The r5 candidate adds the post-link signing flow used by the verified giflib
consumer path. The shared library is signed only after CMake install; the
consumer is signed only after its complete CMake link and before execution.
Both paths use a clean intermediate, a distinct signed output, final-path
replacement, and mode `0755`.

Offline gates completed:

- Signing source contract: `2` positive and `4` negative cases passed.
- Evidence validator self-tests: `9/9` passed, including rejection of an empty
  signing section, invalid signing/PASS order, duplicate terminal PASS, and a
  shared consumer RUNPATH.
- Runner shell syntax, Python syntax, Ruff, and Git whitespace checks passed.
- W0 source/dependency/test accounting remained `8/8` passed.

| Frozen r5 item | SHA-256 |
| --- | --- |
| Candidate manifest | `4d376488ffb08b6f0338cf09c3ef9ee298f340dabb805da83de1e1fb1941ab8f` |
| Runner | `6f9641b6fdb43c93ac48dee8a1d146da7d663521ab583a36d1d139957da575e0` |
| Root recipe | `5776bd195883f2ff688f79d49ca209bbbfa8e42423dce7c7007554c3a92ac39c` |
| Test recipe | `8a1e5e0c78bf13e63b5374c258dae1ede6acfc1a780c95eeed6589f046d5adb0` |

The runner requires one non-empty signing section in the installed shared
library and in each shared/static consumer. It binds reported call-order line
numbers back to the original Conan logs. No r5 target run is claimed.

## Fresh W3 r10 result

The locked r10 candidate-manifest SHA-256 is
`4166bff68123a779082555ee4193090fa8b9d54443442f024bd918a5d2b7ba52`.
Fresh shared and static `conan create` runs both exited `0`; each executed and
passed the same single consumer flow. The recipe produced one real unversioned
`libmt32emu.so` with SONAME `libmt32emu.so`, and the shared consumer contained
no RPATH or RUNPATH. The installed shared library and both consumers each had
one non-empty signing section with the required clean-sign-execute ordering.
The returned evidence hash closure passed
`validate_fresh_w3_evidence.py`. Test accounting is upstream `0`, consumer
`1/1`; the shared/static repetition is not counted twice.

An independent W4 audit is required after this evidence synchronization.
