/*
 * epoxy 1.5.10 test_package — real GL/EGL dispatch through libepoxy (R34).
 *
 * OHOS/aarch64 真机验证 epoxy 的函数指针派发层：
 *
 *   epoxy_has_egl()            → dlopen libEGL.so（补丁把 libEGL.so.1 换成 libEGL.so）
 *   eglGetDisplay/Initialize   → 经 epoxy EGL 派发表调系统 libEGL.so
 *   eglBindAPI(ES) / eglChooseConfig(ES3 renderable, RGBA888)
 *   eglCreatePbufferSurface(1x1)  — OHOS 真机 EGL 1.4 拒绝 >=2px 的 pbuffer
 *   eglCreateContext(ES3) / eglMakeCurrent
 *   epoxy_gl_version()         → dlopen libGLESv2.so（补丁把 libGL.so.1 换成 libGLESv2.so），
 *                                在当前 ES3 上下文取 GL_VERSION（期望 >= 30）
 *   epoxy_is_desktop_gl()      → ES 上下文下必须为 false
 *   epoxy_egl_version(dpy)     → 期望 >= 14
 *   release / destroy / terminate
 *
 * 每步失败都带阶段名 abort()，让 L1 测试报出第一个真实失败点。
 */
#include <epoxy/egl.h>
#include <epoxy/gl.h>

#include <stdio.h>
#include <stdlib.h>

static int checks = 0;

static void report(const char *stage, int ok)
{
    if (!ok) {
        fprintf(stderr, "[FAIL] %s\n", stage);
        fflush(stderr);
        abort();
    }
    printf("[ OK ] %s\n", stage);
    fflush(stdout);
    checks++;
}

int main(void)
{
    /* 1. epoxy_has_egl() — 验证 epoxy 派发层真实调用了 dlopen 系统 libEGL.so
     *
     * 注意：本机构建机（无真机 GPU 驱动）没有可用的 libEGL.so 运行时（SDK sysroot
     * 的 libEGL.so 是 stub，eglGetDisplay 等返回空）。若 epoxy_has_egl() 返回 false，
     * 说明当前环境无 EGL 运行时可供真实验证——此时仍完成了 epoxy_has_egl() 这一个
     * 真实 dispatch 调用，但无法进行完整 EGL/GLES 生命周期（需真机）。打印说明并
     * 以成功返回，避免在无 EGL 的构建机上因缺运行时库而崩溃；在具备真实 EGL 的
     * 真机/CI 环境中，以下完整 15 项生命周期测试会真实执行。
     */
    if (!epoxy_has_egl()) {
        fprintf(stderr,
                "[SKIP] no EGL runtime (libEGL.so not dlopen-able) on this build host; "
                "full EGL/GLES lifecycle test requires a real device/EGL stack\n");
        fprintf(stderr,
                "[SKIP] epoxy_has_egl() dispatch probe succeeded, EGL runtime absent — "
                "remaining 14 lifecycle checks skipped (device required, exit 77)\n");
        fflush(stderr);
        return 77; /* distinct skip code: CI/build host without EGL must not be counted as PASS */
    }
    report("epoxy_has_egl()", 1);

    /* 2. EGL 生命周期（经 epoxy 的 EGL 派发表） */
    EGLDisplay dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    report("eglGetDisplay", dpy != EGL_NO_DISPLAY);

    EGLint major = 0, minor = 0;
    report("eglInitialize", eglInitialize(dpy, &major, &minor));
    printf("  EGL version: %d.%d\n", major, minor);

    report("eglBindAPI(ES)", eglBindAPI(EGL_OPENGL_ES_API));

    const EGLint cfgAttribs[] = {
        EGL_SURFACE_TYPE,    EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
        EGL_RED_SIZE,        8,
        EGL_GREEN_SIZE,      8,
        EGL_BLUE_SIZE,       8,
        EGL_ALPHA_SIZE,      8,
        EGL_NONE
    };
    EGLConfig cfg = NULL;
    EGLint numCfg = 0;
    report("eglChooseConfig(ES3)",
           eglChooseConfig(dpy, cfgAttribs, &cfg, 1, &numCfg) && numCfg > 0 && cfg != NULL);

    /* OHOS 真机 EGL 1.4 只接受 1x1 pbuffer（同 egl/1.0.5 实测） */
    const EGLint pbufAttribs[] = { EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE };
    EGLSurface surf = eglCreatePbufferSurface(dpy, cfg, pbufAttribs);
    report("eglCreatePbufferSurface(1x1)", surf != EGL_NO_SURFACE);

    const EGLint ctxAttribs[] = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctxAttribs);
    report("eglCreateContext(ES3)", ctx != EGL_NO_CONTEXT);

    report("eglMakeCurrent", eglMakeCurrent(dpy, surf, surf, ctx));

    /* 3. GL 派发：epoxy_load_gl() 在 OHOS 走 libGLESv2.so（补丁），当前 ES3 上下文 */
    int glver = epoxy_gl_version();
    printf("  epoxy_gl_version(): %d\n", glver);
    report("epoxy_gl_version() >= 30", glver >= 30);

    report("epoxy_is_desktop_gl() == false", !epoxy_is_desktop_gl());

    /* 4. EGL 版本助手 */
    int ever = epoxy_egl_version(dpy);
    printf("  epoxy_egl_version(): %d\n", ever);
    report("epoxy_egl_version() >= 14", ever >= 14);

    /* 5. 释放 */
    report("eglMakeCurrent(release)",
           eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT));
    report("eglDestroyContext", eglDestroyContext(dpy, ctx));
    report("eglDestroySurface", eglDestroySurface(dpy, surf));
    report("eglTerminate", eglTerminate(dpy));

    printf("\n[ ALL PASS ] epoxy 1.5.10 GL/EGL dispatch (%d checks)\n", checks);
    return 0;
}
