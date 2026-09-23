/* Behavioural contract test for the pure rectangle algebra exported by
 * libmarco-private.so (marco 1.26.2, MATE window manager).
 *
 * These are the plain integer geometry helpers from src/core/boxes.c.  They
 * take no GLib object and open no X connection, so they run fully on a
 * headless HarmonyOS worker.
 *
 * marco installs only a small subset of its private headers, therefore this
 * consumer declares the prototypes it uses itself instead of pulling in a
 * marco private header (which would drag in <gtk/gtk.h>).
 *
 * Every assertion is counted; the program prints "assertions=N failures=M"
 * and exits non-zero as soon as any assertion failed.
 */

#include <stdio.h>

typedef struct _MetaRectangle MetaRectangle;
struct _MetaRectangle
{
  int x;
  int y;
  int width;
  int height;
};

/* gboolean is an int in GLib; int keeps the ABI identical. */
extern int  meta_rectangle_area              (const MetaRectangle *rect);
extern int  meta_rectangle_intersect         (const MetaRectangle *src1,
                                              const MetaRectangle *src2,
                                              MetaRectangle       *dest);
extern int  meta_rectangle_equal             (const MetaRectangle *src1,
                                              const MetaRectangle *src2);
extern void meta_rectangle_union             (const MetaRectangle *rect1,
                                              const MetaRectangle *rect2,
                                              MetaRectangle       *dest);
extern int  meta_rectangle_overlap           (const MetaRectangle *rect1,
                                              const MetaRectangle *rect2);
extern int  meta_rectangle_vert_overlap      (const MetaRectangle *rect1,
                                              const MetaRectangle *rect2);
extern int  meta_rectangle_horiz_overlap     (const MetaRectangle *rect1,
                                              const MetaRectangle *rect2);
extern int  meta_rectangle_could_fit_rect    (const MetaRectangle *outer_rect,
                                              const MetaRectangle *inner_rect);
extern int  meta_rectangle_contains_rect     (const MetaRectangle *outer_rect,
                                              const MetaRectangle *inner_rect);
extern void meta_rectangle_resize_with_gravity (const MetaRectangle *old_rect,
                                                MetaRectangle       *rect,
                                                int                  gravity,
                                                int                  new_width,
                                                int                  new_height);
extern MetaRectangle meta_rect               (int x, int y, int width, int height);

/* X11 gravity constants (X11/X.h) -- kept local so no X11 header is needed. */
#define GRAV_NORTH_WEST 1
#define GRAV_CENTER     5
#define GRAV_EAST       6
#define GRAV_SOUTH_EAST 9
#define GRAV_STATIC     10

static int total = 0;
static int failed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        total++;                                                             \
        if (!(cond)) {                                                       \
            failed++;                                                        \
            fprintf (stderr,                                                 \
                     "geometry_contract: FAIL line %d: %s\n",                \
                     __LINE__, #cond);                                       \
        }                                                                    \
    } while (0)

static int
rect_is (const MetaRectangle *r, int x, int y, int w, int h)
{
  return r->x == x && r->y == y && r->width == w && r->height == h;
}

