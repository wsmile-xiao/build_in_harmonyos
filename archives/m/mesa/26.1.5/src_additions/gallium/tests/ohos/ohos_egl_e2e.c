/*
 * HarmonyOS-specific adapter for Mesa 26.1.5 (rule12 consumer E2E case).
 *
 * This is a *consumer-side end-to-end* test: it drives the real public
 * EGL + GLESv2 entry points exported by the packaged libraries and verifies
 * that an off-screen (surfaceless / pbuffer) rendering round trip really
 * produces the expected pixels.  It is built as part of the mesa tree so it
 * links against the same libEGL / libGLESv2 objects that are packaged.
 *
 * Covered OHOS platform adaptations:
 *   1. util_get_process_name() -> /proc/self/exe basename.  HarmonyOS has
 *      neither program_invocation_name nor getprogname(); upstream Mesa then
 *      returns "" (u_process.c GET_PROGRAM_NAME_NOT_AVAILABLE fallback), which
 *      breaks Mesa's own drirc/shader-cache paths that key off the process
 *      name.  The OHOS port reads /proc/self/exe instead (meson injects
 *      -DHAVE_READ_PROC_SELF_EXE).
 *   2. u_memstream_close() must fflush() before fclose() on musl/OHOS,
 *      otherwise the caller's buffer stays stale.  Verified through the real
 *      util/memstream.h consumer interface.
 *   3. EGL surfaceless + llvmpipe/softpipe software rendering works on
 *      HarmonyOS PC without any window system (platforms = '').
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "util/u_process.h"
#include "util/memstream.h"

/* EGL + GLESv2 public entry points.  Declared here instead of including
 * <EGL/egl.h> so the test can be built before the headers are staged; the
 * symbol set below is exactly what the packaged libEGL/libGLESv2 export. */
typedef void *EGLDisplay;
typedef void *EGLContext;
typedef void *EGLSurface;
typedef void *EGLConfig;
typedef unsigned int EGLBoolean;
typedef int EGLint;
typedef unsigned int GLenum;
typedef unsigned int GLuint;
typedef int GLint;
typedef unsigned char GLubyte;
typedef unsigned int GLbitfield;
typedef float GLfloat;

#define EGL_DEFAULT_DISPLAY ((void *)0)
#define EGL_NO_DISPLAY ((EGLDisplay)0)
#define EGL_NO_CONTEXT ((EGLContext)0)
#define EGL_NO_SURFACE ((EGLSurface)0)
#define EGL_SURFACE_TYPE 0x3033
#define EGL_PBUFFER_BIT 0x0001
#define EGL_RENDERABLE_TYPE 0x3040
#define EGL_OPENGL_ES2_BIT 0x0004
#define EGL_RED_SIZE 0x3024
#define EGL_GREEN_SIZE 0x3023
#define EGL_BLUE_SIZE 0x3022
#define EGL_ALPHA_SIZE 0x3021
#define EGL_DEPTH_SIZE 0x3025
#define EGL_NONE 0x3038
#define EGL_WIDTH 0x3057
#define EGL_HEIGHT 0x3056
#define EGL_CONTEXT_CLIENT_VERSION 0x3098
#define EGL_VENDOR 0x3053
#define EGL_VERSION 0x3054
#define EGL_EXTENSIONS 0x3055
#define EGL_TRUE 1

#define GL_VENDOR 0x1F00
#define GL_RENDERER 0x1F01
#define GL_VERSION 0x1F02
#define GL_COLOR_BUFFER_BIT 0x00004000
#define GL_RGBA 0x1908
#define GL_UNSIGNED_BYTE 0x1401
#define GL_FLOAT 0x1406
#define GL_TRIANGLES 0x0004
#define GL_ARRAY_BUFFER 0x8892
#define GL_STATIC_DRAW 0x88E4
#define GL_FRAGMENT_SHADER 0x8B30
#define GL_VERTEX_SHADER 0x8B31
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82

