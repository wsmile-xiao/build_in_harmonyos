# xf86-video-dummy 0.4.1 test report

## Environment

- Target: HarmonyOS PC, `os=OHOS`, `arch=armv8`, Release profile.
- Compiler: Clang 15.0.4 from `tools.build:compiler_executables`.
- Source: official `xf86-video-dummy-xf86-video-dummy-0.4.1.tar.gz` from
  `gitlab.freedesktop.org/xorg/driver/xf86-video-dummy`.
- Source SHA256: `3f5c9d9904b0e5683edd546d7de2960045dbc9b5e301dabd3abba3c2f1f71bea`.
- Driver SDK headers: extracted at build time from the official
  `xorg-server-21.1.15.tar.xz` (SHA256
  `841c82901282902725762df03adbbcd68153d4cdfb0d61df0cfd73ad677ae089`)
  declared in `conandata.yml` under `sources["xorg-server-21.1.15"]`.
- Conan: 2.29.1.

## Upstream test inventory (R51)

The upstream release ships **no test suite**:

- Source tree contains only `src/dummy_driver.c` and `src/dummy_cursor.c`
  plus autotools boilerplate; there is no `tests/` directory.
- Top-level `Makefile.am` declares only `SUBDIRS = src`; `src/Makefile.am`
  builds the `dummy_drv.la` loadable module and registers no `TESTS` or
  `check` targets.
- `configure.ac` contains only dependency probes (`XORG_DRIVER_CHECK_EXT`,
  `PKG_CHECK_MODULES`), no test harness.

Upstream `make check` is therefore a no-op (0 registered entries), same
situation as other xf86 video drivers.

## Adapted test results

| Scope | Classification | Count | Result |
|---|---|---:|---:|
| Upstream `make check` | Other | 0 | 0 entries registered (no-op) |
| Package artifact checks (test_package) | Integration | 4 | 4 PASS |
| **Total** | | **4** | **4 PASS** |

`test_package` (`test.c`, built with the package toolchain and executed via
`self.run`) verifies:

1. `dummy_drv.so` exists at `lib/xorg/modules/drivers/` inside the installed
   package — PASS (35200 bytes).
2. ELF magic bytes (`\x7fELF`) — PASS.
3. File readable via `stat`/`open` from the consumer binary — PASS.
4. `dlopen(dummy_drv.so, RTLD_LAZY)` — module loads or reports the expected
   `xf86PrintChipsets: symbol not found` relocation diagnostic when no X
   server runtime is present (documented expected behaviour for a
   server-loaded driver module; the driver is loaded by Xorg which provides
   its symbols). — PASS (informational).

Local `conan create` was additionally executed twice against the exact CI
`conandata.yml` shapes (single upstream URL, and the mirror-fallback URL list
the CI rewriter produces) to prove multi-source `get()` compatibility; both
runs completed with `ALL CHECKS PASSED`.

## Commands

```bash
# W3 local CI simulation (uses ci/conan/build_and_test.sh, latest main gates)
CI_PACKAGES="archives/x/xf86-video-dummy/0.4.1" \
  zsh ci/conan/build_and_test.sh archives/x/xf86-video-dummy/0.4.1

# Full package build + consumer test
conan create archives/x/xf86-video-dummy/0.4.1 \
  -pr:a=ohos-aarch64 --build=missing

# Mirror-list shape (as rewritten by CI mirror fallback)
conan create <copy-of-recipe-with-url-list> -pr:a=ohos-aarch64 --build=missing
```

## Result

- Build: PASS (`dummy_drv.so` linked from `dummy_driver.o` + `dummy_cursor.o`,
  `-fPIC -shared`, soname `dummy_drv.so`).
- Consumer test: 4/4 PASS.
- L4 static security scan: PASS. L5 artifact baseline: PASS.
