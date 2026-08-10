# apertium-mkd-eng 0.1.3 — Adaptation Notes

## Software Info

| Field | Value |
|-------|-------|
| Name | apertium-mkd-eng |
| Version | 0.1.3 |
| Description | Apertium linguistic data for Macedonian-English translation |
| License | GPL-3.0-or-later |
| Homepage | https://github.com/apertium/apertium-mkd-eng |
| Source URL | https://github.com/apertium/apertium-mkd-eng/archive/refs/tags/v0.1.3.tar.gz |
| Source SHA256 | `0b597056bc7563d246151b518e78b0e85db33e3d6e36f6f859c6bdea0030751c` |
| Build System | autotools (configure.ac + Makefile.am + autogen.sh) |

## Build Characteristics

apertium-mkd-eng is a **language-pair data package** for the Apertium
machine translation platform. It contains:

- **Monolingual dictionaries**: `apertium-mkd-eng.mkd.dix` (Macedonian),
  `apertium-mkd-eng.eng.dix` (English)
- **Bilingual dictionary**: `apertium-mkd-eng.mkd-eng.dix` (MKD→ENG
  translation correspondences)
- **Transfer rules**: `.t1x` (word-level), `.t2x` (interchunk),
  `.t3x` (postchunk)
- **Constraint grammar**: `.rlx` (CG rules), `.lex` (lexical
  disambiguation)
- **HMM tagger data**: `mkd-eng.prob`, `eng-mkd.prob`
- **Mode definitions**: `modes.xml` (defines translation pipeline modes)
- **Other**: `.acx` (character conversion), `.alpha.dix` (alphabetic
  transliteration), `.post-eng.dix` (post-generation), `lexchoicebil.xsl`

### No C/C++ Compilation

This package contains **no compiled code**. The Makefile.am uses apertium
tools (`lt-comp`, `cg-comp`, `apertium-preprocess-transfer`) to compile
the XML-based `.dix` files into binary `.bin` cache files. These `.bin`
files are text-based serializations, not ELF binaries.

## Dependencies

### Runtime Dependencies (not build-time)

- **apertium** (core engine): provides `lt-comp`, `lt-proc`, `cg-comp`,
  `apertium-tagger`, `apertium-transfer`, `apertium-interchunk`,
  `apertium-postchunk`, `apertium-preprocess-transfer`,
  `apertium-validate-dictionary`, `apertium-validate-transfer`, etc.
- **cg3** (constraint grammar compiler): provides `cg-comp`

**Status**: Neither apertium nor cg3 is published to the OHOS 制品仓
(ohpcd remote). Checked via `conan list 'apertium/*' -r=ohpcd` → 0 results.

### Build-time Dependencies

None. The package is pure linguistic data.

## Adaptation Process

### Decision: Package Raw Data Files

Since the apertium core engine is not available on OHOS:

1. **Skip autotools configure/make**: The `configure` step requires
   `PKG_CHECK_MODULES(APERTIUM, apertium >= 3.8.1)` and
   `PKG_CHECK_MODULES(CG3, cg3 >= 1.3.6)` which would fail without the
   apertium and cg3 packages installed. The `make` step requires
   `lt-comp`, `cg-comp`, and `apertium-preprocess-transfer` binaries.

2. **Install data files directly**: The `package()` method copies all
   linguistic data files (.dix, .t1x, .t2x, .t3x, .rlx, .lex, .prob,
   .acx, modes.xml, etc.) from the source directory to
   `share/apertium/apertium-mkd-eng/` in the Conan package.

3. **Validate in build()**: The `build()` method validates that all
   required data files exist and are non-empty, ensuring data integrity
   before packaging.

### Package Type: header-library

We use `package_type = "header-library"` because:
- No compiled binary output (no .so, no .a)
- Pure data content package
- Conan treats header-library packages as content-only (no binary
  matching needed)

### Settings: os, arch only

No `compiler` or `build_type` settings needed since there's no
C/C++ compilation. The `os` and `arch` settings are retained for
Conan's package compatibility tracking.

## Test Approach

### test_package (Conan L1 test)

The test_package runs `test_apertium.py` which validates 11 substantive
properties of the packaged data:

1. Data directory exists under `share/apertium/apertium-mkd-eng/`
2. `modes.xml` exists and is non-empty
3. `modes.xml` is valid XML with `<modes>` root element
4. `modes.xml` defines the `mkd-eng` translation mode
5. Core `.dix` dictionary files present (Macedonian, English, bilingual)
6. Transfer rule files present (`.t1x`, `.t2x`, `.t3x`)
7. Constraint grammar files present (`.rlx`, `.lex`)
8. HMM tagger probability files present (`.prob`)
9. Total data file count >= 10
10. `mkd-eng.dix` contains Macedonian content (Cyrillic text or
    "Macedonian" references)
11. `mkd-eng.dix` is valid XML with `<dictionary>` root
12. `mkd-eng.t1x` is valid XML with `<transfer>` root

### Upstream Tests

The upstream tests are in the `test/` directory and use
`apertium-regtest`. The test definition (`test/tests.json`) specifies
one test case: `mkd-eng-pending` which processes
`mkd-eng-pending-input.txt` through the `mkd-eng` translation mode.

**Cannot run**: These tests require the full apertium translation
pipeline (all the binary tools from the apertium core package), which
is not available on OHOS. Once `apertium` core is published to the
OHOS 制品仓, these tests can be enabled.

## Key Decisions

1. **Pure data packaging**: Install raw linguistic data files without
   compilation. The `.bin` compiled forms are cache files that can be
   regenerated by downstream consumers with the apertium core installed.

2. **No autotools configure**: Skip the `configure` step entirely since
   it would fail on missing `PKG_CHECK_MODULES` for apertium/cg3. The
   package doesn't need configure — it's pure data.

3. **Runtime dependency documentation**: apertium core is declared as
   a runtime dependency in notes.md and MANIFEST.yml, but not in
   `requirements()` since it's not published to ohpcd and we're only
   packaging the data files.

4. **Substantive test_package**: The test validates file content (XML
   validity, presence of Macedonian translation entries, mode
   definitions) rather than just file existence, per R34.
