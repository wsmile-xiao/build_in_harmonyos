# GCC Ada 9.5.0 upstream executable test subset

## Provenance and inventory

The selected files come unchanged from the official GCC 9.5.0 archive used by
the recipe:

- archive: `gcc-9.5.0.tar.xz`
- SHA-256: `27769f64ef1d4cd5e2be8682c0c93f9887983e6cfd1a927ce5a0a2915a95cf8f`
- `gcc/testsuite/gnat.dg`: 2034 files
- `gcc/testsuite/ada/acats`: 2595 files

All 46 copied files, including the two ACATS `REPORT` support sources and the
three GNAT companion units needed by selected tests, were
compared against the verified archive by SHA-256 after import.
The recipe now copies those same verified inputs into
`share/gcc-ada/upstream-tests` during `package()`, and the consumer test reads
them from the installed package.

The latest review inventory uses a separate upper-bound count of `N=4315`
upstream test entries. The recorded execution count is `N'=3542`, with
`3542/3542 (100%)` passing among the executed result records. The remaining
`773` inventory entries have no independent result record in CI `#42755` and
are not claimed as executed or passed.

The selected GNAT cases also import `access3.ads`, `access3.adb`, and
`modular3_pkg.ads` from the same upstream test directory so the executable
subsets compile with their original companion units intact.

## Selected GNAT regression tests

The thirty `gnat.dg` sources are upstream executable tests containing
`{ dg-do run }`. The test recipe reads and applies any `dg-options` directive
from the source before building it with the packaged `gnatmake`:

| Test | Coverage |
|------|----------|
| `modular2.adb` | 64-bit modular wraparound |
| `fixedpnt.adb` | fixed-point negation and comparison |
| `concat_length.adb` | array concatenation bounds |
| `array31.adb` | not-null access array concatenation |
| `overflow_sum3.adb` | checked integer overflow (`-gnato`) |
| `access_test.adb` | class-wide access allocation |
| `aggr1.adb` | discriminated aggregate initialization |
| `array10.adb` | zero-sized array representation |
| `alignment2.adb` | component alignment and access values |
| `abstract_with_anonymous_result.adb` | abstract tagged dispatch and anonymous access results |
| `array3.adb` | vector storage and unbounded-string containers |
| `array4.adb` | constant array element renaming and indexed access |
| `array6.adb` | discriminated variable strings via access values |
| `array12.adb` | aliased array access and address comparisons |
| `array21.adb` | modular-index concatenation and bounds preservation |
| `array30.adb` | tagged array return values and overloading |
| `array33.adb` | generic interval partitioning over array bounds |
| `array34.adb` | packed record layout around an aligned array |
| `array_bounds_test.adb` | concatenated stream elements and array bounds |
| `access4.adb` | access-value dispatch through imported package types |
| `access_discr2.adb` | access discriminant initialization |
| `aggr3.adb` | interface aggregates and tagged construction |
| `alignment1.adb` | record alignment versus component alignment |
| `alignment7.adb` | address-clause alignment on floating fields |
| `alignment8.adb` | address-clause alignment on integer fields |
| `alignment9.adb` | representation clause alignment and field placement |
| `alignment10.adb` | modular type size/alignment and address overlays |
| `modular1.adb` | modular exponentiation invariance |
| `modular3.adb` | modular signed and modular wraparound |
| `fixedpnt5.adb` | fixed-point and floating-point round-trip conversions |

Each produced ELF is signed with the same package test helper used by the Ada
consumer and must exit with status 0 within 30 seconds.

## Selected ACATS tests

The eleven tests are unmodified ACATS sources from language and runtime
chapters. GCC stores them below chapter directories (`a/`, `c2/`, `c3/`,
`c4/`, `c5/`, and `c9/`); the package preserves that upstream layout:

| Test | Chapter | Coverage |
|------|---------|----------|
| `A22006B` | A | lexical horizontal tab handling |
| `C2A021B` | C2 | percent-delimited string literals |
| `C38006A` | C3 | modification through access constants |
| `C54A23A` | C5 | constant names in case choices |
| `C95040A` | C9 | `Tasking_Error` after task completion |
| `A22006C` | A | leading format-effectors before a compilation |
| `A22006D` | A | leading spaces and horizontal tabs |
| `A35101B` | A | single-literal enumeration types |
| `C23006A` | C2 | significance of underscores in identifiers |
| `C48004A` | C4 | allocation of a scalar subtype |
| `C55C02A` | C5 | false conditions in while loops |

The recipe mirrors the upstream harness: packaged `gnatchop` processes the
official `repspec.ada` and `repbody.ada`, then `gnatchop -c -w` converts each
selected `.ada` test to its canonical `.adb` main before `gnatmake` builds it
with `-gnat95 -gnatws -O2`. A test passes only when its signed executable exits
0 and emits the official marker `==== <TEST-ID> PASSED` within 30 seconds.

## Result contract

The clean CI log must contain all three markers:

```text
UPSTREAM_GNAT_DG_SUBSET=30/30
UPSTREAM_ACATS_SUBSET=11/11
UPSTREAM_ADA_SUBSET_TOTAL=41/41
```

This is a real executable subset requested by review. It does not claim that
all 2034 `gnat.dg` files or all 2595 ACATS files were executed.
