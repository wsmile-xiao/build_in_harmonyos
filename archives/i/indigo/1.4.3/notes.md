# indigo 1.4.3 - adaptation notes

## Source
- URL: https://github.com/epam/Indigo/archive/refs/tags/indigo-1.4.3.tar.gz
- sha256: 0fc4ef5777573a3bcefaa359d58c221d250994e4741ffb7d13b92ea47d63fdb0
- Size: 9494718 bytes (verified by download; identical to Debian orig hash).
- License: Apache-2.0.

## Scope
- Core library only via build_scripts/indigo: common/graph/molecule/reaction/
  layout + api (C API, indigo-shared). Vendored third_party (zlib, tinyxml,
  inchi) used, so no system freetype/fontconfig needed.
- Out of scope: bingo (needs DB), renderer (needs cairo), Java/dotnet/Python
  wrappers.

## Build system
- CMake 3.4+ project with custom ConfigureCommon (SYSTEM/SUBSYSTEM detection,
  -fPIC, RPATH $ORIGIN). On aarch64 the x86-only -m32/-m64 branch is skipped
  (processor guard), so no OHOS patch needed there.
- OHOS portability: api/CMakeLists.txt links `-lpthread -lrt`; OHOS has no
  separate librt, so source() rewrites that line (and the matching
  LINK_INTERFACE_LIBRARIES entry) to `-lpthread` when settings.os == OHOS.
- R32: validate() and package_info() use `in ("Linux", "OHOS")`.

## Upstream tests
- CMake-registered suite in scope: 1 test.
  - indigo-c-test-shared (DEFINE_TEST in api/CMakeLists.txt,
    api/tests/c/indigo-test.c): version print, bad-reaction error path,
    molecule load + canonical SMILES, transform, reaction gross formula.
- indigo-all additionally defines dlopen-test, but it dlopens all four
  plugin libs (indigo/indigo-inchi/indigo-renderer/bingo) which are not
  built in this recipe, so it is not part of this build's ctest run.
- Wider suites outside the CMake gate (audited, not run here):
  api/tests/python (~80 scripts via test.py, needs Python wrapper build and
  rendering reference outputs), api java/dotnet tests (need JDK/.NET),
  bingo-elastic/service tests (need Elasticsearch/DB). Documented in
  test_package/MANIFEST.yml upstream_test_audit.

## Consumer test
- test_package/test_indigo.c: 7 CHECKs over the real C API (version string,
  CCO load + canonical SMILES round-trip, benzene load, reaction load,
  gross formula handle + string). Prints
  "Indigo consumer checks: N/7 passed".
- test_package/conanfile.py test() performs real self.run calls (ctest plus
  direct binary execution) and emits HMBS_TEST_PACKAGE_RESULT with
  discovered/passedCount parsed from the binary output. Exit 0 without the
  marker line is treated as failure.

## Preflight history
- 2026-09-19: worktree was empty / Windows case-collision dirty state
  (archives/l/libxext vs libXext, archives/g/gama bad-name file) left the
  HMBS archive unreadable (evidence/incomplete). Fixed with sparse exclusions
  for those paths and created this recipe tree; awaiting first real
  conan-create preflight on HarmonyOS aarch64.
- 2026-09-19 (round 3): configure-stage OHOS mapping (HarmonyOS/OHOS STREQUAL
  in GetSystemVersion/SetBuildParameters/api CMakeLists) got past
  `Configuring done` to C++ compile; new failure is libc++ reserved-macro
  collision: defs.h `#define __swap(a,b,tmp)` rewrites
  `std::variant::__swap(__impl&)` (variant:1150, via
  cancellation_handler.cpp -> tlscont.h -> <memory>/<iterator>/<variant>).
  Fix route changed from cmake mapping to source macro rename
  (__swap -> INDIGO_SWAP, idempotent bulk rename, third_party excluded).
  Also hardened _run_upstream_tests to deterministic ctest -N + per-test
  Test #N parsing with identity self-check, and added
  upstream_test_total/method to test_package/MANIFEST.yml.
- 2026-09-19 (round 4): fixed self-inflicted verifier failure
  (`Unexpected __swap( call remains in common/base_c/defs.h`): the
  verifier scanned raw file text including our own `// HMBS: renamed
  from __swap (...)` comment, which itself matches `__swap\s*\(`.
  Changed route from naive raw-text search to comment-aware verification
  (strip `//` comments before matching, comment text avoids paren) while
  keeping the actual rename on full content.
- 2026-09-19 (round 5, strategy change): bulk INDIGO_* rename got past the
  first TU but layout/src/molecule_layout_graph_assign_smart.cpp still fails
  with 7 errors, proving bulk rewrite fragile. New route: single-file
  include-order fix in _patch_defs_preinclude (defs.h pre-includes C++11-safe
  system headers before reserved __-macros; include guards make later
  includes no-ops; upstream names and call sites untouched). Legacy bulk
  method kept as delegating stub.