int
main (void)
{
  MetaRectangle a  = { 0, 0, 10, 10 };
  MetaRectangle b  = { 5, 5, 10, 10 };
  MetaRectangle c  = { 20, 20, 5, 5 };
  MetaRectangle c2 = { 3, 3, 10, 10 };
  MetaRectangle d  = { 2, 2, 4, 4 };
  MetaRectangle e  = { 0, 0, 10, 10 };
  MetaRectangle e2 = { 0, 0, 10, 9 };
  MetaRectangle f  = { 100, 100, 10, 10 };
  MetaRectangle g2 = { 0, 0, 11, 10 };
  MetaRectangle g3 = { 10, 10, 1, 1 };
  MetaRectangle zero  = { 0, 0, 0, 0 };
  MetaRectangle zeroh = { 3, 3, 0, 7 };
  MetaRectangle neg   = { -3, -3, 3, 3 };
  MetaRectangle big   = { 0, 0, 46340, 46340 };   /* largest int-safe square */
  MetaRectangle tall  = { 0, 0, 1, 2000000 };
  MetaRectangle t1 = { 0, 0, 5, 5 };
  MetaRectangle t2 = { 5, 0, 5, 5 };
  MetaRectangle v1 = { 0, 0, 10, 10 };
  MetaRectangle v2 = { 50, 10, 10, 10 };
  MetaRectangle hy = { 5, 50, 10, 10 };
  MetaRectangle old = { 10, 10, 20, 20 };
  MetaRectangle out;
  MetaRectangle ab, bc, l, rr, res, tmp;

  /* --- area ------------------------------------------------------------- */
  CHECK (meta_rectangle_area (&a)     == 100);
  CHECK (meta_rectangle_area (&d)     == 16);
  CHECK (meta_rectangle_area (&zeroh) == 0);
  CHECK (meta_rectangle_area (&zero)  == 0);
  CHECK (meta_rectangle_area (&neg)   == 9);
  CHECK (meta_rectangle_area (&big)   == 2147395600);   /* no int overflow */
  CHECK (meta_rectangle_area (&tall)  == 2000000);

  /* --- meta_rect -------------------------------------------------------- */
  res = meta_rect (3, 4, 5, 6);
  CHECK (rect_is (&res, 3, 4, 5, 6));

  /* --- intersect -------------------------------------------------------- */
  CHECK (meta_rectangle_intersect (&a, &b, &out) == 1);
  CHECK (rect_is (&out, 5, 5, 5, 5));
  CHECK (meta_rectangle_area (&out) == 25);
  CHECK (meta_rectangle_intersect (&a, &c, &out) == 0);         /* disjoint */
  CHECK (out.width == 0 && out.height == 0);
  CHECK (meta_rectangle_intersect (&t1, &t2, &out) == 0);       /* touching */
  CHECK (meta_rectangle_intersect (&a, &d, &out) == 1);         /* contained */
  CHECK (rect_is (&out, 2, 2, 4, 4));
  CHECK (meta_rectangle_intersect (&b, &a, &out) == 1);         /* symmetric */
  CHECK (rect_is (&out, 5, 5, 5, 5));
  CHECK (meta_rectangle_intersect (&a, &zero, &out) == 0);      /* zero-area */
  /* associativity: (a n b) n c2 == a n (b n c2) */
  meta_rectangle_intersect (&a, &b, &ab);
  meta_rectangle_intersect (&ab, &c2, &l);
  meta_rectangle_intersect (&b, &c2, &bc);
  meta_rectangle_intersect (&a, &bc, &rr);
  CHECK (l.width > 0 && meta_rectangle_equal (&l, &rr));

  /* --- equal ------------------------------------------------------------ */
  CHECK (meta_rectangle_equal (&a, &e)  == 1);
  CHECK (meta_rectangle_equal (&a, &a)  == 1);
  CHECK (meta_rectangle_equal (&a, &b)  == 0);
  CHECK (meta_rectangle_equal (&a, &e2) == 0);

  /* --- union ------------------------------------------------------------ */
  meta_rectangle_union (&a, &b, &out);
  CHECK (rect_is (&out, 0, 0, 15, 15));
  meta_rectangle_union (&a, &c, &out);
  CHECK (rect_is (&out, 0, 0, 25, 25));
  meta_rectangle_union (&a, &d, &out);
  CHECK (rect_is (&out, 0, 0, 10, 10));              /* d contained in a */
  meta_rectangle_union (&b, &a, &out);
  CHECK (rect_is (&out, 0, 0, 15, 15));              /* symmetric */
  meta_rectangle_union (&a, &f, &out);
  CHECK (rect_is (&out, 0, 0, 110, 110));            /* disjoint bounding box */
  /* associativity: (a u b) u c2 == a u (b u c2) */
  meta_rectangle_union (&a, &b, &ab);
  meta_rectangle_union (&ab, &c2, &l);
  meta_rectangle_union (&b, &c2, &bc);
  meta_rectangle_union (&a, &bc, &rr);
  CHECK (meta_rectangle_equal (&l, &rr));

  /* --- overlap ---------------------------------------------------------- */
  CHECK (meta_rectangle_overlap (&a, &b)  == 1);
  CHECK (meta_rectangle_overlap (&a, &c)  == 0);
  CHECK (meta_rectangle_overlap (&a, &d)  == 1);
  CHECK (meta_rectangle_overlap (&t1, &t2) == 0);    /* adjacent, no overlap */
  CHECK (meta_rectangle_overlap (&a, &a)  == 1);
  CHECK (meta_rectangle_overlap (&a, &f)  == 0);

  /* --- vert_overlap / horiz_overlap ------------------------------------- */
  CHECK (meta_rectangle_vert_overlap (&a, &b)  == 1);
  CHECK (meta_rectangle_vert_overlap (&a, &c)  == 0);
  CHECK (meta_rectangle_vert_overlap (&v1, &v2) == 0);   /* y touch at 10 */
  CHECK (meta_rectangle_vert_overlap (&a, &a)  == 1);
  CHECK (meta_rectangle_horiz_overlap (&a, &b)  == 1);
  CHECK (meta_rectangle_horiz_overlap (&t1, &t2) == 0);  /* x touch at 5 */
  CHECK (meta_rectangle_horiz_overlap (&a, &f)  == 0);
  CHECK (meta_rectangle_horiz_overlap (&a, &hy) == 1);   /* x overlap, y apart */
  CHECK (meta_rectangle_vert_overlap (&a, &hy)  == 0);   /* y apart */

  /* --- contains_rect ---------------------------------------------------- */
  CHECK (meta_rectangle_contains_rect (&a, &d)  == 1);
  CHECK (meta_rectangle_contains_rect (&a, &a)  == 1);   /* inclusive edges */
  CHECK (meta_rectangle_contains_rect (&d, &a)  == 0);
  CHECK (meta_rectangle_contains_rect (&a, &b)  == 0);   /* b overflows a */
  CHECK (meta_rectangle_contains_rect (&a, &e)  == 1);
  CHECK (meta_rectangle_contains_rect (&a, &g2) == 0);   /* 11 > 10 wide */
  CHECK (meta_rectangle_contains_rect (&a, &g3) == 0);   /* 11 > 10 right */

  /* --- could_fit_rect --------------------------------------------------- */
  CHECK (meta_rectangle_could_fit_rect (&a, &d) == 1);
  CHECK (meta_rectangle_could_fit_rect (&d, &a) == 0);
  CHECK (meta_rectangle_could_fit_rect (&a, &b) == 1);   /* size only */

  /* --- resize_with_gravity ---------------------------------------------- */
  meta_rectangle_resize_with_gravity (&old, &tmp, GRAV_NORTH_WEST, 30, 30);
  CHECK (rect_is (&tmp, 10, 10, 30, 30));
  meta_rectangle_resize_with_gravity (&old, &tmp, GRAV_EAST, 30, 30);
  CHECK (rect_is (&tmp, 0, 5, 30, 30));
  meta_rectangle_resize_with_gravity (&old, &tmp, GRAV_CENTER, 30, 30);
  CHECK (rect_is (&tmp, 5, 5, 30, 30));
  meta_rectangle_resize_with_gravity (&old, &tmp, GRAV_SOUTH_EAST, 30, 30);
  CHECK (rect_is (&tmp, 0, 0, 30, 30));
  meta_rectangle_resize_with_gravity (&old, &tmp, GRAV_STATIC, 30, 30);
  CHECK (rect_is (&tmp, 10, 10, 30, 30));

  fprintf (stdout, "geometry_contract: assertions=%d failures=%d\n",
           total, failed);
  return failed == 0 ? 0 : 1;
}
