# test_package/data — fixtures taken verbatim from the upstream source tarball
#
# Source: https://github.com/jblang/d52/archive/ac20ebd03fc2d102b46d6fa4166ebaa7552546dd.tar.gz
#         (d52 3.4.1-git20191024.ac20ebd), directory `cyclefiles/`.
# All files below are byte-identical copies of the upstream originals, with two
# storage adaptations that do not change any byte the tools see:
#
#   1. two file names were lower-cased to the exact name the tools fopen() when
#      invoked as shown (CI workers have case-sensitive filesystems):
#        cyclefiles/BENCH0.HEX  ->  bench0.hex
#        cyclefiles/Bench0.ctl  ->  bench0.ctl
#   2. the Z80 binary input is stored as printable text instead of a raw .bin:
#        cyclefiles/z.bin  ->  z.bin.esc
#      z.bin.esc holds the same 39 bytes as one POSIX octal escape ('\ooo') per
#      byte, on a single line. test.sh rebuilds z.bin from it with
#      `printf '%b' "$(cat z.bin.esc)"` (a shell builtin; verified on the device's
#      /bin/sh = MirBSD KSH R59 and under busybox ash;
#      '%b' expands the escapes in the argument instead of treating the file
#      content as a printf format string).
#      Reason: a raw binary added by a PR cannot be applied by the CI checkout
#      step — the platform-generated pr.diff carries no binary patch data
#      ("error: missing binary patch data ... patch does not apply", CI build
#      44060), which fails the whole pipeline before the build even starts.
#      Keeping the archive text-only avoids that; the rebuilt byte sequence is
#      proven correct end-to-end because any wrong byte changes the disassembly
#      and breaks the byte-for-byte comparison against upstream z.z80.
#
# Upstream ships these files as its own benchmark/reference data: BENCH0.HEX is
# the 8051 benchmark program, bench0.<derivative>.d52 are the disassembler
# outputs including cycle counts for each MCU derivative cycle file, and
# z.bin/z.ctl/z.z80 is the equivalent Z80 example (see cyclefiles/
# cycle_counting.doc in the upstream tarball). test_package/test.sh replays them
# against the installed binaries and compares the output byte for byte, ignoring
# only the 4-line version/date header (3.4.1 prints the date as y/m/d).

| fixture | bytes | sha256 |
|---------|-------|--------|
| bench0.hex (upstream BENCH0.HEX) | 180 | c9adba30e94eea698a6df05cf99ee6166e1a0d4f81fbc339979f7d8c7619c5f7 |
| bench0.ctl (upstream Bench0.ctl) | 12 | 7de8153c05c45dd62430414051681759301bd63abce17f54990803f4c8956727 |
| ADuC84x.cyc | 1874 | a0cac78d4b0fab25711276f898a176beb04dd0440b5debede84750c696568c7d |
| AT89LP.cyc | 1960 | 747d4a28f15ebaa59d8c46ddc8434c96f76503d44626cfd808ce4945987abcaa |
| DS80C320.cyc | 2062 | bc42787fed45eeb3c1b684b5627a47b2559324e66b6de97c0b27361dea6f89d7 |
| DS89C4x0.cyc | 2041 | 2f966a7d696073b44de9e93ebbec764deface1ac7ba1712436d8955a8d611d8a |
| MSC12xx.cyc | 2058 | d0f5fd7a9d2c914c70b557057e05038ee9760d4593339b3b19ffe024c773261f |
| SiLabs.cyc | 2087 | f333aef5c18b7ca9cb3636825794b3dd058a334b430d3cac788cca6f47afae51 |
| W77e.cyc | 2056 | c876a1fdb8c080ef30ba0accc45c4556f97abc9eb7cf53f33ab6250b6550bf59 |
| bench0.aduc84x.d52 | 726 | 6b0800e7bdf8cdb5fad44a4e5f2c15dc43dae4be6f819f2256e3354863ef371b |
| bench0.at89lp.d52 | 726 | 9bde5945a039497b15f90a2e88338e05e80cb0ad3ccce3670c7a8c58fb93992b |
| bench0.ds80c320.d52 | 726 | ac0d98a8c7506716a7b15e296d7ed82710092646793c89349876fc9cfcb596c8 |
| bench0.ds89c4x0.d52 | 726 | df9425c0ac55b08e7e0a2eae236a93a043e51cea4e127e3bab6671fa513afc4c |
| bench0.msc12xx.d52 | 726 | bd8d5ae0a501236bc4bd1a09800f74df85aa6c02b4efa030413522e7ec7471a1 |
| bench0.silabs.d52 | 726 | 923c4161ccf22155ded92f628c9dae40bcb68a8b81d7b3cb0b0f72c7d503d081 |
| bench0.w77e.d52 | 726 | dcb0dbccf529be691f8b7d111fb5feafb7a94b63a1f035c293050d5063a4dceb |
| z.bin.esc (upstream z.bin) | 157 text bytes -> 39 binary bytes | 9479e0716ccbe87ee521c0d7a955d6f45b7cee8338e8bbd9e7f02bbff488db55 (hash of the rebuilt 39 bytes) |
| z.ctl | 244 | 8efa4da77be3addccafe462bff4cdd1c8620c505d9d529a20f9400102631af93 |
| z.z80 | 1470 | 1d43944c21f58befe6fdff50788f1aff94e5985a120cde21a2eb898ccaac455b |

The `.d52`/`.z80` files are GPL-3.0-or-later data taken from the same upstream
source release as the recipe's `sources.url` (see `../conandata.yml`).
`z.bin.esc` is the same upstream GPL-3.0-or-later data in escaped text form; the
sha256 above is of the 39 bytes test.sh rebuilds from it (verified on device with
`printf '%b' "$(cat z.bin.esc)" | sha256sum`).
