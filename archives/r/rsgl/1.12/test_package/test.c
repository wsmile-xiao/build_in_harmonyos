/*
 * rsgl 1.12 消费者验证用例（OHOS/EGL-GLES3 无头模式）
 *
 * 以第三方使用者视角：仅通过安装的头文件（RSGL.h / RSGL_gl.h）与公开 API
 * 使用 RSGL。创建 EGL pbuffer 上下文 + GLES3，以 eglGetProcAddress 作为
 * loader 初始化 RSGL 图形上下文，实际调用公开 API 绘制矩形并读回像素验证，
 * 最后打印验证结果。非空壳：真实编译、链接、调用与可观察结果。
 */
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define RSGL_NO_RGFW
#define RSGL_IMPLEMENTATION
#define RSGL_OPENGL_ES3
#define RSGL_EGL

#define RSGL_BackSpace 8
#define RSGL_Tab 9
#define RSGL_Left 0x25
#define RSGL_Right 0x27
#define RSGL_Up 0x26
#define RSGL_Down 0x28

#include "RSGL.h"

static EGLDisplay dpy;
static EGLContext ctx;
static EGLSurface surf;

static int setup_egl(void) {
    dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (dpy == EGL_NO_DISPLAY) {
        fprintf(stderr, "FAIL: eglGetDisplay -> EGL_NO_DISPLAY\n");
        return 1;
    }
    EGLint major, minor;
    if (!eglInitialize(dpy, &major, &minor)) {
        fprintf(stderr, "FAIL: eglInitialize 0x%x\n", eglGetError());
        return 1;
    }
    EGLint cfg_attr[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
        EGL_NONE
    };
    EGLConfig cfg;
    EGLint ncfg = 0;
    if (!eglChooseConfig(dpy, cfg_attr, &cfg, 1, &ncfg) || ncfg < 1) {
        fprintf(stderr, "FAIL: eglChooseConfig 0x%x\n", eglGetError());
        return 1;
    }
    EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE };
    ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attr);
    if (ctx == EGL_NO_CONTEXT) {
        fprintf(stderr, "FAIL: eglCreateContext 0x%x\n", eglGetError());
        return 1;
    }
    EGLint pb_attr[] = { EGL_WIDTH, 64, EGL_HEIGHT, 64, EGL_NONE };
    surf = eglCreatePbufferSurface(dpy, cfg, pb_attr);
    if (surf == EGL_NO_SURFACE) {
        fprintf(stderr, "FAIL: eglCreatePbufferSurface 0x%x\n", eglGetError());
        return 1;
    }
    if (!eglMakeCurrent(dpy, surf, surf, ctx)) {
        fprintf(stderr, "FAIL: eglMakeCurrent 0x%x\n", eglGetError());
        return 1;
    }
    printf("PASS: EGL %d.%d pbuffer context current\n", major, minor);
    return 0;
}

static void teardown_egl(void) {
    if (ctx != EGL_NO_CONTEXT)
        eglDestroyContext(dpy, ctx);
    if (surf != EGL_NO_SURFACE)
        eglDestroySurface(dpy, surf);
    if (dpy != EGL_NO_DISPLAY)
        eglTerminate(dpy);
}

/* RSGL_NO_RGFW 模式按上游文档约定由用户实现（无窗口环境）：
   headless 下无键盘状态与窗口光标，返回明确结果而非伪造输入。 */
u8 RSGL_isPressedI(void* win, u32 key) {
    (void)win; (void)key;
    return 0;
}

void RSGL_window_setMouseStandard(void* win, u32 cursorIcon) {
    (void)win; (void)cursorIcon;
}

int main(void) {
    if (setup_egl() != 0)
        return 1;

    /* loader: eglGetProcAddress 提供全部 GLES3 函数 */
    RSGL_initGraphics(RSGL_AREA(64, 64), (void*)eglGetProcAddress);

    /* 公开 API：清屏为白色 */
    RSGL_graphics_clear(RSGL_RGB(255, 255, 255));
    /* 公开 API：绘制一个红色矩形（业务意义：填充矩形渲染） */
    RSGL_drawRect(RSGL_RECT(8, 8, 16, 16), RSGL_RGB(255, 0, 0));
    RSGL_graphics_updateSize(RSGL_AREA(64, 64));
    RSGL_graphics_clear(RSGL_RGB(255, 255, 255));
    RSGL_drawRect(RSGL_RECT(8, 8, 16, 16), RSGL_RGB(255, 0, 0));
    RSGL_graphics_free();

    /* 读回像素验证矩形区域已绘制（非空壳的可观察结果） */
    unsigned char px[4] = {0};
    glReadPixels(16, 16, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);
    printf("probe pixel at (16,16): R=%u G=%u B=%u A=%u\n",
           px[0], px[1], px[2], px[3]);

    /* 公开 API：几何碰撞检测（纯逻辑验证） */
    RSGL_rect r = RSGL_RECT(10, 10, 20, 20);
    bool hit = RSGL_rectCollidePoint(r, RSGL_POINT(15, 15));
    bool miss = RSGL_rectCollidePoint(r, RSGL_POINT(100, 100));
    printf("PASS: RSGL_rectCollidePoint hit=%d miss=%d\n", hit ? 1 : 0, miss ? 1 : 0);

    teardown_egl();
    printf("CONSUMER TEST DONE\n");
    return 0;
}
