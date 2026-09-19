# libfec

`libfec` is Phil Karn's (KA9Q) library of forward error correction (FEC
algorithms: Reed-Solomon encoders/decoders for arbitrary codes plus an
optimized CCSDS (255,223) codec, Viterbi convolutional decoders
(r=1/2 K=7, r=1/2 K=9, r=1/6 K=15), and DSP primitives (dot product,
sum of squares, peak value). This archive packages the maintained
[fblomqvi fork](https://github.com/fblomqvi/libfec) (upstream repository
unmaintained) at the exact commit Debian ships as `1.0-26-gc5d935f`
(tag `1.0` + 26 commits, `c5d935f42a79221871ff50e75d3971cf3e87be7c`),
which includes RS decoder bug fixes and extended RS tests.

On aarch64 the build uses the portable C implementations (`cpu_mode_unknown`
dispatch -> PORT); the MMX/SSE/AltiVec assemblies are x86/PowerPC only.

## OpenHarmony adaptation

- 1.0-26-gc5d935f source: official GitHub commit archive of
  fblomqvi/libfec (upstream publishes no release tarball)
- Build system: autotools (autoconf 2.69 `configure` + 1990s-vintage
  hand-written `makefile.in`)
- Dependencies: none (pure C, libc only; `sim.c`'s `normal_rand` uses
  sqrt/log so Linux consumers add `-lm`, musl folds libm into libc)
- Patches:
  - `0001-config-sub-aarch64.patch`: the bundled 2001-era `config.sub`
    predates aarch64; accept `aarch64-*-linux*` / `aarch64-*-ohos*`
  - `0002-configure-umask-022.patch`: create the `config.status` tmp dir
    with umask 022 (setgid hmdfs makes umask 077 dirs unwritable)
  - `0003-makefile-use-cc-variable.patch`: replace hard-coded `gcc` with
    `$(CC)` throughout `makefile.in` so the Conan-configured toolchain
    (clang on OHOS) is honored
- OHOS specifics: `--build=--host=aarch64-unknown-linux-gnu` native-style
  triples bypass the 2006 `config.guess`; `-fuse-ld=ld.lld` for the
  linker-less worker PATH; configure runs through `bash`; build-local
  `bin/` provides `ld`/`ar`/`ranlib` symlinks; `make test` (upstream
  correctness suite) runs inside `conan build()`
- Pure library package (no installed executables) -> no `commands.json`

## Testing

Upstream `make test` runs vtest27/29/39/615 (Viterbi with injected symbol
errors), rstest (23-configuration RS table incl. the fork's extended
cases), dtest, sumsq_test and peaktest — all portable C, executed on the
build target in the recipe `build()`. The Conan consumer test
(`test_package/`) additionally round-trips RS(255,223) through the char
and int codecs (error/erasure/uncorrectable paths), decodes a noise-free
K=7 Viterbi frame bit-exactly, and cross-checks the DSP primitives
against scalar references.
