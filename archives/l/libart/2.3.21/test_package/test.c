/* Consumer test for libart 2.3.21 (libart_lgpl).
 *
 * Verifies, from the installed package (headers under
 * include/libart-2.0/libart_lgpl, lib libart_lgpl_2):
 *  1. exported version constants match 2.3.21
 *  2. affine matrix math: identity, invert, point transform round-trip
 *  3. vpath -> SVP conversion (the rasterization prep path)
 */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <libart_lgpl/libart-features.h>
#include <libart_lgpl/art_affine.h>
#include <libart_lgpl/art_vpath.h>
#include <libart_lgpl/art_svp_vpath.h>
#include <libart_lgpl/art_svp.h>

static int failures = 0;

#define CHECK(cond, msg)                                                \
    do {                                                                \
        if (cond) {                                                     \
            printf ("ok - %s\n", msg);                                  \
        } else {                                                        \
            printf ("not ok - %s\n", msg);                              \
            failures++;                                                 \
        }                                                               \
    } while (0)

int main (void)
{
    /* 1. version constants exported by the library */
    CHECK (libart_major_version == 2, "major version is 2");
    CHECK (libart_minor_version == 3, "minor version is 3");
    CHECK (libart_micro_version == 21, "micro version is 21");
    CHECK (strcmp (libart_version, "2.3.21") == 0, "version string is 2.3.21");

    /* 2. affine: identity, translate, invert, point round-trip */
    double affine[6], inv[6];
    art_affine_identity (affine);
    CHECK (art_affine_rectilinear (affine), "identity is rectilinear");

    art_affine_translate (affine, 3.0, -4.0);
    art_affine_invert (inv, affine);

    ArtPoint src = { 1.5, 2.5 };
    ArtPoint dst, roundtrip;
    art_affine_point (&dst, &src, affine);
    CHECK (dst.x == 4.5 && dst.y == -1.5, "translate moves the point");

    art_affine_point (&roundtrip, &dst, inv);
    CHECK (fabs (roundtrip.x - src.x) < 1e-12 && fabs (roundtrip.y - src.y) < 1e-12,
           "invert undoes the translation");

    /* rotation + expansion */
    art_affine_rotate (affine, 90.0);
    CHECK (fabs (art_affine_expansion (affine) - 1.0) < 1e-12,
           "90-degree rotation preserves expansion");

    /* 3. vpath -> SVP (segments split on direction reversal) */
    ArtVpath vpath[4];
    vpath[0].code = ART_MOVETO; vpath[0].x = 0.0;  vpath[0].y = 0.0;
    vpath[1].code = ART_LINETO; vpath[1].x = 10.0; vpath[1].y = 0.0;
    vpath[2].code = ART_LINETO; vpath[2].x = 10.0; vpath[2].y = 10.0;
    vpath[3].code = ART_END;

    ArtSVP *svp = art_svp_from_vpath (vpath);
    CHECK (svp != NULL && svp->n_segs >= 1, "monotone vpath converts to an SVP");
    art_svp_free (svp);

    /* direction reversal (up then down) must split into 2 segments */
    ArtVpath vpath2[5];
    vpath2[0].code = ART_MOVETO; vpath2[0].x = 0.0;  vpath2[0].y = 0.0;
    vpath2[1].code = ART_LINETO; vpath2[1].x = 0.0;  vpath2[1].y = 10.0;
    vpath2[2].code = ART_LINETO; vpath2[2].x = 5.0;  vpath2[2].y = 5.0;
    vpath2[3].code = ART_LINETO; vpath2[3].x = 5.0;  vpath2[3].y = 0.0;
    vpath2[4].code = ART_END;

    ArtSVP *svp2 = art_svp_from_vpath (vpath2);
    CHECK (svp2 != NULL && svp2->n_segs == 2, "direction reversal splits SVP into 2 segments");
    art_svp_free (svp2);

    if (failures == 0)
        printf ("All tests passed\n");
    else
        printf ("%d test(s) FAILED\n", failures);
    return failures == 0 ? 0 : 1;
}
