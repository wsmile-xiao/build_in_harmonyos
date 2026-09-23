/**
 * freeglut 3.6.0 test_package — consumer-side compile/link + REAL end-to-end test.
 *
 * Runs on the actual HarmonyOS aarch64 device (this is not a cross-compile host),
 * so the binary is executed rather than merely built.
 *
 * What it verifies
 * ----------------
 *   1. freeglut links from the consumer side and glutInit() initialises.
 *   2. glutCreateWindow() creates the offscreen render target and reports the
 *      requested size through glutGet(GLUT_WINDOW_WIDTH/HEIGHT).
 *   3. Registering a display callback and calling
 *      glutPostRedisplay() + glutMainLoopEvent() actually dispatches rendering.
 *   4. The context freeglut created is usable for real GL work: inside the
 *      callback we compile+link a GLES2 shader pair, draw a triangle and read
 *      the centre pixel back.  This is the decisive assertion (a concrete pixel
 *      value, not a tautology).
 *   5. glutSwapBuffers() and glutDestroyWindow() work.
 *
 * NOTE ON GL ENTRY POINTS: on OHOS the symbols linked from libGLESv2.so are
 * dispatcher stubs -- a directly linked glGetString() returns NULL and direct
 * drawing has no effect -- so this test obtains every GL function through
 * eglGetProcAddress(), exactly as the library's own dispatch layer does.
 */
#include <stdio.h>
#include <string.h>

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>

#include <GL/freeglut.h>

/* ---- GL entry points, resolved at runtime (see note above) ---- */
typedef const GLubyte *(*T_getstr)(GLenum);
typedef void (*T_clearcolor)(GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (*T_clear)(GLbitfield);
typedef void (*T_readpixels)(GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void *);
typedef GLuint (*T_createshader)(GLenum);
typedef void (*T_shadersource)(GLuint, GLsizei, const char *const *, const GLint *);
typedef void (*T_compileshader)(GLuint);
typedef void (*T_getshaderiv)(GLuint, GLenum, GLint *);
typedef GLuint (*T_createprogram)(void);
typedef void (*T_attachshader)(GLuint, GLuint);
typedef void (*T_linkprogram)(GLuint);
typedef void (*T_getprogramiv)(GLuint, GLenum, GLint *);
typedef void (*T_useprogram)(GLuint);
typedef void (*T_vertexattribpointer)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void *);
typedef void (*T_enablevertexattribarray)(GLuint);
typedef void (*T_drawarrays)(GLenum, GLint, GLsizei);
typedef GLint (*T_getattriblocation)(GLuint, const char *);

static int failures = 0;
static int display_calls = 0;
static int missing_procs = 0;
static int shader_ok = 0;
static int render_ok = 0;
static int reshape_ok = 0;
static int reshape_requested = 0;

static void check(int cond, const char *what)
{
    printf("  %s %s\n", cond ? "OK:" : "FAIL:", what);
    if (!cond)
        failures++;
}

