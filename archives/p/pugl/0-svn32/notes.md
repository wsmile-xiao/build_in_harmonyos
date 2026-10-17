# Pugl 0-svn32 HarmonyOS PC adaptation

## Source provenance

The version is the 32nd historical upstream revision, Git commit
`1702307bfeb21ad5e59ee3ef4a342c8867d37140`. The official LV2 GitHub mirror
archive is used because GitLab archive downloads return HTTP 403 on the CI
worker. The GitHub and GitLab archives are byte-identical and share SHA-256
`50aa8a751a4fbe7c2c522362e33a2ee63bbd3e2405a68b66b771fba065b08b67`.
Its source tree matches Debian's `0~svn32+dfsg0` snapshot; Debian only bundles
a different Waf launcher and Waf modules.

## Adaptation

Upstream only implements X11/GLX, Win32/WGL, and Cocoa/OpenGL. HarmonyOS has
none of those window systems, so this port adds a complete backend that:

- creates OpenGL ES 3 contexts and window or pbuffer surfaces through EGL;
- accepts an `OHNativeWindow` supplied by an ArkUI/XComponent host;
- queues keyboard, pointer, button, scroll, special-key, and close events;
- supports offscreen rendering and RGBA frame readback;
- removes fixed-function desktop OpenGL state from the GLES reshape path;
- installs a CMake package and propagates EGL, GLESv3, and native_window.

No `__OHOS__` branch is injected into upstream code. Backend selection is an
explicit build feature (`PUGL_GLES_BACKEND`), so unrelated upstream platforms
are unaffected.

## Upstream test inventory

Revision 32 has no automated unit or integration tests. `pugl_test.c` is an
interactive desktop OpenGL/GLU demonstration with an unbounded event loop; it
is built only when Waf's optional `--test` switch is used and is not registered
or run as a test. The archive therefore has 0 upstream automated test cases.

The port adds two executable tests. `test_api.c` exercises the original public
API and EGL rendering lifecycle. `test_ohos.c` is HarmonyOS-specific and tests
the ArkUI input bridge, modifier state, pbuffer rendering, frame readback, and
resource release. Both run through `test_package/conanfile.py::test()`.

## Validation commands

```sh
conan create archives/p/pugl/0-svn32 \
  -pr:h=ohos-aarch64-linux-cross -pr:b=linux-x86_64 --build=missing
ctest --test-dir build --output-on-failure
```

Result: build passed; 2/2 added test programs passed (100%).