extern EGLDisplay eglGetDisplay(void *);
extern EGLBoolean eglInitialize(EGLDisplay, EGLint *, EGLint *);
extern EGLBoolean eglChooseConfig(EGLDisplay, const EGLint *, EGLConfig *, EGLint, EGLint *);
extern EGLSurface eglCreatePbufferSurface(EGLDisplay, EGLConfig, const EGLint *);
extern EGLContext eglCreateContext(EGLDisplay, EGLConfig, EGLContext, const EGLint *);
extern EGLBoolean eglMakeCurrent(EGLDisplay, EGLSurface, EGLSurface, EGLContext);
extern EGLBoolean eglSwapBuffers(EGLDisplay, EGLSurface);
extern const char *eglQueryString(EGLDisplay, EGLint);
extern EGLBoolean eglTerminate(EGLDisplay);
extern EGLint eglGetError(void);

extern void glGetIntegerv(GLenum, GLint *);
extern const GLubyte *glGetString(GLenum);
extern void glViewport(GLint, GLint, GLint, GLint);
extern void glClearColor(GLfloat, GLfloat, GLfloat, GLfloat);
extern void glClear(GLbitfield);
extern void glReadPixels(GLint, GLint, GLint, GLint, GLenum, GLenum, void *);
extern void glFinish(void);
extern GLuint glCreateShader(GLenum);
extern void glShaderSource(GLuint, GLint, const char *const *, const GLint *);
extern void glCompileShader(GLuint);
extern void glGetShaderiv(GLuint, GLenum, GLint *);
extern GLuint glCreateProgram(void);
extern void glAttachShader(GLuint, GLuint);
extern void glLinkProgram(GLuint);
extern void glGetProgramiv(GLuint, GLenum, GLint *);
extern void glUseProgram(GLuint);
extern void glGenBuffers(GLint, GLuint *);
extern void glBindBuffer(GLenum, GLuint);
extern void glBufferData(GLenum, long, const void *, GLenum);
extern void glVertexAttribPointer(GLuint, GLint, GLenum, GLubyte, GLint, const void *);
extern void glEnableVertexAttribArray(GLuint);
extern void glDrawArrays(GLenum, GLint, GLint);
extern GLint glGetAttribLocation(GLuint, const char *);
extern void glVertexAttrib4f(GLuint, GLfloat, GLfloat, GLfloat, GLfloat);
extern void glBindAttribLocation(GLuint, GLuint, const char *);

static int failures = 0;

#define CHECK(cond, ...)                                                      \
   do {                                                                       \
      if (!(cond)) {                                                          \
         printf("  FAIL: ");                                                  \
         printf(__VA_ARGS__);                                                 \
         printf("\n");                                                        \
         failures++;                                                          \
      } else {                                                                \
         printf("  ok  : ");                                                  \
         printf(__VA_ARGS__);                                                 \
         printf("\n");                                                        \
      }                                                                       \
   } while (0)

/* ---------------------------------------------------------------- case 1
 * OHOS process-name adaptation */
static void test_process_name(void)
{
   const char *name = util_get_process_name();
   printf("[1] util_get_process_name() OHOS /proc/self/exe adaptation\n");
   printf("  process name = '%s'\n", name ? name : "(null)");
   CHECK(name != NULL, "util_get_process_name() returns non-NULL");
   CHECK(name != NULL && name[0] != '\0',
         "process name is non-empty (upstream would return \"\" on OHOS)");
   CHECK(name != NULL && strchr(name, '/') == NULL,
         "process name is a basename, not a path");
   CHECK(name != NULL && strcmp(name, "ohos_egl_e2e") == 0,
         "process name equals the executable basename 'ohos_egl_e2e'");
}

/* ---------------------------------------------------------------- case 2
 * u_memstream fflush-before-close adaptation */
/* Payload written into the memstream, shared by the size and content
 * assertions so the two can never drift apart. */
static const char kExpected[] = "mesa-ohos-memstream";

