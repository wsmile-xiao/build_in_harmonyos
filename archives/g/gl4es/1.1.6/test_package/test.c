/* gl4es test_package: REAL offscreen render verification (R34) — enhanced.
 *
 * Creates an EGL pbuffer GLES2 context, draws a desktop fixed-pipeline triangle
 * THROUGH gl4es (glMatrixMode/glBegin/glEnd/glColor3f/glVertex3f), then reads
 * back pixels with glReadPixels.
 *
 * Asserts (non-vacuous, proves clear AND draw AND no GL error):
 *   1. Clear actually set a distinct (dark-blue) background — a corner pixel is
 *      blue-dominant (not the "nothing rendered" default, not black).
 *   2. The fixed-pipeline triangle really rasterized over the background — the
 *      centre pixel differs from the background AND is non-black.
 *   3. A real triangle area was drawn — the count of pixels differing from the
 *      background is a substantial, non-degenerate amount.
 *   4. glGetError()==GL_NO_ERROR — the draw/readback path is clean.
 *
 * Requires a working EGL/GPU context (OHOS PC). Under a headless CI without GL,
 * EGL context creation fails and the test reports that step explicitly (exit 1). */
#include <EGL/egl.h>
#include <GL/gl.h>
#include <stdio.h>

static int fail(const char *step) { printf("gl4es render test FAIL: %s\n", step); return 1; }

int main(void) {
    EGLDisplay dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (dpy == EGL_NO_DISPLAY) return fail("eglGetDisplay");
    EGLint major, minor;
    if (!eglInitialize(dpy, &major, &minor)) return fail("eglInitialize");
    if (!eglBindAPI(EGL_OPENGL_ES_API)) return fail("eglBindAPI");
    printf("gl4es render: EGL %d.%d\n", (int)major, (int)minor);

    EGLint cfg_attrs[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
        EGL_NONE
    };
    EGLConfig cfg; EGLint ncfg = 0;
    if (!eglChooseConfig(dpy, cfg_attrs, &cfg, 1, &ncfg) || ncfg < 1) return fail("eglChooseConfig");

    EGLint ctx_attrs[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attrs);
    if (ctx == EGL_NO_CONTEXT) return fail("eglCreateContext");

    EGLint surf_attrs[] = { EGL_WIDTH, 64, EGL_HEIGHT, 64, EGL_NONE };
    EGLSurface surf = eglCreatePbufferSurface(dpy, cfg, surf_attrs);
    if (surf == EGL_NO_SURFACE) return fail("eglCreatePbufferSurface");

    if (!eglMakeCurrent(dpy, surf, surf, ctx)) return fail("eglMakeCurrent");

    /* Desktop fixed pipeline through gl4es on the current GLES2 context. */
    glViewport(0, 0, 64, 64);
    /* Distinct non-black, non-triangle-color background: dark blue. The triangle
       vertices are red/green/blue so their blends are clearly non-blue-dominant. */
    glClearColor(0.1f, 0.1f, 0.6f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    glMatrixMode(GL_PROJECTION); glLoadIdentity();
    glMatrixMode(GL_MODELVIEW); glLoadIdentity();

    glBegin(GL_TRIANGLES);
    glColor3f(1.f, 0.f, 0.f); glVertex3f(-0.5f, -0.5f, 0.f);
    glColor3f(0.f, 1.f, 0.f); glVertex3f( 0.5f, -0.5f, 0.f);
    glColor3f(0.f, 0.f, 1.f); glVertex3f( 0.0f,  0.5f, 0.f);
    glEnd();
    glFinish();

    unsigned char px[64 * 64 * 4];
    glReadPixels(0, 0, 64, 64, GL_RGBA, GL_UNSIGNED_BYTE, px);
    GLenum err = glGetError();

    /* Background reference = a corner pixel (outside the triangle). */
    int bp = (2 * 64 + 2) * 4;
    int bgR = px[bp], bgG = px[bp + 1], bgB = px[bp + 2];
    /* Centre pixel (inside the triangle). */
    int cp = (32 * 64 + 32) * 4;
    int cR = px[cp], cG = px[cp + 1], cB = px[cp + 2];

    /* Count pixels that clearly differ from the background (the drawn triangle). */
    int diff_count = 0;
    for (int i = 0; i < 64 * 64; i++) {
        int d = abs((int)px[i * 4 + 0] - bgR) + abs((int)px[i * 4 + 1] - bgG) + abs((int)px[i * 4 + 2] - bgB);
        if (d > 60) diff_count++;
    }

    int bg_blue_dominant = (bgB > 40 && bgB > bgR + 20 && bgB > bgG + 20);
    int centre_differs = (abs(cR - bgR) + abs(cG - bgG) + abs(cB - bgB)) > 60;
    int centre_nonblack = (cR || cG || cB) != 0;

    printf("gl4es render: bg=(%d,%d,%d) center=(%d,%d,%d) tri_pixels=%d/%d glGetError=0x%x\n",
           bgR, bgG, bgB, cR, cG, cB, diff_count, 64 * 64, (unsigned)err);

    if (bg_blue_dominant && centre_differs && centre_nonblack
        && diff_count > 200 && diff_count < 4000 && err == GL_NO_ERROR) {
        printf("gl4es render PASS\n"); return 0;
    }
    printf("gl4es render FAIL\n"); return 1;
}
