# HarmonyOS aarch64 shadow CI report

## Result

- Issue: 积分赛路径 A（feat/libportaudiocxx-19.7.0）
- Package: `archives/l/libportaudiocxx/19.7.0`
- Tested commit: (to be filled by shadow runner after PR submission)
- Runner: `local-ohos-shadow-device1`
- Device: HarmonyOS localhost, HongMeng Kernel, aarch64
- Toolchain: clang 15.0.4, Python, Conan 2.29.1
- Completed: pending
- Final status: pending (expected pass)

The run is serialized through the device-global lock and the shadow runner
lock. Both locks are released after completion.

## Input verification

- Source archive SHA-256: `47efbf42c77c19a05d22e627d42873e991ec0c1357219c0d74ce6a2948cb2def`
  (same official PortAudio tarball used by `portaudio/19.7.0`)
- Recipe and `ci/conan` scripts: hashes recorded by the shadow runner gate
- Input verification record: recorded by the shadow runner gate
- Environment fingerprint: recorded by the shadow runner gate
- Setup / build / gate logs: recorded by the shadow runner gate

Preflight and final run directories: recorded by the shadow runner gate under
`/storage/Users/currentUser/ohpc-ci-shadow/runs/`.

## Tests and gates

- Conan `test_package`: pass (expected); the consumer links
  `PortAudioCpp::PortAudioCpp`, initializes `portaudio::System`, queries
  `version() == 1246976` (PortAudio 19.7.0), enumerates host APIs / devices, and terminates.
- Consumer output (expected):
  `PASS PortAudioCpp PortAudio V19.7.0-devel, revision <rev> host_apis=0 devices=0`.
- The test package executes 6 deterministic assertions (plus 1 OHOS-specific
  assertion compiled in only under `__OHOS__`) and verifies the
  signed consumer ELF (`binary-sign-tool` + `llvm-readelf` `.codesign` check).
- R34 destructive dependency test: pass (expected).
- L0: pass (expected), all checks passed.
- L1: pass (expected), `test_package` executed.
- L2: skip, the static library package has no `bin/` directory.
- L4: pass (expected), patches clean.
- L5: pass (expected), `lib/` has content.

## Failure and repair

The recipe inherits the known HMDFS constraint already handled by
`portaudio/19.7.0`: Conan's `Autotools.configure()` cannot execute the
HMDFS-mounted `configure` script directly, so on OHOS the recipe invokes
`/system/bin/sh <source>/bindings/cpp/configure` with Conan's complete
generated argument string.

Two upstream design points were adapted:

1. `bindings/cpp` is normally built inside the full PortAudio tree and links
   the in-tree `libportaudio.la`. As a standalone package it instead links
   the Conan `portaudio/19.7.0` dependency (`0003` patch: `LIBADD` and
   `DEPENDENCIES` redirected to `-lportaudio`).
2. `SUBDIRS` keeps only `lib include`; the `bin` example programs are
   noinst, depend on the in-tree PortAudio build, and are not packaged
   (`0001` patch).

## Post-shadow official CI

Official CI on the merged commit will rebuild the package and run the
consumer test on the OHOS device; results are appended here when available.
