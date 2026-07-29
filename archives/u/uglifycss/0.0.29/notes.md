# uglifycss 0.0.29 Adaptation Notes

## Build Environment

- Build system: custom JavaScript packaging
- Build date: 2026-07-29
- Runtime: Node.js 6.4 or newer supplied by the OpenHarmony build environment
- Conan dependencies: none

## Packaging

The official `0.0.29` source tag is copied into `res/uglifycss`. The packaged
`bin/uglifycss` launcher invokes the source CLI through `node --jitless`,
keeping the package independent of a host-specific Node.js path. This is
required by the validated HarmonyOS aarch64 Node.js v24.13.0 runtime: default
V8 JIT initialization exits with signal 5 before JavaScript executes, while
the JIT-disabled invocation runs the CLI successfully.

The codeload endpoint does not end in an archive extension, so `conandata.yml`
sets the download filename explicitly. This ensures Conan extracts the verified
source as a gzip-compressed tar archive.

## Upstream Tests

The tag includes 70 YUI CSS regression cases in `tests-yui/` and three URL
conversion scenarios in `tests-url.sh`. The original runners report failures
but return success, so `run_upstream_tests.sh` preserves their full coverage
and converts generated `*.FAILED` files or `KO` results into a failing exit
status for Conan. The wrapper runs with Bash and `set -euo pipefail`, so a
failed URL-test transformation cannot be silently ignored. Both upstream
runners execute Node through `--jitless`, so
the complete test set uses the same supported runtime path as the installed
command. The URL runner's fixed temporary path is redirected to `TMPDIR` at
execution time because `/tmp` is read-only on the validated HarmonyOS device.

The 0.0.29 source tag has three internally inconsistent snapshots.
`0001-fix-upstream-css-regressions.patch` corrects the corresponding
minification rules: RGB percentage channels remain percentages, opaque HSLA
is reduced to HSL, and `transform-origin: 0` is not expanded. After the patch,
the complete upstream set remains enabled and must pass.

## Consumer Test

`test_package` runs the installed `uglifycss` command and verifies version
reporting, standard-input minification, file minification, and `--output`.
