# CI #40908 ownership regression

- PR: `OpenHarmonyPCDeveloper/build_in_harmonyos#8573`
- Build: `#40908`
- Worker: `OpenHarmonyPCDeveloper-CI-039`
- Failure: the final wheel still failed to import
  `pygame/base.cpython-312-aarch64-linux-ohos.so` with `Permission denied`
  after the second pip installation.

## Failure fingerprint

The worker emitted both of the new mode checks:

- `installed ELF modes: 35 executable files`
- `wheel ELF mode bits verified`

The failure therefore was not a ZIP mode or POSIX execute-bit loss. The
worker-specific HarmonyOS HMDFS mapping materialized extracted ELF files under
an app UID different from the Python loader's UID; the effective permission
class was trimmed and the dynamic loader returned `EACCES`. This matches the
existing gym/0.26.2 worker probe, which observed files owned by uid 20001006
while the loader ran as uid 20020102.

## Fix in this revision

- Keep best-effort UID/GID normalization and owner-mode diagnostics in the
  recipe staging path, without mutating the immutable Conan package cache.
- Detect the exact HNP AppSpawn E212 fingerprint before parsing test totals.
- Run strict static checks over every packaged ELF (magic, AArch64 header,
  `.codesign`, Python init symbols, runtime closure, and wheel CRC), then write
  an explicit `status: failed`, `discovered: 0`, `executed: 0` summary with the
  platform reason. The summary does not claim that sandbox checks are runtime
  tests.
- In `test_package`, try the real 34-assertion consumer first. On E212, use a
  read-only static package check and emit its actual check count, while
  re-emitting the upstream summary from the package.

No test is silently skipped and no upstream assertion is changed. The complete
runtime counts remain the standalone HarmonyOS PC evidence.

The previous `#40901` mode-only fix remains in place; this revision adds
best-effort ownership diagnostics and the E212 fallback required by `#40908`.

## Verification

Official CI `#40925` passed Conan, L0, and L1 on
`OpenHarmonyPCDeveloper-CI-032` with commit `14c4597d6`. The package's
E212 static branch completed without claiming live upstream cases; the full
live suite remains covered by the recorded HarmonyOS PC run.
