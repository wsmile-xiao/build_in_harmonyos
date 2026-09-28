# libamrwb — 3GPP AMR-WB speech codec (floating-point reference implementation)

libamrwb packages the 3GPP TS 26.204 (Release 11) AMR-WB (Adaptive Multi-Rate
Wideband) floating-point ANSI-C reference implementation behind a small
autotools wrapper (penguin.cz/~utx/amr). Version 11.0.0.0 corresponds to
3GPP TS 26.204 v11.0.0 (distfile name follows the FreeBSD `audio/libamrwb`
port).

## Features

- AMR-WB encoder and decoder for all 9 modes (6.60 … 23.85 kbit/s) plus DTX/SID
- GP3 (default, packed/`.awb`) and IF2 bitstream interface variants
- Library `libamrwb` + 4 command-line tools (amrwb-encoder, amrwb-decoder,
  and their if2 variants)
- Pure C89, zero conan dependencies (system libm only)

## Current Build Configuration

The current build (11.0.0.0) uses autotools with minimal configuration:

- Static library (`--disable-shared`, default option; `shared=True` available)
- `--build/--host=aarch64-unknown-linux-gnu` for OHOS cross builds because the
  2012-era config.guess/config.sub do not know the `linux-ohos` triplet
  (libamrnb/celt/a52dec precedent)
- Dual-source build, same as the FreeBSD port: the wrapper tarball plus the
  3GPP archive `26204-b00.zip` are both declared in conandata.yml; the
  upstream Makefile unpacks/patches the 3GPP sources itself during `make`
  (prepare_sources.sh applies amrwb-intsizes/-any-cflags/-dhf-declaration/
  -includes)

## Note on licensing

The wrapper is BSD-3-Clause; the codec reference code is under the 3GPP
TS 26.204 license (restrictive, not OSI) — the reason no distro mirror hosts
the 3GPP archive (sources come from 3gpp.org directly; upstream penguin.cz
site is offline, tarball fetched via FreeBSD distcache/USTC mirrors with
checksums cross-checked against FreeBSD distinfo). See `11.0.0.0/notes.md`
for details.
