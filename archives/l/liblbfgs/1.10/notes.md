# liblbfgs 1.10 OpenHarmony adaptation

## Source

GitHub release: https://github.com/chokkan/liblbfgs/archive/refs/tags/v1.10.tar.gz
Tag: v1.10, commit 27e905f (2010-12-20).

## Build system

v1.10 does **not** ship a CMakeLists.txt. The build system is autotools only
(`configure.in` + `Makefile.am` + `autogen.sh`). `autoreconf` must be run to
generate the `configure` script.

## Adaptation notes

- **SSE/SSE2 disabled**: `--disable-sse2` — SSE/SSE2 is x86-only, not available
  on ARM (OHOS armv8). The upstream README explicitly warns against enabling SSE
  on non-x86 platforms.
- **Static only**: `--disable-shared --enable-static` — HarmonyOS PC uses static
  linking for system-level C libraries.
- **autoreconf**: Required because v1.10 only ships `configure.in`, not
  `configure`. The CI environment has autotools available.
- **OHOS triplet**: `--build=aarch64-linux-ohos --host=aarch64-linux-ohos` for
  cross-compilation targeting HarmonyOS arm64.

## Verification

- `make check`: upstream sample program runs L-BFGS on a simple quadratic.
- `test_package/liblbfgs_smoke`: 4-dimensional quadratic optimization, verifies
  convergence (LBFGS_SUCCESS = 0).
---

**编译结束**: 2026-08-25 15:00
**最终状态**: built
