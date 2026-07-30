# alsa-lib 1.2.16.1 historical SDK12 compile-only evidence

> Historical boundary: this file preserves the 2026-07-21 pre-target
> compile/link investigation. It is not the current test result. The formal
> result is the fresh OpenHarmony PC target W3 r35 in `test-report.md`:
> upstream `2/2`, consumers `11/11`, logical total `13/13` (100%).

## Scope

- Toolchain: `D:\OpenHarmony\Sdk\12\native`
- Target: `aarch64-linux-ohos`
- Official archive SHA-256:
  `f740db7f488255944ffd4428416ee3390a96742856916433df468c281436480e`
- Evidence date: 2026-07-21
- Target ELFs executed: 0

This report records the earlier cross-compilation and static ELF inspection
only. It is not W3 and does not contribute to the current target pass rate. At
the time this historical snapshot was captured, 0 of 13 target entries had
executed; target W3 r35 later superseded that state with 13/13 PASS.

The 23 log hashes below are an exact closed evidence set. The offline validator
requires every referenced file, rejects missing or additional table entries,
and checks the expected terminal marker for each log. Two logs intentionally
preserve discovery failures: the original root `check_PROGRAMS` link exposed
`pthread_cancel`, and the first shared consumer batch exposed the public
`size_t` include-order defect. Neither is represented as a passing run.

## Library build and stage

An isolated shared build and staged install completed with the four declared
patches. The staged contract is:

- one real `libasound.so`, SONAME `libasound.so`;
- one real `libatopology.so`, SONAME `libatopology.so`, NEEDED
  `libasound.so`;
- one AArch64 `aserver`, NEEDED `libasound.so`;
- 50 installed headers and 78 installed `.conf` files.

Key log SHA-256 values:

| Evidence | SHA-256 |
|---|---|
| `configure-shared-r2.log` | `9ac22637f054c21b24ec2c8a51aa244f4f0eeea5bbacb1ace6efdc6fb6e40648` |
| `make-shared-override-variable-r2.log` | `473e03cefbf7453f391b45d51d6a5ad512a0485e7d42d35e60a8cdef1bd98ecf` |
| `install-shared-override-r2.log` | `756321a22dbf5a5cd0ee51dbc3ecc1e0d9d51bffa4590679c3f1e6b596c55f41` |
| `stage-r2-artifact-contract.log` | `8c90715aa4df2d8315a5bda68d762ae3f725c9dc4c75d6136042ba4bfcc12238` |

## Upstream source entries

Automake registers exactly two upstream entries, `config` and `midi_event`.
Both compile and link as AArch64 ELFs but were not run. All 19 root
`check_PROGRAMS` outputs also compile and link; they remain build-only evidence
and are excluded from the independent test total.

The initial aggregate `check_PROGRAMS` build exposed the unavailable OHOS
`pthread_cancel` symbol in `pcm-multi-thread`. Patch 0004 skips only that call
on OHOS while keeping `running = 0` and all `pthread_join` calls; the isolated
rebuild then linked successfully.

| Evidence | SHA-256 |
|---|---|
| `build-upstream-registered-r2.log` | `3d4b51b85fbeb7a13636a41cc369380da55b7be901469f05d31560b11936a4a2` |
| `build-upstream-check-programs-r2.log` | `656c574ff4233e267c72646f5a531c2812cfe4a951a3eababe2c760019d2bb7d` |
| `build-pcm-multi-thread-patched-r2.log` | `2916684fee9176fa14c010a146d44ed9711cffd01ebe0828e341115669ab9c04` |
| `upstream-entry-build-only-readelf-r2.log` | `09b352565db991e2fef7f0927608d2226136ab1dd1004d6ca145cfca88566bc4` |

## Test-package compile-only batch

The first full batch, `consumer-build-shared-r2`, compiled the 60 ABI probes
and five behavior consumers before `AL-FUN-006` failed. The failure was kept:
`alsa/topology.h` publicly uses `size_t` without including its definition.
Adding `<stddef.h>` before that public header in the two direct topology
consumers follows existing knowledge E065 and does not change their behavior.

A fresh `consumer-build-shared-r3` batch then compiled and linked:

- 60 unique public ABI address probes, build-only and never executed;
- 6 behavior consumer ELFs;
- 2 component consumer ELFs;
- 3 package-workflow helper ELFs.

The build helper asserted 71 outputs and printed `EXECUTED_TESTS=0`.
Independent `llvm-readelf -h` inspection verified all 71 files as AArch64 ELFs
and recorded each file's SHA-256.

| Evidence | SHA-256 |
|---|---|
| `consumer-build-shared-r2.log` (expected failure) | `78678934c3b2d3fe0e248c8ae738a6b0f2eeebee359023d5659f2b42316a9ed9` |
| `consumer-build-shared-r3.log` | `5d803a86dc939c0920badb515b05ec052afef6baac47b213b94518303730bcce` |
| `consumer-build-shared-r3-readelf.log` | `d486b1be3f2bf61d58616993120dfb049ac307dd656c6907a130774959e20071` |

