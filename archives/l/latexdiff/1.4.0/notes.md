# latexdiff 1.4.0 adaptation notes

## Scope

- Package: latexdiff
- Conan version path: 1.4.0
- Upstream release: 1.4.0
- Issue: #811

## Adaptation

- Added a Conan application recipe for latexdiff 1.4.0.
- Downloads the upstream 1.4.0 source archive with a pinned sha256.
- Installs the standalone `latexdiff-so` script as the default `latexdiff` command wrapper.
- Packages `latexdiff-fast`, `latexdiff-vc`, `latexrevise`, manpages, and license text.

## Tests

- The exact 1.4.0 release archive provides three executable Makefile tests:
  `test-ext`, `test-so`, and `test-fast`.
- All three tests run the bundled old/new TeX example and verify that a
  non-empty difference document is generated.
- Added `test_package` consumer smoke tests.
- The test verifies command wrappers use the OHOS-compatible `/bin/sh` shebang, along with libexec scripts, manpages, and the upstream version marker.
- The test requires Perl, executes `latexdiff --version`, and runs a real old/new TeX diff.
- The diff output is checked for delete/add markers and the changed source text.
- The consumer test also invokes `latexdiff` through `PATH` from an unrelated
  working directory to cover wrapper path resolution.

## Validation Environment

- The available DevEco PC emulator is x86_64 and does not include the aarch64 HNP/Conan toolchain used by the contest worker.
- Upstream release tests: 3/3 passed.
- A local Linux x86_64 Docker preflight completed `conan create latexdiff/1.4.0`, including the consumer `test_package`, with all checks passing.
- Added consumer test: 1/1 passed; 26/26 checks passed.
- The authoritative native OHOS/aarch64 result is the contest CI `conan create` run.
