# ACR 2.2.6 adaptation notes

ACR is an architecture-independent shell tool. The exact upstream tag contains
six executable scripts, three data modules, and two upstream test scripts.

The recipe replaces the upstream `@VERSION@` placeholders and makes the module
lookup relative to the packaged `bin` directory, so the Conan package remains
relocatable. There are no compiled or runtime library dependencies.

Upstream inventory: `tests/test.sh` exercises all 18 files in `examples/`, and
`tests/test-triplet.sh` contains 12 active host-triplet mappings (the OpenBSD
line beginning with `#test` is a comment and is not counted). Run the triplet
test first because `test.sh` removes auxiliary files in its directory during
cleanup. The recipe runs both scripts in a disposable copy of the source tree
for every Linux build and requires all 30 cases to pass.

The unmodified `m68k-coff` case expects the current host OS (`linux`) even
though ACR parses the target tuple as CPU `m68k`, OS `coff`. GNU `config.sub`
likewise canonicalizes it as `m68k-unknown-coff`. The Path B patch changes only
that expected OS token from `$UNAME` to `coff`; it does not skip a case, relax a
comparison, or modify ACR's implementation.

The HarmonyOS PC base image does not provide the external `getopt` utility.
ACR already has a portable argument-processing loop, so the second patch uses
the upstream `getopt` normalization when it is present and feeds the original
arguments to that same loop when it is absent. This preserves upstream behavior
on Linux and supports the documented single short/long option forms on OHOS.

Several upstream examples use versions with fewer than three components. On
shells that reject an empty arithmetic expression, the upstream `semver`
helper prints a diagnostic even though the generated configure script succeeds.
The third patch appends numeric defaults before selecting the requested field
with POSIX `cut`, so an absent component becomes `0` without requiring `awk`;
non-empty version components keep the upstream handling.

The base emulator also omits `awk` and `expr`. ACR used both unconditionally
while starting its parser even for input that needs neither tool. The fourth
patch keeps `awk` as the configured tool for directives that genuinely require
it, performs mawk detection only when `awk` exists, and uses `sed` for the
simple line-suffix operation in the unconditional tokenizer. Optional ACR
directives still report their real external-tool requirements.

Generated configure scripts previously invoked `awk` three times in
`split_host` and used `tr` in `guess_os`, even for the minimal configuration.
The fifth patch expresses the same host-triplet rules with POSIX shell `case`,
`cut`, and `sed y`, all present in the HarmonyOS PC base image. The 12-case
upstream triplet matrix remains the behavioral oracle for this logic.
