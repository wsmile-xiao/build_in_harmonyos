/* Installed-package API surface test for libmarco-private.so (marco 1.26.2).
 *
 * Takes a live address for every geometry helper and GObject type constructor
 * exported by libmarco-private.so (the addresses are stored in a volatile
 * array so both the link-time relocation and a runtime non-NULL check are
 * forced), then drives the type constructors.
 *
 * marco does not install its private headers as a supported surface, so the
 * prototypes used here are declared locally instead of including a private
 * header (which would drag in <gtk/gtk.h>).  g_type_name() is looked up with
 * dlsym(RTLD_DEFAULT) -- libgobject is a DT_NEEDED of libmarco-private.so, so
 * the symbol is loaded with the library and no link-time glib dependency is
 * needed for this consumer.
 *
 * The type constructors only register their GType; they do not open an X
 * connection, so they are safe to call on a headless worker.
 */

#include <dlfcn.h>
#include <stdio.h>

typedef struct _MetaRectangle MetaRectangle;
struct _MetaRectangle
{
  int x;
  int y;
  int width;
  int height;
};

/* --- geometry helpers from src/core/boxes.c (installed lib exporter) ----- */
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

/* --- GObject type constructors exported by libmarco-private.so ----------- *
 * Only these four types are GObject/GTK classes in marco 1.26.2:
 *   MetaWindow       (core/window.c)       meta_window_get_type
 *   MetaPreview      (ui/preview-widget.c) meta_preview_get_type
 *   MetaAccelLabel   (ui/metaaccellabel.c) meta_accel_label_get_type
 *   MetaFrames       (ui/frames.c)         meta_frames_get_type
 * MetaDisplay/MetaScreen/MetaWorkspace/MetaCompositor/MetaPrefs/... are plain
 * C structs in marco, not GTypes, so they have no *_get_type constructor. */
extern unsigned long meta_window_get_type      (void);
extern unsigned long meta_preview_get_type     (void);
extern unsigned long meta_accel_label_get_type (void);
extern unsigned long meta_frames_get_type      (void);

typedef const char *(*g_type_name_fn) (unsigned long gtype);

#define N_SYMS 15

static int total = 0;
static int failed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        total++;                                                             \
        if (!(cond)) {                                                       \
            failed++;                                                        \
            fprintf (stderr, "api_surface: FAIL line %d: %s\n",             \
                     __LINE__, #cond);                                       \
        }                                                                    \
    } while (0)

int
main (void)
{
  /* volatile: forces a real load of each relocated symbol at runtime. */
  static volatile void *syms[N_SYMS];
  g_type_name_fn g_type_name;
  void *lookup;

  /* Strong-typed relocation of every exported geometry helper. */
  syms[0]  = (void *) &meta_rect;
  syms[1]  = (void *) &meta_rectangle_area;
  syms[2]  = (void *) &meta_rectangle_intersect;
  syms[3]  = (void *) &meta_rectangle_equal;
  syms[4]  = (void *) &meta_rectangle_union;
  syms[5]  = (void *) &meta_rectangle_overlap;
  syms[6]  = (void *) &meta_rectangle_vert_overlap;
  syms[7]  = (void *) &meta_rectangle_horiz_overlap;
  syms[8]  = (void *) &meta_rectangle_could_fit_rect;
  syms[9]  = (void *) &meta_rectangle_contains_rect;
  syms[10] = (void *) &meta_rectangle_resize_with_gravity;

  /* Strong-typed relocation of the exported GObject type constructors. */
  syms[11] = (void *) &meta_window_get_type;
  syms[12] = (void *) &meta_preview_get_type;
  syms[13] = (void *) &meta_accel_label_get_type;
  syms[14] = (void *) &meta_frames_get_type;

  CHECK (syms[0]  != NULL);
  CHECK (syms[1]  != NULL);
  CHECK (syms[2]  != NULL);
  CHECK (syms[3]  != NULL);
  CHECK (syms[4]  != NULL);
  CHECK (syms[5]  != NULL);
  CHECK (syms[6]  != NULL);
  CHECK (syms[7]  != NULL);
  CHECK (syms[8]  != NULL);
  CHECK (syms[9]  != NULL);
  CHECK (syms[10] != NULL);
  CHECK (syms[11] != NULL);
  CHECK (syms[12] != NULL);
  CHECK (syms[13] != NULL);
  CHECK (syms[14] != NULL);

  /* g_type_name comes from libgobject (DT_NEEDED of libmarco-private.so). */
  lookup = dlsym (RTLD_DEFAULT, "g_type_name");
  CHECK (lookup != NULL);
  g_type_name = (g_type_name_fn) lookup;

  /* Each constructor must register a real, named GType. */
  {
    unsigned long t = meta_window_get_type ();
    CHECK (t != 0);
    CHECK (g_type_name != NULL && g_type_name (t) != NULL &&
           g_type_name (t)[0] != '\0');
  }
  {
    unsigned long t = meta_preview_get_type ();
    CHECK (t != 0);
    CHECK (g_type_name != NULL && g_type_name (t) != NULL &&
           g_type_name (t)[0] != '\0');
  }
  {
    unsigned long t = meta_accel_label_get_type ();
    CHECK (t != 0);
    CHECK (g_type_name != NULL && g_type_name (t) != NULL &&
           g_type_name (t)[0] != '\0');
  }
  {
    unsigned long t = meta_frames_get_type ();
    CHECK (t != 0);
    CHECK (g_type_name != NULL && g_type_name (t) != NULL &&
           g_type_name (t)[0] != '\0');
  }

  fprintf (stdout, "api_surface: assertions=%d failures=%d symbols=%d\n",
           total, failed, N_SYMS);
  return failed == 0 ? 0 : 1;
}
