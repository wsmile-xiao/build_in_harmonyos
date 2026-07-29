# lua-proctitle 0.1 Adaptation Notes

## Build

The upstream Makefile is hard-coded for GCC, Lua 5.1, and glibc. The recipe
instead compiles `proctitle.c` with the Conan-selected C compiler against the
already packaged `lua/5.4.8` dependency.

## OpenHarmony Port

Upstream overwrites glibc's `__progname`. OpenHarmony does not provide that
symbol, so the portability patch calls `prctl(PR_SET_NAME)` and reports a Lua
error if the system call fails. The resulting process name is limited to 15
bytes by the kernel.

## Tests

Upstream provides no formal automated test suite. `test_package` loads the
installed module using Lua 5.4, calls the documented `proctitle("...")` API,
and verifies the kernel process name through `PR_GET_NAME`.

The test package explicitly requires `lua/5.4.8` so CMakeDeps generates the
`lua` package configuration consumed by its C test.
