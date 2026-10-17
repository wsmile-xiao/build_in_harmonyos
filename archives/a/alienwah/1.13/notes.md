# AlienWah 1.13 adaptation notes

AlienWah is a LADSPA plugin, not a command-line tool, so no `commands.json` is
declared. The recipe builds `aw.so` with the Conan C++ compiler and installs it
under `lib/ladspa`.

The upstream source requires `ladspa.h`; this recipe downloads the LADSPA SDK
1.17 source tarball and packages the header with the plugin. The primary
`ladspa.org` URL currently returns a tarball with a different hash on the OHOS
worker, so the recipe keeps the Gentoo distfiles mirror as the verified source.

Upstream's `mtest` and `stest` targets require external `applyplugin` plus
`mono.wav` and `stereo.wav`, and the tarball does not ship those samples. The
consumer test instead loads the packaged plugin with `dlopen`, resolves
`ladspa_descriptor`, and validates the mono/stereo descriptor labels and port
counts.

The patch also fixes descriptor cleanup to free `strdup()`-allocated strings
with `free()` instead of `delete[]`, avoiding unload-time crashes during the
descriptor smoke test.

OHOS new-port validation on 2026-08-09:

- Port: `33332`
- Runner task: `alienwah-1.13-upstream-20260809-r10`
- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-alienwah-alienwah-1.13-upstream-20260809-r10-20260809-010039-23029`
- Result: `ci/conan/build_and_test.sh archives/a/alienwah/1.13` passed with L0/L1/L4/L5 pass and L2 skipped because the package has no `bin/`.
- Full package reference: `alienwah/1.13#1d419b41c1873e872f4346a03b93645b:6b129b068851896169fae42d399fa922d239ce8a#d0bfe774b52d695773aa770102c2d01e`
- Upstream tests: `0/2` executed. Upstream `mtest`/`stest` remain manual targets because they require external `applyplugin` plus audio samples not shipped in the tarball.
- Added consumer validation: `test_package` compiled and ran `test_descriptor`, validating `ladspa_descriptor`, mono/stereo labels, port counts, and required callbacks.
