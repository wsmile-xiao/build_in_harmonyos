# cliclick 5.1 — OHOS PC port notes

## Route decision: pure-C reimplementation over OH_Input (not GNUstep)

Upstream cliclick 5.1 is 100% Objective-C against Cocoa/Carbon/CoreGraphics
(plain Makefile, `-framework Cocoa -framework Carbon`). A straight rebuild on
OHOS is impossible: the SDK sysroot ships no objc headers and no libobjc.

Two routes were evaluated:

1. **GNUstep stack** (libobjc2 + gnustep-base + gnustep-gui): keeps the ObjC
   sources but adds a heavyweight dependency closure; AppKit pasteboard and
   CGEvent layers would still have to be re-backed onto OHOS APIs; the Carbon
   keycode tables would need a full rebuild anyway.
2. **Pure-C CLI re-implementation over `OH_Input_*` (chosen)**: the CLI
   contract (options, command grammar, diagnostics, `-m test` dry run) is
   small, fully specified by upstream `Test.sh`, and the event primitives map
   1:1 onto `multimodalinput/oh_input_manager.h`. Precedent: synergy-core
   1.20.4 already proves the OH_Input injection API works in this repo
   (35 patches, adapted OHOS platform layer).

Route 2 was chosen because the patch is smaller, dependency-free, and every
upstream user-visible behavior stays assertable. The macOS ObjC sources remain
in the tree untouched; the build compiles only the added `ohos/` backend
(one additive patch, replayable with `patch -p1`).

## What the patch adds

- `ohos/main.c` — portable C front end reproducing the upstream CLI contract,
  including the exact diagnostic strings asserted by upstream `Test.sh`
  (UTF-8 typographic quotes included).
- `ohos/backend.c` / `ohos/cliclick_backend.h` — `OH_Input_InjectMouseEvent` /
  `OH_Input_InjectKeyEvent` wrappers, named-key and US-layout char→keycode
  mapping over `multimodalinput/oh_key_code.h`. Button and result-code values
  are the SDK enum constants (`Input_MouseEventButton`, `Input_Result`),
  compile-time bound to the SDK header instead of hand-written numbers;
  display metrics are not used (the position read-back they would serve is
  an explicit unsupported boundary).
- `ohos/Makefile` — builds `cliclick` with `-pie -Wl,-z,relro,-z,now`.

## Runtime capability facts (device probe, this run)

Compiled with the CI-equivalent toolchain (clang 15 aarch64-unknown-linux-ohos,
SDK sysroot 26.0.0.18, linked `-lohinput`):

- `OH_Input_InjectKeyEvent` (KEY_ACTION_DOWN/UP, KEYCODE_A) → `INPUT_SUCCESS`
  **without** prior authorization. Key-based commands (kd/ku/kp/t) work.
- `OH_Input_InjectMouseEvent` (MOUSE_ACTION_MOVE) → `INPUT_PERMISSION_DENIED`
  (201) in the non-interactive session. Mouse commands are fully implemented
  but authorization-gated: the CLI fails with an explicit diagnostic naming
  `OH_Input_RequestInjection`; it never pretends success.
- `OH_Input_RequestInjection` → `INPUT_INJECTION_AUTHORIZING` (3900005); the
  authorize callback never fires non-interactively; `QueryAuthorizedStatus`
  reports `AUTHORIZING`; the probe cleans up with `OH_Input_CancelInjection`.
- `OH_Input_AddMouseEventMonitor` → 201: pointer position read-back is not
  available to CLI processes, so `p`, `.`-coordinates, relative coordinates
  and `-r` are explicit unsupported boundaries (capability-split with
  negative tests, per the E240 pattern), not silent no-ops.
- `cp` has no OHOS screen-pixel read-back API (upstream already deprecated
  the macOS API it uses) → explicit unsupported boundary.
- SDK header quirk: `oh_input_manager.h` uses `bool` in C without including
  `<stdbool.h>`; consumers must include it first.

## Upstream tests

Upstream test entry is `Test.sh` (hand-rolled bash assertions; no upstream CI).
60 assertions total: 58 are platform-independent (argument-error handling,
`-m test` dry-run output, output routing to stderr/file, `-d` routing) and run
in `test_package/test.sh` (POSIX-sh port) against the packaged binary.
The 2 clipboard assertions need `pbpaste` (macOS-only) and are recorded as
platform-blocked; the OHOS clipboard destination asserts an explicit
unsupported diagnostic instead. 14 additional OHOS capability assertions
cover the boundaries above plus version/usage smoke.
