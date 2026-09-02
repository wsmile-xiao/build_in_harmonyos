/*
 * OHOS-specific adaptation test for Mesa 24.3.4.
 *
 * Verifies two real OHOS platform adaptations:
 *   1. util_get_process_name() returns the real process basename on OHOS,
 *      which has neither program_invocation_name nor getprogname(). Mesa
 *      upstream returns "" here (u_process.c GET_PROGRAM_NAME_NOT_AVAILABLE
 *      fallback); the OHOS port reads /proc/self/exe instead.
 *   2. A software (softpipe) off-screen render through the Gallium pipe
 *      loader produces a non-background framebuffer, proving Mesa's
 *      software GL stack actually works on HarmonyOS PC without a GPU
 *      window system (platforms = none).
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "util/u_process.h"
#include "util/u_memory.h"
#include "util/u_draw_quad.h"
#include "util/u_simple_shaders.h"
#include "util/u_sampler.h"
#include "util/u_surface.h"
#include "util/format/u_format.h"
#include "util/u_inlines.h"
#include "cso_cache/cso_context.h"
#include "pipe/p_context.h"
#include "pipe/p_state.h"
#include "pipe/p_screen.h"
#include "pipe/p_defines.h"
#include "pipe/p_shader_tokens.h"
#include "pipe-loader/pipe_loader.h"

#define OHOS_TEST_W 64
#define OHOS_TEST_H 64

int
main(void)
{
   int failures = 0;
   setvbuf(stdout, NULL, _IONBF, 0);

   /* --- Part 1: process name (OHOS /proc/self/exe fix) --- */
   const char *pn = util_get_process_name();
   printf("[OHOS] util_get_process_name() = '%s'\n", pn ? pn : "(null)");
   if (pn == NULL || pn[0] == '\0') {
      fprintf(stderr, "FAIL: process name is empty on OHOS\n");
      failures++;
   } else if (strstr(pn, "ohos_adapt_test") == NULL) {
      fprintf(stderr, "FAIL: process name '%s' is not the test binary\n", pn);
      failures++;
   } else {
      printf("[OHOS] PASS: process name matches binary basename\n");
   }

   /* --- Part 2: softpipe off-screen render --- */
   struct pipe_loader_device *dev = NULL;
   int ndev = pipe_loader_probe(&dev, 1, false);
   if (ndev <= 0) {
      fprintf(stderr, "FAIL: pipe_loader_probe found no software device\n");
      return failures + 1;
   }
   struct pipe_screen *screen = pipe_loader_create_screen(dev, false);
   if (!screen) {
      fprintf(stderr, "FAIL: pipe_loader_create_screen returned NULL\n");
      pipe_loader_release(&dev, 1);
      return failures + 1;
   }
   printf("[OHOS] screen driver = %s\n", screen->get_name(screen));
   struct pipe_context *ctx = screen->context_create(screen, NULL, 0);
   if (!ctx) {
      fprintf(stderr, "FAIL: context_create returned NULL\n");
      screen->destroy(screen);
      pipe_loader_release(&dev, 1);
      return failures + 1;
   }
   printf("[OHOS] context created\n");

   struct cso_context *cso = cso_create_context(ctx, 0);
   assert(cso);
   printf("[OHOS] cso created\n");

   /* Off-screen render target: 64x64 R8G8B8A8_UNORM */
   struct pipe_resource t_tmplt;
   memset(&t_tmplt, 0, sizeof(t_tmplt));
   t_tmplt.target = PIPE_TEXTURE_2D;
   t_tmplt.format = PIPE_FORMAT_R8G8B8A8_UNORM;
   t_tmplt.width0 = OHOS_TEST_W;
   t_tmplt.height0 = OHOS_TEST_H;
   t_tmplt.depth0 = 1;
   t_tmplt.array_size = 1;
   t_tmplt.last_level = 0;
   t_tmplt.bind = PIPE_BIND_RENDER_TARGET;
   struct pipe_resource *target = screen->resource_create(screen, &t_tmplt);
   assert(target);
   printf("[OHOS] render target created\n");

   struct pipe_surface surf_tmpl;
   memset(&surf_tmpl, 0, sizeof(surf_tmpl));
   surf_tmpl.format = target->format;
   surf_tmpl.width = OHOS_TEST_W;
   surf_tmpl.height = OHOS_TEST_H;
   surf_tmpl.texture = target;
   struct pipe_surface *surf = ctx->create_surface(ctx, target, &surf_tmpl);
   printf("[OHOS] surface created\n");

   /* clear to a known color */
   struct pipe_framebuffer_state fb;
   memset(&fb, 0, sizeof(fb));
   fb.width = OHOS_TEST_W;
   fb.height = OHOS_TEST_H;
   fb.nr_cbufs = 1;
   fb.cbufs[0] = surf;
   ctx->set_framebuffer_state(ctx, &fb);
   printf("[OHOS] framebuffer set\n");

   struct pipe_transfer *t;
   struct pipe_box box;
   memset(&box, 0, sizeof(box));
   box.width = OHOS_TEST_W;
   box.height = OHOS_TEST_H;
   box.depth = 1;

   /* Render a full-screen quad via the passthrough shaders. */
   union pipe_color_union clear_color;
   clear_color.f[0] = 0.0f;
   clear_color.f[1] = 0.0f;
   clear_color.f[2] = 0.0f;
   clear_color.f[3] = 1.0f;
   ctx->clear(ctx, PIPE_CLEAR_COLOR, NULL, &clear_color, 0, 0);
   printf("[OHOS] clear done\n");
   {
      const enum tgsi_semantic semantic_names[] =
         { TGSI_SEMANTIC_POSITION, TGSI_SEMANTIC_COLOR };
      const uint semantic_indexes[] = { 0, 0 };
      void *vs = util_make_vertex_passthrough_shader(ctx, 2, semantic_names,
                                                     semantic_indexes, false);
      void *fs = util_make_fragment_passthrough_shader(ctx, TGSI_SEMANTIC_COLOR,
                                                       TGSI_INTERPOLATE_PERSPECTIVE, true);
      assert(fs && vs);
      cso_set_fragment_shader_handle(cso, fs);
      cso_set_vertex_shader_handle(cso, vs);
   }
   printf("[OHOS] shaders set\n");

   struct cso_velems_state velem;
   memset(&velem, 0, sizeof(velem));
   velem.count = 2;
   velem.velems[0].src_offset = 0;
   velem.velems[0].vertex_buffer_index = 0;
   velem.velems[0].src_format = PIPE_FORMAT_R32G32B32A32_FLOAT;
   velem.velems[0].src_stride = 2 * 4 * sizeof(float);
   velem.velems[1].src_offset = 1 * 4 * sizeof(float);
   velem.velems[1].vertex_buffer_index = 0;
   velem.velems[1].src_format = PIPE_FORMAT_R32G32B32A32_FLOAT;
   velem.velems[1].src_stride = 2 * 4 * sizeof(float);
   cso_set_vertex_elements(cso, &velem);
   printf("[OHOS] velem set\n");

   /* Minimal fixed-function-ish state that softpipe expects before a draw. */
   struct pipe_blend_state blend;
   memset(&blend, 0, sizeof(blend));
   blend.rt[0].colormask = PIPE_MASK_RGBA;
   cso_set_blend(cso, &blend);
   struct pipe_depth_stencil_alpha_state dsa;
   memset(&dsa, 0, sizeof(dsa));
   cso_set_depth_stencil_alpha(cso, &dsa);
   struct pipe_rasterizer_state rasterizer;
   memset(&rasterizer, 0, sizeof(rasterizer));
   cso_set_rasterizer(cso, &rasterizer);
   struct pipe_viewport_state viewport;
   viewport.scale[0] = OHOS_TEST_W / 2.0f;
   viewport.scale[1] = OHOS_TEST_H / 2.0f;
   viewport.scale[2] = 1.0f;
   viewport.translate[0] = OHOS_TEST_W / 2.0f;
   viewport.translate[1] = OHOS_TEST_H / 2.0f;
   viewport.translate[2] = 0.0f;
   cso_set_viewport(cso, &viewport);
   printf("[OHOS] state set\n");

   float verts[3][2][4] = {
      { { -1.0f, -1.0f, 0.0f, 1.0f }, { 1.0f, 0.0f, 0.0f, 1.0f } },
      { {  3.0f, -1.0f, 0.0f, 1.0f }, { 0.0f, 1.0f, 0.0f, 1.0f } },
      { { -1.0f,  3.0f, 0.0f, 1.0f }, { 0.0f, 0.0f, 1.0f, 1.0f } },
   };
   struct pipe_resource *vbuf = pipe_buffer_create(screen, PIPE_BIND_VERTEX_BUFFER,
                                                   PIPE_USAGE_DEFAULT, sizeof(verts));
   pipe_buffer_write(ctx, vbuf, 0, sizeof(verts), verts);
   util_draw_vertex_buffer(ctx, cso, vbuf, 0, false,
                           MESA_PRIM_TRIANGLES, 3, 2);
   ctx->flush(ctx, NULL, 0);

   /* Read the rendered pixels back. */
   uint8_t *ptr = ctx->texture_map(ctx, target, 0, PIPE_MAP_READ, &box, &t);
   if (!ptr) {
      fprintf(stderr, "FAIL: texture_map (readback) returned NULL\n");
      failures++;
   } else {
      int colored = 0;
      for (int y = 0; y < OHOS_TEST_H; y++) {
         for (int x = 0; x < OHOS_TEST_W; x++) {
            uint8_t *px = &ptr[y * t->stride + x * 4];
            if (px[0] != 0 || px[1] != 0 || px[2] != 0)
               colored++;
         }
      }
      ctx->texture_unmap(ctx, t);
      printf("[OHOS] non-background pixels: %d/%d\n", colored,
             OHOS_TEST_W * OHOS_TEST_H);
      if (colored == 0) {
         fprintf(stderr, "FAIL: softpipe render produced an empty (black) framebuffer\n");
         failures++;
      } else {
         printf("[OHOS] PASS: softpipe off-screen render produced visible output\n");
      }
   }

   pipe_resource_reference(&vbuf, NULL);
   pipe_resource_reference(&target, NULL);
   cso_destroy_context(cso);
   ctx->destroy(ctx);
   screen->destroy(screen);
   pipe_loader_release(&dev, 1);

   if (failures == 0)
      printf("OHOS_ADAPT_TEST: ALL PASS\n");
   else
      printf("OHOS_ADAPT_TEST: %d FAILURE(S)\n", failures);
   return failures;
}
