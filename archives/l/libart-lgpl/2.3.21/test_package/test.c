/*
 * libart-lgpl consumer test.
 *
 * Links against the installed libart_lgpl_2 library and public headers only,
 * and exercises the API that applications use: affine transforms, vpath
 * construction, SVP flattening/intersection, the low level RGB helpers and
 * the modular anti-aliased renderer.
 *
 * Every check prints a line; the process exits non-zero if any check failed.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libart_lgpl/art_affine.h>
#include <libart_lgpl/art_misc.h>
#include <libart_lgpl/art_render.h>
#include <libart_lgpl/art_render_svp.h>
#include <libart_lgpl/art_rgb.h>
#include <libart_lgpl/art_svp.h>
#include <libart_lgpl/art_svp_intersect.h>
#include <libart_lgpl/art_svp_vpath.h>
#include <libart_lgpl/art_vpath.h>

#define CHECK(condition, message)                                        \
    do {                                                                 \
        if (condition) {                                                 \
            printf("  ok   %s\n", message);                              \
        } else {                                                         \
            printf("  FAIL %s\n", message);                              \
            failures++;                                                  \
        }                                                                \
    } while (0)

#define NEAR(a, b) (fabs((a) - (b)) < 1e-9)

int main(void)
{
    int failures = 0;
    int i;

    printf("libart-lgpl consumer test\n");

    /* --- affine transforms ------------------------------------------- */
    {
        double scale[6], inverse[6], roundtrip[6], identity[6];
        ArtPoint source = { 1.5, 2.5 };
        ArtPoint point;

        /* art_affine_expansion returns sqrt(|det|), here sqrt(6). */
        art_affine_scale(scale, 2.0, 3.0);
        CHECK(NEAR(art_affine_expansion(scale), sqrt(6.0)),
              "art_affine_expansion(diag(2,3)) == sqrt(6)");
        CHECK(art_affine_rectilinear(scale),
              "art_affine_rectilinear(diag(2,3)) is true");

        art_affine_point(&point, &source, scale);
        CHECK(NEAR(point.x, 3.0) && NEAR(point.y, 7.5),
              "art_affine_point maps (1.5,2.5) to (3.0,7.5)");

        art_affine_invert(inverse, scale);
        art_affine_multiply(roundtrip, inverse, scale);
        art_affine_identity(identity);
        for (i = 0; i < 6; i++) {
            if (fabs(roundtrip[i] - identity[i]) > 1e-12)
                break;
        }
        CHECK(i == 6, "inverse * matrix == identity");

        {
            double translate[6], rotate[6], composed[6];
            ArtPoint origin = { 1.0, 0.0 };
            ArtPoint moved;

            /* art_affine_rotate takes degrees; art_affine_multiply(dst, a, b)
             * applies `a` first, so rotate-then-translate is multiply(comp,
             * rotate, translate). */
            art_affine_translate(translate, 10.0, -4.0);
            art_affine_rotate(rotate, 90.0);
            art_affine_multiply(composed, rotate, translate);
            art_affine_point(&moved, &origin, composed);
            CHECK(NEAR(moved.x, 10.0) && NEAR(moved.y, -3.0),
                  "rotate 90deg then translate maps (1,0) to (10,-3)");
        }
    }

    /* --- vpath construction and bounding boxes ----------------------- */
    {
        ArtVpath *circle = art_vpath_new_circle(60.0, 60.0, 20.0);
        ArtIRect irect;
        ArtDRect drect;

        CHECK(circle != NULL, "art_vpath_new_circle returns a path");
        if (circle == NULL)
            return 1;

        art_vpath_bbox_drect(circle, &drect);
        art_vpath_bbox_irect(circle, &irect);
        CHECK(drect.x0 >= 39.5 && drect.y0 >= 39.5 &&
              drect.x1 <= 80.5 && drect.y1 <= 80.5 &&
              drect.x0 < drect.x1,
              "circle bbox stays inside the nominal [40,80] extent");
        CHECK(irect.x0 <= 40 && irect.y0 <= 40 && irect.x1 >= 80 && irect.y1 >= 80,
              "integer bbox covers the circle extremes");
        CHECK(irect.x1 - irect.x0 <= 42 && irect.y1 - irect.y0 <= 42,
              "integer bbox is tight (no runaway padding)");

        {
            const double scale3[6] = { 3.0, 0.0, 0.0, 3.0, 0.0, 0.0 };
            ArtVpath *scaled = art_vpath_affine_transform(circle, scale3);
            ArtDRect scaled_box;

            CHECK(scaled != NULL, "art_vpath_affine_transform returns a path");
            art_vpath_bbox_drect(scaled, &scaled_box);
            CHECK(NEAR(scaled_box.x1, drect.x1 * 3.0) &&
                  NEAR(scaled_box.y1, drect.y1 * 3.0),
                  "affine scaling multiplies the bbox extremes by 3");
            art_free(scaled);
        }

        /* --- SVP flattening and intersection ------------------------- */
        {
            ArtSVP *svp = art_svp_from_vpath(circle);
            ArtSvpWriter *writer;
            ArtSVP *rewound;

            CHECK(svp != NULL && svp->n_segs >= 1,
                  "art_svp_from_vpath produces segments");

            writer = art_svp_writer_rewind_new(ART_WIND_RULE_NONZERO);
            art_svp_intersector(svp, writer);
            rewound = art_svp_writer_rewind_reap(writer);
            CHECK(rewound != NULL && rewound->n_segs >= 1,
                  "art_svp_intersector rewinds the circle to >= 1 segment");

            /* --- low level RGB helpers ------------------------------- */
            {
                art_u8 run[6];
                art_u8 blend[3] = { 0, 0, 0 };

                memset(run, 0, sizeof run);
                art_rgb_fill_run(run, 10, 20, 30, 2);
                CHECK(run[0] == 10 && run[1] == 20 && run[2] == 30 &&
                      run[3] == 10 && run[4] == 20 && run[5] == 30,
                      "art_rgb_fill_run fills two identical pixels");

                art_rgb_run_alpha(blend, 100, 200, 50, 128, 1);
                CHECK(blend[0] == 50 && blend[1] == 100 && blend[2] == 25,
                      "art_rgb_run_alpha blends 50% over black");
            }

            /* --- modular anti-aliased renderer ----------------------- */
            {
                enum { WIDTH = 120, HEIGHT = 120 };
                art_u8 *pixels = (art_u8 *)malloc((size_t)WIDTH * HEIGHT * 3);
                ArtRender *render;
                ArtPixMaxDepth fill[3];
                art_u8 *center;
                art_u8 *corner;
                int partial = 0;

                CHECK(pixels != NULL, "allocate a 120x120 RGB buffer");
                if (pixels == NULL)
                    return 1;

                memset(pixels, 0x7f, (size_t)WIDTH * HEIGHT * 3);
                /* Solid image sources take pixmax values: ART_MAX_DEPTH is 16,
                 * so 8 bit channels must go through ART_PIX_MAX_FROM_8. */
                fill[0] = ART_PIX_MAX_FROM_8(255);
                fill[1] = ART_PIX_MAX_FROM_8(0);
                fill[2] = ART_PIX_MAX_FROM_8(0);

                render = art_render_new(0, 0, WIDTH, HEIGHT, pixels, WIDTH * 3,
                                        3, 8, ART_ALPHA_NONE, NULL);
                CHECK(render != NULL, "art_render_new creates a renderer");
                art_render_clear_rgb(render, 0x000000);
                art_render_svp(render, rewound);
                art_render_image_solid(render, fill);
                /* Mask opacity is fixed point in [0, 0x10000]. */
                art_render_mask_solid(render, 0x10000);
                art_render_invoke(render); /* frees the render object */

                center = pixels + ((size_t)60 * WIDTH + 60) * 3;
                corner = pixels + ((size_t)1 * WIDTH + 1) * 3;
                CHECK(center[0] == 255 && center[1] == 0 && center[2] == 0,
                      "circle interior renders opaque red");
                CHECK(corner[0] == 0 && corner[1] == 0 && corner[2] == 0,
                      "outside the circle renders the cleared black");

                for (i = 0; i < WIDTH * HEIGHT; i++) {
                    int red = pixels[i * 3];
                    if (red > 20 && red < 235)
                        partial++;
                }
                printf("  info anti-aliased partial-coverage pixels: %d\n", partial);
                CHECK(partial > 0,
                      "anti-aliased edge pixels with partial coverage exist");

                free(pixels);
            }

            art_svp_free(rewound);
            art_svp_free(svp);
        }

        art_free(circle);
    }

    printf("consumer assertions: %d failed\n", failures);
    return failures == 0 ? 0 : 1;
}
