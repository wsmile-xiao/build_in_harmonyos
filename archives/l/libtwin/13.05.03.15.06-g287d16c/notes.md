# libtwin 13.05.03.15.06-g287d16c HarmonyOS PC adaptation

Source: Debian authoritative orig tarball; SHA-256 `3ba25ce801313153119b7e507e38aabd5a478e62e058f06a1f7975b87a112e8f`.

Native OHOS exploration uses `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` because the bundled 2012 `config.guess` cannot identify HarmonyOS. The X11/framebuffer/input/TTF backends are unavailable on this device; PNG, JPEG, and zlib remain enabled using published Conan dependencies.

Source changes: probe current `libpng` instead of `libpng12` in Autotools source and bundled generated configure; use libpng 1.6 API in `twin_png.c`; link `libtwin` against its optional image/compression dependencies rather than leaving unresolved symbols. The release tarball carries generated configure/Makefile.in and the target has no `autoreconf`, so both source-of-truth and shipped generated files are patched.

Upstream Makefile declares no tests (`make check` is empty). A real consumer test creates an ARGB pixmap, fills it, checks a pixel, and destroys it; this passed on the native OHOS device. Native OHOS `conan create` and its consumer test passed.

The repository `ci/conan/setup.sh` and targeted `ci/conan/build_and_test.sh` also passed on the OHOS device on 2026-09-27: G0, L0, L1, L4 and L5 passed; L2 was correctly skipped because this is a library without `bin/`. The consumer test's destructive-negative check confirmed that it depends on the packaged library and headers. The runner used `AR=/storage/Users/currentUser/usr/local/bin/llvm-ar`. CI log: `/data/storage/el2/base/files/libtwin-20260927/ci-build.log` on the target device. This test preceded PR submission and hosted CI.

Hosted PR CI #63876 on 2026-09-28 failed at `config.status` while creating `subs1.awk` inside `./confidfcik`: `Permission denied`. All dependency downloads and configure feature probes completed before this error. The bundled `configure` creates that directory under `umask 077`, which is incompatible with the CI worker's HMDFS directory permission behavior (knowledge E129). The existing `0003-configure.patch` now changes only the two temporary-directory creation branches to `umask 022` and uses the recipe-provided `TMPDIR`; the cleanup trap remains unchanged. The previous native OHOS success does not establish hosted CI success, so the new head must be checked independently.