- 2026-09-20 (round 7, strategy change): 3rd/4th/6th-cycle bulk renames still
  leave 7 errors in molecule_layout_graph_assign_smart.cpp; 5th-cycle
  in-defs.h pre-include self-inflicted extern-C list failure. New route keeps
  upstream __xxx names and call sites untouched: build() generates
  hmbs_prefix.h (broad C++11 set + C++14/17-gated headers) and generate()
  force-includes it via -include in extra_cxxflags/extra_cflags, so libc++
  is parsed at TU top outside any extern "C" before defs.h macros exist.
- 2026-09-20 (round 8): force-include route failed in configure, not compile:
  (a) extra flags carried our own quotes while CMakeToolchain quotes again,
  yielding `-include ...hmbs_prefix.h""` + cmake syntax warning; dropped our
  quotes. (b) OHOS libc++ has no <memory_resource> (fatal in CXX compiler
  check); C++14/17 block cut to <variant> only behind __has_include.
- 2026-09-20 (round 9, new hypothesis: cache poisoning, not macros):
  identical 7 errors in molecule_layout_graph_assign_smart.cpp survived
  three mutually exclusive fixes (bulk rename, in-defs.h pre-include,
  -include prefix), implying fixes never hit the compiled tree: build()
  mutates the Conan-cached sources in place with early-return
  idempotence and no reverse migration. Added _restore_pristine_sources()
  at build() start: deletes stale hmbs_prefix.h, strips any #include /
  HMBS marker lines from defs.h (pristine: zero #includes), reverses
  INDIGO_* back to __xxx in defs.h + all non-third_party call sites,
  then loudly verifies the six pristine anchors. Current -include prefix
  strategy then applies on a clean tree.

- 2026-09-20 (round 11, new route: macro-to-inline + extern-C quarantine;
  recipe rebuilt from pyc): local conanfile.py was found truncated to
  0 bytes, so the recipe was reconstructed from the __pycache__ bytecode
  (method list, OHOS anchors, test-runner and package logic verified by
  disassembly) with one deliberate change. Why the old route is abandoned:
  bulk rename / in-defs.h pre-include / -include prefix / include-reorder
  are mutually exclusive mitigations of the same assumption, yet every
  preflight reported the identical 7-error fingerprint in
  molecule_layout_graph_assign_smart.cpp, so the assumption "hide the
  macros from libc++" is falsified (plus each attempt self-inflicted a new
  failure: comment-regex match, extern-C linkage, quote doubling,
  <memory_resource>, restore loud-fail). New implementation route, names
  and call sites byte-identical: (1) the six function-like reserved macros
  in common/base_c/defs.h become C++ inline function templates under
  `#ifdef __cplusplus` (same call syntax; decltype(T1()+T2()) matches the
  macro ternary's arithmetic conversions; audited all ~280 call sites:
  no .c TU uses them, __swap always same-type statement, __max/__min mixes
  are arithmetic-only), C path keeps macros verbatim; (2) bitarray.h moves
  its defs.h include above `extern "C"` (only header in scope with the
  include inside extern-C; bingo/postgres hits are out of scope).
  generate() no longer injects -include flags; _restore_pristine_sources()
  kept to subtract stale hmbs_prefix.h / INDIGO_* / injected includes from
  the Conan cache before the new patch runs. Anchors verified against the
  pristine 1.4.3 tarball locally (py_compile + anchor/reversal checks);
  awaiting HMBS真机复检.

- 2026-09-20 (round 12, recipe self-crash fix; same layout-7-error domain):
  preflight of the rebuilt recipe (73bae2a) crashed in build() BEFORE any
  compile: _restore_pristine_sources line 176 `content = f.read()` raised
  UnicodeDecodeError 0xa9 at offset 97. Local tarball audit proved a single
  non-UTF-8 file in scope: molecule/CDXConstants.h holds Latin-1 0xA9
  (copyright sign) at offset 97 -- byte-exact match with the true-machine
  traceback. Fix (recipe-only, no test-scope change): all recipe file I/O
  now goes through _read_text_safely/_write_text_safely (UTF-8, fallback
  latin-1 which round-trips losslessly; byte-exact writes); conan
  replace_in_file removed accordingly. Same dry-run harness also caught and
  fixed two latent self-failures before they cost preflight rounds:
  (a) bitarray.h verification matched bare `extern "C"` which also occurs
  in our own marker comment -> now matches the `extern "C"\n{` block
  opening; (b) marker-present restore skipped everything -> now still
  sweeps INDIGO_* call-site leftovers outside defs.h/bitarray.h; plus
  defensive CRLF->LF normalization before exact-anchor matching. Verified
  locally: pristine restore+patch+idempotence AND polluted-cache
  restore+patch both pass; CDXConstants.h stays byte-identical. Awaiting
  HMBS真机复检 (the 15:29 preflight still ran the pre-fix 14:52 recipe).

