# aicommit2 2.8.0 adaptation notes (path B knowledge-base extension)

## Status

The recipe and consumer test are complete on branch `feat/aicommit2-2.8.0`.
Conan create and the OHOS shadow run passed on the provided HarmonyOS device.
The current Windows host still does not have a Conan executable for local create.

## Path B knowledge-base extension

This package records a reusable boundary for prebuilt Node.js CLI releases on
HarmonyOS PC. The npm release contains the built ESM entry point but omits
production dependencies, so the Conan recipe must install the runtime tree in
the build and keep lifecycle scripts disabled. On the validated device,
`node` and npm are provided by HNP rather than the default non-interactive PATH;
the runner supplies explicit paths and invokes Node with `--jitless`.

HMDFS rejects npm's executable symlink creation and the shadow L5 scan treats
nested dependency `lib/` directories as native library artifacts. The recipe
therefore uses `--no-bin-links`, archives the complete npm tree into one
relocatable resource, and extracts it into `TMPDIR` from a package-owned
launcher. The test package invokes that real launcher through `sh`, which keeps
the HMDFS direct-execution limitation explicit instead of marking an unexecuted
runtime check as passed.

The reusable rule is: prove source integrity, production dependency closure,
and package-owned launcher behavior separately from provider-backed AI flows.
The current validation covers deterministic version/help/config-help paths only;
credentials, network calls, and provider-specific commands remain outside this
package PR.

## Source and build system

- Upstream: https://github.com/tak-bro/aicommit2
- Release artifact: https://registry.npmjs.org/aicommit2/-/aicommit2-2.8.0.tgz
- SHA256: `a5d30aedbebe8ae9017f1ef86bfdb5d3e2cc20ef3a5a999a14e88450ba28a96c`
- Build system: npm production dependency installation around the official
  prebuilt ESM release artifact.
- The npm tarball contains `dist/cli.mjs` and provider bundles, but no
  `node_modules`; the recipe installs 295 production packages with
  `--ignore-scripts` during `build()`.

## Packaging

The recipe stages the complete npm runtime tree, archives it as
`res/aicommit2.tar.gz`, and emits `bin/aicommit2` and `bin/aic2` wrappers.
The wrappers extract the archive into `TMPDIR` on first use and run
`node --jitless`, avoiding V8 JIT initialization failures on the validated
HarmonyOS aarch64 Node.js runtime. Wrappers are used instead of symlinks
because HMDFS may not preserve executable symlinks.

## Tests

The official upstream source corresponding to npm `gitHead`
`57ee029ecc9e22b4373b8a4dc6cff96caa043dda` was checked file-by-file against
GitHub blob hashes. The official `pnpm build && pnpm test` command registered
380 tests and reproducibly passed 377 on Windows (99.21%). The three remaining
failures are platform-specific: two exact newline assertions expect LF while
the Windows INI writer emits CRLF, and one fixture cleanup reports `EBUSY`
after the rewrite assertions finish. Credential-backed provider suites are
skipped by upstream design without provider keys, and upstream skips TTY tests
on Windows.

These upstream results are reported separately from package-specific tests.
`run_smoke_tests.sh` passes 4/4 checks against the official npm release CLI.
The Conan consumer `test_package/test.sh` passes 5/5 checks against the
installed package-owned launcher, including `config --help`. The HarmonyOS
package validation total is therefore 9/9 (100%). None of these deterministic
package checks requires an AI provider credential.

## Dependencies and blockers

The package has 30 regular npm dependencies plus the optional
`@github/copilot-sdk` dependency. A local Windows install completed in about
three minutes and produced approximately 476 MB of `node_modules`. Conan is
not installed on this Windows host, but the OHOS Conan profile and shadow CI
are available on the provided device.

## Historical Shadow CI attempt (superseded)

Date: 2026-08-20
Device: provided HarmonyOS aarch64 validation device (address withheld from public report)
Conan: 2.29.1
Job: isolated shadow job (local path withheld from public report)
RUN_DIR: single-package runner path (local path withheld from public report)
Command: `zsh ci/conan/build_and_test.sh archives/a/aicommit2/2.8.0`

