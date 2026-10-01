# E550 - Windows OHOS cross-build and HMDFS signed ELF execution

## Problem pattern

On a Windows Conan host, a Make-based OHOS recipe can run the wrong shell or
compiler: `export CC=...` is interpreted by `cmd.exe`, and `basic_layout`
places the Makefile in `source_folder` while `build_folder` is separate.  After
cross-build, an ELF copied to HMDFS may also return `Permission denied` even
when its bytes are intact, because shared storage maps the file owner UID to a
different numeric UID between SSH sessions.

## Root cause

The recipe relied on POSIX shell variables instead of Conan's structured build
configuration, and it assumed that a chmod result visible in one session
guaranteed execution by the current UID.  The device additionally validates
OHOS ELF signatures with its native signer; host-side packaging or a JAR
signature is not target acceptance.

## Reusable repair

1. Run Make from `self.source_folder`; keep host generators in
   `self.build_folder` when the target binary cannot execute on the build host.
2. Read `tools.build:compiler_executables`, `tools.build:cflags`,
   `tools.build:exelinkflags`, and `tools.build:sysroot` from Conan conf.  Build
   command lines from argument lists and use Windows-safe quoting; never emit
   `export`, `${CC}`, or `${CFLAGS}` as a required shell contract.
3. Keep upstream tests unchanged.  If the host libc lacks a format extension
   such as `%F`, run the registered test recipe in a POSIX-compatible shell or
   use a validation-only shim, and record the host limitation separately.
4. For W3, read the current device inventory and bind endpoint, boot_id and UID.
   Transfer the official native `binary-sign-tool`, perform
   `sign -selfSign 1` on a task-private pending copy, verify `display-sign`, and
   preserve owner/group execute permission.  Exact-byte transfer/readback and
   one launch are mandatory; after launch consumption, create a successor for
   any repair.

## Evidence from scdoc 1.11.3

The first cross-build attempt failed on Windows `export`; the next failed in
the wrong Conan build directory, and the following attempt selected host `cc`.
Direct compiler binding produced a real OHOS ELF and package.  The target run
`w3-r001` then froze a genuine HMDFS UID/execute failure and released its root.
Successor `w3-r002` used the official signer archive
(`2076594` bytes,
`efb7d04e8dd326aef40d8c3788e5932a1f5b9ef4b4c1405ec049d872414306ce`),
self-signed the ELF, preserved group execute bits, and completed one target
consumer with exit code 0, zero stderr, and a 338-byte roff output.  The
registered upstream suite completed `44/44` in Git Bash; MinGW's `%F` and
Windows `find.exe` limitations were isolated to host validation evidence.

## Safety boundary

This pattern applies to Windows-hosted OHOS cross builds and shared-storage
target execution.  A local or host test pass does not prove target signing or
HMDFS acceptance.  Never copy another task's signer, mutate shared Conan cache,
reuse a consumed launch, or combine evidence across run IDs, endpoints,
boot_ids, payload hashes, or signer identities.
