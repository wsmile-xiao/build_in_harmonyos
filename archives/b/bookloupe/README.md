# bookloupe

bookloupe checks Project Gutenberg(TM) candidate e-texts for common formatting
errors: over-long/too-short lines, unbalanced quotes or brackets, punctuation
and spacing queries, probable HTML tags and likely typos.

- Homepage: http://www.juiblex.co.uk/pgdp/bookloupe/ (upstream is http-only)
- License: GPL-2.0-only
- Build system: autotools (`configure` + `make`), GLib >= 2.18
- Conan reference: bookloupe/2.0（上游唯一正式发布版，源码 bookloupe-2.0.tar.gz）

## Package contents

- `bin/bookloupe` — the e-text checker
- `bin/bookloupe.typ` — runtime typography/user-typo data (looked up in CWD,
  then next to the executable; installed there so the tool is self-contained)

## Notes

- The Conan package links the published static `glib/2.88.0.1` (armv8/clang15/
  OHOS).  `bookloupe.typ` and GLib are statically resolved, so the binary only
  needs the OHOS system libraries at runtime.
- Upstream regression suite: 37 `.tst` cases (`test/compatibility` 35 +
  `test/bookloupe` 2) run through the `loupe-test` harness with `make check`;
  executed on native OHOS workers/devices.  `test_package` additionally
  smoke-tests the packaged binary on a sample e-text.
- `bookloupe --help` prints help but exits 1 by design (GOption parse-failure
  path); functional verification runs the tool on an input file.
