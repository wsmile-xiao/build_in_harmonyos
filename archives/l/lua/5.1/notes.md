# lua 5.1 adaptation notes

## Scope

- Issue: 22
- Branch: feat/lua-5.1-22
- Package path: archives/l/lua/5.1
- Upstream source: https://www.lua.org/ftp/lua-5.1.tar.gz
- Source sha256: 7f5bb9061eb3b9ba1e406a5aa68001a66cb82bac95748839dc02dd10048472c1

## W0 dependency check

- Required Conan dependencies: none.
- System libraries: libm and libdl.
- Optional readline/history/ncurses support is disabled. Lua 5.1 upstream `linux` target enables readline and links `-lreadline -lhistory -lncurses`; this recipe avoids that target and supplies `-DLUA_USE_POSIX -DLUA_USE_DLOPEN` directly.

## Build-system analysis

- Build system: hand-written Makefile.
- No configure script.
- Top-level `make test` runs `src/lua test/hello.lua`.
- Top-level `make install INSTALL_TOP=<prefix>` installs `bin/lua`, `bin/luac`, headers, `lib/liblua.a`, and man pages.

## Conan packaging decisions

- The recipe builds directly with clang instead of invoking make. The current OHOS runner image does not expose a usable `make` binary in non-interactive Conan builds.
- Source lists are taken from upstream `src/Makefile`.
- `-fPIC` is used so static lib consumers can link in common Conan scenarios.
- `LUA_USE_DLOPEN` is enabled with `-ldl` so Lua 5.1 can load C modules when consumers need it.
- The package exports the embeddable headers and static library only. The recipe still builds and runs the upstream interpreter during `build()`, but it does not install `lua`/`luac` into `bin` because the current target use case is a dependency for `acf-lib-lua5.1` and the generic shadow-CI command smoke probe only checks `--version`/`--help`, which Lua 5.1 does not support.
- Package exports `lua::lua` and pkg-config name `lua-5.1`.

## Test package

`test_package` builds and runs a C API smoke test that verifies:

- `luaL_newstate` succeeds.
- The math standard library opened by `luaL_openlibs` executes `math.sqrt`.
- `luaL_loadstring` plus `lua_pcall` returns the expected result.
- `_VERSION` is exactly `Lua 5.1`.
- `package` table and `require` are available through the standard package library.

The test package compiles the C smoke test directly with clang from Conan profile settings. It intentionally avoids CMake because the current OHOS runner image does not expose a usable `cmake` binary in non-interactive Conan builds.

## Local verification

- Source tarball downloaded from lua.org and sha256 verified on Windows.
- Makefile and `luaconf.h` inspected locally.
- Python syntax check passed for Conan recipe files.
- Local `conan create` was not run because this Windows front-end has no `conan` command.
- First true-device shadow CI attempt reached `build()` and failed because `make` was not available; recipe was revised to build without make.
- Second true-device shadow CI attempt built and packaged Lua successfully, then failed because test_package used CMake; test_package was revised to compile directly with clang.
- Third true-device shadow CI attempt built and packaged Lua successfully, then failed because `package.loadlib` is not exposed on the current OHOS runtime; the test now avoids requiring dynamic C module loading for this pure Lua dependency path.
- Fourth true-device shadow CI attempt showed default `package.path` is not initialized as a string on this runtime; the test now verifies `package` and `require` availability while explicitly assigning `package.path`.
- A follow-up interpreter probe confirmed `require` and `package.path` are available; the earlier C smoke test misused Lua 5.1 `luaL_dostring`, which discards return values. The test now uses `luaL_loadstring` plus `lua_pcall` and direct C API global checks.
- Shadow CI run `/storage/Users/currentUser/ohos-test-runs/codex-5.1-lua-5.1-issue22-conan-20260807-184157-14862` passed `conan create`, test_package, L1, L5, and L1e; it stalled in the generic L2 command smoke test while probing packaged CLI binaries with long options. The package surface was then reduced to the dependency artifacts required by consumers.
- Final shadow CI run `/storage/Users/currentUser/ohos-test-runs/codex-5.1-lua-5.1-issue22-conan-20260807-185222-20335` passed with `Total: 1`, `Success: 1`, `Failed: 0`.
- Final CI results: L0 pass, L1 pass, L1e pass, L2 skip because no `bin/` directory is packaged, L4 pass, L5 pass. L0k emitted a non-blocking commands.json hint because the recipe builds upstream `lua`/`luac` during `build()`, but this issue intentionally does not modify software-level `archives/l/lua/commands.json`.
- PR CI build `#22290` on `OpenHarmonyPCDeveloper-CI-030` failed during executable link because the OHOS SDK `lld` process could not load `libxml2.so.16` symbols. This matches knowledge entry E132. The recipe and test_package now prepend the discovered OHOS SDK `ohos/native/llvm/lib` directory to `LD_LIBRARY_PATH` for link commands, instead of relying on the worker environment.

## Next validation commands

Run single-package shadow CI:

```sh
CI_PACKAGES="archives/l/lua/5.1" zsh ci/conan/build_and_test.sh
```

Runner wrapper:

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/lua/5.1
```