- 2026-09-21 (round 13, 13th policy cycle: single-macro __swap rename;
  previous code routes all shared one hypothesis - the six reserved
  macros (__max/__min/__min3/__max3/__sign/__swap) collide as a class
  with new libc++ internals - yet bulk rename, in-defs.h pre-include,
  -include prefix header, TU reorder, and inline templates each left
  the identical 7-error fingerprint in
  layout/src/molecule_layout_graph_assign_smart.cpp, so the class-wide
  hypothesis is suspended this round. New falsifiable hypothesis: the
  only concretely evidenced collision is __swap (round-3 log: defs.h
  `#define __swap(a,b,tmp)` textually rewrote `std::variant::__swap`
  via cancellation_handler -> tlscont.h -> <memory>/<iterator>/<variant>);
  no log ever implicated __max/__min/__sign, and the failing TU itself
  only calls __max/__min (:1674). Change: _restore_pristine_sources now
  REVERTS the abandoned inline-template blocks by exact-string inversion
  (module-level constants, loud on mismatch) instead of skipping them;
  new _patch_swap_rename renames exactly __swap -> INDIGO_SWAP in defs.h
  plus all 89 call sites (21 files, all C++; tarball audit: no .c TU,
  no string-literal or // comment use; comment-aware rewrite, loud on
  leftovers or INDIGO_SWAP count < 80); the other five macros stay
  byte-identical upstream and bitarray.h quarantine is reverted to
  pristine. Verified locally (stubbed-conan import of the real recipe):
  pristine->rename gives 0 __swap leftovers and 90 INDIGO_SWAP (89 calls
  + definition); second cycle idempotent; restore-only returns the tree
  to pristine __swap; synthetic inline-dirty tree reverts byte-exact;
  exactly 22 files change (21 + defs.h), no .c file touched,
  INDIGO_PLUGIN intact, CDXConstants.h byte-identical. Awaiting HMBS真机复检
  to confirm or falsify (unchanged fingerprint kills the macro hypothesis;
  a __max/__min-shaped error escalates the same machinery to those names).

- 2026-09-24 (round 14, new route: C++-scoped `::byte`; tree-wide
  `indigo_byte` rename falsified and reverted): the 2026-09-23/24
  preflight (20 errors, `unknown type name 'indigo_byte'` in
  molecule_fingerprint.h/output.h/scanner.h via api/src/indigo.cpp)
  proves the rename design never accounted for the SECOND provider of
  the `__byte_typedef__` guard: `api/indigo.h` (public C header) and
  `common/base_c/defs.h` define `typedef unsigned char byte` under the
  same guard. Any TU including indigo.h first (indigo.cpp via
  indigo_internal.h) wins the guard race, so defs.h skips its guarded
  block INCLUDING the inserted alias, while renamed uses have no
  declaration. The layout TU (no indigo.h) compiled fine in the same
  build, confirming the guard race. New implementation: `_restore`
  reverts all `indigo_byte`/`::byte`/`:::byte`/marker residue (plus a
  `:::byte` collapse for double-patch residue); `_patch_byte_ambiguity`
  now spells `::byte` ONLY in C++ scope (all .cpp + headers outside the
  C include-closure computed by BFS from .c files: 23 .c + 12 headers
  incl. indigo.h/bitarray.h/defs.h stay pristine `byte`). `::byte`
  resolves to either provider (identical unsigned char) and is immune
  to `using namespace std` (layout/molecule_layout_macrocycles.h:31).
  No new type names are introduced, so the unknown-type class is
  unrepresentable. Verified locally by importing the real recipe with
  stubbed conan: pristine tree -> 369 uses/104 files, verification
  passes; dirty tree (alias+marker+:::byte+stale ::byte in .c) ->
  byte-identical convergence; 3rd build cycle -> 0 diffs (fixpoint;
  only benign CRLF->LF normalization on rewritten files). Awaiting
  HMBS真机复检.

- 2026-09-24 (round 15, link-stage __isascii; compile passed, test link
  failed): preflight got past all C++ compile (byte/macro routes held)
  and built libindigo.so, but linking indigo-c-test-shared failed with
  `ld.lld: error: undefined reference due to --no-allow-shlib-undefined:
  __isascii referenced by libindigo.so`. Local tarball audit: the only
  __isascii users in scope are third_party/inchi/INCHI_BASE/src/util.c
  lrtrim() (2 call sites) plus the ichicomp.h COMPILE_ANSI_ONLY fallback;
  util.c includes ichicomp.h only under COMPILE_ANSI_ONLY && __APPLE__,
  so on glibc/Linux the calls resolve via glibc <ctype.h> __isascii macro
  while on musl/OHOS (neither macro nor symbol) they become an undefined
  function reference. Fix: new _patch_inchi_isascii() appends an
  unconditional `#ifndef __isascii / #define __isascii(val)
  ((unsigned)(val) <= 0x7F)` block (identical to upstream's own fallback)
  after the Apple-only include block in util.c; guarded so glibc builds
  are unchanged, idempotent via HMBS_ISASCII_FALLBACK, loud on missing
  anchor/call sites. Verified locally: anchor present in pristine 1.4.3
  tarball, 2 call sites, recipe py_compiles; awaiting HMBS真机复检.
