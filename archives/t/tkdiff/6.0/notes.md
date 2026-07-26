# tkdiff 6.0 HarmonyOS PC Adaptation Notes

## Overview

TkDiff is a Tcl/Tk graphical side-by-side diff utility. Upstream ships a
single Tcl script with a shell trampoline.

## Adaptation

- No native compilation is required.
- The upstream `#!/bin/sh` trampoline was changed to `#!/usr/bin/env sh` for
  HarmonyOS PC path compatibility.
- The package declares `tk/9.0.3.1` so consumers get a `wish` runtime.

## Verification

- `test_package` checks the packaged `bin/tkdiff` script exists.
- It verifies the shebang was changed and that the script still contains
  `package require Tk` and the built-in help switch handling.
- A GUI runtime smoke test is attempted only when a display environment is
  present, because Tk GUI initialization is not reliable in headless CI.

## Source

- URL: https://downloads.sourceforge.net/project/tkdiff/tkdiff/6.0/tkdiff-6-0.zip
- SHA256: `4fa27c87846c1d6635da5beaa90ce4561638ee25a9169e455175afcf5288e453`
