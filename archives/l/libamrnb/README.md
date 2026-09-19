# libamrnb — 3GPP AMR-NB speech codec (floating-point reference implementation)

libamrnb packages the 3GPP TS 26.104 (Release 11) AMR-NB (Adaptive Multi-Rate
Narrowband) floating-point ANSI-C reference implementation behind a small
autotools wrapper (penguin.cz/~utx/amr). Version 11.0.0.0 corresponds to
3GPP TS 26.104 v11.0.0 (distfile name follows the FreeBSD `audio/libamrnb`
port).

## Features

- AMR-NB encoder and decoder for all 8 modes (MR475 … MR122) plus DTX/SID
- GP3 (default, packed/`.amr`), IF2 and ETSI bitstream interface variants
- VAD1/VAD2 encoder variants
- Library `libamrnb` + 9 command-line tools (amrnb-encoder, amrnb-decoder,
  and their if2/etsi/vad2 variants)
- Pure C89, zero conan dependencies (system libm only)

## Current Build Configuration

The current build (11.0.0.0) uses autotools with minimal configuration:

- Static library (`--disable-shared`, default option; `shared=True` available)
- `--build/--host=aarch64-unknown-linux-gnu` for OHOS cross builds because the
  2012-era config.guess/config.sub do not know the `linux-ohos` triplet
  (celt/a52dec precedent)
- Dual-source build, same as the FreeBSD port: the wrapper tarball plus the
  3GPP archive `26104-b00.zip` are both declared in conandata.yml; the
  upstream Makefile unpacks/patches the 3GPP sources itself during `make`
  (prepare_sources.sh applies amrnb-intsizes/-strict-aliasing/-any-cflags)

## Note on licensing

The wrapper is BSD-3-Clause; the codec reference code is under the 3GPP
TS 26.104 license (restrictive, not OSI) — the reason no distro mirror hosts
the 3GPP archive (sources come from 3gpp.org directly; upstream penguin.cz
site is offline, tarball fetched via FreeBSD distcache/USTC mirrors with
checksums cross-checked against FreeBSD distinfo and RPM Fusion md5 records).
See `11.0.0.0/notes.md` for details.
