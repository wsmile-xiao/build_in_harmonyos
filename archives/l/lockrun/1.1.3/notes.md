# lockrun 1.1.3 adaptation notes

## Scope

- Package: `lockrun/1.1.3`
- Issue: #589
- Official source: `http://unixwiz.net/tools/lockrun.c`
- SHA256: `cea2e1e64c57cb3bb9728242c2d30afeb528563e4d75b650e8acae319a2ec547`

## Adaptation

- Builds the single upstream C source with the compiler selected by Conan.
- Maps each Conan build type to explicit optimization and debug flags.
- Treats compiler warnings as errors.
- Reports a failed `execvp()` deterministically instead of reading an
  uninitialized child exit status.
- Installs the executable under `bin/lockrun`.
- Signs the packaged ELF only for OHOS builds.

The upstream server publishes this single source file over HTTP only. The
recipe uses that canonical artifact directly and requires its pinned SHA256
before compilation. Homebrew's current 1.1.3 formula records the same canonical
URL and checksum.

## Tests

The exact upstream source is one C file and contains no test harness or
registered test cases. The added `test_package` checks the packaged executable,
version output, command execution, lock-file creation, failed command
execution, and the core overrun protection: while one process holds the lock, a
second process must be rejected without executing its payload. It contains one
deterministic scenario with ten checks.

## Local validation

- Linux x86_64 `conan create`, Release: passed.
- Linux x86_64 `conan create`, Debug: passed.
- Added consumer test: 1/1 passed; 10/10 checks passed.
- The local Docker preflight is not an official OHOS armv8 CI result.
