# zlib 1.3.1.1.1.1 HarmonyOS PC adaptation notes

Issue: #1829
Difficulty: B
Branch: fix/zlib-1.3.1.1.1.1
Target path: archives/z/zlib/1.3.1.1.1.1

## Summary

`zlib/1.3.1`, `zlib/1.3.1.1` and `zlib/1.3.1.1.1` already exist in the artifact
repo, so the R33 hard-code fix that was previously attempted against
`zlib/1.3.1.1.1` (commit `ff4c6ee8f4`) is re-packaged as `zlib/1.3.1.1.1.1` to
satisfy R37 (bump the version instead of mutating an already-published
reference). The source remains upstream zlib 1.3.1.

The package stays static-only because zlib is a system same-name library on
HarmonyOS. To support consumers that link zlib into shared libraries or Python
extension modules, the recipe builds `libz.a` with hard-coded `-fPIC -O2`.

## Build

```text
CONFIG_SHELL=/data/service/hnp/bin/bash
CC=<compiler from tools.build:compiler_executables>
CFLAGS=-fPIC -O2   # 硬编码，禁止依赖 shell 环境变量 CFLAGS（R33）
./configure --static --prefix=/
make -j1
make check
```

## Validation Strategy

The recipe runs upstream `make check`, which builds and runs zlib's official
`example` and `infcover` tests.

The `test_package` verifies two consumer paths:

- `test_zlib` performs a compress/uncompress round trip.
- `zlib_pic_probe` is a shared library linked against `zlib::zlib`; this catches
  the AArch64 non-PIC relocation failure that blocked higher-level consumers.

## Downstream Context

This fix was split out while adapting `gobject-introspection/1.78.1`. That
package builds a Python extension module and failed when static GLib pulled in
the existing non-PIC `zlib/1.3.1` archive:

```text
relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'
```

Downstream packages that need PIC zlib should depend on `zlib/1.3.1.1.1.1`
instead of the already-published `zlib/1.3.1`, `zlib/1.3.1.1` or
`zlib/1.3.1.1.1`.

## Fix: hard-code -fPIC (R33)

The previous recipe derived `-fPIC` from the shell `CFLAGS` env var
(`os.environ.get("CFLAGS", "-O3")`). That violates R33 (build() must not
depend on undefined shell env vars) and silently breaks on release workers
where `CFLAGS` is empty/absent. This fix hard-codes `CFLAGS="-fPIC -O2"`,
matching `zlib/1.3.1.1` and `zlib/1.3.2`.

### Before / after (AArch64 relocations in `deflate.o`, symbol `z_errmsg`)

| State | `z_errmsg` relocation | Link into DSO |
|-------|-----------------------|---------------|
| non-PIC (`-fno-pic`) | `R_AARCH64_ADR_PREL_PG_HI21` + `R_AARCH64_LDST64_ABS_LO12_NC` | ❌ `ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC` |
| PIC (`-fPIC`) | `R_AARCH64_ADR_GOT_PAGE` + `R_AARCH64_LD64_GOT_LO12_NC` | ✅ links |

### Downstream: glib/2.88.0 shared=True

With `[replace_requires] zlib/1.3.1: zlib/1.3.1.1.1.1`, `glib/2.88.0 -o shared=True`
links `libgio-2.0.so` (which consumes `zlib::zlib`) successfully with no zlib
relocation errors.
