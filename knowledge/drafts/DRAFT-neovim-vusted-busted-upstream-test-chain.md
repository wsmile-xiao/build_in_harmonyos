# Draft: Neovim + Vusted/Busted upstream test chain for Path B validation

> Contributor: zxyAtom | Status: DRAFT | Created: 2026-08-24
> Scope: nvim-lspconfig/2.5.0 and similar Neovim Lua runtime plugins

## Error Surface

Neovim Lua runtime plugins can ship upstream tests whose real entry point is a
Vusted command, for example:

```text
make test -> vusted ./test
```

For `nvim-lspconfig/2.5.0`, `test/lspconfig_spec.lua` contains 9 upstream
spec cases. A Python-only `test_package` can verify package layout and selected
behavior inputs, but it does not execute those upstream Vusted cases. That
evidence must be recorded as adapted consumer validation, not as upstream-test
passes.

## Root Cause

The upstream test harness needs a packaged runtime chain:

- `neovim/0.11.3` for `nvim --headless`
- `vusted/2.5.3-1` as the Neovim-aware Lua test runner
- `busted/2.2.0-1` and the Lua dependency modules used by Vusted/Busted

Without that chain in the Conan run environment, the package can still publish
plugin files, but Path A cannot be claimed and upstream Vusted accounting stays
at `0/N`.

## Recommended Handling

1. Inventory the upstream test entry and case count before changing the recipe.
2. Package the runtime plugin directories needed by the tests, including
   `lua/`, `lsp/`, `plugin/`, `doc/`, and upstream `test/`.
3. Treat Neovim and Vusted/Busted as Path B prerequisites and build them as
   packaged dependencies for the validation workspace.
4. Run the real upstream command from the installed plugin root:

   ```sh
   cd <package>/share/nvim-lspconfig
   vusted ./test
   ```

5. Keep layout or smoke checks in `test_package`, but do not count them as
   upstream Vusted cases.
6. Record the prerequisite run directories, the consumer package run directory,
   the independent upstream runner directory, full Conan package refs, and the
   final upstream pass count.

## Validation Evidence

MR !3752 validated `nvim-lspconfig/2.5.0` on OHOS new port `33332` through the
isolated `neovim-vusted-pathb-integration-20260806` workspace.

The final upstream command was:

```sh
vusted ./test
```

The independent upstream runner reported `9/9` passed with `# Success: 9`.
The package-level Python check remains useful as an installed-layout guard but
is not counted as upstream Vusted execution.

## Non-Weakening Rule

Do not convert package layout checks, `nvim --version`, or other consumer smoke
tests into upstream Vusted pass counts. They prove a different property. A
Path B claim for this pattern requires the packaged Neovim/Vusted/Busted chain
and the real upstream command to run against the installed package root.

If the dependency PR chain is cyclic or requires human sequencing, state that
explicitly in the PR evidence instead of expecting automatic merge ordering to
prove the Path B chain.
