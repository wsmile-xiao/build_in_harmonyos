# cryptopant 1.3.2 OpenHarmony adaptation

## Source

- Upstream tarball: `https://ant.isi.edu/software/cryptopANT/cryptopANT-1.3.2.tar.gz`
- sha256: `049b98da835a356230259e68684165fbfa08bf6540424a6f4d815660ae55f278`
- Verified size: 498289 bytes

## Build System

Autotools (`configure.ac` + `Makefile.am`). Requires `openssl >=3.1.0`.

- `AC_CHECK_HEADERS` for `openssl/evp.h`, `openssl/provider.h`, etc.
- `AC_CHECK_LIB([crypto], [EVP_CIPHER_CTX_new])` gate.
- Optional `--with-scramble_ips` builds the `scramble_ips` text utility; mandatory for `make check`.

## Adaptation

- Added `openssl/3.5.6` Conan requirement; `AutotoolsToolchain` injects include/lib via toolchain (Conan buildenv).
- Used `--with-scramble_ips` unconditionally so upstream test suite (16 checks) can run.
- Kept static/shared option handling explicit (`--enable-shared/--disable-static` etc.).
- No OHOS-specific patches needed: library is pure C with POSIX `regex.h` and `netinet/in.h` only; `config.sub` from 2023-06-23 recognizes `aarch64` but HMBS runs native build (no cross triplet), so configure succeeds without patching. If future cross-build required, add `config.sub` OHOS triplet patch.
- Library name is `libcryptopANT.{a,so}` (case-sensitive `cryptopANT`).

## Upstream Tests

- **Location**: `Makefile.am` `test` / `check` targets.
- **Structure**: `test_bf` / `test_aes` / `test_sha1` / `test_md5` each runs 4 checks:
  - `ipv4 scrambling` (cmp `test/ip4s` vs `test/ip4s.anon.<type>`)
  - `ipv6 scrambling` (`head -n 1000` vs `test/ip6s.anon.<type>`)
  - `ipv4 descrambling`
  - `ipv6 descrambling`
  - Total **16** logical checks (4 types * 4).
- **Execution**: `make check` builds `scramble_ips` then pipes data through it and `cmp -s` against reference files in `test/`.
- **Verification quirk**: `Makefile.am` uses `&& echo PASSED || echo FAILED` so exit code is always 0; true pass/fail must be parsed by counting `PASSED` strings (build script does this and emits `HMBS_UPSTREAM_TEST_RESULT`).
- **Data files**: `test/` contains ~2k lines of IPv4/IPv6 vectors per crypto type; all are non-empty reference files shipped in tarball.

## Test Package

- **Consumer test**: `test_package/test_cryptopant.c` exercises real library API:
  1. `scramble_type2name` / `scramble_name2type` round-trip (AES, Blowfish, MD5, SHA1)
  2. `scramble_init` with deterministic AES key/pad
  3. `scramble_ip4` + `unscramble_ip4` round-trip (1.2.3.4, full prefix)
  4. Prefix-preserving check (scramble same /24 shares prefix)
  5. `scramble_ip6` + `unscramble_ip6` round-trip (fe80::1)
  6. `scramble_cleanup` lifecycle
  - **Assertions**: 8 distinct checks, emits `HMBS_TEST_PACKAGE_RESULT` with `discovered=8 passedCount=8`.
- **Upstream re-emit**: test_package also re-emits upstream marker if build step did not (defensive).

## Verification

- `conan create` on HarmonyOS aarch64: build + `make check` 16/16 PASSED, test_package 8/8.
- Toolchain: `/data/service/hnp/bin/clang` (HMBS env), `conan 2.30`, profile `ohos-aarch64`.

## References

- https://ant.isi.edu/software/cryptopANT/
- https://forgejo.debian.net/dns-oarc/cryptopant