## Static build and consumer linkage

A fresh source extraction received the same four declared patches and was
configured with `--disable-shared --enable-static`. The first complete
configure probe reached final file generation but exceeded its outer command
timeout. After confirming no related child process remained,
`config.status --config` reported the exact static arguments and a full
`config.status` replay completed successfully. The subsequent single-thread
build and isolated install both returned zero.

The installed static contract is:

- `libasound.a`: 101 members;
- `libatopology.a`: 13 members;
- no installed `.so*` files;
- AArch64 `aserver` with no NEEDED `libasound.so*`;
- 50 installed headers and 78 installed `.conf` files.

The fresh `consumer-build-static-r1` batch compiled the same 60 ABI probes and
11 consumer/helper ELFs without executing them. Independent `llvm-readelf`
inspection verified 71 of 71 AArch64 files and zero NEEDED entries matching
`libasound.so*` or `libatopology.so*`. Shared and static modes exercise the same
independent entries and are not counted twice.

| Evidence | SHA-256 |
|---|---|
| `config-status-static-r4.log` | `7c42e6b7c564a60091a2380375012ca072c826bd25898c0e346a4e6023bfea15` |
| `make-static-r4.log` | `58ea0316a258db4c52e6fc712a29737483d662ec95a1ae86be6ad80aa7c557e7` |
| `install-static-r4.log` | `8875f2cc04acb67d5a30fdab2299d57028818132b5b6c90ea397a71958c02296` |
| `stage-artifact-contract.log` | `14ff5148db87d86578cfa7d8919f1668b18e0142d6eeecb1dae0a7863ffa439a` |
| `consumer-build-static-r1.log` | `2a6734564d4fa55136d3ec15e051d31779541a5905324f8a727e44a8790cc2f2` |
| `consumer-build-static-r1-readelf.log` | `f1ce7106e7bb5703c8dd02e96a3f5738f1a8e660ab1929db29212f2d1ea8f2da` |

## Static fPIC whole-archive regression

A new isolated static build used the standard compiler `-fPIC` flag and no
`--with-pic` configure argument. Configure, single-thread build, and staged
install all returned zero. The stage contains 101 `libasound.a` members and 13
`libatopology.a` members with no `.so*` files.

Both complete archives were then linked under `--whole-archive` into one shared
ELF with `-fPIC -shared -Wl,-z,defs`. The output is AArch64 DYN, needs only
`libc.so`, and contains no RPATH or RUNPATH. This is build-only evidence inside
the existing `AL-PKG-004` artifact workflow; it is not an additional test entry.

| Evidence | SHA-256 |
|---|---|
| `configure-static-pic-r3.log` | `8e9f18b477c8f0048ee127468754d8b9540a3ce95fcce9dad1f5233319e4f7df` |
| `config-static-pic-r3.log` | `b60d496f8e533f6183423c1436297ab3c8cd77a3f56b4867ff2680b0c2b38799` |
| `make-static-pic-r3.log` | `3c6f683591c2b5803c6163df7f677674af8b4abc4b0fb959946a6d013c16a8f8` |
| `install-static-pic-r3.log` | `1be1803ec5860e43ef4044f35de6c48082d4e49f55309e6a1486849258f3dc31` |
| `static-pic-link-r3.log` | `c92048901477d618b4ab13286148f09e97edf62ed32ef45665777e2b72cfebc6` |
| `static-pic-readelf-r3.log` | `7fab943425b6d7b3d246dcf1771a5296adc7558df61a4fe40d383bb802061954` |

## Test accounting

| Class | Independent entries | Compiled/linked | Executed | Passed | Failed |
|---|---:|---:|---:|---:|---:|
| Registered upstream tests | 2 | 2 | 0 | 0 | 0 |
| Prepared consumer flows | 11 | 11 helper ELFs in each mode | 0 | 0 | 0 |
| Total counted tests | 13 | 13 entry/helper outputs per applicable mode | 0 | 0 | 0 |
| ABI address probes (build-only) | 0 | 60 in each mode | 0 | 0 | 0 |
| Root `check_PROGRAMS` (build-only) | 0 | 19 | 0 | 0 | 0 |
| Static PIC whole-archive link (build-only) | 0 | 1 | 0 | 0 | 0 |

## Gates that remained at capture time

- fresh Conan W3 on the known HarmonyOS target;
- execution of both registered upstream entries and all 11 consumer flows;
- readback of the generated configure/build compile-sign TSV pair, both
  Automake `.trs` PASS terminals, the package ELF signing manifest, and the 11
  unique consumer signing rows;
- target library-collision and loader-isolation checks;
- evidence validation with no unexpected result;
- independent W4 audit with P0/P1 equal to zero.

The target execution, signed evidence readback, loader/package checks, and
evidence validation listed above were later completed by fresh W3 r35. Their
current hashes and terminal counts are recorded only in `test-report.md`; this
historical file does not duplicate or replace them.
