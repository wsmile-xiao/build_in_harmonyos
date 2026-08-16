# acf-dnscache 0.6.0 notes

## Package

- Upstream: https://gitlab.alpinelinux.org/acf/acf-dnscache
- License: GPL-2.0-only
- Type: Alpine Configuration Framework app module
- Build: pure Lua/LSP resources; upstream `all` is empty and `install` copies `dnscache*` into `$(appdir)/dnscache`

## Tests

The upstream v0.6.0 source archive does not provide a first-party automated
test suite. The added `test_package` checks the installed ACF module layout:
controller, model, roles, menu, LSP templates, and preserved template symlinks.
If a Lua interpreter is available it also parses installed `.lua` files without
executing module code.

## OHOS old-port validation

- Date: 2026-08-16
- Port: old port `56267`
- Job: `/storage/Users/currentUser/ohos-users/codex-a/acf-recover-oldport-r1-20260816-0303`
- Run: `/storage/Users/currentUser/ohos-test-runs/codex-a-acf-recover-build-both-r3-20260816-030750-37076`
- Result: `build_and_test.sh` exit 0
- Full ref: `acf-dnscache/0.6.0#3f8ffab41aadd15f3e17daed7e54b3e7:6b129b068851896169fae42d399fa922d239ce8a#24cb3bf7abb4acb9fd2ca765468f055a`
- Gates: L0 pass, L1 pass, L2 skip (`no bin/ dir`), L4 pass (`no patches`), L5 warn (`no artifacts found`, pure resource package)
- test_package: 8/8 file-layout checks passed; 2 Lua module files found

Recovery note: the first real `conan create` passed download/package, then failed
because dangling ACF template symlinks were not present in the package. The
recipe now recreates `dnscache-expert-html.lsp` and
`dnscache-status-html.lsp` when `conan.tools.files.get()` skips those links.
