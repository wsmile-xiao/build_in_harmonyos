# libdav1d 1.5.4 adaptation notes

## Environment

- Upstream project: VideoLAN dav1d
- Build system: Meson
- Date: 2026-07-30
- Status: built on OHOS

## Build flow

The Conan recipe downloads the official VideoLAN GitLab archive and builds the
decoder library with a C-only Meson profile:

```bash
-Denable_asm=false
-Denable_tools=false
-Denable_examples=false
-Denable_tests=true
-Denable_docs=false
-Dtestdata_tests=false
```

The package installs headers plus `libdav1d.so*` and keeps command-line tools
out of scope. `test_package` links against the packaged library and calls
`dav1d_version()`.

## Platform findings

| # | Finding | Impact | Handling |
|---|---------|--------|----------|
| 1 | OHOS Meson receives compiler wrappers as shell scripts. | Meson cannot execute `/bin/sh` wrappers directly in this runner. | Patch the generated Meson machine file to use `[shell, compiler]` arrays. |
| 2 | `clock_gettime` and `CLOCK_MONOTONIC` are hidden under C99 unless POSIX feature macros are set. | Meson `cc.has_function('clock_gettime')` fails during configure. | Add `-D_POSIX_C_SOURCE=200809L` to OHOS Meson `c_args`. |
| 3 | The OHOS clang wrapper injects `-Wl,--code-sign`; Meson compile-only probes add `-Werror=unused-command-line-argument`. | `stdatomic.h` and GCC atomics probes fail even though atomics are usable. | Add `-Qunused-arguments` to OHOS Meson `c_args`. |
| 4 | Meson install cannot create shared-library symlinks on this worker. | Consumers need `libdav1d.so`, `libdav1d.so.7`, and intermediate SONAME names. | Copy `.so*` aliases after install when symlink creation is skipped. |
| 5 | OHOS ELF shared libraries must be signed before runtime use. | The consumer test can fail to load otherwise valid shared libraries. | Sign packaged ELF files under `lib/` and `bin/` with `binary-sign-tool -selfSign 1`. |

## Verification

Local preflight completed on the workspace branch:

```bash
python -m py_compile archives/l/libdav1d/1.5.4/conanfile.py archives/l/libdav1d/1.5.4/test_package/conanfile.py
conan inspect archives/l/libdav1d/1.5.4
conan export archives/l/libdav1d/1.5.4
git diff --check -- archives/l/libdav1d/1.5.4
```

OHOS real-device verification:

- Runner: old SSH port 56267, heavy mode with `--try-lock`.
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-libdav1d-libdav1d-1.5.4-conan-oldport-r4-upstream-tests-20260730-043719-43168`
- Full package reference: `libdav1d/1.5.4#c75f6145f2236c27a6607592cfa95d0d:01d92cf349a0dd98ff915f4bd99a04430171517f#8016237438c5ddeb04831cbc55875515`
- Result: `conan create`, upstream Meson header tests, and `test_package` passed.
- CI summary: `L0=pass`, `L1=pass(upstream tests + test_package executed)`, `L2=skip(no bin/ dir)`, `L4=pass`, `L5=pass`.
- L1e destructive negative test passed, confirming the consumer test genuinely depends on packaged headers and libraries.

Upstream test handling:

- Report: `reports/upstream-tests.md`.
- Meson registered header tests: 6/6 passed on OHOS.
- `tests/libfuzzer/dav1d_fuzzer` and `tests/libfuzzer/dav1d_fuzzer_mt`
  were built by the upstream test build, but they are not registered Meson
  `test()` entries and require a corpus for meaningful execution.
- `checkasm` was identified but not run in this package profile because it
  requires `enable_asm=true` plus the external `checkasm` wrap dependency.
- `dav1d-test-data` was identified but not run because it requires a separate
  test-data repository and `testdata_tests=true`.
