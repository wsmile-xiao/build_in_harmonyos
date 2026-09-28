# jdupes 1.31.1 adaptation notes

## Status

- Branch: `feat/jdupes-1.31.1`
- Task: `7597`
- Package path: `archives/j/jdupes/1.31.1/`
- Current status: built and verified locally on the HarmonyOS PC target; PR submission pending

## W0 and source

- Canonical upstream source: `https://codeberg.org/jbruchon/jdupes/archive/v1.31.1.tar.gz`, tag `v1.31.1`, commit `3a50704d4b53f30df099b7700d58789f9379c6e3`.
- CI transport source: Fedora Project's official lookaside cache for Fedora's `jdupes-1.31.1-2` package: `https://src.fedoraproject.org/repo/pkgs/jdupes/v1.31.1.tar.gz/sha512/1b0163d261c523007e1000a188e4d738f1aa9d1d92ef90097b64eb870bbf60555617a34b8d5ca34117ed6c0a0965c600c06a228229392bfbe7e488cd78520e0a/v1.31.1.tar.gz`. Fedora's spec records the Codeberg Source0 and the lookaside SHA512; the extracted file set and contents were compared byte-for-byte with the Codeberg archive (archive compression bytes differ).
- The Codeberg worker request returned HTTP 429; the Fedora lookaside archive is 178534 bytes, SHA256 `c80d4c1deb03cc891a7e938f886952cfc480b8a0bc48baf21b312d350b62d8e3`, and SHA512 `1b0163d261c523007e1000a188e4d738f1aa9d1d92ef90097b64eb870bbf60555617a34b8d5ca34117ed6c0a0965c600c06a228229392bfbe7e488cd78520e0a`.
- The source archive contains a portable Makefile, `testdir/` fixtures, and a
  placeholder `test.sh` that prints `OK`.
- `libjodycode/4.1.2` was verified with `conan download --only-recipe` and its
  published OHOS arm64 shared binary was downloaded from `ohpcd` for exploratory
  compilation. The source embeds xxHash, so xxhash is not a Conan dependency.

## Build system and adaptation

jdupes is a raw Makefile project. The recipe obtains `CC`, `AR`, and `RANLIB`
from Conan's compiler executable configuration, passes `-j1`, disables the
nearby-library auto-discovery path, and injects the published libjodycode
include/library directories. The default upstream build links the dynamic
libjodycode package and runs its feature-level check.

The clang build initially failed at `act_linkfiles.c` because a hash-database
`switch` ended with a `default:` label and no statement. The source-side
portable fix adds explicit `break` statements for the `case 1` and `default`
labels. It is not guarded by an OHOS macro and applies to any compiler that
rejects an empty label.

The OHOS image does not provide GNU `install`; the package method passes
`INSTALL_PROGRAM=cp INSTALL_DATA=cp` to the existing upstream Makefile. No
upstream install source is changed.

## Upstream tests

The upstream `make test` target executes `test.sh`, which only prints `OK` and
has no functional assertions. The recipe preserves this test trace by running
the script through the resolved shell. The consumer test additionally verifies:

1. `jdupes` is on PATH and reports version 1.31.1;
2. recursive scanning finds two files with identical contents; and
3. a unique file is not reported as a duplicate.

## Exploratory evidence

- `lang-preflight`: task `cpp`, detected source language `c` from the top-level
  Makefile and 24 C source files; accepted as the C/C++ adaptation route.
- Raw `make CC=clang ... -j1`: passed after the switch fix.
- Raw `make test`: passed (`OK`).
- Raw package install with `PREFIX=/ DESTDIR=... INSTALL_PROGRAM=cp
  INSTALL_DATA=cp`: passed and produced `bin/jdupes` and
  `share/man/man1/jdupes.1`.
- Installed consumer run with recursive duplicate/unique fixture: passed.

## Verification record

- `resolve-deps --check-tools`, `preflight_check.sh`, `check-env`, and
  `lang-preflight` completed on the OHOS arm64 target. The language preflight
  accepted task language `cpp` with detected C source language.
- `refresh-patch --auto jdupes 1.31.1` generated exactly one source patch.
- `python3 -m py_compile`, YAML parsing, and `conan inspect` passed.
  `git diff --check` reports only the upstream tab-indentation context line in
  the generated patch; the patch has no OHOS macro guard.
- `conan create` with the absolute `ci/conan/profiles/ohos-aarch64` path passed,
  including source extraction, patch application, build, package install, and
  the real consumer test. The OHPCD remote supplied `libjodycode/4.1.2` for
  OHOS arm64.
- `python3 scripts/ohc-run.py conan-verify jdupes 1.31.1 --profile=ohos-aarch64`
  passed G1, G2, G3, G4, L2, L4, and L5.
- W3 local CI passed when run with the PR diff file so the incremental junk
  checker inspected only this package. The default local fork `origin/main` is
  stale relative to `upstream/main`; using the PR diff mirrors the CI checkout
  mode and does not modify unrelated files.
- The standalone `clean-verify` command returns exit 1 because this repository
  version unconditionally invokes `./configure` even for raw Makefile projects.
  This is the known non-blocking G0 limitation; Conan G2 is the clean source-archive
  build used for this Makefile package. No framework file was modified.
- The final direct W3 run after the metadata count correction passed 100%
  (L0/L1/L4/L5 passed). Its generic L2 version/help smoke emitted a
  non-blocking warning, while the consumer test version assertion and the
  manual installed-package run both passed.
- The upstream test is intentionally reported as a placeholder (`OK` only); the
  consumer test supplies the functional duplicate/unique-file assertions.

## Submission boundary

No source tarball, binary, packaging archive, lifecycle marker, Conan cache, or
framework change is part of the package diff. The PR and platform binding remain
pending; no special or unable-adaptation route is being used.
## 对话记录

### 对话 #1 — 2026-09-20

完成任务认领、W0/W1、源代码构建、可移植补丁、Conan consumer test、Conan
G1/G2/G3/G4/L2/L4/L5 和 W3 本地 CI。当前保留普通适配路径，PR 与平台提审
尚未创建。

---

**编译结束**: 2026-09-20 10:37
**最终状态**: built
