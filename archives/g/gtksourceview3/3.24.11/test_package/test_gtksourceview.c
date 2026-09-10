#include <gtksourceview/gtksource.h>
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[]) {
    /* R34: real gtksourceview API usage, no display needed.
     * These APIs exercise language manager, language metadata,
     * style scheme manager and buffer APIs without opening a
     * display connection. */
    gtk_init_check(&argc, &argv);

    GtkSourceLanguageManager *lm = gtk_source_language_manager_get_default();
    if (!GTK_SOURCE_IS_LANGUAGE_MANAGER (lm)) {
        fprintf(stderr, "language manager init failed\n");
        return 1;
    }
    const gchar * const *ids = gtk_source_language_manager_get_language_ids(lm);
    if (ids == NULL || *ids == NULL) {
        /* language-specs not installed in package share dir when run
         * outside of the build tree; the manager itself must still work */
        fprintf(stderr, "no language ids found (search path may be empty)\n");
    }
    int n_langs = 0;
    if (ids != NULL) {
        for (const gchar * const *p = ids; *p != NULL; p++) n_langs++;
    }
    printf("language ids visible: %d\n", n_langs);

    /* Version macros: 3.24.11 → major 3, minor 24, micro 11 */
    if (GTK_SOURCE_MAJOR_VERSION != 3 || GTK_SOURCE_MINOR_VERSION != 24) {
        fprintf(stderr, "unexpected version macros: %d.%d.%d\n",
                GTK_SOURCE_MAJOR_VERSION, GTK_SOURCE_MINOR_VERSION,
                GTK_SOURCE_MICRO_VERSION);
        return 1;
    }

    /* Buffer API (pure logic, no display) */
    GtkSourceBuffer *buffer = gtk_source_buffer_new(NULL);
    if (!GTK_SOURCE_IS_BUFFER (buffer)) {
        fprintf(stderr, "buffer creation failed\n");
        return 1;
    }
    GtkTextIter start, end;
    gtk_text_buffer_set_text(GTK_TEXT_BUFFER(buffer), "int main() { return 0; }", -1);
    gtk_text_buffer_get_bounds(GTK_TEXT_BUFFER(buffer), &start, &end);
    gchar *got = gtk_text_buffer_get_text(
        GTK_TEXT_BUFFER(buffer), &start, &end, TRUE);
    if (g_strcmp0(got, "int main() { return 0; }") != 0) {
        fprintf(stderr, "buffer roundtrip failed: %s\n", got ? got : "()");
        return 1;
    }
    g_free(got);

    /* Search context API (async search: pump glib main context until
     * the search idle callback settles the occurrences count) */
    gtk_text_buffer_get_start_iter(GTK_TEXT_BUFFER(buffer), &start);
    GtkSourceSearchContext *ctx =
        gtk_source_search_context_new(buffer, NULL);
    GtkSourceSearchSettings *settings =
        gtk_source_search_context_get_settings(ctx);
    gtk_source_search_settings_set_search_text(settings, "main");
    for (int spin = 0;
         gtk_source_search_context_get_occurrences_count(ctx) == -1 && spin < 1000;
         spin++) {
        g_main_context_iteration(NULL, FALSE);
    }
    guint n_occ = gtk_source_search_context_get_occurrences_count(ctx);
    printf("occurrences of 'main': %u\n", n_occ);
    if (n_occ != 1) {
        fprintf(stderr, "search occurrences mismatch\n");
        return 1;
    }
    g_object_unref(ctx);

    /* Style scheme manager */
    GtkSourceStyleSchemeManager *sm =
        gtk_source_style_scheme_manager_get_default();
    const gchar * const *scheme_ids =
        gtk_source_style_scheme_manager_get_scheme_ids(sm);
    int n_schemes = 0;
    if (scheme_ids != NULL) {
        for (const gchar * const *p = scheme_ids; *p != NULL; p++) n_schemes++;
    }
    printf("style schemes visible: %d\n", n_schemes);

    g_object_unref(buffer);

    printf("test gtksourceview3 3.24.11: OK\n");
    return 0;
}