static void test_memstream(void)
{
   struct u_memstream mem;
   char *ptr = NULL;
   size_t size = 0;
   FILE *f;
   bool opened;

   printf("[2] u_memstream_close() OHOS flush-before-close adaptation\n");
   /* Upstream API: u_memstream_open() returns bool, the FILE* lives in mem.f */
   opened = u_memstream_open(&mem, &ptr, &size);
   CHECK(opened, "u_memstream_open() succeeds");
   if (!opened)
      return;
   f = u_memstream_get(&mem);
   CHECK(f != NULL, "u_memstream_get() returns the backing stream");
   if (f == NULL)
      return;

   fputs("mesa-ohos-memstream", f);
   /* Deliberately do NOT call fflush()/fseek() ourselves: on musl/OHOS the
    * upstream implementation leaves the caller's buffer stale after fclose(),
    * so this is exactly the adaptation under test (patch 0004 makes
    * u_memstream_close() flush before closing). */
   u_memstream_close(&mem);

   CHECK(ptr != NULL, "buffer pointer populated after close");
   if (ptr == NULL)
      return;

   /* Guard the size BEFORE touching the buffer contents.  If the fflush
    * adaptation regresses, `ptr` may not be NUL-terminated at the expected
    * offset, and strcmp() on it would read out of bounds -- crashing the
    * process and taking case 3 (the EGL render round-trip, the core of this
    * test) down with it.  Returning here keeps the failure readable. */
   CHECK(size == strlen(kExpected),
         "size correct after close (got %zu, want %zu)", size, strlen(kExpected));
   if (size != strlen(kExpected)) {
      free(ptr);   /* release before bailing out: no leak on the failure path */
      return;
   }

   CHECK(strcmp(ptr, kExpected) == 0,
         "buffer contents correct after close (got '%s')", ptr);
   free(ptr);
}

/* ---------------------------------------------------------------- case 3
 * real EGL + GLESv2 off-screen render round trip */
static const char *VS =
   "attribute vec4 aPos;\n"
   "void main() { gl_Position = aPos; }\n";

static const char *FS =
   "precision mediump float;\n"
   "void main() { gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0); }\n";

static GLuint make_program(void)
{
   GLuint vs = glCreateShader(GL_VERTEX_SHADER);
   GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
   GLuint prog;
   GLint ok = 0;

   glShaderSource(vs, 1, &VS, NULL);
   glCompileShader(vs);
   glGetShaderiv(vs, GL_COMPILE_STATUS, &ok);
   if (!ok) { printf("  vertex shader compile failed\n"); return 0; }

   glShaderSource(fs, 1, &FS, NULL);
   glCompileShader(fs);
   glGetShaderiv(fs, GL_COMPILE_STATUS, &ok);
   if (!ok) { printf("  fragment shader compile failed\n"); return 0; }

   prog = glCreateProgram();
   glAttachShader(prog, vs);
   glAttachShader(prog, fs);
   glBindAttribLocation(prog, 0, "aPos");
   glLinkProgram(prog);
   glGetProgramiv(prog, GL_LINK_STATUS, &ok);
   if (!ok) { printf("  program link failed\n"); return 0; }
   return prog;
}

