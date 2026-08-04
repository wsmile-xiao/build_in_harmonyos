# Link Grammar 5.13.0 adaptation notes

## Scope

- Conan reference: `link-grammar/5.13.0`
- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1651
- Target: HarmonyOS PC, OHOS 6.0, AArch64
- Delivery: static core library, public headers, language dictionaries, and
  the `link-parser` command-line program

## W0 dependency verification

The following exact OHOS 6.0/armv8 binaries were downloaded from the `ohpcd`
Conan remote before implementation:

- `pcre2/10.45`, recipe revision
  `5ecd2f9871deb549e2ae07489f2e40df`, package revision
  `cf10e83f43cd9b8dd5dc5d21d4d44ab9`
- `sqlite3/3.49.1`, recipe revision
  `669361066cc2c76e0ed897e6b6a27e38`, package revision
  `9bae7e00509d3fd4c2f65da552f63fad`
- `automake/1.18` and `libtool/2.5.4` tool packages

The published `flex/2.6.4` Conan package was inspected but does not contain a
`bin/flex` executable. Autoreconf therefore uses the HNP Flex executable from
the HarmonyOS PC build profile instead of declaring a non-functional Conan
tool requirement.

`hunspell/1.7.2` and `libedit/20240808` were not downloadable from the remote,
so those optional integrations are explicitly disabled instead of declaring
unavailable dependencies.

## Source and build decisions

The official Git tag archive has SHA256
`a545b7efb7aceab2d8ad301466f199778a3da712928999ed8d66deb32ca3184f`.
It contains `configure.ac` and `Makefile.am` but no generated `configure`, so
the recipe runs `autoreconf` with published tool packages plus the official GNU
Autoconf Archive macro collection. Because Automake and Libtool scripts cannot
be executed directly from their HMDFS Conan package paths, the recipe builds
small AArch64 ELF launchers that invoke those scripts through the HNP Perl and
Bash interpreters. The generated configure script reuses the project's
established HMDFS workaround by changing Autoconf temporary-directory mode from
077 to 022, and the VPATH build directory is placed under the writable
`/data/storage/el2/base/cache` filesystem.

PCRE2 and SQLite3 paths are passed through the standard Autoconf override
variables. Their static archives are copied into a build-private directory
without Libtool metadata and passed as scoped `-L`/`-l` values instead of
global dependency flags. This avoids the non-relocatable `libpcre2-8.la`
shipped by the dependency package, whose archived `libdir='//lib'` otherwise
causes Libtool to reject it after reporting that the library was moved. It also
lets Libtool record SQLite as a link dependency instead of nesting the complete
`libsqlite3.a` archive inside `liblink-grammar.a`. The dependency packages
themselves are not modified.

After configure, the recipe removes Conan dependency include directories from
the generated `LG_CFLAGS` display string in `link-features.h`. The real compile
flags remain in the generated Makefiles, while `link-parser --version` no
longer embeds a machine-specific Conan cache path.

The recipe uses `--with-regexlib=pcre2` without also passing
`--enable-pcre2`. In Link Grammar 5.13.0, explicitly passing the latter clears
the selected `with_regexlib` value and silently falls back to the libc regex
implementation.

## Upstream tests

With language bindings and the SAT solver disabled, upstream `make check`
contains four C++ test programs:

1. `dict-reopen`
2. `multi-dict`
3. `multi-thread`
4. `mem-leak`

Native OHOS builds execute all four. Cross builds compile all four without
claiming that they ran.

## Consumer test

The Conan `test_package` links a C++ consumer, supplies the packaged dictionary
directory through the public `dictionary_set_data_dir()` API, verifies the
reported library version, parses an English sentence, creates a linkage, and
checks its words and links.

## Validation status

The final v16 run used a new Conan home on a HarmonyOS PC test device; no
package or build result was reused from earlier runs.
It completed Autoreconf, configure, compile/link, all four upstream tests,
installation, Conan packaging, CMake consumer compile/link, API consumer
execution, `link-parser --version`, and a CLI sentence parse.

- Upstream tests: 4/4 passed (`dict-reopen`, `multi-dict`, `multi-thread`,
  `mem-leak`).
- Added package-consumer tests: 2/2 passed (C++ API parser and packaged CLI).
- The API consumer loaded the packaged English dictionary and produced eight
  valid linkages.
- The CLI loaded the packaged English dictionary and parsed the same sentence
  in batch mode.
- Both executables are AArch64 ELF files and ran directly on the target.
- The package contains 546 files, no `.la` metadata, and no Conan test-run path
  in the CLI or static library.
- `liblink-grammar.a` contains 66 object members and no nested PCRE2 or SQLite
  archives.
- Final log SHA256:
  `2659e1c1eb99608e4708b82cea60c096a4ea9f09bda7b527e268809aba99be7b`.

Detailed evidence is in `reports/device-test-20260731.md`.

## Knowledge decision

The recipe reuses existing project knowledge for Git archives without a
generated configure script, HMDFS-safe Autoconf temporary permissions, target
tool discovery from the configured compiler, and explicit interpreter
launching for HMDFS scripts. Latest-main review also found the existing Aravis
ELF launcher precedent, so those parts do not independently qualify for path B.

The final latest-main de-duplication covered `knowledge/graph`,
`knowledge/doc`, `knowledge/operations`, and archived knowledge drafts. It
found generic Libtool diagnostic text and upstream `ltmain.sh` patches, but no
entry that explains the combined failure where a relocated dependency `.la`
file redirects Libtool to an invalid install path and an absolute `.a`
workaround becomes a nested archive member. E253 records the reusable fix:
stage only dependency archives in a `.la`-free private directory, pass them
through dependency-scoped `*_LIBS` variables, preserve the Conan cache, and
verify archive members plus a real target consumer. The delivery therefore
claims path A (base adaptation) and path B (knowledge extension).

Knowledge draft:
`archives/knowledge/graph/draft/E253-draft-7950.{kv,md}`.
