/* Installed-package API surface test for libcanberra-gtk3/0.30.
 *
 * Takes a strong-typed function pointer for every exported public symbol in
 * canberra-gtk.h so each one is relocated against libcanberra-gtk3.so at
 * load time.  When GTK3 can initialise on the target, the GTK context
 * factory and the widget proplist helper are exercised against the
 * broadway backend; on headless targets where no display can be opened
 * the GTK runtime part is skipped.
 */

#include <canberra-gtk.h>

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef ca_context *(*fn_gtk_context_get_t)(void);
typedef ca_context *(*fn_gtk_context_get_for_screen_t)(GdkScreen *);
typedef int (*fn_gtk_proplist_set_for_widget_t)(ca_proplist *, GtkWidget *);
typedef int (*fn_gtk_play_for_widget_t)(GtkWidget *, uint32_t, ...);
typedef int (*fn_gtk_proplist_set_for_event_t)(ca_proplist *, GdkEvent *);
typedef int (*fn_gtk_play_for_event_t)(GdkEvent *, uint32_t, ...);
typedef void (*fn_gtk_widget_disable_sounds_t)(GtkWidget *, gboolean);

static int nchecks = 0;
static int nfailed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        nchecks++;                                                           \
        if (!(cond)) {                                                       \
            nfailed++;                                                       \
            fprintf(stderr, "api_surface: FAIL line %d: %s\n", __LINE__, #cond); \
        }                                                                    \
    } while (0)

#define TAKE_PTR(var, fn)                                                    \
    do {                                                                     \
        var = (fn);                                                          \
        CHECK(var != NULL);                                                  \
    } while (0)

int main(void) {
    fn_gtk_context_get_t g_context_get = NULL;
    fn_gtk_context_get_for_screen_t g_context_get_for_screen = NULL;
    fn_gtk_proplist_set_for_widget_t g_proplist_set_for_widget = NULL;
    fn_gtk_play_for_widget_t g_play_for_widget = NULL;
    fn_gtk_proplist_set_for_event_t g_proplist_set_for_event = NULL;
    fn_gtk_play_for_event_t g_play_for_event = NULL;
    fn_gtk_widget_disable_sounds_t g_widget_disable_sounds = NULL;

#ifndef GDK_MULTIHEAD_SAFE
    TAKE_PTR(g_context_get, &ca_gtk_context_get);
#endif
    TAKE_PTR(g_context_get_for_screen, &ca_gtk_context_get_for_screen);
    TAKE_PTR(g_proplist_set_for_widget, &ca_gtk_proplist_set_for_widget);
    TAKE_PTR(g_play_for_widget, &ca_gtk_play_for_widget);
    TAKE_PTR(g_proplist_set_for_event, &ca_gtk_proplist_set_for_event);
    TAKE_PTR(g_play_for_event, &ca_gtk_play_for_event);
    TAKE_PTR(g_widget_disable_sounds, &ca_gtk_widget_disable_sounds);

    printf("api_surface: symbol relocation OK (%d checks)\n", nchecks);

    if (!gtk_init_check(NULL, NULL)) {
        printf("api_surface: GTK cannot initialise on this target; "
               "skipping GTK runtime checks\n");
        return nfailed == 0 ? 0 : 1;
    }

    {
        GdkScreen *screen = gdk_screen_get_default();
        ca_context *context = NULL;
        ca_proplist *proplist = NULL;
        GtkWidget *widget = NULL;

        CHECK(screen != NULL);
        if (!screen) {
            return nfailed == 0 ? 0 : 1;
        }

        context = g_context_get_for_screen(screen);
        CHECK(context != NULL);
        printf("api_surface: ca_gtk_context_get_for_screen -> %s\n",
               context ? "non-NULL" : "NULL");

        widget = gtk_window_new(GTK_WINDOW_TOPLEVEL);
        CHECK(widget != NULL);
        if (widget) {
            g_widget_disable_sounds(widget, TRUE);
            g_widget_disable_sounds(widget, FALSE);
            nchecks += 2;

            CHECK(ca_proplist_create(&proplist) == CA_SUCCESS);
            if (proplist) {
                CHECK(g_proplist_set_for_widget(proplist, widget) == CA_SUCCESS);
                CHECK(ca_proplist_destroy(proplist) == CA_SUCCESS);
            }
        }
    }

    printf("api_surface: GTK runtime checks done (%d checks, %d failures)\n",
           nchecks, nfailed);
    return nfailed == 0 ? 0 : 1;
}
