# libxtst

X.Org client library for the X TEST extension: XTest fake input injection /
querying and the X Record extension for recording X protocol events.

## OHOS adaptation

- Builds the official release tarball with its generated Autotools files.
- Consumes published Conan packages: libx11, libxext, libxi, libxfixes,
  libxau, xorgproto.
- Preserves the upstream `libXtst.so.6` ABI and the `XTest.h` / `XRecord.h`
  public headers.
- Upstream ships no test suite; `test_package` links the library and resolves
  `XTestQueryExtension`, falling back to symbol verification when no X server
  is available.

## Versions

- `1.2.5` — upstream version tracking (source: libXtst 1.2.5)
- `6.1.0` — historical ABI version scheme (source: libXtst 1.2.4)
