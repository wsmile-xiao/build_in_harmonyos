# E260: Execute the validated fixed-interpreter descriptor

## Symptom

A signed native launcher exits 126 or 127 even though a fixed Python candidate
exists and is executable. It may select an executable shell wrapper, or it may
validate a real ELF and then execute a different object after the pathname is
atomically replaced.

## Scope

Use this pattern for signed C or C++ launchers that invoke a Python companion
through fixed absolute interpreter candidates and deliberately prohibit shell
or `PATH` fallback.

## Root Cause

`stat()`, `S_ISREG()`, and `access(X_OK)` do not prove that an executable file
is an ELF. Reading ELF magic is still insufficient if the launcher closes that
descriptor and later calls path-based `execv()`: validation and execution are
then separate pathname operations, leaving a same-UID replacement window.

## Fix

1. Keep the fixed absolute-path allow-list.
2. Open each candidate read-only and compare path and open identities.
3. Require the first four bytes to match ELF magic.
4. Keep that descriptor open and execute it with `fexecve()` or an equivalent
   fd-bound primitive.
5. Fail closed when every candidate is non-ELF.

## Forbidden Shortcuts

- Do not search `PATH` or invoke `/bin/sh`.
- Do not accept `stat() + X_OK` as final proof.
- Do not close the verified descriptor and reopen the pathname for execution.

## Validation

Cover three independent negative contracts:

- an executable wrapper followed by a valid ELF selects only the ELF;
- an all-non-ELF allow-list fails deterministically without shell fallback;
- replacing the candidate pathname after validation does not change the inode
  executed through the retained descriptor.

GraalVM 25.0.3 implements the pattern in
`archives/g/graalvm/25.0.3/files/native_image_launcher.c` and exercises it from
the Native Image consumer tests in PR #3928.

## Related Knowledge

- E083 covers JDK/JNI signature compatibility, not interpreter object binding.
- E232 covers Libtool wrapper discovery, not a signed launcher's exec boundary.
