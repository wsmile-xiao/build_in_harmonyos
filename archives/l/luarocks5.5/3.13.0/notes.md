# luarocks5.5 3.13.0 adaptation notes

## Source

- Canonical source: `https://luarocks.org/releases/luarocks-3.13.0.tar.gz`
- SHA-256: `245bf6ec560c042cb8948e3d661189292587c5949104677f1eecddc54dbe7e37`

## Build system

LuaRocks uses a POSIX `configure` script and `GNUmakefile`. This recipe configures LuaRocks for the existing `lua/5.5.0` Conan dependency:

```bash
./configure --prefix=/ --sysconfdir=/etc --force-config \
  --lua-version=5.5 \
  --with-lua-bin=<lua/5.5.0>/bin \
  --with-lua-include=<lua/5.5.0>/include \
  --with-lua-lib=<lua/5.5.0>/lib
make -j1
make install DESTDIR=<package_folder>
```

The package installs `bin/luarocks`, `bin/luarocks-admin`, Lua modules under `share/lua/5.5`, and the system config file under `etc/luarocks`.
When cross-building from a Windows host, the recipe invokes the POSIX configure
script through `CONFIG_SHELL`/Git Bash `sh` and normalizes paths to `F:/...`
form so the configure script can consume Conan package paths.
For OHOS cross builds the target Lua executable cannot run on the Windows host,
so the recipe does not execute LuaRocks' native `make all` bootstrap path. It
installs the LuaRocks launcher scripts, Lua modules, and `config-5.5.lua`
directly, then relies on `test_package` and the HarmonyOS PC emulator to execute
the target package.

## Dependencies

- `lua/5.5.0` with `with_tools=True`, so the package provides the `bin/lua`
  executable path required by the LuaRocks configure step.

## Upstream tests

The exact release archive contains:

- `smoke_test.sh`
- `test_regression.sh`
- `.busted`
- `spec/README.md`
- 44 upstream `*_spec.lua` files under `spec/`

The upstream rockspec declares Busted-based tests with `luacov` and `busted-htest` as test dependencies. The Unix flags exclude `ssh` and `git` tagged tests. These tests are recorded as upstream inventory; consumer checks in `test_package` are separate and are not counted as upstream tests.

A reproduced upstream Busted run with Lua 5.5 did not satisfy the strict Path A requirement. It executed 55 Busted cases from 43 test files: 52 passed, 3 were skipped, and 178 errors were reported. The repeated setup failure is caused by the test environment trying to install `luacov 0.15.0-1`, which declares `lua >= 5.1, < 5.5` while the target VM provides Lua 5.5. The release rockspec itself also contains duplicate `tag` entries, so `luarocks test` cannot be used as the only runner without first applying an upstream-test adaptation.

Because this is upstream test-suite behavior, the package `test_package` below is only consumer validation. It must not be reported as a full Path A upstream-test pass.

## Consumer and fault-injection checks

The test package verifies that the packaged LuaRocks commands run with Lua 5.5 and exercise deterministic offline behavior:

1. `luarocks --version`
2. `luarocks config lua_version`
3. `luarocks-admin --version`
4. `luarocks help install`
5. an invalid command returns non-zero
6. `luarocks lint` rejects an intentionally invalid rockspec
