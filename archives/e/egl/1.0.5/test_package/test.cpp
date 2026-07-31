/*
 * egl 1.0.5 test_package — real EGL lifecycle on OHOS/aarch64.
 *
 * R34: this is the L1 Conan test; it exercises the EGL API end-to-end against
 * the system libEGL forwarded by our OHOS backend:
 *
 *   eglGetDisplay(EGL_DEFAULT_DISPLAY)
 *   → eglInitialize
 *   → eglBindAPI(EGL_OPENGL_ES_API)
 *   → eglChooseConfig(EGL_SURFACE_TYPE+EGL_PBUFFER_BIT,
 *                     EGL_RENDERABLE_TYPE+EGL_OPENGL_ES3_BIT, RGBA888)
 *   → eglCreatePbufferSurface(1×1)  — OHOS 真机系统 EGL 1.4 拒绝 ≥2px 的 pbuffer
 *                                     (eglCreatePbufferSurface 返回 EGL_BAD_ATTRIBUTE for w|h ≥ 2),
 *                                     仅 1×1 可创建;本测试用真机最小可用尺寸。
 *   → eglCreateContext(ES3, EGL_CONTEXT_MAJOR_VERSION=3)
 *   → eglMakeCurrent
 *   → eglGetProcAddress("glGetString")  (must be non-NULL)
 *   → eglMakeCurrent(EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT)  release
 *   → eglDestroyContext / eglDestroySurface / eglTerminate
 *
 * Every step abort()s with the EGL error code on failure so the test reports
 * the first real failure root cause, not a stubbed pass.
 */
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <cstdio>
#include <cstdlib>

