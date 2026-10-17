#include <stdio.h>
#include <libportal-gtk3/portal-gtk3.h>
#include <libportal/portal.h>
#include <libportal/portal-helpers.h>
#include <gtk/gtk.h>

int main(int argc, char *argv[]) {
    // R34: must call tested package API, not just print string.
    // 1. Verify GTK version API (no display needed for version query —
    //    gtk package test_package uses the same headless-safe pattern).
    unsigned int major = gtk_get_major_version();
    unsigned int minor = gtk_get_minor_version();
    unsigned int micro = gtk_get_micro_version();
    printf("GTK %u.%u.%u\n", major, minor, micro);

    // 2. Verify the gtk3 backend API: xdp_parent_new_gtk wraps a GObject
    //    into an opaque XdpParent (vtable wiring + g_object_ref only; it
    //    does not touch the window internals — parent_export reads the
    //    display lazily, only when a handle is actually exported).
    //    GtkWindow instantiation itself needs a display (style provider
    //    lookup at g_object_new time), which does not exist in headless
    //    CI; any GObject exercises the backend code path safely.
    //    The main library's xdp_portal_new() is deliberately NOT called
    //    here: it aborts when no D-Bus machine-id exists (GLib spawns a
    //    session bus eagerly — documented runtime limitation).
    GObject *obj = g_object_new(G_TYPE_OBJECT, NULL);
    XdpParent *parent = xdp_parent_new_gtk((GtkWindow *)obj);
    if (parent == NULL) {
        fprintf(stderr, "xdp_parent_new_gtk returned NULL\n");
        return 1;
    }
    printf("xdp_parent_new_gtk OK: %p\n", (void *)parent);

    // 3. Verify the backend shared library's XDP types are wired to the
    //    main libportal GObject introspection data (headless-safe).
    GType portal_type = XDP_TYPE_PORTAL;
    if (portal_type == 0) {
        fprintf(stderr, "XDP_TYPE_PORTAL is 0\n");
        return 1;
    }
    printf("XDP_TYPE_PORTAL registered: %lu\n", (unsigned long)portal_type);

    g_object_unref(obj);
    printf("test libportal-gtk3 0.10.0: OK\n");
    return 0;
}
