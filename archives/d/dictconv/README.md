# dictconv

dictconv is a small command line converter for dictionary file formats. It reads
Babylon (`.bgl`), FreeDict/TEI (`.tei`), Sdictionary (`.dct`) and StarDict
(`.ifo`) dictionaries and writes PlainText (`.dic`), StarDict (`.ifo`) or
DICTd (`.index`) files. Upstream development stopped after the 0.2 release
(October 2007).

## OHOS adaptation

- Builds the official 0.2 tarball with the CMake path that upstream ships next
  to its Autotools files. The 2006 `config.guess` cannot identify HarmonyOS
  (`uname -p` is `unknown`), so `./configure` aborts.
- Adds `cmake_minimum_required(VERSION 3.5)` to the 2007 CMakeLists, which
  CMake 4.x otherwise rejects outright.
- Includes `<sys/types.h>` in the seven translation units that rely on the
  legacy `u_int32_t` / `uint` typedefs, which musl headers no longer provide
  implicitly.
- Switches the option parser to `getopt_long` so the GNU style options
  (`--help`, `--version`, `--output`) work.
- Keeps upstream source semantics otherwise untouched; no behaviour changes
  beyond the four portability fixes above.
- Upstream ships no test suite at all, so the consumer tests live in
  `test_package/test.sh` (7 cases, byte-for-byte comparisons of every supported
  output format plus two error paths).

## Dependencies

- `libxml2/2.15.3.1` parses the FreeDict/TEI and Babylon readers.
- `zlib/1.3.1.1` is linked statically for the compressed dictionary support
  (R26: no dynamic link against the system `libz`).

## Known upstream limitations (not fixed by this port)

- Output file names shorter than six bytes trip an unsigned underflow in
  `outfile.compare(outfile.length() - 6, ...)` and abort with
  `std::out_of_range`.
- The StarDict reader (`dump()` / `search()`) returns pointers into local
  `std::string` objects, so `.ifo` input conversion output is not
  deterministic.
- DICTd plain or compressed dictionary bodies (`.dict`, `.dict.dz`) are not
  accepted as input; only the four formats listed above are.

## References

- http://dictconv.sourceforge.net/ (site gone; archived tarballs live in the
  Debian pool: https://ftp.debian.org/debian/pool/main/d/dictconv/)
