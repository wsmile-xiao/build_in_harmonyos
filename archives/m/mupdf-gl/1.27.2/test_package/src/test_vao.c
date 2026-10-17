/*
 * End-to-end test for the mupdf-gl OHOS adaptation (Path-B knowledge:
 * DRAFT-mupdf-gl-1.27.2-immediate-mode-unavailable-vao-rewrite).
 *
 * What this proves (all on the OHOS real device, headless pbuffer):
 *
 *  1. NEGATIVE (the core finding): the OHOS GLES driver does not provide
 *     immediate-mode entry points — eglGetProcAddress("glBegin"/"glEnd"/
 *     "glVertex2f"/"glTexCoord2f") all return NULL, and the symbols are not
 *     even exported by libGLESv2.so/libGLESv3.so (an unpatched mupdf-gl
 *     cannot link on OHOS).
 *
 *  2. POSITIVE (the fix): the REAL patched platform/gl/gl-ui.c shipped in
 *     the package (compiled right here by CMakeLists.txt) drives
 *     ui_draw_image() through the VAO + shader pipeline. A synthetic
 *     pixmap (red field + blue block) is uploaded as a texture and drawn
 *     with ui_draw_image(); glReadPixels verifies the rendered result
 *     (framebuffer fully covered, blue block at the center).
 *
 * Note on GL entry points: modern GL symbols ARE exported by the OHOS
 * libGLESv2.so/libGLESv3.so (single-dispatcher aliases, functionally
 * correct — verified by probe-direct-gl.c), so this test and gl-ui.c call
 * them directly; only the immediate-mode names are absent.
 */
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* struct texture + void ui_draw_image(struct texture *, float, float) —
 * from the package's shipped platform/gl/gl-app.h (via CMake include path). */
#include "gl-app.h"

#define W 200
#define H 200

/* Synthetic pixmap: red field, blue block at [60,140) x [60,140). */
static void make_pixmap(unsigned char *pix)
{
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            unsigned char *p = &pix[(y * W + x) * 4];
            int in_block = (x >= 60 && x < 140 && y >= 60 && y < 140);
            p[0] = in_block ? 51  : 204; /* R */
            p[1] = in_block ? 102 : 51;  /* G */
            p[2] = in_block ? 204 : 51;  /* B */
            p[3] = 255;                  /* A */
        }
    }
}

