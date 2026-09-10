# cloop

cloop provides compressed loopback filesystem utilities. This HarmonyOS PC package contains the user-space `create_compressed_fs` and `extract_compressed_fs` tools; the Linux kernel module is intentionally not built because HarmonyOS PC does not expose the Linux kernel-module build interface.

## OHOS adaptation

- Builds the bundled `advancecomp-1.15` compressor and the cloop extractor with clang.
- Uses explicit `aarch64-unknown-linux-gnu` configure identities because the old bundled `config.guess` does not recognize HarmonyOS.
- Adjusts the bundled Autoconf temporary-directory mode for HMDFS and avoids the HMDFS-forbidden hard-link install step.
- Preserves cloop's 64-bit big-endian offset format by using `int64_t` in the extractor.
- Validates an installed-package consumer round trip, including the format's zero padding to a complete block.

## Dependencies

- `zlib/1.3.1` — compression implementation used by the extractor and advancecomp.

## References

- https://github.com/KlausKnopper/cloop
- https://github.com/Code7R/cloop/tree/debian/sid
