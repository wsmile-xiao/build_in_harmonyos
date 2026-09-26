# jellyfish1

Jellyfish is a tool for fast, memory-efficient counting of k-mers in DNA.
A k-mer is a substring of length k, and counting the occurrences of all such
substrings is a central step in genome assembly. Jellyfish stores the histogram
of k-mer counts in a compact lookup table that is read back through mmap.

## Homepage
https://github.com/gmarcais/Jellyfish

## License
GPL-3.0-or-later

## Build System
Autotools (configure + make + make check)

## Dependencies
None outside the C/C++ standard library and POSIX pthreads (verified by
ci/scripts/preflight_check.sh for this version).

## OHOS Adaptation
- The 2013-era config.sub shipped in this tarball rejects the -musl triplet
  (measured first error: "Invalid configuration aarch64-unknown-linux-musl:
  machine aarch64-unknown-linux not recognized"), so the
  --build/--host=aarch64-unknown-linux-musl pin that other OHOS recipes use
  (4ti2/1.6.10) does not work here.  The recipe pins both triplets to
  aarch64-unknown-linux-gnu, which also keeps config.guess out of the
  configure run (no config.guess patch needed).
- config.status runs (umask 077 && mktemp -d ./confXXXXXX); on HMDFS that
  produces a setgid directory without group-execute and configure aborts. The
  recipe relaxes the umask to 002 (same class of fix as 4ti2/1.6.10).
- CONFIG_SHELL must NOT be pointed at /data/service/hnp/bin/bash for this
  package, even though the shared OHOS profile exports it.  Under that shell
  the 2013 autoconf/libtool pair loses one level of quoting when config.status
  rewrites @archive_cmds@, so the generated libtool stops parsing
  (./libtool: line 350: syntax error near unexpected token), and libtool picks
  ECHO="print -r --" where print is a toybox ash builtin that that bash does
  not provide (./libtool: line 907: print: command not found).  Disposition:
  after configure, the recipe rewrites the recorded bash path inside
  config.status to /bin/sh and re-runs it with CONFIG_SHELL=/bin/sh
  SHELL=/bin/sh as a command-line prefix assignment (full regeneration,
  followed by sh -n libtool).  Key reverse experience - see
  1.1.11/notes.md section 3.
- Two test readings are reported side by side and must not replace each other.
  *Pre-patch upstream baseline*: 19 of 19 tests failed (probe-check.log:44);
  that total failure has one entry point, a throwing destructor:
  jellyfish/err.hpp raises from ~raise_t(), which is implicitly noexcept since
  C++11, so every eraise became std::terminate and the retry loop's catch
  clause in tests/generate_sequence.cc could never be reached.  This is a
  language-rule version difference, not cross-DSO RTTI/typeinfo matching: the
  same unpatched idiom aborts with RC=134 under both the static and the
  shared link flavour.  Disposition is a one-line upstream patch,
  noexcept(false).  *Delivered round (patch 0001 applied)*: 4 PASS / 15 FAIL /
  1 SKIP, UPSTREAM_MAKE_CHECK_RC=2 (1.1.11/reports/w3-local-ci.log:788,
  :800); the 15 remaining failures are the tests/compat.sh baked-md5 baseline
  family, not this mechanism.  See 1.1.11/notes.md.

## Versions
- 1.1.11 - see 1.1.11/manifest.yaml