static void test_egl_render(void)
{
   const EGLint cfg_attr[] = {
      EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
      EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
      EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
      EGL_DEPTH_SIZE, 24,
      EGL_NONE
   };
   const EGLint pb_attr[] = { EGL_WIDTH, 64, EGL_HEIGHT, 64, EGL_NONE };
   const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
   EGLDisplay dpy;
   EGLConfig cfg;
   EGLint ncfg = 0;
   EGLSurface surf;
   EGLContext ctx;
   GLuint prog;
   GLubyte px[64 * 64 * 4];
   int i, greenish = 0, background = 0;
   const char *vendor, *ver, *rend;

   printf("[3] EGL surfaceless/pbuffer + GLESv2 off-screen render round trip\n");

   dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
   CHECK(dpy != EGL_NO_DISPLAY, "eglGetDisplay(EGL_DEFAULT_DISPLAY) -> %p", dpy);
   if (dpy == EGL_NO_DISPLAY) return;

   CHECK(eglInitialize(dpy, NULL, NULL) == EGL_TRUE,
         "eglInitialize() succeeds (eglGetError=0x%x)", eglGetError());

   vendor = eglQueryString(dpy, EGL_VENDOR);
   ver = eglQueryString(dpy, EGL_VERSION);
   printf("  EGL_VENDOR  = %s\n", vendor ? vendor : "(null)");
   printf("  EGL_VERSION = %s\n", ver ? ver : "(null)");
   CHECK(vendor != NULL && vendor[0] != '\0', "EGL_VENDOR non-empty");
   /* EGL_VERSION 是 EGL 规范版本（如 "1.5"）；Mesa 版本号在 GL_VERSION 中，
    * 在 eglMakeCurrent 之后断言。 */
   CHECK(ver != NULL && ver[0] != '\0', "eglQueryString(EGL_VERSION) non-empty");

   CHECK(eglChooseConfig(dpy, cfg_attr, &cfg, 1, &ncfg) == EGL_TRUE && ncfg >= 1,
         "eglChooseConfig() found %d matching config(s)", ncfg);
   if (ncfg < 1) return;

   surf = eglCreatePbufferSurface(dpy, cfg, pb_attr);
   CHECK(surf != EGL_NO_SURFACE,
         "eglCreatePbufferSurface(64x64) -> %p (eglGetError=0x%x)", surf, eglGetError());
   if (surf == EGL_NO_SURFACE) return;

   ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attr);
   CHECK(ctx != EGL_NO_CONTEXT,
         "eglCreateContext(GLES2) -> %p (eglGetError=0x%x)", ctx, eglGetError());
   if (ctx == EGL_NO_CONTEXT) return;

   CHECK(eglMakeCurrent(dpy, surf, surf, ctx) == EGL_TRUE,
         "eglMakeCurrent() succeeds (eglGetError=0x%x)", eglGetError());

   rend = (const char *)glGetString(GL_RENDERER);
   printf("  GL_VENDOR   = %s\n", (const char *)glGetString(GL_VENDOR));
   printf("  GL_RENDERER = %s\n", rend ? rend : "(null)");
   printf("  GL_VERSION  = %s\n", (const char *)glGetString(GL_VERSION));
   CHECK(rend != NULL && rend[0] != '\0', "GL_RENDERER non-empty");
   {
      const char *glver = (const char *)glGetString(GL_VERSION);
      CHECK(glver != NULL && strstr(glver, "26.1.5") != NULL,
            "GL_VERSION reports upstream Mesa 26.1.5 ('%s')", glver ? glver : "");
   }

   prog = make_program();
   CHECK(prog != 0, "GLES2 program compiled and linked");
   if (prog == 0) return;

   glViewport(0, 0, 64, 64);
   glClearColor(1.0f, 0.0f, 0.0f, 1.0f);   /* red background */
   glClear(GL_COLOR_BUFFER_BIT);
   glUseProgram(prog);

   {
      static const GLfloat tri[] = {
         0.0f,  0.8f, 0.0f,
        -0.8f, -0.8f, 0.0f,
         0.8f, -0.8f, 0.0f
      };
      GLuint vbo = 0;
      glGenBuffers(1, &vbo);
      glBindBuffer(GL_ARRAY_BUFFER, vbo);
      glBufferData(GL_ARRAY_BUFFER, (long)sizeof(tri), tri, GL_STATIC_DRAW);
      glEnableVertexAttribArray(0);
      glVertexAttribPointer(0, 3, GL_FLOAT, 0 /*GL_FALSE*/, 0, (const void *)0);
      glDrawArrays(GL_TRIANGLES, 0, 3);
   }
   glFinish();

   memset(px, 0, sizeof(px));
   glReadPixels(0, 0, 64, 64, GL_RGBA, GL_UNSIGNED_BYTE, px);

   for (i = 0; i < 64 * 64; i++) {
      GLubyte r = px[i * 4 + 0], g = px[i * 4 + 1], b = px[i * 4 + 2];
      if (g > 200 && r < 80 && b < 80) greenish++;
      else if (r > 200 && g < 80 && b < 80) background++;
   }
   printf("  green(triangle) pixels = %d, red(clear) pixels = %d, total = %d\n",
          greenish, background, 64 * 64);
   CHECK(greenish > 0, "rendered triangle produced green fragments (%d px)", greenish);
   CHECK(background > 0, "clear colour survived outside the triangle (%d px)", background);
   CHECK(greenish + background == 64 * 64,
         "every pixel is either triangle or background (no uninitialised data)");

   eglSwapBuffers(dpy, surf);
   eglTerminate(dpy);
}

int main(void)
{
   printf("=== mesa 26.1.5 HarmonyOS PC consumer end-to-end test ===\n");
   printf("rule12: real consumer-side E2E case over the packaged EGL/GLESv2 libs\n\n");

   test_process_name();
   test_memstream();
   test_egl_render();

   printf("\n=== %s: %d failure(s) ===\n", failures == 0 ? "ALL PASS" : "FAILED",
          failures);
   return failures == 0 ? 0 : 1;
}
