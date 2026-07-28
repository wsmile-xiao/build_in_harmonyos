# VCFtools - OpenHarmony build archive

VCFtools is a collection of C++ and Perl command-line tools for inspecting,
filtering, comparing, and transforming Variant Call Format (VCF) files.

## Versions

| Version | Status | Build system | Notes |
|---------|--------|--------------|-------|
| 0.1.17 | built | Autotools | OHOS aarch64 local validation passed: 75 upstream assertions and 3 consumer scenarios |

## Dependencies

- `zlib/1.3.1`: compression library linked by the `vcftools` C++ binary
- `htslib/1.24-r0`: provides `bgzip` and `tabix` for the Perl tools
- Perl: runtime supplied by the OHOS worker tool environment

## Upstream

- Homepage: https://vcftools.github.io/
- Repository: https://github.com/vcftools/vcftools
- License: LGPL-3.0-only
