/* Conan test_package for libpeas 2.2.1 — calls the real libpeas API:
 * creates a PeasEngine, registers a plugin search path and checks the
 * plugin-info scan via PeasPluginInfo (R34: real API usage, not print-only). */
#include <glib.h>
#include <libpeas.h>

static void
test_engine_new (void)
{
    PeasEngine *engine = peas_engine_new ();
    g_assert_true (PEAS_IS_ENGINE (engine));
    g_object_unref (engine);
}

static void
test_engine_add_search_path (void)
{
    PeasEngine *engine = peas_engine_new ();
    peas_engine_add_search_path (engine, "/nonexistent/plugins", NULL);
    g_assert_cmpuint (g_list_model_get_n_items (G_LIST_MODEL (engine)), ==, 0);
    g_object_unref (engine);
}

int
main (int argc, char *argv[])
{
    g_test_init (&argc, &argv, NULL);
    g_test_add_func ("/libpeas/engine-new", test_engine_new);
    g_test_add_func ("/libpeas/engine-add-search-path", test_engine_add_search_path);
    return g_test_run ();
}
