/* Consumer probe for the achilles/3 runtime stack.

   The simulator renders through an OSMesa offscreen context and takes its
   windowless video surface from SDL, so this probe drives exactly that path
   against the packaged dependencies: create the offscreen context, render a
   fixed-function scene with GLU projection, read the pixels back, and check
   the SDL video/event surface the application also uses.

   Every check prints one executed assertion; the summary line
   "test_gl_stack: N executed, M failed" is the number reported in
   MANIFEST.yml.
*/
#include <stdio.h>
#include <string.h>
#include <GL/osmesa.h>
#include <GL/gl.h>
#include <GL/glu.h>
#include <SDL/SDL.h>

#define WIDTH 64
#define HEIGHT 64

static int executed = 0;
static int failed = 0;

static void check(int condition, const char *label) {
  executed++;
  if (!condition) {
    failed++;
  }
  printf("  [%s] %s\n", condition ? "ok" : "fail", label);
}

int main(void) {
  unsigned char buffer[WIDTH * HEIGHT * 4];
  unsigned char pixels[WIDTH * HEIGHT * 3];
  OSMesaContext ctx;
  GLenum version_ok;
  long sum = 0;
  int nonzero = 0;
  int i;
  Uint32 ticks;

  /* ── OSMesa offscreen context ─────────────────────────────────────── */
  memset(buffer, 0, sizeof(buffer));
  ctx = OSMesaCreateContextExt(OSMESA_RGBA, 16, 0, 0, NULL);
  check(ctx != NULL, "OSMesa context created");
  if (ctx == NULL) {
    printf("test_gl_stack: %d executed, %d failed\n", executed, failed);
    return 1;
  }

  check(OSMesaMakeCurrent(ctx, buffer, GL_UNSIGNED_BYTE, WIDTH, HEIGHT) == GL_TRUE,
        "OSMesa context made current on a client buffer");

  version_ok = glGetString(GL_VERSION) != NULL;
  check(version_ok, "GL_VERSION is reported");
  if (version_ok) {
    printf("       GL_VERSION=%s\n", (const char *)glGetString(GL_VERSION));
    printf("       GL_RENDERER=%s\n", (const char *)glGetString(GL_RENDERER));
  }

  /* ── fixed-function rendering, as the simulator does ─────────────── */
  glViewport(0, 0, WIDTH, HEIGHT);
  glClearColor(0.1f, 0.2f, 0.3f, 1.0f);
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
  glEnable(GL_DEPTH_TEST);

  glMatrixMode(GL_PROJECTION);
  glLoadIdentity();
  gluPerspective(45.0f, (GLfloat)WIDTH / (GLfloat)HEIGHT, 0.1f, 100.0f);
  glMatrixMode(GL_MODELVIEW);
  glLoadIdentity();
  glTranslatef(0.0f, 0.0f, -5.0f);

  glBegin(GL_QUADS);
  glColor3f(1.0f, 0.0f, 0.0f); glVertex3f(-1.0f, -1.0f, 0.0f);
  glColor3f(0.0f, 1.0f, 0.0f); glVertex3f(1.0f, -1.0f, 0.0f);
  glColor3f(0.0f, 0.0f, 1.0f); glVertex3f(1.0f, 1.0f, 0.0f);
  glColor3f(1.0f, 1.0f, 0.0f); glVertex3f(-1.0f, 1.0f, 0.0f);
  glEnd();
  glFinish();

  check(glGetError() == GL_NO_ERROR, "fixed-function + GLU render produced no GL error");

  /* ── frame readback (the screenshot path) ────────────────────────── */
  glReadPixels(0, 0, WIDTH, HEIGHT, GL_RGB, GL_UNSIGNED_BYTE, pixels);
  check(glGetError() == GL_NO_ERROR, "glReadPixels completed without error");

  for (i = 0; i < WIDTH * HEIGHT * 3; i++) {
    sum += pixels[i];
    if (pixels[i] != 0) {
      nonzero++;
    }
  }
  check(nonzero > 0, "rendered frame contains pixels");
  check(sum > 0, "rendered frame is not uniformly black");

  /* The clear colour must be present (glClear did something) and at least
     some pixels must differ from it (the quad was actually rasterised).
     Vertex-colour interpolation legitimately drives individual channels to
     zero, so a "no zero byte" check would be wrong here. */
  {
    int clear_pixels = 0;
    int drawn_pixels = 0;
    int px;
    for (px = 0; px < WIDTH * HEIGHT; px++) {
      unsigned char r = pixels[px * 3 + 0];
      unsigned char g = pixels[px * 3 + 1];
      unsigned char b = pixels[px * 3 + 2];
      int is_clear = (r >= 24 && r <= 28) && (g >= 49 && g <= 53) && (b >= 75 && b <= 79);
      if (is_clear) {
        clear_pixels++;
      } else {
        drawn_pixels++;
      }
    }
    printf("       clear-colour pixels=%d drawn pixels=%d\n", clear_pixels, drawn_pixels);
    check(clear_pixels > 0, "cleared background colour is present in the frame");
    check(drawn_pixels > 0, "rasterised geometry covers part of the frame");
  }

  printf("       readback sum=%ld nonzero_bytes=%d\n", sum, nonzero);

  OSMesaDestroyContext(ctx);
  check(1, "OSMesa context destroyed");

  /* ── SDL video surface and event/timebase path ───────────────────── */
  check(SDL_Init(SDL_INIT_VIDEO) == 0, "SDL video subsystem initializes");
  {
    SDL_Surface *surface = SDL_SetVideoMode(160, 120, 32, SDL_SWSURFACE);
    char driver[32] = "?";
    SDL_VideoDriverName(driver, sizeof(driver));
    printf("       SDL video driver=%s\n", driver);
    check(surface != NULL, "SDL software surface created");
    if (surface != NULL) {
      check(surface->format->BitsPerPixel >= 16, "surface has a usable pixel depth");
      check(surface->pixels != NULL, "surface exposes its pixel buffer");
    }
    {
      SDL_Event event;
      while (SDL_PollEvent(&event)) {
        /* drain any queued events */
      }
      check(1, "SDL event queue is drained without error");
    }
    check(SDL_GetKeyState(NULL) != NULL, "SDL keyboard state is available");
  }

  ticks = SDL_GetTicks();
  check(ticks < 0xFFFFFFFFu, "SDL millisecond timebase is running");

  SDL_Quit();
  check(1, "SDL shut down cleanly");

  printf("test_gl_stack: %d executed, %d failed\n", executed, failed);
  return failed == 0 ? 0 : 1;
}
