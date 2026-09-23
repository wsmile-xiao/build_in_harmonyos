# libetonyek-tools

> Command-line converters for Apple iWork documents (Keynote / Pages / Numbers).

## Intro

libetonyek parses Apple iWork files and exports them through the librevenge
document model.  Its release tarball also carries nine command-line converters
under `src/conv/`, which this package installs:

| Tool | Purpose |
|---|---|
| `key2raw` / `pages2raw` / `numbers2raw` | dump the parsed document as a raw text tree |
| `key2text` / `pages2text` / `numbers2text` | plain-text extraction |
| `numbers2csv` | spreadsheet → CSV |
| `pages2html` | word-processing document → HTML |
| `key2xhtml` | presentation → XHTML |

This archive holds the **tools only** (`bin/` + license); the library itself is
`libetonyek/<version>`.  That mirrors the Debian split between
`libetonyek-0.1-1` and `libetonyek-tools`.

## OHOS Adaptation Notes

- Upstream's `AC_ARG_WITH([tools])` has no default and is tested as
  `test "x$with_tools" != xno`, so the converters are built unless explicitly
  disabled.  `package()` installs the whole tree into a staging root and copies
  only the nine binaries out; if a converter is missing the recipe raises
  rather than shipping a partial package.
- The library is built in-tree (`src/lib/libetonyek-0.1.la`) and statically
  embedded, so the package is self-contained and `make check` runs against the
  very code the converters link.
- liblangtag is disabled — see `0.1.12/manifest.yaml`; only the language tags of
  text spans are lost.
- Cross-mode tool lookups (`<host>-ar`, `<host>-ld`) do not exist on this
  platform: the device has no `ar`/`ld` on PATH at all, only
  `~/.harmonybrew/bin/llvm-ar` and `<sdk>/native/llvm/bin/ld.lld`.  The recipe
  exports `AR`/`RANLIB`/`NM`/`STRIP`/`LD` itself — details in
  `0.1.12/notes.md`.
- Upstream ships a real cppunit suite (`src/test/`: `core`, `detection`,
  `streams`, registered in `TESTS`), executed by `make -j1 check` inside
  `build()`.

## Dependencies

| Dependency | Version | Note |
|---|---|---|
| librevenge | 0.0.5 | document model / generators / stream readers |
| libxml2 | 2.15.3.1 | IWORK/Pages XML and Keynote .apxl parsing |
| zlib | 1.3.1 | zip containers of iWork packages |
| boost, glm, mdds | 1.90.0.3, 1.0.3, 3.2.1 | `tool_requires`: private headers only |
| cppunit | 1.15.1 | `tool_requires`: upstream test suite |
| liblangtag | — | **not used** (see above) |

## Versions

| Version | Status | Notes |
|---|---|---|
| 0.1.12 | built | task #13150, `feat/libetonyek-tools-0.1.12` |
