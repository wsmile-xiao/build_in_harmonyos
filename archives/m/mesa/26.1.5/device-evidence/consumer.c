/* mesa 26.1.5 HarmonyOS PC consumer end-to-end test (public API only).
 * Uses EGL + GLESv2 exactly as an application would: create a pbuffer
 * surface, render a triangle, read the pixels back and verify them.
 */
#include <stdio.h>
#include <string.h>
#include <EGL/egl.h>
#include <GLES2/gl2.h>

static int fails = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("  ok  : %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); fails++; } \
} while (0)

static const char *VS =
    "attribute vec2 p;\n"
    "void main(){ gl_Position = vec4(p, 0.0, 1.0); }\n";
static const char *FS =
    "precision mediump float;\n"
    "void main(){ gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0); }\n";

int main(void)
{
    printf("=== mesa 26.1.5 device consumer e2e (HarmonyOS PC) ===\n");

    EGLDisplay dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    CHECK(dpy != EGL_NO_DISPLAY, "eglGetDisplay()");
    if (dpy == EGL_NO_DISPLAY) return 1;

    EGLint maj, min;
    CHECK(eglInitialize(dpy, &maj, &min) == EGL_TRUE, "eglInitialize()");
    printf("  EGL_VENDOR  = %s\n", eglQueryString(dpy, EGL_VENDOR));
    printf("  EGL_VERSION = %s\n", eglQueryString(dpy, EGL_VERSION));

    const EGLint cfg_attr[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8,
        EGL_NONE
    };
    EGLConfig cfg; EGLint n = 0;
    CHECK(eglChooseConfig(dpy, cfg_attr, &cfg, 1, &n) == EGL_TRUE && n > 0,
          "eglChooseConfig()");
    if (n <= 0) return 1;
    printf("  configs = %d\n", n);

    const EGLint pb_attr[] = { EGL_WIDTH, 64, EGL_HEIGHT, 64, EGL_NONE };
    EGLSurface surf = eglCreatePbufferSurface(dpy, cfg, pb_attr);
    CHECK(surf != EGL_NO_SURFACE, "eglCreatePbufferSurface(64x64)");

    const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attr);
    CHECK(ctx != EGL_NO_CONTEXT, "eglCreateContext(GLES2)");

    CHECK(eglMakeCurrent(dpy, surf, surf, ctx) == EGL_TRUE, "eglMakeCurrent()");

    printf("  GL_VENDOR   = %s\n", (const char *)glGetString(GL_VENDOR));
    printf("  GL_RENDERER = %s\n", (const char *)glGetString(GL_RENDERER));
    printf("  GL_VERSION  = %s\n", (const char *)glGetString(GL_VERSION));

    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &VS, NULL); glCompileShader(vs);
    GLint ok = 0; ok = 0;   /* reset: a stale success must not mask this failure */
   glGetShaderiv(vs, GL_COMPILE_STATUS, &ok);
    CHECK(ok, "vertex shader compiled");

    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &FS, NULL); glCompileShader(fs);
    ok = 0;   /* reset: a stale success must not mask this failure */
   glGetShaderiv(fs, GL_COMPILE_STATUS, &ok);
    CHECK(ok, "fragment shader compiled");

    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs); glAttachShader(prog, fs);
    glBindAttribLocation(prog, 0, "p");
    glLinkProgram(prog);
    ok = 0;   /* reset: a stale success must not mask this failure */
   glGetProgramiv(prog, GL_LINK_STATUS, &ok);
    CHECK(ok, "GLES2 program linked");
    glUseProgram(prog);
    glViewport(0, 0, 64, 64);
    glClearColor(1.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);

    /* triangle covering the lower-left half of the 64x64 pbuffer */
    static const GLfloat verts[] = { -1.f,-1.f,  1.f,-1.f,  -1.f,1.f };
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, verts);
    glEnableVertexAttribArray(0);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glFinish();

    unsigned char px[64 * 64 * 4];
    memset(px, 0, sizeof(px));
    glReadPixels(0, 0, 64, 64, GL_RGBA, GL_UNSIGNED_BYTE, px);

    int green = 0, red = 0;
    for (int i = 0; i < 64 * 64; i++) {
        unsigned char r = px[i*4+0], g = px[i*4+1], b = px[i*4+2];
        if (g > 200 && r < 60 && b < 60) green++;
        else if (r > 200 && g < 60 && b < 60) red++;
    }
    printf("  green(triangle) px = %d, red(clear) px = %d\n", green, red);
    CHECK(green > 0, "triangle rendered (green pixels present)");
    CHECK(red > 0, "clear colour retained (red pixels present)");

    eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    eglDestroyContext(dpy, ctx);
    eglDestroySurface(dpy, surf);
    eglTerminate(dpy);

    printf("=== %s: %d failure(s) ===\n", fails ? "FAIL" : "ALL PASS", fails);
    return fails ? 1 : 0;
}
