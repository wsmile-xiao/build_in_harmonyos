# Source and build-system analysis

- Upstream release: `luaposix` v36.3
- Official source: `https://github.com/luaposix/luaposix/archive/refs/tags/v36.3.tar.gz`
- SHA-256: `82cd9a96c41a4a3205c050206f0564ff4456f773a8f9ffc9235ff8f1907ca5e6`
- Upstream Lua range: `>= 5.1, < 5.5`
- Build system: `build-aux/luke`, executed by a build-context Lua interpreter
- Host inputs: Lua 5.4 headers and library plus the profile-provided C compiler
- Build tool: Lua 5.5 interpreter; `luke` only generates and invokes compile
  commands, so its interpreter ABI does not affect the output module ABI
- Products: Lua files under `share/lua/5.4/posix` and C modules under
  `lib/lua/5.4/posix`

The only OHOS source change is the existing `luke` temporary-file patch. It
honors `TMPDIR` because `/tmp` may be read-only on the device. No additional
upstream feature is disabled.

The published `lua/5.4.8` package intentionally contains headers and
`liblua.a`, but no interpreter. The build context therefore uses the published
`lua/5.5.0` package, which provides `bin/lua`; compilation still consumes only
the host-context Lua 5.4 headers and library.

The source contains 26 upstream `specl` files plus `spec_helper.lua`. A
true-device diagnostic launched every file separately: 16 completed and 10
exposed sandbox, filesystem, identity database, PTY, timezone, or SysV IPC
differences. The 16-file OHOS-runnable subset then exited zero with 1147/1147
expectations passed, 5 upstream pending expectations, and no failures. Its file
coverage is 61.54%; the ten incompatible files are not counted as passed. The
consumer test separately validates the Lua 5.4 runtime, package search path,
pure-Lua entry point, compiled C submodule, and upstream version metadata with
six assertions.
