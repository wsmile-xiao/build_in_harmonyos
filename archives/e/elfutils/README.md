# elfutils

This OpenHarmony package exposes the static `libelf` portion of elfutils for
OHOS armv8 consumers. The command-line elfutils programs are intentionally not
built because they require GNU argp, which is unavailable on OHOS.

## Versions

| Version | Status |
| --- | --- |
| 0.191 | built and smoke-tested on OHOS armv8 |

See `0.191/notes.md` for the portability changes and supported API surface.
