# libxml2-utils 2.15.3

This package provides the `xmllint` and `xmlcatalog` command-line utilities
from the official libxml2 2.15.3 source release for OpenHarmony PC arm64.

The library itself is not exported by this package; use `libxml2/2.15.3` for
the C library. LZMA and iconv are disabled because the OHOS utility closure
uses the published zlib binary and musl-compatible built-ins only.
