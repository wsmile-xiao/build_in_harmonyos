# libcmtspeechdata 2.1.1-git20160721-8efc468 HarmonyOS adaptation notes

## Build environment

- Build system: Autotools (Debian original source archive has `configure.ac` but no generated `configure` or `Makefile.in`; Conan build tools are `autoconf/2.72`, `automake/1.18`, and `libtool/2.5.4`)
- Build date: 2026-09-26
- Compiler: OHOS SDK clang 15, aarch64
- Conan recipe version: `2.1.1-git20160721-8efc468`
- Upstream source version: `2.1.1+git20160721~8efc468`
- Source SHA-256: `4f01aeba95fbe2c87193e41fd3eb414f0599c00b0a021411a514d797fc7acb05`

## Build approach

The recipe selects the upstream default `nokiamodem` backend, static library output, and disables optional Doxygen documentation. It declares Autoconf, Automake, and Libtool as Conan build tools. `build()` uses the Conan tool package paths explicitly and creates build-folder shims for Automake's relocatable Perl scripts, invoking them with the native Perl because the bundled Perl binary is ABI-incompatible with OHOS. It passes the matching Automake and Libtool macro directories to bootstrap so the generated files use consistent tool versions, then runs bootstrap from the extracted source directory and configures/builds the project.

The generated GNU `config.guess` does not classify the device's HarmonyOS uname. The recipe supplies `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`, following the repository's existing E160 adaptation pattern. Autoconf's generated configure script changes the `umask 077` temporary-directory setup to `022` for HMDFS (E011).

The registered D-Bus Conan package does not install `dbus-1.pc`. The recipe passes its exported include and library paths to `PKG_CHECK_MODULES`. Upstream also compiles `utils/cmtspeech_ofono_test` by default, although its Makefile omits PulseAudio flags; the recipe supplies the registered PulseAudio headers and static libraries, plus Expat's transitive library path.

## Test environment and portability patch

Upstream defines two Automake test programs. libcheck 0.15.2 runs each test case in a child process and defaults its communication temp file to musl `P_tmpdir` (`/tmp`) before checking `TMPDIR`; `/tmp` is read-only in this environment. The recipe sets `TEMP` to its writable build directory and adds Check's Conan library directory to the test runtime path (existing E571 pattern).

Both upstream test programs also hard-code their XML report to `/tmp/result.xml`. Patch `0001-tests-write-check-report-in-build-dir.patch` changes only that output path to `result.xml` in the writable test working directory; test cases and assertions are unchanged.

## Verification results

Command:

```sh
conan create archives/l/libcmtspeechdata/2.1.1-git20160721-8efc468 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

- Conan create: exit 0.
- Upstream `make check`: 2/2 Automake test programs passed; libcheck reported `test_ring` 2/2 and `test_cmtspeech_msgs` 8/8, totaling 10/10 assertions (0 failures, 0 errors).
- Conan `test_package`: installed-library consumer passed. It calls `cmtspeech_msg_encode_reset_conn_req`, validates the returned control-message type/domain and little-endian byte layout, and exits 0.

## CI bootstrap fix

The first CI run on head `3b0eac57` failed before configuration because the worker's system `autoreconf` could not run `aclocal` and its system Autoconf Perl modules were incomplete (`Autom4te/FileUtils.pm`, exit 2). Conan tool requirements plus explicit tool paths and native-Perl shims fix bootstrap without relying on worker-installed `aclocal`. The source archive URL and SHA-256 remain unchanged, and the existing `test_package/MANIFEST.yml` remains in place.

## Adaptation experience record

This package reuses existing repository knowledge entries E160 (Autotools host/build identification), E011 (HMDFS temporary directory permissions), and draft E571 (libcheck `TEMP` precedence on read-only `/tmp`). Package-specific follow-up is recorded in [knowledge.md](knowledge.md); this is archive documentation for Path A, not a separate Path B submission.
