# EGL 1.0.5 OHOS Adaptation Notes

## Upstream and platform status

- Upstream v1.0.5 supports WGL on Windows and GLX/X11 or Wayland on Unix-like systems.
- OHOS provides `/system/lib64/libEGL.so` and `libGLESv3.so`, but no `libGLESv2.so`.
- The OHOS backend dynamically loads the system EGL implementation and forwards EGL calls.

## Patch design

The portability patch updates four upstream areas:

1. `CMakeLists.txt` selects `src/egl_ohos.cpp` for OHOS or HarmonyOS, links `${CMAKE_DL_LIBS}`, and skips examples.
2. `src/egl_internal.h` adds the OHOS platform definitions and minimal GL types without X11/GLX headers.
3. `include/EGL/eglctxinternals.h` adds the OHOS context internals definition.
4. `src/egl_ohos.cpp` loads `libEGL.so`, implements the double-underscore backend hooks, supports pbuffer and OpenGL ES contexts, and explicitly rejects window and pixmap surfaces.

## Device validation

The test package exercises this lifecycle on OHOS/aarch64:

`eglGetDisplay` -> `eglInitialize` -> `eglBindAPI` -> `eglChooseConfig` ->
`eglCreatePbufferSurface` -> `eglCreateContext` -> `eglMakeCurrent` ->
`eglGetProcAddress("glGetString")` -> cleanup.

The device successfully created a 1x1 pbuffer and an ES3 context. The resolved
`glGetString(GL_VENDOR)` returned `HUAWEI`.

## Validation commands

```sh
python3 scripts/ohc-run.py conan-verify egl 1.0.5
CI_PACKAGES=archives/e/egl/1.0.5 /usr/bin/zsh ci/conan/build_and_test.sh
```