static void display(void)
{
    int i;

    T_getstr        fGetString    = (T_getstr)eglGetProcAddress("glGetString");
    T_clearcolor    fClearColor   = (T_clearcolor)eglGetProcAddress("glClearColor");
    T_clear         fClear        = (T_clear)eglGetProcAddress("glClear");
    T_readpixels    fReadPixels   = (T_readpixels)eglGetProcAddress("glReadPixels");
    T_createshader  fCreateShader = (T_createshader)eglGetProcAddress("glCreateShader");
    T_shadersource  fShaderSource = (T_shadersource)eglGetProcAddress("glShaderSource");
    T_compileshader fCompileShader = (T_compileshader)eglGetProcAddress("glCompileShader");
    T_getshaderiv   fGetShaderiv  = (T_getshaderiv)eglGetProcAddress("glGetShaderiv");
    T_createprogram fCreateProgram = (T_createprogram)eglGetProcAddress("glCreateProgram");
    T_attachshader  fAttachShader = (T_attachshader)eglGetProcAddress("glAttachShader");
    T_linkprogram   fLinkProgram  = (T_linkprogram)eglGetProcAddress("glLinkProgram");
    T_getprogramiv  fGetProgramiv = (T_getprogramiv)eglGetProcAddress("glGetProgramiv");
    T_useprogram    fUseProgram   = (T_useprogram)eglGetProcAddress("glUseProgram");
    T_vertexattribpointer fVertexAttribPointer =
        (T_vertexattribpointer)eglGetProcAddress("glVertexAttribPointer");
    T_enablevertexattribarray fEnableVAA =
        (T_enablevertexattribarray)eglGetProcAddress("glEnableVertexAttribArray");
    T_drawarrays    fDrawArrays   = (T_drawarrays)eglGetProcAddress("glDrawArrays");
    T_getattriblocation fGetAttribLocation =
        (T_getattriblocation)eglGetProcAddress("glGetAttribLocation");

    display_calls++;

    if (display_calls == 1) {
        missing_procs =
              !fGetString + !fClearColor + !fClear + !fReadPixels + !fCreateShader
            + !fShaderSource + !fCompileShader + !fGetShaderiv + !fCreateProgram
            + !fAttachShader + !fLinkProgram + !fGetProgramiv + !fUseProgram
            + !fVertexAttribPointer + !fEnableVAA + !fDrawArrays + !fGetAttribLocation;
        check(missing_procs == 0, "all GL entry points resolved via eglGetProcAddress");
        if (fGetString) {
            printf("    GL_VERSION  = %s\n", (const char *)fGetString(GL_VERSION));
            printf("    GL_RENDERER = %s\n", (const char *)fGetString(GL_RENDERER));
        }
    }

    if (missing_procs || !fGetString)
        return;

    {
        const char *vs = "attribute vec4 p; void main(){ gl_Position = p; }";
        const char *fs = "precision mediump float;"
                         " void main(){ gl_FragColor = vec4(0.0, 0.0, 1.0, 1.0); }";
        GLuint v = fCreateShader(GL_VERTEX_SHADER);
        GLuint f = fCreateShader(GL_FRAGMENT_SHADER);
        GLuint prog;
        GLint okv = 0, okf = 0, linked = 0;
        GLint loc;
        static const GLfloat tri[] = { -0.8f, -0.8f, 0.8f, -0.8f, 0.0f, 0.8f };
        unsigned char px[4] = { 9, 9, 9, 9 };

        fShaderSource(v, 1, &vs, NULL);
        fCompileShader(v);
        fShaderSource(f, 1, &fs, NULL);
        fCompileShader(f);
        fGetShaderiv(v, GL_COMPILE_STATUS, &okv);
        fGetShaderiv(f, GL_COMPILE_STATUS, &okf);

        prog = fCreateProgram();
        fAttachShader(prog, v);
        fAttachShader(prog, f);
        fLinkProgram(prog);
        fGetProgramiv(prog, GL_LINK_STATUS, &linked);

        i = (okv && okf && linked);
        shader_ok = i;
        if (display_calls == 1)
            check(i, "GLES2 shader pair compiles and links");

        if (!linked)
            return;

        fUseProgram(prog);
        loc = fGetAttribLocation(prog, "p");
        fVertexAttribPointer(loc, 2, GL_FLOAT, GL_FALSE, 0, tri);
        fEnableVAA(loc);

        fClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        fClear(GL_COLOR_BUFFER_BIT);
        fDrawArrays(GL_TRIANGLES, 0, 3);
        fReadPixels(150, 150, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);

        /* Concrete expectation: the triangle centre must be blue. */
        i = (px[2] > 200 && px[0] < 50);
        render_ok = i;
        if (display_calls == 1) {
            printf("    centre pixel = %d,%d,%d,%d\n", px[0], px[1], px[2], px[3]);
            check(i, "triangle really rendered (centre pixel is blue)");
        }
        /*
         * Frame rendered right after a reshape request: this only succeeds if
         * the platform layer re-created the pbuffer AND re-bound the context to
         * it.  If the context had been left unbound, every GL call here would
         * silently do nothing and the read-back would not be the cleared colour.
         */
        if (reshape_requested && !reshape_ok)
            reshape_ok = i;
    }

    glutSwapBuffers();
}

int main(int argc, char **argv)
{
    int win, w, h;

    printf("freeglut smoke test\n");

    /* ---- 1) init ---- */
    glutInit(&argc, argv);
    check(glutGet(GLUT_INIT_STATE) != 0, "glutInit() initialises the library");

    /* ---- 2) create the offscreen render target ---- */
    glutInitContextVersion(2, 0);
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE);
    win = glutCreateWindow("freeglut-ohos-test");
    check(win > 0, "glutCreateWindow() returns a valid window id");

    w = glutGet(GLUT_WINDOW_WIDTH);
    h = glutGet(GLUT_WINDOW_HEIGHT);
    printf("    window %d: %dx%d (offscreen pbuffer)\n", win, w, h);
    check(w == 300 && h == 300, "glutGet() reports the requested 300x300 size");

    /* ---- 3) render through the callback framework ---- */
    glutDisplayFunc(display);
    glutPostRedisplay();
    glutMainLoopEvent();
    check(display_calls >= 1, "display callback dispatched by glutMainLoopEvent()");
    check(shader_ok != 0, "GLES2 rendering path works in the freeglut context");
    check(render_ok != 0, "rendered output verified via glReadPixels");

    /* a second frame, to prove the loop is re-enterable */
    glutPostRedisplay();
    glutMainLoopEvent();
    check(display_calls >= 2, "second redisplay dispatches the callback again");

    /* ---- 4) reshape the current window, then render again ----
     * glutReshapeWindow() only queues GLUT_SIZE_WORK; the platform layer must
     * process it (re-create the pbuffer and re-bind the context) on the next
     * main-loop iteration.  A stub fgPlatformPosResZordWork would swallow the
     * request and leave the old size/context. */
    {
        int before_calls = display_calls;
        glutReshapeWindow(400, 320);
        reshape_requested = 1;
        glutPostRedisplay();
        glutMainLoopEvent();

        w = glutGet(GLUT_WINDOW_WIDTH);
        h = glutGet(GLUT_WINDOW_HEIGHT);
        printf("    after reshape: %dx%d\n", w, h);
        check(w == 400 && h == 320, "reshape request processed (size is now 400x320)");
        check(display_calls > before_calls, "redisplay after reshape dispatched");
        check(reshape_ok != 0, "still rendering after reshape (context re-bound)");
    }

    /* ---- 5) teardown ---- */
    glutDestroyWindow(win);
    printf("    glutDestroyWindow() done\n");

    if (failures) {
        printf("freeglut smoke test: FAILED (%d assertion(s))\n", failures);
        return 1;
    }
    printf("SUMMARY display_calls=%d shader=%s render=%s reshape=%s missing_procs=%d\n",
           display_calls, shader_ok ? "OK" : "FAIL", render_ok ? "OK" : "FAIL",
           reshape_ok ? "OK" : "FAIL", missing_procs);
    printf("freeglut smoke test: PASS\n");
    return 0;
}
