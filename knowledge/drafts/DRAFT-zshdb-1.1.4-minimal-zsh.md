# A zsh version number does not guarantee standard functions or optional modules

Status: Path B knowledge-base extension candidate for maintainer review, not a
pre-assigned grade or defense exemption.

## Symptom and cause

HarmonyOS PC reports zsh 5.9, so zshdb 1.1.4 appears to meet its minimum
version. However, official `configure` fails at `is-at-least: function
definition file not found`. Without that check, source caching fails because
`zsh/mapfile` is absent. The optional PCRE capture module is absent too:
regular-expression matching may succeed while `BASH_REMATCH` remains empty.
The target's `/tmp` is read-only. These are independent capability checks,
not a version mismatch.

The official release tarball also lists an integration test but omits its
script, command file, and expected result. The exact upstream Git tag 1.1.4
contains all three. A failure of that test from the release tarball is a
distribution defect, not necessarily a debugger defect.

## Reusable adaptation pattern

1. Check a shell's function search path and optional modules separately from
   `zsh --version`. Supply only the missing standard function with its
   upstream license, and preserve a module-backed fast path while providing
   a correct newline-preserving file-read fallback.
2. Do not interpret an empty capture array as a valid condition. For the
   debugger's limited extraction grammar, a POSIX `sed` fallback preserves
   behavior without relying on PCRE. Verify the extraction against the
   upstream unit assertions.
3. Resolve package data relative to the installed script, not a temporary
   Conan cache path. Redirect runtime scratch and test filters to a private
   writable `TMPDIR`.
4. If an archive's test manifest references missing files, compare the exact
   same-version upstream Git tag. Restore only byte-identical fixtures and
   retain the original expected output; do not silently skip or fabricate.
5. Run both the full upstream suite and a separate consumer that invokes the
   installed debugger on a real script.

## Evidence and boundaries

Official release SHA-256:
`83749450ffe030c28e7b7d1d8b06aea63232504ff61f31f9becc5a5717e69638`.
The Git-tag fixtures' SHA-256 values are recorded in
`archives/z/zshdb/1.1.4/notes.md`. Target root:
`/data/storage/el2/base/haps/entry/files/zshdb-1.1.4-work`.
Final integrated Conan log `create-v9-local-source.log` has SHA-256
`40176f82d8c845036e1eab47aa570d133bc87d13635780bc8e67102e8f7da829`.
It passed 5/5 Automake unit
cases, 34 shunit functions (216/216 assertions), 27/27 integration cases,
and the installed-package debugger consumer test.

This case differs from the existing TinyIRC passwd/terminfo entry: the
non-obvious failure is that a suitable zsh executable can omit both standard
autoload functions and optional modules. It also documents release-archive
test-fixture reconciliation. If an equivalent entry exists, merge rather
than double count. Interactive terminal behavior, editor integration, and
target network reliability were not verified.
