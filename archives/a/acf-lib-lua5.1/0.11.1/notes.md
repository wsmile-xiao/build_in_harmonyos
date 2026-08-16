# acf-lib-lua5.1 0.11.1 adaptation notes

## Scope

- Issue: #2140
- Branch: `feat/acf-lib-lua5.1-0.11.1-2140`
- Package path: `archives/a/acf-lib-lua5.1/0.11.1`
- Upstream source: `https://distfiles.alpinelinux.org/distfiles/edge/acf-lib-v0.11.1.tar.gz`
- Source SHA-256: `0b89ffa3ccfc4d15c10686ead182ecfcaf78f9600028a6175573078a7a8def48`

## W0 dependency check

- Required dependency: `lua/5.1`.
- The dependency was adapted separately in issue #22 and merged as PR #4635.
- The current main branch contains `archives/l/lua/5.1`, so this package can
  proceed without mixing dependency changes into this PR.

## Source and packaging analysis

- The upstream release contains eight Lua modules and no native source.
- Its Makefile only copies the modules and creates compatibility symlinks.
- This recipe validates the complete eight-module inventory, then packages
  copies under both `share/lua/5.1/acf` and `share/lua/5.1`.
- No source patch is required for Lua 5.1 or HarmonyOS PC.
- Modules using `posix`, `subprocess`, or LuaSQL need those separate runtime
  packages. They are not declared until compatible recipes are available.

## Upstream tests and added verification

- The release has no test directory, test framework, or `make test/check`
  target. Alpine aports also marks the package `!check` with "no test suite".
- `db.lua` has ten runtime `assert` call sites that CI's source scanner treats
  as upstream tests. The test package loads the real packaged `acf.db` and
  drives all ten sites with a test-only in-memory LuaSQL stub.
- A separate consumer scenario checks all 16 packaged module entries, loads
  all eight real ACF modules, checks the top-level compatibility module, and
  exercises format and validator success/error behavior.
- Test stubs are confined to `test_package` and are not shipped in the package.
- The consumer scenario contains 35 checks; the CI-classified `db.lua`
  scenario contains 10 checks, for 45 executed checks in total.

## Difficulty classification

Classification: **Path A (basic adaptation) + Path B (knowledge extension
candidate)**.

Path A evidence:

- Pure Lua data package; no compiler, ABI, syscall, or system-service port.
- No HarmonyOS source patch and no upstream behavior change.
- One already-published dependency (`lua/5.1`).
- Platform work is limited to deterministic package layout and substantive
  target-side consumer verification.

Path B evidence:

- Added `knowledge/drafts/E324-draft-ACF51.kv` and its human-readable document.
- The draft generalizes a pure Lua 5.1 Conan pattern: exact source inventory,
  interpreter-versioned layout, real-copy compatibility imports for HMDFS,
  build/run `LUA_PATH`, target-interpreter `require` and behavior checks, and
  test-only isolation for unavailable optional integrations.
- `reports/path-b-knowledge.md` maps every recommendation to executable package
  evidence and distinguishes the contribution from E050, E132, E216, and E241.

The final Path B classification is subject to official review. This package
still does not meet Path C because it has no system-level or multi-toolchain
adaptation challenge.

## Knowledge use and contribution

- Reused E050 to replace upstream compatibility symlinks with real copies on
  HMDFS.
- Reused E132 while linking the target-side Lua runner with OHOS SDK `lld`.
- Reused the separate `lua/5.1` adaptation knowledge in
  `E216-draft-lua51-runner-make-cmake-lld`.
- Contributed `E324-draft-ACF51` for downstream pure Lua module packaging and
  target-side runtime validation. The draft is directly derived from and scoped
  to this library's adaptation.

## Validation

- Official tarball SHA-256 verified on Windows on 2026-08-13.
- Python recipe syntax, E324 KV parsing, knowledge graph integrity (319 entries),
  latest-main pre-commit, diff whitespace, and change-scope checks: passed.
- The graph validator reports one pre-existing E305 approach warning and no
  errors.
- Shadow CI #24734 passed G0/G0e and reached the target package; L0p rejected
  the two-setting recipe. The recipe now declares the full OHOS profile settings
  and retains `self.info.clear()` for a platform-independent source artifact.
- Shadow CI #24739: passed Conan `test_package`, L0, and L1. Both Lua test
  scripts fail on any missing, failed, or skipped assertion, so the successful
  run proves all 45/45 checks executed and passed.

Command:

```sh
CI_PACKAGES="archives/a/acf-lib-lua5.1/0.11.1" zsh ci/conan/build_and_test.sh
```
