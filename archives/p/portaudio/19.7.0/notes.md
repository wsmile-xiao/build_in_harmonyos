# portaudio 19.7.0 HarmonyOS PC adaptation notes

## Scope

- Conan coordinate: `portaudio/19.7.0`
- Issue: AtomGit #33
- Branch: `feat/portaudio-19.7.0-33`
- Build system: Autotools
- Package type: static library by default
- Status: HarmonyOS aarch64 shadow CI passed

This issue changes only `archives/p/portaudio/19.7.0`.

## W0 dependency check

The recipe intentionally disables ALSA, JACK, OSS, and ASIHPI, so it has no
direct Conan dependencies. The target-coordinate lookup and isolated device
graph check completed under the serialized device lock with the OHOS aarch64
profile. The evidence is recorded in `reports/W0-report.md`.

## Build strategy

The verified upstream release archive uses Autotools. The default package is
static because abx consumes the library directly and this avoids an additional
runtime object while retaining the complete public API. Shared builds remain a
recipe option and sign installed OHOS shared objects.

Three focused portability patches are used:

1. `0001-config-sub-ohos.patch` recognizes `aarch64-linux-ohos`.
2. `0002-configure-hmdfs-umask.patch` lets `config.status` create its temporary
   directory on HMDFS.
3. `0003-disable-pthread-cancel.patch` probes `pthread_cancel` during configure
   and selects PortAudio's existing no-cancellation path when it is unavailable.

The unused OSS backend patch and a redundant `config.guess` modification from
the baseline draft are deliberately excluded. All audio backends are disabled,
so modifying OSS source would add untested, unreachable code.

## Tests

Upstream exposes 30 `TESTS`, three QA self-tests, 47 files in `test/`, and 16
examples. Nearly all require an audio backend and physical input/output device.
The recipe selects and packages the hardware-independent `paqa_errs` QA test.
Official CI #27925 signed and ran it on OHOS with `20 passed, 0 failed`. The
other 48 inventoried targets remain deferred because they require an enabled
host API, physical audio hardware, loopback, or timing fixtures. The explicit
Conan consumer test exercises initialization and API error handling without
audio hardware. See `reports/upstream-test-inventory.md`.

The explicit Conan `test_package` links `PortAudio::PortAudio`, checks the
version structure, initializes the library, validates Host API and device
counts/default indexes, verifies an error string, terminates cleanly, and signs
and verifies the consumer ELF on OHOS. Shadow CI's R34 negative test must also
prove that the executable materially consumes package artifacts.

## Local validation

- Official source SHA-256 matched `47efbf42c77c19a05d22e627d42873e991ec0c1357219c0d74ce6a2948cb2def`.
- The three selected patches passed strict sequential `git apply --check`.
- Recipe and test recipe pass Python AST parsing.
- Shadow preflight passed at `/storage/Users/currentUser/ohpc-ci-shadow/runs/7a8ba84d2629-20260819T030432Z-preflight-33222`.
- Final Shadow run passed at `/storage/Users/currentUser/ohpc-ci-shadow/runs/7a8ba84d2629-20260819T030503Z-run-33620`.
- Source archive SHA-256: `5c7656f04e5a03649b406a6faf75874908dc48876a9ad2c4df0ef0be9e659639`.
- Input verification record: `e883b82f8bdf11f78a65acda912f799e3cd26ef65870f810960dd3f07b50b9f6`.
- Environment fingerprint: `169c18c545ecd9c53d653f26dac784fb1202e314608cbb6cc5d3a27b5d1a4410`.
- Setup log: `ba71f6fdeb307b428a794dc3267ce902bb9859d80e5848d695b8065cf6ff8ca8`.
- Build log: `03fd6f991e6616df4d46a3092b418398f0769b415fb5250270f50de1b5ec63e8`.
- Gate results: `c133933448138962779f5d466bcb28dc995f7492108d759ff8f30cc6dc554459`.
- `test_package` passed and reported `host_apis=0 devices=0`; R34 passed.
- L0/L1/L4/L5 passed; L2 was skipped because the package has no `bin/` directory.
- Official CI #27925 passed at commit `826dcf72b4971547df74eeea8e0f7722c56557b9`;
  `paqa_errs` reported `QA Report: 20 passed, 0 failed.` before the consumer ran.
