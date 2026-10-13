/*
 * test_package consumer for mesa 26.1.5 on HarmonyOS PC.
 *
 * Drives the packaged EGL + GLESv2 public headers/libraries through a real
 * off-screen rendering round trip and checks the resulting pixels.  Upstream
 * removed OSMesa in 25.1.0, so the headless path is EGL surfaceless/pbuffer +
 * llvmpipe software rasterisation.
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <EGL/egl.h>
#include <GLES2/gl2.h>

static int failures = 0;

#define CHECK(cond, ...)                                                      \
   do {                                                                       \
      if (!(cond)) { printf("  FAIL: "); printf(__VA_ARGS__); printf("\n");   \
                     failures++; }                                            \
      else { printf("  ok  : "); printf(__VA_ARGS__); printf("\n"); }         \
   } while (0)

static const char *VS =
   "attribute vec4 aPos;\n"
   "void main() { gl_Position = aPos; }\n";

static const char *FS =
   "precision mediump float;\n"
   "void main() { gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0); }\n";

int main(void)
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
   GLuint vs, fs, prog;
   GLint ok = 0;
   GLubyte px[64 * 64 * 4];
   int i, greenish = 0, background = 0;
   const char *vendor, *ver, *rend;
   static const GLfloat tri[] = {
      0.0f,  0.8f, 0.0f,
     -0.8f, -0.8f, 0.0f,
      0.8f, -0.8f, 0.0f
   };
   GLuint vbo = 0;

   printf("=== mesa 26.1.5 test_package (HarmonyOS PC, EGL+GLESv2) ===\n");

   dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
   CHECK(dpy != EGL_NO_DISPLAY, "eglGetDisplay() -> %p", (void *)dpy);
   if (dpy == EGL_NO_DISPLAY) return 1;

   CHECK(eglInitialize(dpy, NULL, NULL) == EGL_TRUE,
         "eglInitialize() succeeds");

   vendor = eglQueryString(dpy, EGL_VENDOR);
   ver = eglQueryString(dpy, EGL_VERSION);
   printf("  EGL_VENDOR  = %s\n", vendor ? vendor : "(null)");
   printf("  EGL_VERSION = %s\n", ver ? ver : "(null)");
   /* EGL_VERSION 是 EGL 规范版本（如 "1.5"），Mesa 版本号在 GL_VERSION 里 */
   CHECK(ver != NULL && ver[0] != '\0', "eglQueryString(EGL_VERSION) non-empty");

   CHECK(eglChooseConfig(dpy, cfg_attr, &cfg, 1, &ncfg) == EGL_TRUE && ncfg >= 1,
         "eglChooseConfig() -> %d config(s)", ncfg);
   if (ncfg < 1) return 1;

   surf = eglCreatePbufferSurface(dpy, cfg, pb_attr);
   CHECK(surf != EGL_NO_SURFACE, "eglCreatePbufferSurface(64x64) -> %p",
         (void *)surf);
   if (surf == EGL_NO_SURFACE) return 1;

   ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attr);
   CHECK(ctx != EGL_NO_CONTEXT, "eglCreateContext(GLES2) -> %p", (void *)ctx);
   if (ctx == EGL_NO_CONTEXT) return 1;

   CHECK(eglMakeCurrent(dpy, surf, surf, ctx) == EGL_TRUE,
         "eglMakeCurrent() succeeds");

   rend = (const char *)glGetString(GL_RENDERER);
   printf("  GL_VENDOR   = %s\n", (const char *)glGetString(GL_VENDOR));
   printf("  GL_RENDERER = %s\n", rend ? rend : "(null)");
   printf("  GL_VERSION  = %s\n", (const char *)glGetString(GL_VERSION));
   CHECK(rend != NULL && rend[0] != '\0', "GL_RENDERER non-empty");
   /* 版本证据：GL_VERSION 应报告本包的上游 Mesa 版本 */
   {
      const char *glver = (const char *)glGetString(GL_VERSION);
      CHECK(glver != NULL && strstr(glver, "26.1.5") != NULL,
            "GL_VERSION reports upstream Mesa 26.1.5");
   }

   vs = glCreateShader(GL_VERTEX_SHADER);
   glShaderSource(vs, 1, &VS, NULL);
   glCompileShader(vs);
   ok = 0;   /* reset: a stale success must not mask this failure */
   glGetShaderiv(vs, GL_COMPILE_STATUS, &ok);
   CHECK(ok, "vertex shader compiled");

   fs = glCreateShader(GL_FRAGMENT_SHADER);
   glShaderSource(fs, 1, &FS, NULL);
   glCompileShader(fs);
   ok = 0;   /* reset: a stale success must not mask this failure */
   glGetShaderiv(fs, GL_COMPILE_STATUS, &ok);
   CHECK(ok, "fragment shader compiled");

   prog = glCreateProgram();
   glAttachShader(prog, vs);
   glAttachShader(prog, fs);
   glBindAttribLocation(prog, 0, "aPos");
   glLinkProgram(prog);
   ok = 0;   /* reset: a stale success must not mask this failure */
   glGetProgramiv(prog, GL_LINK_STATUS, &ok);
   CHECK(ok, "GLES2 program linked");
   if (!ok) return 1;

   glViewport(0, 0, 64, 64);
   glClearColor(1.0f, 0.0f, 0.0f, 1.0f);
   glClear(GL_COLOR_BUFFER_BIT);
   glUseProgram(prog);

   glGenBuffers(1, &vbo);
   glBindBuffer(GL_ARRAY_BUFFER, vbo);
   glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)sizeof(tri), tri, GL_STATIC_DRAW);
   glEnableVertexAttribArray(0);
   glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, (const void *)0);
   glDrawArrays(GL_TRIANGLES, 0, 3);
   glFinish();

   memset(px, 0, sizeof(px));
   glReadPixels(0, 0, 64, 64, GL_RGBA, GL_UNSIGNED_BYTE, px);

   for (i = 0; i < 64 * 64; i++) {
      GLubyte r = px[i * 4 + 0], g = px[i * 4 + 1], b = px[i * 4 + 2];
      if (g > 200 && r < 80 && b < 80) greenish++;
      else if (r > 200 && g < 80 && b < 80) background++;
   }
   printf("  green(triangle) pixels = %d, red(clear) pixels = %d\n",
          greenish, background);
   CHECK(greenish > 0, "triangle rendered (%d green px)", greenish);
   CHECK(background > 0, "clear colour retained (%d red px)", background);

   eglSwapBuffers(dpy, surf);
   eglTerminate(dpy);

   printf("\n=== %s: %d failure(s) ===\n",
          failures == 0 ? "test_mesa: ALL PASS" : "test_mesa: FAILED", failures);
   return failures == 0 ? 0 : 1;
}
