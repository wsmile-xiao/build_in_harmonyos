# E2165 - Probe openat2 (or similar syscalls) in a Child Process; Treat SIGSYS Child Death as "Not Supported"

## Symptom

A program that tries to detect kernel support for the `openat2` syscall by
issuing it at startup terminates abruptly with `Signal 31 (core dumped)` on
the target platform. The intended `errno == ENOSYS` fallback never runs.

## Root Cause

`openat2` was introduced in Linux 5.6. On OHOS the syscall is absent, and the
seccomp policy does **not** return `ENOSYS` — it kills the offending process
with `SIGSYS` (signal 31). A naive probe that checks `errno` after the syscall
therefore never gets a chance to fall back: the process dies in the middle of
the probe. When the probe sits in the constructor of a lazily-initialized
singleton (e.g. `PlatformInfo`), the whole process — including an entire CTest
suite — crashes on first touch.

This pattern is easy to miss because on mainstream Linux kernels the syscall
exists or returns `ENOSYS` cleanly, so the probe appears safe; only on
seccomp-hardened or syscall-limited targets does it become fatal.

## Recommended Fix

1. **Probe the syscall in a forked child process** (POSIX-based,
   platform-macro-free, R8-compliant). The child issues the syscall and exits
   with a status the parent can read; if seccomp kills the child with `SIGSYS`,
   `WIFSIGNALED` simply means "not supported" and the caller is never killed:

   ```cpp
   const pid_t pid = fork();
   if (pid == 0) {
     // Child: run the probe, then exit with a status the parent can read.
     const int fd = FileUtils::openat2(AT_FDCWD, ".", O_RDONLY, 0,
                                       FileUtils::OPENAT2_RESOLVE_IN_ROOT);
     _exit(fd >= 0 ? 0 : 1);
   }
   if (pid > 0) {
     int status = 0;
     if (waitpid(pid, &status, 0) > 0 &&
         WIFEXITED(status) && WEXITSTATUS(status) == 0) {
       d_enableOpenat2 = true;
     }
     // WIFSIGNALED(status) with SIGSYS => syscall unavailable, degrade.
   }
   ```

2. Ensure every consumer of the capability flag has a safe fallback path for
   `false` (e.g. use `openat` + `O_PATH` or relative-path resolution instead).

3. **Do NOT gate the probe with platform conditional-compilation macros**
   (e.g. `#if defined(__OHOS__)`). The project rule R8 forbids platform macros
   in source/patches — platform decisions must live in the build system
   (feature macros) or use POSIX mechanisms like the child-process probe above.
   If a runtime probe is impossible on a target, simply skip it and leave the
   capability flag at its safe default.

## Validation

recc 1.4.13 (buildbox 1.4.13) reproduced this on OHOS: after the E2164
tolerant-parse fix allowed `PlatformInfo` construction to proceed, the
`openat2` probe immediately crashed with `Signal 31 (core dumped)`. Switching
the probe to the child-process form (patch `0011-platforminfo.patch`) restored
normal execution: the child dies by `SIGSYS`, the parent reads `WIFSIGNALED`
and leaves the capability flag `false`, and the affected tests then ran their
real assertions instead of dying.

## Scope

Applies to any runtime feature probe that issues a syscall on a target where
seccomp or the kernel may kill unknown syscalls with `SIGSYS` rather than
returning `ENOSYS`. Prefer a child-process probe over errno checks; never gate
with platform macros (R8).
