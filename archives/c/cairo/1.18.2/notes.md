# cairo 1.18.2 HarmonyOS PC adaptation notes

## Source and build

- Official release: `https://cairographics.org/releases/cairo-1.18.2.tar.xz`
- SHA-256: `a62b9bb42425e844cc3d6ddde043ff39dbabedd1542eba57a2eb79f85889d45a`
- Upstream tag `1.18.2` resolves to commit `200441e6855854eb4dbf338e44d67b00ababe07f`.
- Meson, OHOS AArch64, shared Cairo library. X11/XCB/Quartz/DWrite and cairo-gobject are disabled; PNG, FreeType, and zlib are enabled; Fontconfig is disabled.
- Source patches preserve Cairo temporary-file behavior on the read-only OHOS `/tmp`: prefer `TMPDIR`, then fall back from `O_TMPFILE` to `mkstemp`.

## Knowledge captured

Cairo 1.18.2 registers one Meson test executable, but that executable runs hundreds of named Cairo image/rendering cases. `meson test --list` therefore understates the test corpus; count the runner's `results.txt` records and summary after running it. Optional Ghostscript, Poppler GLib, and librsvg integrations are detected independently when tests use Meson's `auto` mode.

## Dependency revisions

- `pixman/0.46.4`
- `libpng/1.6.58`
- `freetype/2.14.3`
- `zlib/1.3.1.1`

## Verification

- OHOS AArch64 `conan create` completed successfully. Cairo built and packaged; the three non-slow Meson checks passed (3/3).
- The real Conan test package compiled and ran through `self.run`; Cairo 1.18.2 painted and read back ARGB32 `0xffff0000` (1/1).
- A separate upstream `CAIRO_TEST_TARGET=image` case run recorded 1,094 outcomes before `pthread-show-text` stalled in a child blocked on a futex: 909 PASS, 167 FAIL, 18 XFAIL, 0 ERROR, 0 UNTESTED. Excluding expected failures, pass rate was 909/1,076 (84.48%). This is a partial run, not a full-suite pass.
- An earlier unfiltered attempt also stalled before Meson produced a summary. At interruption it had emitted 571 case outcomes (249 PASS, 305 FAIL, 15 UNTESTED, 1 ERROR, 1 XFAIL); disabled X backends and OHOS image differences are included in that diagnostic run.
- The OHOS loader rejected Fontconfig from the Conan cache (`Permission denied`), so the package disables Fontconfig while retaining FreeType. Meson install also changes the linked Cairo library's RPATH and invalidates its linker signature; packaging restores the signed build-tree ELF when `binary-sign-tool` is unavailable.
