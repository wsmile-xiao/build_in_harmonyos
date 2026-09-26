# tboot

tboot is the Intel TXT (Trusted Execution Technology) reference implementation
of a measured launch: a small pre-kernel module that performs a measured
launch of a Linux/Xen kernel through the SINIT ACM, plus the host-side tooling
used to create and manage the launch control policies (LCP).

- Upstream: <https://sourceforge.net/projects/tboot/> (Mercurial
  `hg.code.sf.net/p/tboot/code`; version 1.10.5 → tag `v1.10.5`, node
  `9c406d761d2ebb51ef7e762a7ed37a0664c65370`)
- License: BSD-3-Clause

## What this package provides

Only the **host-side tools** are portable C; the boot module itself is
freestanding 32-bit x86 firmware, so it is not built for aarch64 targets:

| Tool | Purpose |
|---|---|
| `lcp2_mlehash` | compute the MLE hash (binds kernel image + command line) |
| `lcp2_crtpol` | create an LCP policy / policy data file |
| `lcp2_crtpollist` | create an LCP policy list (TPM 1.2 / 2.0 structures) |
| `lcp2_crtpolelt` | create a policy element (`mle`, `pconf`, `sboa`, `custom`, …) |
| `tb_polgen` | create and maintain a Verified Launch Policy |
| `txt-stat` | show Intel TXT status/measurements from the TXT registers |
| `txt-parse_err` | decode a TXT.ERRORCODE value |

Plus the man pages (`share/man/man8`) and the in-tree building blocks
(`safestringlib`).

## Not built on aarch64 (documented exclusions)

- `tboot/` — the measured-launch boot module. `tboot/Config.mk` hard-codes
  `-m32 -march=i686` and `LDFLAGS = -melf_i386`; it is x86 firmware.
- `utils/txt-acminfo` — reads x86 MSRs and IO ports through
  `tboot/include/processor.h` / `io.h`.
- `txt-test/`, `test-patches/`, `lcp-gen2/` (Python/M2Crypto GUI) — not part of
  the upstream default build (`SUBDIRS`).

## Dependencies

| Dependency | Version | Use |
|---|---|---|
| `openssl` | 3.5.6.1 | `libcrypto` for the LCP/RSA/ECDSA/SM2 policy work (`lcputils.c` uses the OpenSSL 3 provider API) |
| `zlib` | 1.3.1.1 | `lcp2_mlehash` decompresses gzip kernel images, `tb_polgen` handles compressed policy inputs |

Both are consumed as static archives, so the shipped executables depend on
libc only (`DT_NEEDED: libc.so`).

## Building

```bash
conan install --requires=tboot/1.10.5 -pr:h=ci/conan/profiles/ohos-aarch64 -r=ohpcd
```

See `1.10.5/notes.md` for the nine portability patches, the upstream test run
and the OHOS-specific findings (`/tmp` is read-only, `-Werror` vs clang 15).
