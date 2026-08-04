# uglify 3.19.3 Adaptation Notes

## Identity and Source

- Conan name: `uglify`
- Upstream and npm name: UglifyJS / `uglify-js`
- Upstream tag: `v3.19.3`
- Upstream commit: `3ea33afc72462a470466473208a33379b7204765`
- Official source archive SHA256:
  `6988b64d4169c150ce46b8ae6e2c369aa82b1d67adc755236abf972c38857737`

The official GitHub tag archive is used because the npm distribution tarball
contains the runtime files but omits the upstream test tree.

## Dependency Verification

The official npm registry metadata for `uglify-js@3.19.3` has no
`dependencies`, `optionalDependencies`, `peerDependencies`, or
`bundledDependencies`. The Conan recipe therefore declares no requirements
and the installed package contains no `node_modules`.

Upstream tests use two dev-only npm packages:

- `acorn ~8.7.1`
- `semver ~6.3.0`

They are installed only in the isolated Conan source/build tree and are not
copied into the package.

The W0 preflight found no Conan dependency declarations. The direct remote
version query from this Windows workstation returned
`system acceleration policy not enabled`; version availability must therefore
also be checked by the normal OHOS/CI environment.

## Build and Packaging

UglifyJS is portable JavaScript and does not require native compilation.
`build()` runs `npm install` with scripts disabled, then executes both commands
from the complete upstream `npm test` suite under `NODE_OPTIONS=--jitless`.
The compression fixtures are partitioned by their upstream files across four
workers; every file and every case still runs, while the independent Mocha
suite remains sequential.
The upstream test harness already supports `UGLIFY_GITHUB_LAG` for slower CI
runtimes; the recipe sets it to 300,000 ms because two self-build performance
checks exceed their default ten-second budget under JIT-disabled Node.js.

`package()` copies only the runtime files declared by upstream (`bin`, `lib`,
`tools`, `package.json`, and license/documentation). It deliberately excludes
`test/`, `node_modules/`, and npm-generated lock data. The installed
`bin/uglifyjs` launcher resolves its package-relative JavaScript entry point
and invokes `node --jitless`.

## Upstream Tests

Upstream `npm test` runs:

1. `node test/compress.js`
2. `node test/mocha.js`

The tag contains 126 compression fixture files with 4,233 declared compression
cases and 25 mocha suite files with 264 `it()` cases.

The repository runner invokes all 126 compression files through the unchanged
upstream `test/compress.js` harness with four concurrent workers, then invokes
the unchanged `test/mocha.js` harness. This preserves the upstream test set
while keeping the JIT-disabled execution within the W3 wall-clock budget.

## Consumer Test

`test_package` executes the installed `uglifyjs` command, verifies its version,
compresses and mangles JavaScript from a file, executes the compressed output
with Node.js, and validates stdin-to-stdout compression. This is a real
installed-artifact test and fails when the package `bin/` directory is removed.

## Validation Evidence

- `conan-verify` completed with the `ohos-aarch64` host and build profiles.
- The upstream runner reported `Compression fixture files passed: 126/126`
  and `264 test(s) passed`.
- W3 `ci/conan/build_and_test.sh` forced a clean recipe rebuild and passed.
- The installed-package consumer test reported
  `uglify consumer tests passed`.
- Manual cache inspection found 24 package metadata/runtime files, no
  `node_modules` or `test` tree, and an executable `bin/uglifyjs`.
- The packaged CLI reported `uglify-js 3.19.3`; JavaScript compressed by that
  installed CLI executed under `node --jitless` and produced the expected
  result `42`.

The validation ran in WSL with Node.js 24.14.1 and the repository's
OpenHarmony aarch64 Conan profile. It verifies the package and JIT-disabled
runtime path locally, but is not evidence of execution on a physical
OpenHarmony device.

## Workflow Notes

The current generic `finish` implementation still checks deprecated
`packaging/` and `.staging-verified` outputs even though Archive Specification
v3.0 replaces both with Conan isolation. Its generic G0 path also assumes a
configure/make tarball build, so it is not applicable to this npm recipe.
The blocking W3 gate nevertheless completed and generated the integrity-bound
`.ci-result.json`. SUMMARY generation failed on pre-existing qpdf manifests,
not on this archive.

---

**编译结束**: 2026-07-30 00:04
**最终状态**: built
