/*
 * test_package consumer test for mesa 24.3.4.1.1 (HarmonyOS PC).
 *
 * This test links against the packaged libOSMesa and exercises the desktop
 * OpenGL fixed-function entry points needed by Coin3. It also verifies that
 * the software renderer produces non-background pixels in an off-screen
 * framebuffer.
 */
#include <stdio.h>
#include <stdlib.h>

#include <GL/gl.h>
#include <GL/osmesa.h>

int
main(void)
{
   const int width = 64;
   const int height = 64;
   const size_t pixel_count = (size_t)width * (size_t)height;
   unsigned char *pixels = calloc(pixel_count, 4);
   if (!pixels) {
      fprintf(stderr, "FAIL: framebuffer allocation\n");
      return 1;
   }

   OSMesaContext context = OSMesaCreateContextExt(
      OSMESA_RGBA, 24, 8, 0, NULL);
   if (!context) {
      fprintf(stderr, "FAIL: OSMesaCreateContextExt\n");
      free(pixels);
      return 1;
   }

   if (!OSMesaMakeCurrent(context, pixels, GL_UNSIGNED_BYTE, width, height)) {
      fprintf(stderr, "FAIL: OSMesaMakeCurrent\n");
      OSMesaDestroyContext(context);
      free(pixels);
      return 1;
   }

   glViewport(0, 0, width, height);
   glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
   glClear(GL_COLOR_BUFFER_BIT);

   /* Exercise desktop fixed-function symbols absent from OHOS GLES. */
   glMatrixMode(GL_MODELVIEW);
   glPushMatrix();
   glLoadIdentity();
   glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);
   glBegin(GL_TRIANGLES);
   glColor3f(1.0f, 0.0f, 0.0f);
   glVertex2f(-0.75f, -0.75f);
   glColor3f(0.0f, 1.0f, 0.0f);
   glVertex2f(0.75f, -0.75f);
   glColor3f(0.0f, 0.0f, 1.0f);
   glVertex2f(0.0f, 0.75f);
   glEnd();
   glPopMatrix();
   glFinish();

   int colored_pixels = 0;
   for (size_t i = 0; i < pixel_count; i++) {
      const unsigned char *pixel = pixels + i * 4;
      if (pixel[0] != 0 || pixel[1] != 0 || pixel[2] != 0) {
         colored_pixels++;
      }
   }

   const GLubyte *version = glGetString(GL_VERSION);
   printf("OSMesa GL_VERSION: %s\n",
          version ? (const char *)version : "(null)");
   printf("colored pixels: %d\n", colored_pixels);

   OSMesaDestroyContext(context);
   free(pixels);

   if (!version || colored_pixels == 0) {
      fprintf(stderr, "FAIL: OSMesa fixed-function render produced no output\n");
      return 1;
   }
   printf("test_mesa: ALL PASS\n");
   return 0;
}
