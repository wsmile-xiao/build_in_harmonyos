# ai-cli 0.4.2 HarmonyOS adaptation notes

## Scope and identity

- Issue: `2284`
- Branch: `feat/ai-cli-0.4.2`
- Upstream: `https://github.com/vercel-labs/ai-cli`
- Tag/commit: `v0.4.2` / `2a72d32793e21839439e96adc8429453f17500f1`

## W0 and build analysis

The npm manifest declares `ai@7.0.3`, `@ai-sdk/gateway@4.0.3`, and
`commander@^14.0.3`. The official release bundles them into `dist/index.js`;
remaining imports are Node.js built-ins. No separate Conan dependency is
required. The external runtime prerequisite is Node.js 22 or newer.

Upstream builds this package with Bun 1.3.9 in a Turborepo monorepo:

```sh
bun build src/index.ts --target=node --outdir=dist
```

The recipe consumes the official npm release because it already contains the
final `dist/index.js` and `dist/openh264-d6yed0d8.wasm`. It verifies those
artifacts, runs offline version/help smoke checks, packages them under
`libexec/ai-cli`, and creates the relocatable `bin/ai` launcher.

## Tests and local validation

Upstream tag `v0.4.2` contains 15 TypeScript test files with 135 `test(...)`
declarations, run by `bun test`. The npm release excludes test sources, so the
test was run from a clean upstream source checkout at commit
`2a72d32793e21839439e96adc8429453f17500f1` with Bun `1.3.9` and the lockfile.
All 135 tests passed (`135 pass, 0 fail`). The initial isolated run exposed only
a runner PATH issue for child processes invoking the `bun` command; adding the
same Bun 1.3.9 bin directory to PATH and rerunning the unchanged test command
passed all cases.

Completed locally:

- Official npm tarball SHA256 matched
  `1552fe238facb166cb09dcd626e31e53925458196e74bdbd876a2c97369c4f80`.
- Python AST, YAML parsing, `conan inspect`, and the repository L0 pre-commit
  hook passed.
- Isolated Conan 2.31.2 completed source download, `build()`, and `package()`
  with a simulated Linux x86_64 host profile.
- The resulting package contained `bin/ai`, the JavaScript bundle, and WASM.
- The real packaged launcher passed all 7 offline consumer assertions through
  Git Bash with Node.js `v24.19.0`.
- Upstream source tests passed with Bun 1.3.9: 135/135 (100%).

## OHOS real-device Shadow CI

The first single-package Shadow CI run used a clean isolated repository but its
inherited stale `origin/main` ref caused JC6 to compare against the wrong base.
After pinning the isolated `origin/main` to base commit
`f7f57bfa384017957e8b9c3fdf59bf7965c8aebd`, JC6 passed with exactly one
software and all L0 checks passed.

The second run reached `conan create` and downloaded the official npm tarball
successfully. Plain Node v24.13.0 then failed deterministically with:
`Check failed: 12 == (*__errno_location())`, Signal 5. A locked, isolated
diagnostic showed the same failure for inherited and minimal environments,
`--v8-pool-size=1`, and narrower V8 flags including `--max-opt=0`,
`--no-sparkplug`, `--no-maglev`, `--no-turbofan`, and `--single-threaded`.
Only `node --jitless` completed `--version` and `--help` successfully. This
matches the existing `aicommits`/`uglify` device workarounds.

The recipe therefore uses `--jitless` only for OHOS build smoke and the OHOS
launcher. Linux keeps the normal JIT path. On this device,
`node --jitless -e 'console.log(typeof WebAssembly)'` prints `undefined`.
The WASM file remains packaged and verified, but multimedia/OpenH264 and AI
generation paths remain unvalidated and may not work in JITless mode.

The third run passed L0, KC, JC, source download, OHOS JITless build smoke, and
package-content checks. Its only failure was test-package exit 126: the cache
materialized `bin/ai` as mode `0750`, owned by a different service UID/group,
so the SSH test process could not execute it directly. The recipe now sets the
launcher to `0755` explicitly, and the test invokes that packaged launcher via
`/system/bin/sh` on OHOS. This also avoids the documented cache/shebang direct
execution restriction while still testing the actual packaged launcher.

The final r5 run passed on the OHOS armv8 device with Node.js v24.13.0. Its
input SHA256 was `53383b4ea19264386c0ff403656d208ba98ec5a3605643e76e2f82d55a00ad49`
and isolated snapshot commit was `31f44bbb5605d10daa0e34821c0e062be3f8aabd`.
L0, KC, JC, L1, L4, L5, package creation, all 7 offline consumer assertions,
and the destructive negative test passed. The build summary was 1/1 success.
L2 was skipped as non-blocking because it directly executes the cached launcher,
while L1 successfully ran the same packaged launcher through
`/system/bin/sh` and verified version/help output.

## L0k authorization

The user explicitly authorized `archives/a/ai-cli/commands.json`. Its
`ai-cli/0.4.2` entry passed JSON and L0k name/type/version/ref checks.

## Reproduction commands

```sh
CI_PACKAGES="archives/a/ai-cli/0.4.2" zsh ci/conan/build_and_test.sh
/path/to/run-ohos-shadow-ci.sh archives/a/ai-cli/0.4.2
```

Use an isolated runner/job. Copy project `settings.yml` and profiles into its
`CONAN_HOME`, and set `TMPDIR` plus zsh `TMPPREFIX` below the runner-created
`RUN_DIR`.

## Remaining limitations

- AI generation needs a Gateway credential and network; offline validation only
  covers deterministic CLI entry points.
- Upstream Bun tests pass on the source checkout with Bun 1.3.9: 135/135
  (100%). This host result does not replace the OHOS runtime validation below.
- JITless mode disables WebAssembly on the tested Node.js runtime, so
  multimedia/OpenH264 paths need separate runtime support or follow-up testing.
