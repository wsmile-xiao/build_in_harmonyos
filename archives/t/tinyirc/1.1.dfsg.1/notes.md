# tinyirc 1.1.dfsg.1 adaptation notes

- Task: claimed by `@tank_you` on the contribution board on 2026-09-25;
  required branch `feat/tinyirc-1.1.dfsg.1`. The board labels the task C++;
  the actual implementation and Makefile target are C.
- Source provenance: the pinned commit
  `f903d435a50dea04c6ab427856404f9d9426ba08` in author Nathan Laredo's
  [repository](https://github.com/nlaredo/tinyirc) has a
  `debian/changelog` entry headed `tinyirc (1:1.1.dfsg.1-1)`. Its GitHub
  archive hashes to
  `1404616375f391f87b32658687d3e9ef66e6d178af2c133597d5e0326f215b6b`.
  It is **not byte-identical** to Debian's separate
  `tinyirc_1.1.dfsg.1.orig.tar.gz` (SHA-256
  `a9e36f418285201bb580348fabefcfae6d903d74f1fe38e50fc2e6562ac0b2a2`).
  The author commit already contains several Debian-era source fixes; this
  recipe fixes and tests that exact pinned author commit. No claim is made
  that the two archives are interchangeable.
- W0: `ncurses/6.6` recipe and the matching OHOS AArch64/Clang 15 static
  binary (package ID `21b17f8b2bc0e9511e276e3d57a23893067cefe5`) were
  downloaded from the `ohpcd` Conan remote with `--build=never`.
- Source census: the pinned archive has no `tests/` directory, no registered
  CTest/pytest suite and no Makefile `test` or `check` target. Upstream test
  count is therefore 0; `tinyircd.c` is an alternative program, not a
  registered test. No upstream test was changed or claimed as executed.
- Build: serial GNU Make using target Clang 15, `-std=gnu89 -DPOSIX`, and the
  published ncurses headers/archive. Source patch makes passwd lookup
  nullable and guards the optional `getutline` path by the generic
  `HAVE_GETUTLINE` feature macro. OHOS application UID `20020084` had
  no passwd entry on the test device; upstream dereferenced NULL and exited
  with signal 11. The target's `utmp.h` does not declare `getutline`.
  The patch's fallback uses the selected nickname and `USER` where needed.
- `hline` and `timeout` global names collide with public ncurses symbols
  when linking the static `libncursesw.a`. Compile-time identifier remapping
  to `tinyirc_hline` and `tinyirc_timeout` avoids a source-wide rename.
  The build still emits legacy C warnings; no `-Werror` claim is made.
- The static ncurses archive still needs its terminfo *data* at runtime.
  Without Conan `run=True`, a downstream `test_package` graph skipped the
  ncurses binary and `TERMINFO` was absent. Declaring
  `self.requires("ncurses/6.6", run=True)` retained its run environment.
- The added native `test_package` starts a loopback fake IRC server and
  checks USER/NICK registration, PING/PONG token, incoming and outgoing
  PRIVMSG, QUIT, process exit 0 and the incoming message in stdout.
  It has one integration scenario and seven behavioral assertions. It does
  not exercise a public IRC network, TLS or the interactive curses mode.
- HarmonyOS PC AArch64 / Clang 15 / Conan 2.29.1: final forced
  `conan create` returned 0 and the native consumer scenario passed 1/1.
  The first attempt to repeat the build after adding the patch metadata
  encountered a GitHub connection timeout on the target. The exact upstream
  archive (SHA-256 above) was seeded into this task's Conan source download
  cache, and the complete forced build was then rerun with
  `-cc core.sources:download_cache=...`. The log explicitly records source
  retrieval from that hash-keyed cache; no source URL or recipe was changed.
  Target-only log:
  `/data/storage/el2/base/haps/entry/files/tinyirc-20260925-2145-01/conan-final3.log`,
  SHA-256 `50299ffd2d667258a900e0599cf4b10aaac1d03ff0e7ac81acfddf832a032a78`.
  Baseline failing log: `conan-create4.log`, SHA-256
  `e1bd788cdeed9d9b07dc7252b1530187e5ca64ba51adcfa88a7b981e8120e4fa`.
  No CI or publication result is claimed.

To reproduce from a repository checkout on the target with configured
`ohos-aarch64` profile and `ohpcd` remote:

```sh
conan create archives/t/tinyirc/1.1.dfsg.1 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  -r=ohpcd --build=tinyirc/1.1.dfsg.1 -c tools.build:jobs=1
```
