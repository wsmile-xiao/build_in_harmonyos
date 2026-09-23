/* "No X server -> degrade, do not crash" contract for marco on HarmonyOS.
 *
 * marco is an X11 window manager: its startup path drives GDK/X11 seam
 * helpers to obtain the X display, screen and xid.  On a headless HarmonyOS
 * worker there is no DISPLAY and no Xvfb, so those helpers must stay
 * resolvable and the argument-validating ones must return a legal "empty"
 * value (NULL / None / 0) rather than crash when handed a missing display.
 *
 * The seam functions live in libgdk-3.so, a DT_NEEDED of the
 * libmarco-private.so this consumer links, so they are resolved with
 * dlsym(RTLD_DEFAULT, ...) and need no link-time GTK dependency.
 *
 * The program is anchored on the tested package by calling an exported
 * libmarco-private.so symbol (meta_rectangle_area) so the link really pulls
 * the library (and, transitively, libgdk-3) in.
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

extern int meta_rectangle_area (const MetaRectangle *rect);

typedef void          *(*fn_get_xdisplay)   (void *display);
typedef void          *(*fn_lookup_xdisplay)(void *xdisplay);
typedef void          *(*fn_window_lookup)  (void *display,
                                             unsigned long window);
typedef unsigned long  (*fn_window_get_xid) (void *window);

static int total = 0;
static int failed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        total++;                                                             \
        if (!(cond)) {                                                       \
            failed++;                                                        \
            fprintf (stderr, "no_display_guard: FAIL line %d: %s\n",        \
                     __LINE__, #cond);                                       \
        }                                                                    \
    } while (0)

int
main (void)
{
  MetaRectangle r = { 0, 0, 3, 4 };

  /* Anchor: exercise an exported libmarco-private.so symbol so the tested
   * library (and its libgdk-3 dependency) is loaded before dlsym runs. */
  CHECK (meta_rectangle_area (&r) == 12);

  /* Existence of the seam helpers marco's headless startup must be able to
   * resolve. */
  {
    void *s_xdisplay = dlsym (RTLD_DEFAULT, "gdk_x11_display_get_xdisplay");
    void *s_lookup   = dlsym (RTLD_DEFAULT, "gdk_x11_lookup_xdisplay");
    void *s_rootwin  = dlsym (RTLD_DEFAULT, "gdk_x11_get_default_root_xwindow");
    void *s_wlookup  = dlsym (RTLD_DEFAULT, "gdk_x11_window_lookup_for_display");
    void *s_wxid     = dlsym (RTLD_DEFAULT, "gdk_x11_window_get_xid");
    void *s_xscreen  = dlsym (RTLD_DEFAULT, "gdk_x11_screen_get_xscreen");
    void *s_xnumber  = dlsym (RTLD_DEFAULT, "gdk_x11_screen_get_screen_number");

    CHECK (s_xdisplay != NULL);
    CHECK (s_lookup   != NULL);
    CHECK (s_rootwin  != NULL);
    CHECK (s_wlookup  != NULL);
    CHECK (s_wxid     != NULL);
    CHECK (s_xscreen  != NULL);
    CHECK (s_xnumber  != NULL);

    /* The argument-validating helpers must degrade to NULL / None (0) when
     * handed a missing display/window instead of dereferencing it.
     * (gdk_x11_screen_get_xscreen/_get_number and
     * gdk_x11_get_default_root_xwindow are *not* argument-guarded in GDK and
     * would dereference a NULL handle, so only their existence is pinned
     * here -- calling them with NULL is not a real marco code path.) */
    if (s_xdisplay != NULL)
      CHECK (((fn_get_xdisplay) s_xdisplay) (NULL) == NULL);
    if (s_lookup != NULL)
      CHECK (((fn_lookup_xdisplay) s_lookup) (NULL) == NULL);
    if (s_wlookup != NULL)
      CHECK (((fn_window_lookup) s_wlookup) (NULL, 0) == NULL);
    if (s_wxid != NULL)
      CHECK (((fn_window_get_xid) s_wxid) (NULL) == 0);
  }

  fprintf (stdout, "no_display_guard: assertions=%d failures=%d\n",
           total, failed);
  return failed == 0 ? 0 : 1;
}