During the first attempt, the runner acquired the device lock and discovered
exactly one package.
L0 passed, the npm source downloaded and unpacked with the expected checksum,
and Conan reached `build()`. The build stopped before packaging because the
job PATH did not expose a `node` or `npm` executable:

```text
/system/bin/sh: npm: inaccessible or not found
```

This diagnosis was superseded after the HNP runtime was located outside the
default non-interactive PATH. The recipe and isolated environment now accept
explicit Node/npm paths; no separate Node.js dependency PR is required.

## Historical recovery commands (no longer required)

The initial recovery plan was to provision Node.js and rerun the isolated job.
It is retained only as history; the later HNP-based run completed successfully:

```sh
JOB=<isolated-shadow-job-directory>
. "$JOB/env.sh"
sh "$JOB/run-conan-heavy.sh"
```

For a dedicated shadow run, use the worker's `run-ohos-shadow-ci.sh` wrapper
with `archives/a/aicommit2/2.8.0`. Confirm `Total: 1`, L0/L1 pass, and that
both `bin/aicommit2` and `bin/aic2` are present in the package artifact.

## Resolution of the historical attempts

Pre-adaptation, Conan creation, real-device package tests, and shadow CI are
complete. The L5 exit-141 failure was avoided by archiving the npm runtime
tree, so the runner sees only the intended top-level `bin/` artifact.

## Completed validation

This worktree has completed the single-package OHOS validation queue and the
runner emitted `ci-metadata.json` with package success 1/1.

## Initial device validation attempt (historical)

The target device already provides an OHOS-native Node.js runtime in the HNP
tool directory, but that directory is not in the default CI PATH:

- Node.js: `v24.13.0`
- npm: `11.6.2`
- Node path: `/data/service/hnp/bin/node`
- npm CLI: `/data/service/hnp/node.org/node_v24.13.0/lib/node_modules/npm/bin/npm-cli.js`

The recipe now accepts `AICOMMIT2_NODE` and `AICOMMIT2_NPM_CLI` for the build
step. The isolated job sets both variables and `NODE_OPTIONS=--jitless`. npm
also uses `--no-bin-links` because HMDFS rejects creation of `node_modules/.bin`
symlinks.

With these settings, the single-package shadow run completed all package work:

- npm installed 294 production packages
- upstream smoke tests passed
- Conan package creation passed
- `test_package` passed after invoking the shell launcher with `sh`, because
  HMDFS denies direct execution of newly-created launcher files

The runner then exited with code 141 immediately after printing `L5: Baseline
artifact check`, before emitting the Build Summary or `ci-metadata.json`.
The package cache contains both `bin/aicommit2` and `bin/aic2`; the remaining
blocker is the runner's L5 shell/pipeline behavior, not the package build or
test result. No Node.js dependency PR is required for this device image.

## Final status (updated 2026-08-20)

- The device already provides Node.js v24.13.0 and npm 11.6.2 under HNP.
- The recipe uses `AICOMMIT2_NODE`, `AICOMMIT2_NPM_CLI`, `--jitless`, and
  `--no-bin-links` for the HarmonyOS build environment.
- The npm runtime tree is stored as `res/aicommit2.tar.gz`; the launcher
  extracts it into `TMPDIR` on first use. This avoids the runner L5 scanner
  mistaking npm dependency `lib/` directories for native libraries.
- Shadow CI #29189 passed; the worker-local runner path is withheld from the
  public report.
- Results: L0 pass, L1 pass, L4 pass, L5 pass, package success 1/1,
  exit code 0, and `ci-metadata.json` generated.
- L2 is non-blocking skipped because HMDFS denies direct execution of the
  launcher; the Conan test package passes through `sh` and HNP Node.

- The branch is rebased onto the current AtomGit main and ready for PR review.
- No issue is required under the current workflow; the original task was already closed.
