# wandio

`wandio` (WAND I/O) is the file-I/O library behind libtrace: a small C API
(`wandio_create`, `wandio_read`, `wandio_wcreate`, ...) that reads and writes
plain files and, when built with optional backends, transparently handles
gzip/bzip2/lzo/lzma/zstd/lz4 compression plus HTTP reads.

## Versions

| Version | Status |
| --- | --- |
| 4.2.7 | built |

Homepage: https://github.com/LibtraceTeam/wandio

## OHOS adaptation

- Portable core only: every optional backend (`--without-bzip2/zlib/lzo/lzma/
  zstd/lz4/qatzip/http`) is disabled, so the package has zero external
  requirements and the plain-file API is fully verified on device.
- Upstream 4.2.7 ships no automated test suite (no `TESTS`/`check` target);
  `test_package/test_wandio.c` exercises lookup, extension detection, a
  write/read roundtrip, and the printf/fgets/peek/tell/seek text API.
- Ships the `wandiocat` helper binary alongside `libwandio`.

## Reference

- Upstream: https://github.com/LibtraceTeam/wandio
