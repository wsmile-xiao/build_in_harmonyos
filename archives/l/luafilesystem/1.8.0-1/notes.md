# luafilesystem 1.8.0-1 adaptation notes

## Scope

This package adds LuaFileSystem 1.8.0-1 as a native Lua dependency for
Penlight and the Busted/Vusted chain used by nvim-lspconfig validation.

## Source

- Upstream repository: https://github.com/lunarmodules/luafilesystem
- Source archive: https://github.com/lunarmodules/luafilesystem/archive/refs/tags/v1_8_0.tar.gz
- SHA256: 16d17c788b8093f2047325343f5e9b74cccb1ea96001e45914a58bbae8932495
- LuaRocks release: 1.8.0-1

## Package layout

- Builds `src/lfs.c` directly into `lib/lua/5.4/lfs.so`
- Copies the MIT/X11 license to `licenses/LICENSE`
- Exports `LUA_CPATH` through Conan runenv

## Upstream tests

The upstream tarball includes `tests/test.lua`. The file is a standalone
assertion script, not a Busted spec file. The recipe runs an adapted working
copy during `build()` after compiling `lfs.so`. On the current OHOS runner, two
test environment assumptions need adaptation:

- upstream hard-codes `local tmp = "/tmp"`, but `/tmp` is not writable/readable
  for this SSH validation user, so the runner rewrites it to `TMPDIR`;
- upstream assumes hardlink creation works when symlink creation works, but both
  `lfs.link(..., hard=false)` and system `ln` return `Operation not permitted`
  or `Permission denied` on writable OHOS runner filesystems. The recipe-level
  runner keeps the symlink checks and skips only the hardlink-specific
  assertions when hardlink creation is denied.

## Validation plan

The test package requires `lua/5.4.8.1`, builds a small C program against
`liblua.a`, sets `LUA_CPATH`, and executes:

```lua
local lfs = require('lfs')
assert(type(lfs.currentdir()) == 'string')
assert(lfs.attributes(lfs.currentdir()).mode == 'directory')
local count = 0
for _ in lfs.dir('.') do count = count + 1 end
assert(count > 0)
```

This verifies native module loading and representative filesystem APIs needed
by Penlight `pl.dir`.

## Validation results

- Upstream run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r8-20260807-061840-58054`
- Upstream result: `0 successes / 0 failures / 1 error / 0 pending`; failure at `tests/test.lua:102`, hardlink creation returns `Operation not permitted`
- Capability probe: system `ln a b` also fails under `/storage/Users/currentUser` and `/data/storage/el*/base`, so this is a runner filesystem policy limit rather than a LuaFileSystem wrapper-only failure
- OHOS new-port run: `/storage/Users/currentUser/ohos-test-runs/codex-a-1.8.0-1-luafilesystem-4529-upstream-guard-20260807-1758-conan-20260807-181723-42885`
- Full ref: `luafilesystem/1.8.0-1#bd28f08adc22c5a00cca9975afcda232:b3c0011005d51381f1539bc96e0d2a6e4f804b4e#49bcda12cfc3524a0a4cc1cb87147f1a`
- Consumer smoke: `luafilesystem smoke ok`
- Gates: L0 pass, L1 pass, L2 skip-no-bin-dir, L4 pass, L5 pass
- Adapted upstream run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r10-20260807-065322-10699`
- Adapted upstream result: `tests/test.lua` completed with `Ok!`, Busted wrapper reported `0 failures / 0 errors`, and runner rc was 0. Busted reports `0 successes` because this upstream file is an assertion script rather than Busted `it(...)` specs.
- Recipe-level adapted upstream result: `LuaFileSystem 1.8.0`, `[hardlink skipped: Operation not permitted]`, `Ok!`.
- Upstream test modifications: the recipe now creates an adapted working copy during `build()`, rewrites `/tmp` to `TMPDIR`, and adds a hardlink capability guard; package source is not patched.
- Upstream pass-rate summary: original upstream script is `0/1 (0%)` on the current OHOS runner because hardlink creation is denied; adapted recipe-level upstream script is `1/1 (100%)`, with only hardlink-specific assertions skipped when the platform rejects hardlinks.