#define CHECK(cond, stage)                                                     \
    do {                                                                       \
        if (!(cond)) {                                                         \
            EGLint e = eglGetError();                                          \
            std::fprintf(stderr,                                              \
                "[FAIL] %s: cond='%s' EGLerror=0x%x\n",                       \
                (stage), #cond, (unsigned)e);                                 \
            std::abort();                                                      \
        }                                                                      \
    } while (0)

static void report(const char* stage, bool ok, EGLint e = EGL_SUCCESS)
{
    // Print to BOTH stdout and stderr + fflush so the failing line is never
    // swallowed by conan's pipe capture or an aborted subprocess buffering.
    const char* tag = ok ? " OK " : "FAIL";
    std::printf("[ %s ] %s (EGLerror=0x%x)\n", tag, stage, (unsigned)e);
    std::fflush(stdout);
    if (!ok) {
        std::fprintf(stderr, "[FAIL] %s EGLerror=0x%x — aborting\n", stage, (unsigned)e);
        std::fflush(stderr);
        std::abort();
    }
}

int main()
{
    // 1. eglGetDisplay(EGL_DEFAULT_DISPLAY)
    EGLDisplay dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (dpy == EGL_NO_DISPLAY) {
        report("eglGetDisplay", false, eglGetError());
    }
    report("eglGetDisplay", true);

    // 2. eglInitialize
    EGLint major = 0, minor = 0;
    EGLBoolean ok = eglInitialize(dpy, &major, &minor);
    if (!ok) report("eglInitialize", false, eglGetError());
    std::printf("  EGL version: %d.%d\n", major, minor);
    report("eglInitialize", true);

    // 3. eglBindAPI(EGL_OPENGL_ES_API)
    ok = eglBindAPI(EGL_OPENGL_ES_API);
    if (!ok) report("eglBindAPI(ES)", false, eglGetError());
    report("eglBindAPI(ES)", true);

    // 4. eglChooseConfig — pbuffer + ES3 + RGBA888 (OHOS 真机 EGL 1.4: ES3 renderable config 可创建 ES3 ctx;ES2 config 创建 ES2 ctx 报 EGL_BAD_MATCH)
    const EGLint cfgAttribs[] = {
        EGL_SURFACE_TYPE,    EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
        EGL_RED_SIZE,        8,
        EGL_GREEN_SIZE,      8,
        EGL_BLUE_SIZE,       8,
        EGL_ALPHA_SIZE,      8,
        EGL_NONE
    };
    EGLConfig cfg = nullptr;
    EGLint numCfg = 0;
    ok = eglChooseConfig(dpy, cfgAttribs, &cfg, 1, &numCfg);
    if (!ok) report("eglChooseConfig", false, eglGetError());
    CHECK(numCfg > 0 && cfg != nullptr, "eglChooseConfig result");
    report("eglChooseConfig", true);

    // 5. eglCreatePbufferSurface — 1×1 (OHOS 真机 EGL 1.4 拒 ≥2px pbuffer,见文件头注释)
    const EGLint pbufAttribs[] = {
        EGL_WIDTH,  1,
        EGL_HEIGHT, 1,
        EGL_NONE
    };
    EGLSurface surf = eglCreatePbufferSurface(dpy, cfg, pbufAttribs);
    if (surf == EGL_NO_SURFACE) report("eglCreatePbufferSurface", false, eglGetError());
    report("eglCreatePbufferSurface", true);

    // 6. eglCreateContext — ES3 (OHOS 真机 EGL 1.4: ES3 ctx 在 ES3 renderable config 上可创建)
    const EGLint ctxAttribs[] = {
        EGL_CONTEXT_MAJOR_VERSION, 3,
        EGL_CONTEXT_MINOR_VERSION, 0,
        EGL_NONE
    };
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctxAttribs);
    if (ctx == EGL_NO_CONTEXT) report("eglCreateContext(ES3)", false, eglGetError());
    report("eglCreateContext(ES3)", true);

    // 7. eglMakeCurrent
    ok = eglMakeCurrent(dpy, surf, surf, ctx);
    if (!ok) report("eglMakeCurrent", false, eglGetError());
    report("eglMakeCurrent", true);

    // 8. eglGetProcAddress("glGetString") — must be non-NULL
    //
    // NOTE: eglGetProcAddress returns __eglMustCastToProperFunctionPointerType
    // (aka void(*)()) — a *function* pointer. clang rejects implicit init of
    // a void* (data pointer) from a function pointer; capture it in a matching
    // function-pointer typedef first, then reinterpret to the concrete ES2 fn.
    using PFN_glGetString = const char* (*)(unsigned int);
    using GenericFnPtr = void (*)();
    GenericFnPtr rawFn = reinterpret_cast<GenericFnPtr>(eglGetProcAddress("glGetString"));
    if (rawFn == nullptr) report("eglGetProcAddress(glGetString)", false, eglGetError());
    // GL_VENDOR = 0x1F00 (ES2) — call the resolved entry to confirm it is live.
    if (rawFn) {
        PFN_glGetString glGetString = reinterpret_cast<PFN_glGetString>(rawFn);
        const char* vendor = glGetString(0x1F00 /* GL_VENDOR */);
        std::printf("  GL_VENDOR: %s\n", vendor ? vendor : "(null)");
    }
    report("eglGetProcAddress(glGetString)", true);

    // 9. Release (unbind)
    ok = eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    if (!ok) report("eglMakeCurrent(release)", false, eglGetError());
    report("eglMakeCurrent(release)", true);

    // 10. Destroy context / surface / terminate
    ok = eglDestroyContext(dpy, ctx);
    if (!ok) report("eglDestroyContext", false, eglGetError());
    report("eglDestroyContext", true);

    ok = eglDestroySurface(dpy, surf);
    if (!ok) report("eglDestroySurface", false, eglGetError());
    report("eglDestroySurface", true);

    ok = eglTerminate(dpy);
    if (!ok) report("eglTerminate", false, eglGetError());
    report("eglTerminate", true);

    std::printf("\n[ ALL PASS ] egl 1.0.5 EGL lifecycle (pbuffer + ES3) complete.\n");
    return 0;
}
