# Boost 1.91.0.1.1 Multiprecision dependency repair

## Scope

This adaptation-fix version keeps the verified official
`boost-1.91.0-1-cmake.tar.xz` source from `boost/1.91.0.1`. It extends the
selective package with Boost.Multiprecision because Redex v2026.04.30 uses
`boost::multiprecision::cpp_int_backend` unconditionally in
`sparta/FiniteAbstractDomain.h`.

Redex W3 r93 resolved the published `boost/1.91.0.1` include root and built
through `libredex/Debug.cpp`, then failed in `DexTypeEnvironment.cpp` with:

```text
fatal error: 'boost/multiprecision/cpp_int.hpp' file not found
```

The failing package selected filesystem, graph, iostreams, program_options,
regex, and thread, but not multiprecision. This is a package-content defect,
not an include propagation problem. Redex must not copy the missing header or
guard out a core lattice implementation.

## Component contract

The official Boost 1.91.0-1 CMake project defines `Boost::multiprecision` as an
INTERFACE target. In superproject mode it links the header-only Assert, Config,
Core, Integer, LexicalCast, and Math targets plus `Boost::random`. The Conan
component therefore exports the official CMake target name and depends on the
package `headers` component and the existing `random` component.

The production selection and the test selection both include
`multiprecision`, so the installed package must contain:

- `include/boost/multiprecision/cpp_int.hpp`;
- the `Boost::multiprecision` CMake target;
- the existing compiled Random dependency used by the official target.

## Test inventory

The selected official upstream inventory increases from 17 to 18 flows. The
new official entry is the only Multiprecision leaf registered by the release's
CMake `Simple_Jamfile` bridge:

- `libs/multiprecision/test/reduced_cpp_double_fp.cpp`.

The package consumer inventory increases from 6 to 7. The new
`multiprecision.cpp` consumer includes `cpp_int.hpp`, instantiates the exact
fixed-width allocator-free backend shape used by Redex, and verifies bit,
`msb`, backend-size, limb-access, union, and intersection operations through
`Boost::multiprecision`.

## Validation state

The HarmonyOS PC r4 transaction is complete for frozen HEAD
`5116ab2fa920e2224098e41804c00feb82c241ca` and candidate tree
`42457694d8ac540ffd46d54158c7a0310ccb7088`. Shared and static variants each
executed the complete selected inventory. The unique result is 18/18 upstream
PASS and 7/7 consumer PASS; the two package variants are not double-counted.

Both packages contain `boost/multiprecision/cpp_int.hpp`, export the
Multiprecision CMake target, contain exactly 12 compiled libraries, and contain
zero symlinks. All shared libraries are AArch64 ELF files with a `.codesign`
section. The exact local package references are:

- shared: `boost/1.91.0.1.1#a87a5f6c933b59858076703e53cff426:01d92cf349a0dd98ff915f4bd99a04430171517f#978f06a635235df28409196d5aefb699`
- static: `boost/1.91.0.1.1#a87a5f6c933b59858076703e53cff426:21b17f8b2bc0e9511e276e3d57a23893067cefe5#d0c81c39274e78a17a81cfeb757d0ff8`

The raw shared and static logs have SHA-256
`0e848ee0395d193e31947e13b24ddc6d4a5f962658c44dca476d789a0028e5e1`
and `e7a4be0db6f7dc791c6a7558a8d1ab2bb3263b080601882a34f818915b1a5298`.
`reports/upstream-pass-summary.txt` is a separately generated, provenance-bound
summary; it does not alter either raw log.

The legacy outer `finish` returned 1 after producing a valid `.ci-result.json`
because it still asks Conan recipes for standalone `packaging/` and staging
markers. As with `boost/1.91.0.1`, no empty marker or fabricated binary tarball
is added. W3 passed only after the runner validated the CI result, both test
variants, both artifact inventories, and the closed evidence manifest.

The consumed r2 attempt failed before Conan because the target shell tried to
materialize an inline Python heredoc under read-only `/tmp`. The r4 runner uses
hash-bound helper files, contains no heredoc syntax, and binds `TMPDIR` plus
`TMPPREFIX` to its task-local work root before Python or zsh execution. The r3
successor was retired with zero launches when `origin/main` changed before its
launch boundary.

Independent W4, the current-tree Pre-PR contract, PR review, CI, merge, and
post-merge publication remain separate gates. Redex must continue using the
old dependency until a fresh OHOS/arm64 `--build=never` readback proves the new
published RREV/PID/PREV.

## Tracking

- Existing Boost Issue: #1247 (must be reopened and updated before submission)
- Downstream Redex Issue: #1092
- Prior dependency task: `boost/1.91.0.1` (completed; immutable)
- Candidate branch: `fix/boost-1.91.0.1.1`
