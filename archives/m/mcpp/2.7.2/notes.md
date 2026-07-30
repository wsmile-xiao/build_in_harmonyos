# mcpp 2.7.2 OHOS adaptation notes

## Current recipe

- Source: official SourceForge release tarball with pinned SHA-256.
- Build system: release Autotools files driven by Conan `AutotoolsToolchain` and `Autotools`.
- Outputs: `libmcpp`, the `mcpp` command, headers, and package metadata.
- Options: `shared` selects exactly one library type; `fPIC=True` is available for static consumers and removed for shared builds.
- No local wrapper compiler, private source path, manually installed package, or hard-coded SDK executable is used.

## OHOS patches

1. `0001-config-config.guess.patch` detects HarmonyOS before the legacy platform cases.
2. `0002-config-config.sub.patch` accepts `linux-ohos` triplets.
3. `0003-configure.patch` changes the two `config.status` temporary-directory masks from `077` to `022` for HMDFS.

## Tests

- The upstream validation data requires external GCC testsuite integration and is not run as a self-contained upstream suite.
- The Conan C consumer calls `mcpp_lib_main`, validates its output file, and verifies macro expansion.
- The Conan Python consumer runs the packaged `mcpp` CLI and verifies the same expansion behavior.
- Together these are two consumer flows with six semantic assertions; temporary-file and diagnostic I/O failures are propagated.
- Current-head Buildbot evidence is recorded in the PR verification section; this versioned note does not pin a CI SHA that becomes stale after code changes.

## Status

The package is built and tested on the OHOS aarch64 worker. It remains `built` until merge and release upload.
