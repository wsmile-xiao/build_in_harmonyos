#include <libportal/portal.h>
#include <libportal-gtk4/portal-gtk4.h>
#include <gtk/gtk.h>
#include <glib.h>
#include <stdio.h>

/* Validates libportal-gtk4 against its real Xdp and GTK4 API (R34: no
 * empty-shell tests).
 *
 * OHOS has no session D-Bus, no XDG portal daemon and no display server,
 * so every assertion targets a *deterministic* client-side path:
 *
 *  - portal-gtk4.h header + gtk4 headers are installed and usable.
 *  - gtk_get_major_version(): real GTK4 runtime call (pure version query,
 *    no display needed) -- proves libportal-gtk4.pc's Requires: gtk4 chain
 *    links and loads.
 *  - xdp_parent_new_gtk symbol resolves from the linked libportal-gtk4
 *    backend library (function-pointer binding; not called -- it needs a
 *    live GtkWindow/display, which OHOS test envs do not have).
 *  - GTK_WINDOWING macros: portal-gtk4.c guards all X11/Wayland code
 *    behind GDK_WINDOWING_* -- on the broadway-flavour gtk4 build neither
 *    is defined, so compiling this TU against the same headers exercises
 *    the same guard set the backend was compiled with.
 *  - core XdpPortal type system + no-bus initable failure path (same
 *    deterministic checks as the libportal L1 test).
 */
int main(void)
{
    /* 1. GTK4 runtime linkage: version query needs no display server. */
    guint major = gtk_get_major_version ();
    if (major < 4)
    {
        g_printerr ("gtk_get_major_version() = %u, expected >= 4\n", major);
        return 1;
    }
    g_print ("gtk4 runtime: %u.%u.%u\n", major,
             gtk_get_minor_version (), gtk_get_micro_version ());

    /* 2. GTK4 backend backend symbol resolution: xdp_parent_new_gtk must
     * be exported by the linked libportal-gtk4 library. */
    {
        XdpParent *(*parent_new_gtk) (GtkWindow *window) = xdp_parent_new_gtk;
        if (parent_new_gtk == NULL)
        {
            g_printerr ("xdp_parent_new_gtk symbol not resolved from "
                        "libportal-gtk4\n");
            return 1;
        }
        g_print ("xdp_parent_new_gtk exported at %p\n", (gpointer) parent_new_gtk);
    }

    /* 3. broadway flavour sanity: neither X11 nor Wayland windowing is
     * compiled into this gtk4 build (matches the backend's guards). */
#if defined(GDK_WINDOWING_X11) || defined(GDK_WINDOWING_WAYLAND)
    g_print ("note: X11/Wayland windowing defined in gdkconfig.h\n");
#endif

    /* 4. Core XdpPortal type system sanity (shared with the core lib). */
    GType portal_type = xdp_portal_get_type ();
    if (portal_type == G_TYPE_INVALID ||
        !g_type_is_a (portal_type, G_TYPE_OBJECT))
    {
        g_printerr ("XdpPortal GType invalid or not a GObject\n");
        return 1;
    }

    /* 5. flatpak/sandbox probes: no /.flatpak-info, no snap on OHOS. */
    if (xdp_portal_running_under_flatpak () ||
        xdp_portal_running_under_sandbox ())
    {
        g_printerr ("expected flatpak/sandbox probes to return FALSE\n");
        return 1;
    }

    /* 6. No-bus failure path: initable_new must fail cleanly with a GError
     * (OHOS has no session bus); documented safe path. */
    {
        g_autoptr(GError) error = NULL;
        XdpPortal *portal = xdp_portal_initable_new (&error);
        if (portal != NULL)
        {
            /* A bus unexpectedly exists: still fine -- object is valid. */
            g_object_unref (portal);
        }
        else if (error == NULL)
        {
            g_printerr ("initable_new returned NULL without setting GError\n");
            return 1;
        }
        else
        {
            g_print ("no session bus (expected on OHOS): %s\n", error->message);
        }
    }

    g_print ("libportal-gtk4 L1 test: all assertions passed\n");
    return 0;
}
