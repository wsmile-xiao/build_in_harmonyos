# unzoo

unzoo is Martin Schoenert's extractor for **zoo** archives — the format used by
Rahul Dhesi's `zoo` archiver.  It lists and extracts members; it cannot add or
delete them (that needs `zoo` itself).  The whole program is a single ANSI C
file placed in the Public Domain.

- Original source (now dead): `http://archives.math.utk.edu/software/multi-platform/gap/util/unzoo.c`
- Source used here: https://archive.debian.org/debian/pool/main/u/unzoo/unzoo_4.4.orig.tar.gz
  (Debian's pristine-upstream tarball — one `unzoo.c`, no Debian patches)
- Release: 4.4 (`$Id: unzoo.c,v 4.4 2000/05/29 ...`)
- License: Public Domain
- Package form: `bin/unzoo` (application)

## HarmonyOS PC adaptation

Two portability patches; the archiver logic itself is untouched.

| Patch | Purpose |
|---|---|
| `0001-unzoo-unix-portability.patch` | add the six system headers the `SYS_IS_UNIX` branch calls functions from but never includes (`<stdlib.h>`, `<string.h>`, `<sys/types.h>`, `<sys/stat.h>`, `<utime.h>`, `<unistd.h>`) — every one of those calls was an implicit declaration, which GCC 14+ and C23 reject; and replace the `unsigned int Secs[2]` handed to `utime()` with a real `struct utimbuf`, since `time_t` is 64-bit on LP64 while `unsigned int` is 32 |
| `0002-add-GNUmakefile.patch` | the distribution carries no build file, only the header comment `cc -o unzoo -DSYS_IS_UNIX -O unzoo.c`; this adds the equivalent GNU make rule, taking the compiler and flags from the Conan toolchain |

## Usage

```sh
unzoo -l archive.zoo         # list members
unzoo -x archive.zoo         # extract all members
unzoo -x archive.zoo '*.txt' # extract selected members
```

## Upstream tests

None — the distribution is one C file with no test suite, test data or test
target.  `test_package` therefore performs a real round trip: it builds a
spec-valid zoo archive (descriptor, one directory entry with a stored member and
its CRC-16, and the `posnxt == 0` terminator), has the installed `unzoo` list
and extract it, and compares the extracted bytes with the original payload.
unzoo prints `extracted` only when the member's CRC-16 matches the value in the
directory entry, so the check covers the CRC path too.

See `4.4/notes.md` for the full record — including the four archive-format
details that are easy to get wrong (the terminator entry, `minver` must be 0,
little-endian fields, reflected CRC-16) — and `4.4/test_package/MANIFEST.yml`
for the test audit.
