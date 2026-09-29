# zshdb 1.1.4 HarmonyOS PC verification

- Board: `@tank_you` claimed exact task `zshdb/1.1.4`, branch
  `feat/zshdb-1.1.4`, in the 10-fire-seed competition activity. The board
  labels this C++, but upstream zshdb is a zsh shell-script application.
- Official upstream release archive:
  `https://github.com/Trepan-Debuggers/zshdb/releases/download/1.1.4/zshdb-1.1.4.tar.gz`,
  329607 bytes, SHA-256
  `83749450ffe030c28e7b7d1d8b06aea63232504ff61f31f9becc5a5717e69638`.
  The same hash appears in Homebrew's 1.1.4 formula and matched local and
  HarmonyOS PC bytes. Target work area:
  `/data/storage/el2/base/haps/entry/files/zshdb-1.1.4-work`.
- The target has zsh 5.9 but lacks the standard `is-at-least` autoload file
  and optional `zsh/mapfile` and PCRE modules. The recipe carries the
  `is-at-least` function from zsh's official 5.9 source, substitutes a
  newline-preserving source read when mapfile is absent, and uses POSIX sed
  for condition capture. The installed script locates its package data
  relative to its own path, so it does not embed Conan's cache directory.
  Runtime and test scratch files use writable `TMPDIR`; the target's
  `/tmp` is read-only.
- The release tarball itself omits `test/example/bug-step-subshell.sh`,
  `test/data/bug-step-subshell.cmd`, and
  `test/data/bug-step-subshell.right`, although its test runner lists the
  case. The three files under `test_fixtures/` are byte-identical to the
  same upstream Git tag 1.1.4 archive, with SHA-256 respectively
  `b5ac54184d99bec3b89b4c704a6cc54b3813252725cead92566229a5ce75a3eb`,
  `69cad2ce73b65bb6f8eb77e954e9e9b60fdfc83591ac8afed1829249ff8b0373`,
  and `9c18016d9eae3073e46a3aa7fd86b35baacf5ae032ad2953772c6f5c4a975b27`.
  No expected-output fixture is invented or edited.
- Native isolated `conan create` builds and runs the full upstream
  `make -j1 check` under the patched recipe. Final integrated run passed
  5/5 Automake unit cases, 34 shunit functions with 216/216 assertions,
  and 27/27 integration tests, with no skipped integration tests. Log
  `create-v9-local-source.log` SHA-256:
  `40176f82d8c845036e1eab47aa570d133bc87d13635780bc8e67102e8f7da829`;
  package revision `003ac6c4c32096db0c4ca9ad2170c294`. The installed-package consumer test
  checks the version and noninteractive debugging of an actual script.
  zshdb reports exit code 128 after the test script terminates normally;
  the consumer verifies both the output marker and the explicit normal
  termination message rather than treating any exit 128 as success.
- The target can download the official GitHub archive, but a later retry
  timed out intermittently. The final local verification used `file://`
  for an already SHA-256-verified byte-identical copy on the target; the
  committed `conandata.yml` retains the official HTTPS URL. This tests
  packaging and runtime, not network reliability. `term-highlight.py`
  requires optional syntax-highlighting dependencies and was not exercised.
  Interactive terminal behavior and editor integration were not tested.
