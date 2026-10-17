# ratpoints 2.1.3 adaptation notes

## Source and build system

- Official source: `https://www.mathe2.uni-bayreuth.de/stoll/programs/ratpoints-2.1.3.tar.gz`
- SHA-256: `c4bd55b4fe6234ed4793edfb6126f63b13ee2eaf122f3dfd8f4737a7096a0a7e`
- Build system: upstream handwritten Makefile
- Dependency: published `gmp/6.3.0.1` package

## Adaptation decisions

The upstream Makefile hardcodes GCC and places `-lgmp -lgcc -lc -lm` before `-lratpoints`. Modern linkers process static archives from left to right, so this order leaves `ceil` and `floor` unresolved. The Conan recipe directly invokes the compiler selected by `tools.build:compiler_executables`, generates the two upstream headers, compiles all four library translation units, and links libraries after the objects. No upstream test file is modified.

`sturm.c` defines its recursive interval iterator as a GNU C nested function. Clang does not implement this extension. The portability patch moves that helper to file scope and passes the formerly captured state explicitly; the recursive algorithm and all call arguments remain unchanged. The patch is compiler-portable and contains no platform-specific macro.

The upstream `USE_SSE` definition is retained. `rp-private.h` automatically undefines it when `__SSE2__` is unavailable, so OHOS armv8 uses the portable bit-array implementation.

## Test inventory

Upstream provides one regression executable, `rptest`, backed by `testdata.h` with `NUM_TEST=1000` and expected output in `testbase`. The recipe executes all 1000 curves and performs a strict byte comparison. This is stronger than upstream `make test`, which prints a diagnostic on mismatch but still exits successfully.

The consumer package adds eight portable public API assertions, three installed CLI output assertions, and two HarmonyOS-specific arm64 ABI assertions. Total adapted assertions: 1013, compared with 1000 upstream cases.

## Verification commands

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
python3 scripts/ohc-run.py finish ratpoints 2.1.3 built
```
---

**编译结束**: 2026-10-08 14:52
**最终状态**: built
