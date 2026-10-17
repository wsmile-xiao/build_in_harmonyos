# libdca

`libdca` is a free DTS Coherent Acoustics audio decoder library. The source
distribution also provides the `dcadec` and `extract_dca` command-line tools,
plus the compatibility aliases `dtsdec` and `extract_dts`.

## Versions

| Version | Status |
| --- | --- |
| 0.0.7 | device validation pending |

## HarmonyOS adaptation notes

- The release archive contains Autotools input files but no generated
  `configure` script, so the recipe runs `autoreconf` first.
- Optional platform audio backends are disabled. The decoder library itself
  only needs the system math library.
- Final Conan build and consumer-test evidence must be collected on an
  aarch64 HarmonyOS PC; Windows is used only for recipe development and static
  checks.

Homepage: https://www.videolan.org/developers/libdca.html
