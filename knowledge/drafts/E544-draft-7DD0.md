# E544 — Legacy `.tar.Z` source archives on OHOS

Draft by moonlight142790, from VolPack 1.0b3 adaptation on 2026-09-28.

## 错误特征
The official Stanford download is `volpack-1.0b3.tar.Z`. On the HarmonyOS PC:

```
gzip: not gzip
tar: Not tar
```

## 触发条件
- Source is distributed in historical UNIX `compress`/LZW format (`.Z`).
- The build worker has Toybox `gzip` but no `uncompress` or LZW decoder.
- The failure occurs before configure, during source extraction.

## 根因分析
`.Z` is not a gzip stream; Toybox `gzip` does not decode it. Conan's ordinary
archive extraction cannot treat this as `.tar.gz`. Renaming the file does not
change the compression format. This is distinct from E402 (unsupported gzip
long options), E271 (uncompressed single-file asset), and E483 (wrong URL
extension for a gzip/zip stream).

## 解决方案

### 推荐方案
Prefer a versioned `tar.gz` repack from an authoritative distribution mirror.
Record its URL and SHA256 in `conandata.yml`, then compare the relevant source
files and test fixtures with the official archive unpacked on a host that does
support LZW. Keep the normal Conan hash check. If no trustworthy repack exists,
bundle a reviewed decoder as a build tool instead.

For VolPack, Debian's `volpack_1.0b3.orig.tar.gz` has SHA256
`dce3d892ad34b2810fc80b0592c7224a4606f8ebfb8206421e24288753f230d7`.
All `vp_*.c` files, `volpack.h`, `examples/brainsmall.den` and
`examples/check.ppm` match Stanford's `.tar.Z` byte-for-byte; Debian updated
the Autotools distribution files. The official `.tar.Z` has SHA256
`d7cfd5f6819cccf88363d2270377e547a07f35da6a0dac45845ecc1640e410fa`.

### 禁止做法
- Do not rename `.tar.Z` to `.tar.gz` or invoke `gzip -dc` and assume success.
- Do not switch to a personal fork or repack without checking content identity.

## 验证
```bash
sha256sum volpack_1.0b3.orig.tar.gz
conan create archives/v/volpack/1.0b3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

## 关联条目
- E271 — uncompressed single-file release mistaken for an archive.
- E402 — Toybox gzip option compatibility.
- E483 — URL extension mismatched with a supported compression format.
