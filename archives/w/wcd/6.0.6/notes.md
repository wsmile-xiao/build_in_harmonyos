# HarmonyOS PC verification

- Official WCD 6.0.6 SourceForge archive SHA-256:
  `c5d1b22aefbb0f142e27b1cddad17021c43034c76103830fb2757387ac593eb1`.
  Exact bytes transferred to `10.62.210.132:2222`; target checksum matched.
  Target verification root:
  `/data/storage/el2/base/haps/entry/files/wcd-6.0.6-20260926T190000`.
- Native Clang serial build with `EXT= ENABLE_NLS= CURSES=` succeeded. The
  target binary is AArch64 musl ELF. Optional translations and curses UI were
  not built or tested. Source `test/` contains fixtures, not an automated test
  runner; no upstream test count is claimed.
- Manual native smoke: `WCDHOME=<private>/smoke/home wcd -S <tree>` and
  `wcd alpha` both returned 0. The program wrote `.treedata.wcd` and
  `bin/wcd.go` under that state root, with the selected path in the script.
- Isolated `CONAN_HOME` with OHOS AArch64 host/build profiles: dependency
  graph contained no external packages. `conan create` built the official
  archive and passed the installed-package consumer test: bounded scan,
  selection, generated go script, and sourced shell function changing `pwd`.
  `create-v1.log` SHA-256:
  `b6f0cbd6995b911ed1a264f3c442415314264013b8eb9fddc84d7b0a29e76013`.
  Package revision: `4d55c2cb7ec4cf600acb3cb901adca2f`.
- Reproducible negative case: unset `WCDHOME`, then `wcd --version` prints
  `Unable to write file /storage/Users/currentUser/bin/wcd.go: Permission denied`
  but exits 0. With private `WCDHOME`, same command has no permission error.
  The consumer test checks generated state and caller directory, not only RC.
- Conan verification used `file://` for the exact same SHA-256 official
  archive because target SourceForge access was not verified; committed
  `conandata.yml` retains the official HTTPS URL. Direct target download and
  optional feature paths are not claimed.
