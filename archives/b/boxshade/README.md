# boxshade

BOXSHADE — shade multiple sequence alignments into PostScript/EPS/HPGL/RTF/HTML/ASCII/xfig/PICT/ReGIS/LJ250 output.

- Homepage: https://sources.debian.org/src/boxshade/ (authoritative 3.3.1 source; original EMBnet page defunct)
- License: Public Domain
- Build system: Makefile (`makefile.unx`)
- Conan reference: boxshade/3.3.1

## Notes

- The 3.3.1 source (Debian pool `boxshade_3.3.1.orig.tar.gz`) is the classic 1997
  C version (v3.31 C port by Hartmut Schirmer; authors Kay Hofmann / Michael D. Baron).
- Data files `*.par` / `*.sim` / `*.grp` must be reachable at runtime: the program
  searches the current directory and then `$BOXDIR`, which defaults to the directory
  of the executable — the Conan package installs them in `bin/` next to `boxshade`.
- No upstream test suite; `test_package` smoke-tests the packaged binary (`-help`).
