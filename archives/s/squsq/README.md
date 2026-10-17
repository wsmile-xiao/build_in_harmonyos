# squsq

Compressor/decompressor for CP/M "Squeeze" compressed files. Provides two
command line tools:

* `sq` — squeezes a file (LZ-style run encoding + Huffman coding), writing the
  result under the CP/M 3.0 naming convention (extension replaced by `.SQ`).
* `usq` — unsqueezes a `.SQ` file back to the name recorded in its header, with
  optional preview modes (`usq -<n>`, `usq -F`, `usq -`).

Version 3.3 is the TOPS-20 port of SQU-PORT v3 released to SIMTEL20 by
Frank J. Wancho; the same `t20-squsq-3.3.tar.gz` distfile is packaged by NetBSD
pkgsrc and FreeBSD ports as `archivers/squsq`.

## Versions

| Version | Status |
| --- | --- |
| 3.3 | built |

Homepage: <https://cdn.netbsd.org/pub/pkgsrc/current/pkgsrc/archivers/squsq/>

Usage (after `conan install`): `sq file.txt` → `file.SQ`; `usq file.SQ` → `file.txt`.

## Platform notes (HarmonyOS PC / aarch64)

* The tarball contains **no build system**: only K&R C sources plus TOPS-20 MIC
  scripts (`makesq.mic` / `makeusq.mic`, unusable outside TOPS-20). The Unix
  build recipe lives in the distribution ports (`files/Makefile`), and this
  recipe reproduces its exact target/source mapping with the compiler taken from
  the Conan profile.
* Two diagnostics that the era's compilers treated as warnings are hard errors
  under ISO C99+: `-Wno-error=return-type` and `-Wno-error=int-conversion` —
  the same switches the FreeBSD port uses. The 1986/1988 sources stay unpatched.
* The OHOS SDK clang driver self-signs every linked image (`ld.lld --code-sign`),
  so the packaged ELFs already carry `.codesign` / `.note.ohos.ident`; the recipe
  only re-signs if the signature were missing.
* There is no upstream test suite; 27 cases derived from the upstream readme and
  source behaviour are executed by `test_package`. See `3.3/notes.md`.
