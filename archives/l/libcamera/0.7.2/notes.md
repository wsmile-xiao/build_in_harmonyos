# libcamera 0.7.2 OpenHarmony adaptation notes

## Scope and source

- Upstream: `https://gitlab.com/libcamera/libcamera`
- Version: `0.7.2`
- Official archive: `https://gitlab.com/libcamera/libcamera/-/archive/v0.7.2/libcamera-v0.7.2.tar.gz`
- Source SHA-256: `64881a4bafbda02f34861153d8f0d42be9ff46f5598408f9b585b07a10c448c9`
- Build target: OpenHarmony PC arm64 (`os=OHOS`, clang 15, libc++)
- Build system: Meson
- Validation date: 2026-09-30

This is a library adaptation. No `commands.json` is added: the packaged `libcamera-bug-report` and IPA proxy are internal/support artifacts, not the user-facing deliverable of this library package.

## Conan recipe and dependencies

The recipe is `libcamera/0.7.2` and requires the already published:

- `libyaml/0.2.5` for libcamera's mandatory `yaml-0.1` Meson dependency
- `openssl/3.5.6` for IPA public-key/signature verification

PLY 3.11 is downloaded from its official PyPI sdist with SHA-256
`00c7c1aaa88358b9c765b6d3000c6eec0ba42abca5351b095321aef446081da3` as a host-side IPC/code-generation tool. It is not a target/runtime dependency.

The minimal shared-library configuration enables the `uvcvideo` and `vimc`
pipeline handlers and upstream tests. Optional documentation, Android, cam,
GStreamer, Python bindings, qcam, V4L2 emulation, tracing, udev, libdw, and
libunwind integrations are disabled. The recipe rejects static builds because
upstream's Meson targets are shared libraries/modules.

The recipe generates `yaml-0.1.pc` and `libcrypto.pc` aliases in the private
Conan build environment. These point at the selected Conan dependency folders;
no ambient host library is used.

## Adaptation patch

`patches/0001-ohos-compatibility.patch` has SHA-256
`0cf0ce6b438395e224aed87f33b525e73b030981ca8666a4536c2936d648e748`.
It contains only narrow OHOS portability and test-environment changes:

- detect optional `pthread_setaffinity_np` instead of assuming it;
- use an unlinked `TMPDIR` regular file only for unsealed `MemFd` allocations
  when OHOS `memfd_create`/`fstat` behavior is unavailable; sealed allocations
  still fail rather than being unsafely emulated;
- probe whether the configured `clone3` namespace syscall actually runs and
  select the capability-backed `posix_spawn` path when it does not; use
  `waitpid` status handling instead of `waitid(P_PIDFD)` and redirect spawn
  standard streams to `/dev/null` while removing inherited non-syslog
  `LIBCAMERA_LOG_FILE`;
- guard nullable YAML diagnostic strings;
- make the Unix-socket, file, YAML, and logging tests use `TMPDIR` rather than
  assuming writable `/tmp`;
- keep the `threads.cpp` source but register its test only when
  `pthread_cancel` is available;
- keep the OpenSSL public-key generator on the selected `openssl` executable.

The patch does not convert unsupported failures to passes and does not emulate
sealed memfd behavior with ordinary files.

## Actual build and test commands

The clean Conan verification used explicit host and build profiles:

