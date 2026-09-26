# oneTBB 2023.1.0

The source release is built with its CMake entry point. The recipe enables the
upstream CTest suite, while disabling examples, Python bindings, IPO, and
automatic HWLOC discovery; the public core library only requires the platform
Threads facility. On OHOS the recipe binds CMake's system name to `OHOS`,
installs into `lib`, and signs the final shared ELF files after installation.

W0 evidence for the empty Conan dependency closure is in the task directory:
`F:\\HarmonyPC\\onetbb-2023.1.0-20260905\\w0`.
---

## Validation boundaries

- Windows host Conan regression (`local-upstream/conan-create-host-final.log`):
  `conan create` completed with exit code 0 and the CMakeDeps consumer printed
  `PASS: oneTBB parallel_for computed 1000 elements`.
- The upstream OHOS-generated CTest inventory contains 142 entries. Buildbot
  #41540 ran 141 on commit `86d839949` because `conformance_resumable_tasks`
  was already omitted. The current candidate keeps `TBB_TEST=ON`, preserves
  the passing `test_malloc_used_by_lib` and `test_malloc_lib_unload` cases, and
  supports 136 entries after six named capability exclusions: resumable tasks,
  malloc compliance, and four malloc-proxy tests. The current-head platform CI
  log remains the authoritative pass/fail result; the earlier MinGW 133/139
  diagnostic is historical only.
- OHOS W3 run-02 built and signed `libtbb.so.12.3` and the real consumer passed
  on `10.62.150.125:8022`; the immutable result is in
  `F:\\HarmonyPC\\onetbb-2023.1.0-20260905\\w3\\run-02-result-frozen.json`.
- Target execution remains bound to the platform CI worker. A missing target
  test runner must be reported as a per-test-class limitation; it cannot be
  represented by setting `TBB_TEST=OFF` or by claiming the consumer smoke as
  the upstream result.

## CI repair

- Buildbot #41426 reached the upstream tbbmalloc test build and stopped because
  the OHOS SDK does not declare `pvalloc` in `malloc.h`. The recipe now applies
  `patches/0001-ohos-disable-pvalloc-test.patch`, which uses a CMake symbol
  check to disable only the unavailable `pvalloc` code path inside the overload
  test; the test itself remains registered.

- Buildbot #41450 reached 80% of the CTest build before
  `conformance_resumable_tasks.cpp` failed with 13 errors: OHOS does not expose
  `oneapi::tbb::task::suspend`, `resume`, or `suspend_point` because
  `__TBB_RESUMABLE_TASKS` is false. The follow-up patch excludes only this
  unsupported test target on OHOS; all other upstream tests remain enabled.

- The latest platform AI Review identified two correctness issues. The
  `pvalloc` compatibility hunk now uses CMake `check_symbol_exists` and a
  generic `TBB_PVALLOC_PRESENT` definition instead of an `__OHOS__` source
  guard. The consumer test now uses an explicit failure return rather than
  `assert`, so Release/NDEBUG builds still validate every computed element.

- Buildbot #41540 executed 141 cases on commit `86d839949`: 134 passed and
  seven failed. `test_global_control` and `test_tbb_header` exposed hidden RTTI
  for `unsafe_wait` across the shared-library boundary and are fixed with a
  narrow non-glibc visibility guard. `test_malloc_compliance` requires target
  address-space-limit behavior that OHOS lacks, while four malloc-proxy tests
  trapped because allocator interposition is unavailable. The candidate now
  gates those five unsupported cases while retaining the normal allocator and
  its supported tests.

- Buildbot #40659 reached the OHOS `test_package` CMake configure and failed
  because `cpp_info.libs = ["tbb12"]` made CMakeDeps search for a file named
  `libtbb12.*`; the OHOS package actually installs `libtbb.so.12.3`.
- The upstream install macro uses `NAMELINK_SKIP` for the versioned runtime
  and `NAMELINK_ONLY` for the Unix development link, so the recipe selects
  `tbb` for shared non-Windows packages and keeps `tbb12` for Windows and
  static packages. This preserves the logical `TBB::tbb` target while binding
  each consumer to the package's real linker lookup name.
- The repair is not a CI or submission pass until a fresh target consumer and
  exact-current-HEAD Buildbot run succeed.

**编译结束**: 2026-09-05 18:45
**最终状态**: built
