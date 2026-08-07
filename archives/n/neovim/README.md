# neovim

Neovim is a Vim-based extensible text editor.  This archive currently contains
a headless OHOS package created to unblock the `nvim-lspconfig` Vusted test
chain.

## OHOS scope

- Target: `nvim --headless`, not full interactive UI validation.
- First package route: Neovim bundled dependency build.
- Required smoke:
  - `nvim --version`
  - `nvim --headless -u NONE -i NONE '+lua print(vim.version().major)' +qa`

After the headless package lands, later Path B work can replace bundled
dependencies with explicit dependency PRs and wire `vusted ./test` into
`nvim-lspconfig`.
