# Project IceStorm 1.1.1

## Scope

Version 1.1.1 is 1.1 plus a correctness fix for the iCE40 device databases.
The upstream source, the source sha256, and the built tool set are unchanged;
only the recipe's build description changed.

Version is bumped 1.1 -> 1.1.1 per R37 (the artifact registry does not host
multiple revisions of the same version).  Branch `fix/icestorm-1.1.1` carries
the bumped version, matching the CI L0n rule that the branch name end in
`{package}-{version-directory}`.

## Defects in 1.1

### 1. The device databases were never packaged

`share/icebox/chipdb-*.txt` were absent from the 1.1 package.  These files are
build products, not source files:

- The v1.1 source tarball's `icebox/` directory holds only generator scripts
  (`icebox_chipdb.py`, `iceboxdb.py`, `icebox.py`) - no `chipdb-*.txt`.
- Upstream `icebox/Makefile` generates them at build time:
  `chipdb-5k.txt: icebox.py iceboxdb.py icebox_chipdb.py` ->
  `$(PYTHON3) icebox_chipdb.py -5 > chipdb-5k.new`, and installs them with
  `cp chipdb-*.txt $(DESTDIR)$(PREFIX)/share/icebox/`.
- The 1.1 recipe replaced upstream's recursive Makefiles with a hand-written
  CMakeLists that builds the five tools and the timing tables but never runs
  `icebox_chipdb.py`.
- Its `install(DIRECTORY icebox/ ... FILES_MATCHING PATTERN "chipdb-*.txt")`
  matched an empty set.  CMake does not warn when `FILES_MATCHING` selects
  nothing, so the package was silently incomplete.

### 2. `CHIPDB_SUBDIR` was given a wrong value

`icetime` resolves its device database through `find_chipdb()`
(`icetime/iceutil.cc`), which builds both of these:

```
PREFIX "/share/" CHIPDB_SUBDIR "/chipdb-" + device + ".txt"
proc_self_dirname() + "../share/" CHIPDB_SUBDIR "/chipdb-" + device + ".txt"
```

`CHIPDB_SUBDIR` is the component *below* `share/`: upstream
`config.mk:26` sets `CHIPDB_SUBDIR ?= $(PROGRAM_PREFIX)icebox`, i.e. `icebox`.
The 1.1 recipe compiled `CHIPDB_SUBDIR="/share/icebox"`, so the two paths became
`<prefix>/share//share/icebox/...` and `<bindir>/../share//share/icebox/...`,
neither of which can exist.  Even once the databases are installed, the binary
would not find them.

## Fix

In the recipe's generated CMakeLists:

- Generate `chipdb-{384,1k,8k,5k,lm4k,u4k}.txt` at configure time by running
  `icebox/icebox_chipdb.py` with the same per-device flags as upstream's
  `icebox/Makefile` (`-3`, none, `-8`, `-5`, `-4`, `-u`), and
  `install(FILES ... DESTINATION share/icebox)`.
  The six devices match upstream's `all:` target exactly.
- Set `CHIPDB_SUBDIR="icebox"`.

`PREFIX` is left as-is: it is baked to the build-time install prefix, but
`find_chipdb()` falls back to the binary-relative path, which resolves correctly
in the Conan layout (`<pkg>/bin/` + `<pkg>/share/icebox/`).

## Verification

### Local reproduction (WSL, x86_64, cmake 4.2.3)

The extracted CMakeLists was configured against the pristine v1.1 source:

- configure exit 0; all six databases produced
  (384: 1.8 MB, 1k: 7.1 MB, 5k: 27.8 MB, 8k: 38.1 MB, lm4k: 17.7 MB, u4k: 18.6 MB)
- 7 timing `.cc` files produced

`icetime` was then built twice from that source, differing only in
`CHIPDB_SUBDIR`, and asked where it looks for the 1k database (driven with a
minimal `.asc` containing `.device 1k`, since the device name comes from the
`.asc`, not from `-d`):

| `CHIPDB_SUBDIR` | path reported by `icetime -v` | exists |
|---|---|---|
| `/share/icebox` (as 1.1 shipped) | `<build>/../share//share/icebox/chipdb-1k.txt` | no |
| `icebox` (this fix) | `<build>/../share/icebox/chipdb-1k.txt` | yes |

### Downstream interface (nextpnr 0.1)

nextpnr's `ice40/CMakeLists.txt` runs `ice40/chipdb.py` against
`${ICEBOX_DATADIR}/chipdb-<device>.txt` plus the `icefuzz` timing tables.
Feeding the freshly generated databases and the shipped timing files into
nextpnr's own generator succeeded for all tested devices:

- `chipdb-1k.bba` (93 MB), `chipdb-5k.bba` (359 MB), `chipdb-8k.bba` (494 MB),
  all exit 0, emitting the expected `EmbeddedFile chipdb_file_<dev>(...)` form.

The package now provides the five devices nextpnr uses (384, 1k, 5k, u4k, 8k)
plus `lm4k`, and all seven `timings_*.txt` nextpnr requests.

## Upstream tests

Executed: **3** - the whole of upstream's `icebox/Makefile` `check` target
(`tc_logic_xpr.py`, `tc_xlat_netnames.py`, `tc_rxlat_netnames.py`).  They run in
`build()` after the databases are generated.  They are pure Python
(`icebox.py` imports only `iceboxdb`) and need no Yosys; the two netname tests
load the chipdb databases, so they additionally prove the databases this
revision generates are readable by `icebox.py`.

Not executed: **13** upstream test items, none claimed as passed.

| Item | Count | Why not executed |
|---|---|---|
| `icetime` `test0`..`test9` | 10 | Both the `testN` and `runN` forms need the `testN.asc`/`testN.pcf` inputs from `icetime/mktest.py`, which runs `icefuzz/icecube.sh` and `yosys -qp ... testN_ref.v` (mktest.py:150, 204). No Yosys available. |
| `icebram` `test` (`bash rundemo.sh`) | 1 | Runs yosys, nextpnr-ice40, icebox_vlog, iverilog and vvp. |
| `icecompr` `test` (`example_1k.ok`, `example_8k.ok`) | 2 | Needs the `icecompr` / `iceuncompr` utilities. Upstream's default build does not cover them either (top-level `SUBDIRS` is `icebox icepack icemulti icepll icebram icetime`), so this recipe does not widen its tool set to reach them. |

`icefuzz/Makefile` `check` is wildcard-driven over `work_*/*.bin`; no such
directories exist in the release tarball, so it materialises zero test items
rather than being skipped.  The 1.1 manifest's stated reason for its icetime
tests (external Yosys) was correct and is retained.

The five CLI tools are also exercised by the consumer test, which drives a real
runtime chipdb lookup through the installed `icetime`.