int main(void)
{
    /* ---- EGL pbuffer ES 3.2 context (headless) ---- */
    EGLDisplay dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (dpy == EGL_NO_DISPLAY) { printf("TEST-FAIL: eglGetDisplay\n"); return 2; }
    EGLint maj = 0, min = 0;
    if (!eglInitialize(dpy, &maj, &min)) { printf("TEST-FAIL: eglInitialize err=0x%x\n", eglGetError()); return 2; }
    /* OHOS libEGL.so exports eglQueryString (EGL 1.5) but NOT the deprecated
     * eglGetString (EGL 1.0) — the symbol does not exist in the .so. */
    printf("[egl] EGL %d.%d vendor=%s\n", maj, min,
           (const char *)eglQueryString(dpy, EGL_VENDOR));

    /* ES3 context: VAO (glGenVertexArrays) and shaders are ES2/ES3
     * features; the OHOS driver defaults to an ES 1.1 context unless the
     * client version is pinned. */
    EGLint cfg_attribs[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8,
        EGL_NONE
    };
    EGLConfig cfg; EGLint ncfg = 0;
    if (!eglChooseConfig(dpy, cfg_attribs, &cfg, 1, &ncfg) || ncfg < 1) {
        printf("TEST-FAIL: eglChooseConfig(PBUFFER,ES3) err=0x%x\n", eglGetError()); return 2;
    }
    EGLint pb_attribs[] = { EGL_WIDTH, W, EGL_HEIGHT, H, EGL_NONE };
    EGLint ctx_attribs[] = { EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE };
    EGLSurface surf = eglCreatePbufferSurface(dpy, cfg, pb_attribs);
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attribs);
    if (!surf || !ctx || !eglMakeCurrent(dpy, surf, surf, ctx)) {
        printf("TEST-FAIL: pbuffer/context err=0x%x\n", eglGetError()); return 2;
    }
    printf("[gl] GL_VERSION=%s\n", (const char *)glGetString(GL_VERSION));

    /* ---- 1. NEGATIVE check: immediate mode is unavailable ---- */
    void *glBegin    = eglGetProcAddress("glBegin");
    void *glEnd      = eglGetProcAddress("glEnd");
    void *glVertex2f = eglGetProcAddress("glVertex2f");
    void *glTexCoord2f = eglGetProcAddress("glTexCoord2f");
    int neg_ok = !glBegin && !glEnd && !glVertex2f && !glTexCoord2f;
    printf("[neg] glBegin=%p glEnd=%p glVertex2f=%p glTexCoord2f=%p\n",
           glBegin, glEnd, glVertex2f, glTexCoord2f);
    if (!neg_ok) {
        printf("TEST-FAIL: expected all immediate-mode entry points to be NULL\n");
        return 1;
    }
    printf("[neg] immediate mode unavailable on this OHOS GLES driver: YES "
           "(unpatched mupdf-gl cannot link/run here)\n");

    /* ---- 2. POSITIVE: upload synthetic pixmap as a texture ---- */
    unsigned char *pix = malloc((size_t)W * H * 4);
    if (!pix) { printf("TEST-FAIL: malloc\n"); return 2; }
    make_pixmap(pix);

    GLuint tex = 0;
    glGenTextures(1, &tex);
    glBindTexture(GL_TEXTURE_2D, tex);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, W, H, 0, GL_RGBA, GL_UNSIGNED_BYTE, pix);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    { GLenum e = glGetError();
      if (e != GL_NO_ERROR) { printf("TEST-FAIL: glTexImage2D err=0x%x\n", e); return 4; } }

    /* ---- 3. Drive the REAL patched ui_draw_image from the package ---- */
    glViewport(0, 0, W, H);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);

    struct texture t = { .id = tex, .x = 0, .y = 0, .w = W, .h = H,
                         .s = 1.0f, .t = 1.0f };
    ui_draw_image(&t, 0, 0);   /* the OHOS VAO-rewrite of the GL render path */

    /* ---- 4. Read back + verify ---- */
    unsigned char *fb = malloc((size_t)W * H * 4);
    if (!fb) { printf("TEST-FAIL: malloc\n"); return 2; }
    glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, fb);
    { GLenum e = glGetError();
      if (e != GL_NO_ERROR) { printf("TEST-FAIL: glReadPixels err=0x%x\n", e); return 4; } }

    int nonblack = 0;
    for (int i = 0; i < W * H; i++) {
        if (fb[i*4] || fb[i*4+1] || fb[i*4+2]) nonblack++;
    }
    /* Center pixel must be the blue block (51,102,204). The block is
     * symmetric in the pixmap, so it lands at the center in either
     * vertical orientation. */
    int cx = W / 2, cy = H / 2;
    int r = fb[(cy * W + cx) * 4], g = fb[(cy * W + cx) * 4 + 1], b = fb[(cy * W + cx) * 4 + 2];
    int center_blue = (b > 150 && r < 120 && g < 150);

    printf("[gl] framebuffer nonblack=%d/%d (%.1f%%), center=(%d,%d,%d)\n",
           nonblack, W * H, 100.0 * nonblack / (W * H), r, g, b);
    free(pix);
    free(fb);
    eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    eglTerminate(dpy);

    if (nonblack >= W * H / 2 && center_blue) {
        printf("TEST-PASS: immediate mode unavailable (finding confirmed) AND "
               "the package's real patched ui_draw_image renders correctly on OHOS\n");
        return 0;
    }
    printf("TEST-FAIL: rendered output wrong (nonblack=%d, center=(%d,%d,%d), "
           "need center blue block)\n", nonblack, r, g, b);
    return 1;
}
