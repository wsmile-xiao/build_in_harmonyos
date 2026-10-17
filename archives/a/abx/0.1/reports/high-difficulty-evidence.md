# abx 0.1 high-difficulty candidate evidence

Date: 2026-08-19

## Position and scope

This document supports a Path C (high-difficulty) candidate review. It does not
self-award a category or score. The final classification belongs to the event
reviewer, and the unpublished-dependency and formal-CI gates remain explicit.
All implementation changes are confined to `archives/a/abx/0.1/`.

## Why this is more than a basic recipe

The adaptation crosses the application, build-system, package, and target
runtime boundaries:

1. The 2016 release is a GTK2 GUI application with no automated upstream test
   suite. A reviewed Debian patch supplies the GTK3 source migration, while the
   recipe supplies the HarmonyOS-specific package and target execution work.
2. Autotools must be regenerated on HMDFS. Conan-cache Automake/aclocal entry
   points require explicit SDK Perl, `config.status` needs an HMDFS-compatible
   temporary-directory mode, generated configure must run under
   `/system/bin/sh`, and make is restricted to one job.
3. The original headless CLI path still entered GTK option handling and waited
   indefinitely in a target futex. Version/help handling is now completed before
   GTK registration without weakening normal GUI initialization.
4. The package is a real OHOS/aarch64 application. The installed ELF is signed,
   its `.codesign` section is checked, and the packaged binary is executed with
   the complete dependency run environment.
5. Since upstream supplies no suite, the adaptation adds a deterministic
   installed-binary runtime entry that drives production libsndfile, ABX model,
   GTK3, and PortAudio code instead of counting empty `make check` output.

## Production defects exposed by target runtime validation

The expanded runtime gate found two defects in the upstream production code:

| Defect | Risk | Fix and proof |
|---|---|---|
| Trial bounds used `t > ntrials` | `t == ntrials` could read or write one element beyond the answer/guess arrays. | Patch 0006 changes all three accessors to `t >= ntrials`; the installed binary verifies answer, guess, and setter rejection at the exact upper bound. |
| `seek_sound_file()` assigned fractional seconds back to integer `sf_count_t` | Sub-second seek results were truncated to zero even when libsndfile sought correctly. | Patch 0008 returns the floating-point conversion directly; deterministic 0.05-second seek/read now passes on target. |

These fixes affect real application behavior and are independently covered by
the installed-binary self-test; they are not test-only expectation changes.

## Target runtime coverage

`test_package/test_abx.sh` executes 37 assertions in four scenarios:

| Area | Assertions | Target behavior |
|---|---:|---|
| Package and CLI | 8 | Installed file/permission, exact version, usage, and real options. |
| libsndfile and ABX model | 18 | Two stereo PCM fixtures, metadata/read/seek/close, equal geometry, eight trials, guess roundtrips, upper bound, and exact p-value. |
| GTK3 and PortAudio | 7 | GTK3 object model plus PortAudio version, initialize, inventory consistency, and terminate. |
| Negative inputs | 4 | Mismatched duration and malformed audio both fail and emit stable diagnostics. |
| Total | 37 | `37/37 PASS` in the r10 device integration diagnostic. |

The positive runtime line is:

```text
abx self-test: PASS files=2 frames=800 trials=8 gtk=3.24.38 portaudio-host-apis=0 portaudio-devices=0
```

The two negative paths report `audio fixtures have different geometry` and
`cannot open audio fixture`, followed by `abx test_package: PASS`.

## Reproducible device evidence

- Device run root:
  `/storage/Users/currentUser/ohpc-ci-shadow/abx-r10-0819`
- Base commit: `d7a52587f8e209b08bf64c2132f89f1b5ece3534`
- Input SHA256:
  `b4fced911d8f26d4610784393e979c49a2329a7b88806f074493d77676f9181d`
- `conan create` exit: 0
- Log SHA256:
  `da9fb4f0ee8f919e6e2389ae58d1e93a5f860591a705435750d6e7bd05f3e4c7`
- Artifact: OHOS/aarch64 PIE, 551360 bytes
- Artifact SHA256:
  `2351870532e510c81f4e6df86026b268119fe7c2d3110d063b14b48ad5517cd6`
- `.codesign` section count: 1

The run held and released the global device lock and used an isolated Conan
home populated from independently validated dependency PR caches.

## Boundaries that must remain visible

- Upstream abx 0.1 has no automated test suite. The 37 assertions are
  adaptation/runtime coverage and are never presented as upstream tests.
- The independent `portaudio/19.7.0` package currently exposes zero host APIs
  and zero devices. Initialization and inventory behavior are proven; speaker
  playback and a native HarmonyOS audio backend are not.
- `gtk/3.24.38`, `libsndfile/1.2.2`, and `portaudio/19.7.0` are not yet
  published to `ohpcd`. This run is integration prevalidation, not formal W0,
  Shadow CI, or a build-complete claim.
- The software-level `archives/a/abx/commands.json` required by L0k is outside
  this round's version-directory-only write scope.

## Classification assessment

The cross-subsystem port, target-filesystem build fixes, target startup
diagnosis, two production bug fixes, signed application packaging, and real
installed-binary runtime gate provide defensible Path C candidate material.
However, the submission must say "candidate" until the independent
dependencies are published and formal Shadow CI passes. If the event requires
a working target audio backend or a complete upstream suite for Path C, abx
does not currently meet that narrower rule and should be submitted as Path B.
