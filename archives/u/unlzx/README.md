# unlzx

unlzx is Erik Meusel's portable ANSI-C extractor for the **Amiga LZX** archive
format — on a POSIX system it is the way to read `.lzx` archives.  Version 1.1
added the ability to read an archive from stdin, so it can be used in a pipe.

- Upstream: https://aminet.net/package/misc/unix/unlzx.c (Aminet, v1.1, 03.04.01)
- Source: https://aminet.net/misc/unix/unlzx.c.gz (a single gzip-compressed C file)
- License: **none stated upstream** — neither the source nor the readme mentions
  copyright, licence or redistribution terms.  The recipe declares
  `license = "unknown"` rather than guessing one.
- Package form: `bin/unlzx` (application)

## HarmonyOS PC adaptation

Two portability patches; the algorithm itself is untouched.

| Patch | Purpose |
|---|---|
| `0001-unlzx-missing-includes.patch` | add `<sys/stat.h>` (for `mkdir()`) and `<unistd.h>` (for `getopt()`/`optind`) — both were implicit declarations, which GCC 14+ and C23 make a hard error |
| `0002-add-GNUmakefile.patch` | the distribution contains no build file at all, only the comment `/* Compile with: gcc unlzx.c -ounlzx -O6 */`; this adds the equivalent GNU make rule, taking the compiler and flags from the Conan toolchain |

## Usage

```sh
unlzx -v archive.lzx        # list
unlzx -x archive.lzx        # extract (default mode)
cat archive.lzx | unlzx -x -c   # extract from stdin
```

## Upstream tests

None — the distribution is one C file plus a readme, with no test suite, no test
data and no test target.  `test_package` therefore performs a real round trip
instead: it builds a spec-valid LZX archive (header CRC, a stored member and its
data CRC), has the installed `unlzx` list and extract it, compares the extracted
bytes with the original payload, and checks that an archive with a corrupted
header CRC is refused.

See `1.1/notes.md` for the full record — including the two format details that
are easy to get wrong (multi-byte fields are little-endian; the CRCs are
ordinary CRC-32) — and `1.1/test_package/MANIFEST.yml` for the test audit.
