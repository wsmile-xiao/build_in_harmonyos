# pygame 2.6.1 test report

## Upstream inventory

- Source: official PyPI pygame 2.6.1 sdist
- Runner: `python -m pygame.tests`
- Top-level test modules: 45
- Modules scheduled by the runner: 44
- Upstream tag exclusion: `scrap_test` (`ignore`)
- Static `test_*` methods: 1,773
- Runtime cases in the host reference: 1,855

## Windows host reference

Command:

```text
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=disk python -m pygame.tests -v
```

| Result | Count |
|---|---:|
| Ordinary pass | 1,794 |
| Upstream expected failure | 14 |
| Upstream skip | 47 |
| Failure | 0 |
| Error | 0 |
| Unexpected success | 0 |
| Total | 1,855 |

Exit code: 0. All executed non-skipped cases produced an accepted upstream
outcome. Raw log:
`output/pygame-2.6.1/reports/host-upstream-tests.log`, SHA256
`a67cef742700ba0fe8bd4d4aa7bc68739a624338bdf00804f8f793f6c38c56ce`.

## Windows sdist build probe

The official source reached dependency configuration, downloaded upstream
Windows SDK bundles, and stopped before compilation because MSVC 14.3 was not
installed. Exit code: 1. This result only records the Windows host prerequisite
and is not an OHOS build conclusion. Raw log:
`output/pygame-2.6.1/reports/host-sdist-build.log`, SHA256
`70b870cb1ac33f38eb3114a851a6bdeb3fe687b11e218a7fa78af2970043ccdd`.

## Consumer probe host reference

The same `test_package/test_pygame.py` entry intended for the device was run
against the official pygame 2.6.1 Windows wheel with dummy video and audio
drivers. All 34 assertions passed and the process returned 0. Raw log:
`output/pygame-2.6.1/reports/host-consumer-stop-normal.log`, SHA256
`f6e8d49462541e59550840acff90eba9bfe311500237f391c90d9726167eb718`.

The `--self-test-failure` negative control ran the same functional checks,
failed its injected assertion 35 and returned 1 as required. Raw log:
`output/pygame-2.6.1/reports/host-consumer-stop-negative.log`, SHA256
`90cab8132a8600f1acb9561d1fc215352efc35e881a9049092f7f6da9686c597`.

## HarmonyOS build and tests

Status: target run 5 passed; CI mode-preservation fix is pending rebuild.

Target attempt 1 (2026-09-04) passed environment setup, source/language checks,
and W0, then failed before pygame compilation in the
`sdl2/2.30.10.1:shared=True` dependency test link (`-lSDL2` not found). This is
recorded as a failed dependency configuration, not as a pygame test result.
The recipe now consumes the published PIC-static SDL2 configuration and
derives its private shared runtime; later target runs verified this design.
See `device-g2-attempt-1.md` for the preserved failure fingerprint and evidence
archive hash. The follow-up run reached pygame compilation but stopped on the
SDL header-root omission (`SDL.h`); see `device-g2-attempt-2.md`.

Attempt 3 (`20260904T181656Z-10027`) built, signed, repacked, and reinstalled
the final OHOS wheel, then executed all 1,855 upstream cases. It reported
1,746 ordinary passes, 14 expected failures, 47 skips, 12 failures, and 36
errors. The exact groups and bounded recipe/test-environment corrections are
recorded in `device-g2-attempt-3.md`.

The next device run (`20260905T105823Z-5672`, archive SHA256
`742986b27a597a0e55b7cbf5b14ac29da2a96fadad73611f312dd5d5eeebecdf`) reached
the same 1,855-case inventory and reduced the unexpected set to one dummy
audio `Channel.queue` timing assertion. `device-g2-attempt-4.md` records the
failure fingerprint. A source patch prevents the stop callback from restarting
queued audio. The upstream queue test is unchanged, including all 11
assertions. The target skip count remains 73.

Selected target run `20260905T181436Z-54433` used CPython 3.12.9 and OHOS
Clang 15.0.4. W3 executed the exact 1,855-case and 44-module inventory with
1,768 ordinary passes, 14 expected failures, 73 declared capability/upstream
skips, and zero failures or errors. The original `Channel.queue` test passed.
The packaged consumer passed all 34 assertions. Its structured results were:

| Result | Count |
|---|---:|
| Ordinary pass | 1,768 |
| Upstream expected failure | 14 |
| Declared skip | 73 |
| Failure | 0 |
| Error | 0 |
| Total | 1,855 |

The generated W3 result has integrity hash `3eece1eee3fba97e`. Its recorded and
independently recomputed log SHA256 both equal
`fb2439568a14381e58a79392dc95f3108ed83faed32bbf3083471241abd81c45`.
The received evidence archive SHA256 is
`fefe05fe105950512d39bfae50353dbbd43a3d6d0c8a90c9b0b9983057fe1283`.
The structured consumer marker reports `sdlDynamicApiClean=true`; both W3 and
the standalone consumer logs are free of the SDL override diagnostic. See
`device-g2-attempt-5.md`.

The standalone minimal-package test passed 34/34 assertions and returned 0.
The negative control repeated all functional assertions, failed its injected
assertion 35, and returned 1. The validated wheel is 17,507,956 bytes with
SHA256 `5fb4cdcfa7f56461b00a612c2c79086bd4066ca5efb459bff4314eb18c2c6246`.
The device session log SHA256 is
`059c3198ea7c2de2cec8936a68dd6453518171cb32ccab8aaf0c00325bd1973e`.

## CI follow-up

Official CI build `#40901` compiled the recipe but failed while importing the
final wheel after its second pip installation. The first follow-up normalized
ZIP and filesystem execute modes. CI `#40908` reported the same import failure
even with 35 executable ELF files and verified wheel mode bits, proving mode
loss was no longer the cause. The remaining cause is the worker's HMDFS UID
mapping, where extracted files are owned by a different app UID than the Python
loader. The current revision keeps best-effort staging diagnostics, detects the
E212 fingerprint, and performs strict read-only ELF/signature/ABI/wheel checks
without counting sandbox-static checks as runtime cases. The consumer follows
the same live-first/static-fallback rule. CI `#40925` subsequently passed for
the implementation commit; the current metadata update preserves that result.

Official CI build `#40925` passed on worker `OpenHarmonyPCDeveloper-CI-032`
for commit `14c4597d6` (Conan, L0, and L1 all passed). The worker reached the
documented HNP AppSpawn E212 path: it preserved the real import failure and
completed read-only signed-artifact checks; it did not count sandbox checks as
runtime cases. The standalone HarmonyOS PC run remains the authoritative full
runtime result (1,855 cases and 34 consumer assertions), and the version
status is `built`.

This device evidence was produced from baseline
`f5131ee224ce0f5028e6bba671ea1a1f23342f35`. The final task branch is rebased
to `dfe3d3ac77fa7afa801d0a7223122e63f43802c3`; that range changes neither
pygame nor the selected dependency recipes. Its OHOS profile change only adds
the SDK LLVM `libxml2` loader directory, and its package-loop change only
extends the repository root allowlist.

The recipe first derives and validates private `libpygame_sdl2.so` and
`libpygame_sdl2_mixer.so` runtimes from the published PIC-static packages. It signs and repacks the
wheel, deletes the initial staging tree, reinstalls that exact final wheel, and
only then runs the full installed upstream suite during `conan create`. The
consumer probe now executes 34 assertions. Both commands return nonzero on any
unexpected failure. The real-device procedure is documented in
`device-test.md`.

Host validation of the source patch and the updated consumer is documented in
`stop-patch-verification.md`; the selected W3 run supplies the OHOS evidence.