```text
conan create archives/l/libcamera/0.7.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

The recipe's `build()` runs:

```text
meson test -C <builddir> --print-errorlogs
```

The complete configured Meson graph was executed from a valid OHOS build
context. No test names were passed to an exclusion filter. The upstream
`threads.cpp` source is the one feature-detected target omission described
above; camera/media/V4L2 cases use the upstream `TestSkip` result when the
validation device has no corresponding hardware.

## Test accounting

The authoritative final clean-create log is `reports/conan-create.log`; the
clean create execution observed:

```text
Ok:                45
Expected Fail:      1
Fail:               0
Skipped:           30
```

The expected failure is upstream's intentional `timer-fail` test. Thus the
strict non-skipped/non-expected-failure result is 45/45, with zero unexpected
failures. The 30 skips are documented device/environment skips; they are not
reported as passes.

The installed-package Conan `test_package` builds and executes one real C++
consumer. It checks:

- `CameraManager::version()` contains `0.7.2`;
- `PixelFormat::fromString("NV12")` and `toString()` round-trip;
- `CameraManager::start()`/`stop()`;
- missing-camera lookup returns no camera;
- both `LIBCAMERA_IPA_MODULE_PATH` and `LIBCAMERA_IPA_PROXY_PATH` are present
  in the consumer environment and are printed;
- the program is signed before execution on OHOS.

Observed result:

```text
libcamera consumer test: version=v0.7.2, cameras=0, ipa_module_path=/storage/Users/currentUser/.conan2/p/b/libca39400e9e71c16/p/lib/libcamera/ipa, ipa_proxy_path=/storage/Users/currentUser/.conan2/p/b/libca39400e9e71c16/p/bin/libcamera
```

The zero-camera result is an environment observation: the validation device
had no `/dev/media0`-`/dev/media2` nodes. This does not claim physical camera
discovery, capture, or hardware pipeline support.

All OHOS executables used by the upstream test run, IPA signing/install step,
and installed consumer were signed with `binary-sign-tool`; the recipe checks
for exactly one `.codesign` section with `llvm-readelf` before execution.

The authoritative `conan-verify` run used the qualified reference
`libcamera/0.7.2@ohpcd/stable` and produced package ID
`f9be3ce24bb8d8f8cdc3231d9da4d156c6b87b3f`; its recipe revision was
`8568b533fd80f05f896d87903cab37c3` and package revision was
`5beaa33507a5ee85ed6b4c9dc5ff48e4`. The verifier's G0 knowledge query emitted
a non-blocking generic Meson platform warning (E090); the actual configured
libcamera graph completed successfully with the compiler-feature OHOS guard.
The verifier's G4 parser did not extract the package ID, so artifact and
security checks were independently supported by the Conan log and signed-ELF
checks rather than overstated as G4 details.

A clean retry immediately before the final pass had one transient upstream
`timer` failure (`44 OK / 1 expected failure / 1 failure / 30 skipped`) and
was preserved as `reports/conan-create-26-fail.log`; no source or recipe change
was made. An earlier clean retry also passed before the final wait-status
correction and is retained as `reports/conan-create-27-pre-process-fix.log`.
A clean retry after that correction passed with the 45/1/0/30 accounting
shown above and is retained as `reports/conan-create-28-pre-ipa-assert.log`.
The final clean retry added explicit consumer assertions that both IPA runtime
variables were received and printed; it passed the same accounting and is
preserved as `reports/conan-create-29-pass.log`.

The create log also contains non-fatal environment warnings: the OHOS shell
reported a stale/deleted working-directory path during Conan/Meson invocations,
and CMake's Unix Makefiles test build could not create its jobserver FIFO. The
package and test consumer still completed successfully; these warnings are
retained as evidence rather than hidden. The final consumer asserted that both
IPA runtime variables were received and printed their installed-package paths.
With no camera media nodes, IPA module loading and proxy execution are not
functionally exercised; only their packaged locations and runtime-path
configuration are validated.

## P1-fix validation rerun (2026-09-30)

The platform-macro fix was regenerated and verified against the official
v0.7.2 source. The new patch contains no `LIBCAMERA_OHOS` or `__OHOS__`
condition; it uses compiler/runtime capability probes. The fresh direct
command was:

```text
conan create archives/l/libcamera/0.7.2 \
  -pr:h=/storage/Users/currentUser/OpenHarmony-Adaption/build_in_harmonyos-libcamera-0.7.2/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/OpenHarmony-Adaption/build_in_harmonyos-libcamera-0.7.2/ci/conan/profiles/ohos-aarch64 \
  --build=libcamera/* --build=missing
```

`reports/conan-create-31-pass.log` records a fresh package build and
installed consumer pass with 45 OK, 1 expected failure, 0 failures, and 30
skips. The configured clone3 probe reported `NO (-31)` on this OHOS target;
`HAVE_POSIX_SPAWN` was selected and `process_test` passed. The memfd fallback
retains the fstat check documented for this target.

W3 was independently rerun. Two timer-flaky failures (`44/1/1/30`) are
preserved as `reports/w3-local-ci-p1-fix.log` and
`reports/w3-local-ci-p1-fix-rerun.log`; the subsequent clean rerun passed as
`reports/w3-local-ci-p1-fix-rerun2.log` and is copied to
`reports/w3-local-ci.log` with a regenerated `.ci-result.json`.

## Current status and limits

The local OHOS Conan create, W3 CI simulation, and installed consumer pass.
This archive is marked `built`, not `published`: PR review/approval, merge,
platform completion, and points remain pending. No physical camera behavior
is claimed.

---

**编译结束**: 2026-09-30 13:10
**最终状态**: built
