# nvim-lspconfig 2.5.0

## Summary

This is a Neovim Lua runtime plugin. The recipe downloads the official GitHub
tag and packages `lua/`, `lsp/`, `plugin/`, `doc/`, upstream `test/`,
`README.md`, and `LICENSE.md` under `share/nvim-lspconfig`.

## Tests

Upstream ships a Vusted test suite:

- `make test` -> `vusted ./test`
- `test/lspconfig_spec.lua` contains 9 spec cases covering `root_pattern`,
  archive-subpath stripping, user-command option parsing, available-server
  filtering, setup hooks, and config normalization.

The Path B integration workspace now provides packaged `neovim/0.11.3` and
`vusted/2.5.3-1`. In this workspace, `test_package` first checks that upstream
`lsp/` and `test/` are packaged, then runs the real upstream command equivalent
from the packaged plugin root:

```sh
vusted ./test
```

The earlier Python-only verification is kept as a package layout guard and is
not counted as an upstream Vusted pass by itself. The real upstream Vusted run
now passes on the new-port device through the Path B integration chain.

## OHOS notes

No native code is compiled. Runtime use still requires a target Neovim
installation and language server binaries outside this package.

## New Port Validation

Date: 2026-07-31

Validated on the new OHOS device port `33332` with isolated job
`nvim-lspconfig-2.5.0-upstreamtests-r1`.

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.5.0-nvim-lspconfig-2.5.0-upstreamtests-r1-conan-20260731-201209-60932`
- Command:
  `zsh ci/conan/build_and_test.sh archives/n/nvim-lspconfig/2.5.0`
- Lock wait: 1251 seconds
- Result: `Build Summary` success, 1 package built, 0 failed
- Full package reference:
  `nvim-lspconfig/2.5.0#3f006260fd93db5f07869ea1861f8cb8:fc3eeb021243959114a0318489539cad6d087e28#cb1f15ff469b7765c6ec36c6cfe3fdf3`
- Gate summary:
  `L0=pass`, `L1=pass(test_package executed)`, `L2=skip(no bin/ dir)`,
  `L4=pass(no patches)`, `L5=warn(no bin/lib artifacts; share-only plugin)`
- Test evidence: `test_package` ran
  `test_nvim_lspconfig.py` and printed
  `nvim-lspconfig upstream spec cases and runtime files are packaged`.
- Historical upstream test result for this independent package validation:
  `0/9` actual upstream Vusted tests executed; the package-level Python checks
  are recorded separately as adapted consumer validation.

## Path B integration status

- Test entry enabled: packaged `vusted ./test` from
  `share/nvim-lspconfig`
- Required packages: `neovim/0.11.3`, `vusted/2.5.3-1`,
  `busted/2.2.0-1`, and the Lua dependency chain
- OHOS upstream Vusted result: pass, `9/9`

## Knowledge Draft

This PR carries the unnumbered draft
`knowledge/drafts/DRAFT-neovim-vusted-busted-upstream-test-chain.{kv,md}` for
the Neovim headless + Vusted/Busted Path B validation pattern. The draft
intentionally has no E-number; formal numbering should happen only when the
knowledge entry is reviewed and promoted.

## Path B New Port Validation

Date: 2026-08-07

Validated on the new OHOS device port `33332` with isolated job
`neovim-vusted-pathb-integration-20260806`.

- Prerequisite `neovim/0.11.3` run:
  `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-neovim-vusted-pathb-build-neovim-r1-20260807-040203-8515`
- Prerequisite `vusted/2.5.3-1` run:
  `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-neovim-vusted-pathb-build-vusted-r4-20260807-041208-20816`
- `nvim-lspconfig/2.5.0` build and test_package run:
  `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-neovim-vusted-pathb-build-nvim-lspconfig-r1-20260807-041359-21772`
- Full package reference:
  `nvim-lspconfig/2.5.0#3f006260fd93db5f07869ea1861f8cb8:fc3eeb021243959114a0318489539cad6d087e28#cb1f15ff469b7765c6ec36c6cfe3fdf3`
- Independent upstream runner:
  `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-neovim-vusted-pathb-nvim-lspconfig-upstream-r1-20260807-041438-22122`
- Upstream command:
  `vusted ./test`
- Upstream result:
  `9/9` passed, `# Success: 9`.
