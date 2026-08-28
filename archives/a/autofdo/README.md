# AutoFDO

AutoFDO converts sampled performance profiles into compiler optimization
profiles. This package targets OpenHarmony armv8 and builds the upstream 0.19
Autotools source with LLVM support disabled.

## Versions

| Version | Status |
| --- | --- |
| 0.19 | built and smoke-tested on OHOS armv8 |

## OpenHarmony Notes

The upstream archive omits two required git submodules. The recipe downloads
the pinned `perf_data_converter` and protobuf revisions, then applies the
documented OHOS portability patches.

See `0.19/notes.md` for source, dependency, and test details.
