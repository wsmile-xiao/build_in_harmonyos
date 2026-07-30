# lua-luv 1.51.0-1

## Build approach

luv normally carries Lua and libuv as Git submodules. This recipe disables
those bundled builds and uses the already adapted `lua/5.4.8` and
`libuv/1.52.1` Conan packages instead.

The upstream CMake file did not link the configured Lua library for its
non-Linux branch. The portability patch treats `OHOS` and `HarmonyOS` as
POSIX-like targets and links the configured Lua library plus `rt`.

## Test coverage

The upstream C test driver (`src/test.c`) runs 19 supported upstream
`test-*.lua` scripts and `tests/manual-test-external-loop.lua`. The runner
injects the `arg[0]` value normally supplied by the Lua CLI. It explicitly
skips `test-loop.lua` (issue #599 callback-count assertion differs on the
OHOS test host), `test-pipe.lua` (pipe permission and abstract socket
behavior), and `test-udp.lua` (`recvmmsg` returns `ENOBUFS` on the OHOS test
host). The consumer test loads the packaged `luv.so`, calls
`uv.version_string()`, and drives a libuv timer through Lua.
