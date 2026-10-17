# lbrate

lbrate (Russell Marks, 2001) lists, tests and extracts CP/M **LBR** archives and
transparently decompresses their squeezed (`?Q?`), crunched (`?Z?`) and LZH
(`?Y?`) members, `unzip`-style.  It also handles such compressed files outside
an LBR, treating them as single-member archives.

- Source: https://ibiblio.org/pub/Linux/utils/compress/lbrate-1.1.tar.gz (ibiblio / Sunsite Linux archive, the upstream distribution site)
- Release: 1.1
- License: GPL-2.0-or-later
- Package form: `bin/lbrate` (application) + `share/man/man1/lbrate.1`

## HarmonyOS PC adaptation

No patches.  The upstream Makefile hard-codes `CC=gcc`; the recipe overrides it
on the make command line with the profile compiler
(`tools.build:compiler_executables`).  The five C files build with zero
warnings under OHOS clang 15 `-O2 -Wall`; `getopt.h`, `utime.h` and the
`gmtime`/`mktime` pair are all provided by the OHOS musl libc.

## Usage

```sh
lbrate -l archive.lbr          # list members (-v for method/CRC detail)
lbrate -t archive.lbr          # test member CRCs
lbrate archive.lbr             # extract (and decompress) all members
lbrate archive.lbr '*.txt'     # extract selected members
lbrate -n archive.lbr          # extract without decompressing
```

## Tests

Upstream ships none.  `1.1/test_package/test_lbrate.py` builds spec-valid LBR
archives (stored + squeezed members, CRC-16, CP/M date stamps) and runs 12
checks against the packaged binary, two of them OHOS-specific.  See
`1.1/notes.md` and `1.1/test_package/MANIFEST.yml`.
