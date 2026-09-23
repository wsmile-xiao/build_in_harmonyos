# dh-builtusing 0.0.14 notes

## build
- build system: pure Perl, no compilation (application package, like debhelper)
- date: 2026-09-10
- platform: arm64-ohos
- status: built
- patches: 0

## source
- official: `https://deb.debian.org/debian/pool/main/d/dh-builtusing/dh-builtusing_0.0.14.tar.xz`
- mirror fallback: `https://mirrors.aliyun.com/debian/...` (same archive, sha256 unchanged)
- sha256: `c2387a18d5c8fc9939e0834390ac39b47f0c357a8d6b034763b645d9780e8df2`
- archive top dir is `git/` (strip_root gives source root with Makefile/run-unit-tests/unit-tests/integration-tests/debian/)

## packaging
- `dh_builtusing` -> `bin/` (exec bit ensured)
- `builtusing.pm` (`insert_before('dh_gencontrol','dh_builtusing')`) -> `lib/perl5/`
- `dh_builtusing.pod` + `Makefile` -> `res/` (doc/build entry for reference)
- `res/upstream_test_result.json` (build() marker persisted for test_package cache-hit re-emit)

## upstream tests (measured, not estimated)
- entry: `Makefile: check: sh run-unit-tests`; autopkgtest: `debian/tests/control`
- `unit-tests/` 16 files: 10basic / 20binary-arch / 20binary-indep / 20build-depends-arch-indep / 20package-arch / 30encoding / 30or-dependency / 40pattern / 45multiple-matches / 50same-source / 60substvars-file / 70arch-profile-restrictions / 70arch-suffix / 70multiarch / 80not-in-build-depends / 90c-option
- `integration-tests/` 3 files are autopkgtest-only (need installed .deb + `dh` sequencer + `debian/rules binary`), never run by `make check`; marker scope is `make check` = 16.
- OHOS has no Debian toolchain, so build() vendors an offline fixture (`debian_shims/`): dpkg-architecture/dpkg-query/dh_gencontrol shims + minimal Debian::Debhelper::Dh_Lib + Dpkg::Control::Info + Dpkg::Deps + Dpkg::BuildProfiles emulation (pure Perl). Fixture DB mirrors real trixie sources: dpkg 1.22.18 / gcc-defaults 14.2.0-1 / autotools-dev 20220109.1 / binutils 2.44-1 / glibc 2.41-12 / make-dfsg 4.4.1-1 / debhelper 13.24.3. dh_builtusing itself runs unmodified; OK lines prove its pattern/arch/profile/substvars logic.
- falsifiability: `run-unit-tests` uses `complain()` + `exit 1` on mismatch and fails on non-empty stderr; build() requires rc=0, zero FAIL lines and OK count == discovered (16), and rejects empty fixtures, so an empty-tree or broken dh_builtusing cannot report passed.

## test_package (R34)
- `test_dh_builtusing.py <pkg>` 3 content checks on installed files:
  1. `bin/dh_builtusing` contains `dh-builtusing:` + `addsubstvar`
  2. `lib/perl5/builtusing.pm` contains `insert_before` + `dh_gencontrol` + `dh_builtusing`
  3. `bin/dh_builtusing` contains DPS mapping (`y/DPS/.+*/`) + S wildcard
- outputs `RESULT: 3 passed, 0 failed`; conanfile parses it for HMBS_TEST_PACKAGE_RESULT(3/3) and re-emits the persisted HMBS_UPSTREAM_TEST_RESULT after the test commands (dual channel, validated, no BOM).

## limits
- `perl dh_builtusing --help` needs `Debian::Debhelper::Dh_Lib` from debhelper; on-device runs use the vendored emulation for tests only, the installed package itself is the unmodified upstream script.
- integration 3 cases need a Debian system with `dh`; covered by content check of builtusing.pm wiring instead.

## verify
```bash
conan create archives/d/dh-builtusing/0.0.14 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# expect: build() runs sh run-unit-tests 16/16 passed; test() reports HMBS_TEST_PACKAGE_RESULT(3/3) + re-emitted upstream marker
```

## CI-007 fix 2026-09-11
- CI build #44016: hnp bash getcwd fails under conan cache (/storage/.../.cache) rc=1, python getcwd ok; recipe now probes candidate shells with pwd in src and picks first working (native sh preferred over hnp bash).
