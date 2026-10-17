/* Consumer test for glade 3.40.0 — exercises the packaged libgladeui.
 *
 * Runs under a broadway virtual display (same mechanism as the upstream
 * test suite proven during the port). Asserts, in order:
 *   1. glade_init() initializes the library (catalog paths resolve);
 *   2. GladeApp singleton materializes (glade_app_get);
 *   3. the gtk+ catalog is loaded and exposes widget adaptors (proves
 *      the packaged catalogs + catalog search path are functional);
 *   4. a GladeProject can be created and a minimal .glade interface XML
 *      round-trips through glade_project_load_from_file with the
 *      expected toplevel object count.
 */
#include <glib.h>
#include <glib-object.h>
#include <glib/gstdio.h>
#include <gtk/gtk.h>

#include <gladeui/glade.h>
#include <gladeui/glade-app.h>
#include <gladeui/glade-catalog.h>
#include <gladeui/glade-project.h>

#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define REQUIRE(cond)                                                     \
    do {                                                                  \
        if (!(cond)) {                                                    \
            fprintf(stderr, "FAIL: %s (%s:%d)\n", #cond, __FILE__,       \
                    __LINE__);                                            \
            return 1;                                                     \
        }                                                                 \
        fprintf(stderr, "ok: %s\n", #cond);                              \
    } while (0)

static const char *test_project_xml =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<interface>\n"
    "  <requires lib=\"gtk+\" version=\"3.20\"/>\n"
    "  <object class=\"GtkBox\" id=\"box1\">\n"
    "    <property name=\"visible\">True</property>\n"
    "    <property name=\"orientation\">vertical</property>\n"
    "    <child>\n"
    "      <object class=\"GtkLabel\" id=\"label1\">\n"
    "        <property name=\"visible\">True</property>\n"
    "        <property name=\"label\">hello glade</property>\n"
    "      </object>\n"
    "    </child>\n"
    "  </object>\n"
    "</interface>\n";

int main(int argc, char **argv)
{
    gtk_test_init(&argc, &argv, NULL);

    /* 1. library initialization */
    glade_init();

    /* 2. GladeApp singleton */
    GladeApp *app = glade_app_get();
    REQUIRE(GLADE_IS_APP(app));

    /* 3. gtk+ catalog loaded with adaptors */
    GladeCatalog *catalog = glade_app_get_catalog("gtk+");
    REQUIRE(catalog != NULL);
    REQUIRE(glade_catalog_get_adaptors(catalog) != NULL);

    /* 4. project XML round-trip */
    GladeProject *project = glade_project_new();
    REQUIRE(GLADE_IS_PROJECT(project));

    /* mkstemp contract: template MUST end with six 'X' (glib g_mkstemp is
     * a mkstemp wrapper; a ".glade" suffix violates the contract and
     * returns -1 with EINVAL on glibc). The project loader does not
     * depend on the file extension. */
    gchar *path = g_build_filename(g_get_tmp_dir(),
                                   "glade-test-pkg-XXXXXX", NULL);
    gint fd = g_mkstemp(path);
    REQUIRE(fd >= 0);
    close(fd);
    REQUIRE(g_file_set_contents(path, test_project_xml, -1, NULL) == TRUE);
    REQUIRE(glade_project_load_from_file(project, path) == TRUE);

    GList *toplevels = glade_project_toplevels(project);
    REQUIRE(g_list_length(toplevels) == 1);

    /* toplevel must be the GtkBox GObject we authored
     * (glade_project_toplevels returns a list of GObjects — the user
     * widgets, not GladeWidget wrappers; verified against upstream
     * tests/toplevel-order.c usage of g_list_nth(project toplevels)） */
    if (toplevels != NULL) {
        GObject *tobj = toplevels->data;
        REQUIRE(G_IS_OBJECT(tobj));
        REQUIRE(GTK_IS_BOX(tobj));
    }

    g_unlink(path);
    g_free(path);
    g_object_unref(project);

    printf("test glade 3.40.0: OK\n");
    return 0;
}
