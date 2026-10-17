/* Triangle consumer test.
 *
 * Links the installed libtriangle.a and drives the real embeddable API
 * declared in triangle.h (R34: the test must exercise the package under
 * test, not merely link it).
 *
 * triangle.h deliberately does not define REAL/VOID itself — upstream's own
 * sample driver tricall.c defines them before the include, and triangle.h's
 * prototypes are only ANSI when ANSI_DECLARATORS is set.  We do the same.
 */

#define REAL double
#define VOID void
#define ANSI_DECLARATORS

#include "triangle.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

static void check(int ok, const char *what)
{
    printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) {
        ++failures;
    }
}

int main(void)
{
    struct triangulateio in, out;
    /* Delaunay triangulation, zero-based indices, quiet (no per-run banner). */
    char switches[] = "zQ";
    int i;
    int inrange = 1;
    double area = 0.0;

    memset(&in, 0, sizeof(in));
    memset(&out, 0, sizeof(out));

    /* The four corners of the unit square. */
    in.numberofpoints = 4;
    in.pointlist = (REAL *)malloc(8 * sizeof(REAL));
    if (in.pointlist == NULL) {
        fprintf(stderr, "out of memory\n");
        return 2;
    }
    in.pointlist[0] = 0.0;
    in.pointlist[1] = 0.0;
    in.pointlist[2] = 1.0;
    in.pointlist[3] = 0.0;
    in.pointlist[4] = 1.0;
    in.pointlist[5] = 1.0;
    in.pointlist[6] = 0.0;
    in.pointlist[7] = 1.0;

    triangulate(switches, &in, &out, (struct triangulateio *)NULL);

    check(out.numberofpoints == 4, "unit square keeps its 4 input vertices");
    check(out.numberoftriangles == 2,
          "unit square triangulates into exactly 2 triangles");
    check(out.numberofcorners == 3, "triangles are linear (3 corners)");

    for (i = 0; i < out.numberoftriangles * out.numberofcorners; i++) {
        int idx = out.trianglelist[i];
        if (idx < 0 || idx >= out.numberofpoints) {
            inrange = 0;
        }
    }
    check(inrange, "every triangle corner index is within the point list");

    /* The two triangles must tile the unit square exactly. */
    for (i = 0; i < out.numberoftriangles; i++) {
        int i0 = out.trianglelist[i * out.numberofcorners + 0];
        int i1 = out.trianglelist[i * out.numberofcorners + 1];
        int i2 = out.trianglelist[i * out.numberofcorners + 2];
        double x0 = out.pointlist[2 * i0], y0 = out.pointlist[2 * i0 + 1];
        double x1 = out.pointlist[2 * i1], y1 = out.pointlist[2 * i1 + 1];
        double x2 = out.pointlist[2 * i2], y2 = out.pointlist[2 * i2 + 1];
        area += fabs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0;
    }
    check(fabs(area - 1.0) < 1e-12,
          "the two triangles together cover the unit square (area == 1)");

    /* A square's four corners are cocircular, so Delaunay is ambiguous; the
     * vertex set must nevertheless be preserved exactly. */
    check(out.numberofpoints == in.numberofpoints,
          "no vertex was added or removed");

    trifree(out.pointlist);
    trifree(out.trianglelist);
    free(in.pointlist);

    if (failures != 0) {
        fprintf(stderr, "%d triangle consumer check(s) FAILED\n", failures);
        return 1;
    }
    printf("all triangle consumer checks passed\n");
    return 0;
}
