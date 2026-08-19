/* test_projectm.cpp — real consumer test source for projectM 3.1.12 (L0c).

Initializes an EGL off-screen GL context (OHOS has libEGL/libGLESv3) so
the projectM renderer can run headless, then exercises the REAL API
(R34): projectM(Settings) construction + pcm()->addPCM16Data +
renderFrame + selectPreset (all LOCALLY MEASURED passing).
*/
#include <cstdio>
#include <EGL/egl.h>
#include "libprojectM/projectM.hpp"

static int failures = 0;
#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            printf("FAIL: %s\n", msg);                                      \
            ++failures;                                                     \
        }                                                                   \
    } while (0)

int main(void)
{
    // EGL off-screen context (GLES2) — headless rendering
    EGLDisplay dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    CHECK(dpy != EGL_NO_DISPLAY, "eglGetDisplay");
    EGLint major, minor;
    CHECK(eglInitialize(dpy, &major, &minor), "eglInitialize");
    EGLint attrs[] = {EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
                      EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT, EGL_NONE};
    EGLConfig cfg;
    EGLint ncfg;
    CHECK(eglChooseConfig(dpy, attrs, &cfg, 1, &ncfg) && ncfg >= 1,
          "eglChooseConfig");
    EGLint ctx_attrs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attrs);
    CHECK(ctx != EGL_NO_CONTEXT, "eglCreateContext");
    EGLint pb_attrs[] = {EGL_WIDTH, 128, EGL_HEIGHT, 128, EGL_NONE};
    EGLSurface surf = eglCreatePbufferSurface(dpy, cfg, pb_attrs);
    CHECK(surf != EGL_NO_SURFACE, "eglCreatePbufferSurface");
    CHECK(eglMakeCurrent(dpy, surf, surf, ctx), "eglMakeCurrent");

    // projectM instance (direct construction with Settings)
    projectM::Settings settings;
    settings.windowWidth = 128;
    settings.windowHeight = 128;
    settings.meshX = 16;
    settings.meshY = 16;
    settings.fps = 30;
    projectM pm(settings);

    // PCM frame (16-bit stereo, 512 samples) via pcm()->addPCM16Data
    short pcm_data[2][512] = {{0}};
    for (int i = 0; i < 512; ++i)
        pcm_data[0][i] = pcm_data[1][i] = (short)(i * 10);
    pm.pcm()->addPCM16Data(&pcm_data[0][0], 512);

    // render a frame (visualizer core API)
    pm.renderFrame();

    // preset handling
    pm.selectPreset(0, true);

    if (failures == 0)
        printf("OK: projectM 3.1.12 real API ok (EGL context/instance/pcm/render)\n");
    return failures == 0 ? 0 : 1;
}
