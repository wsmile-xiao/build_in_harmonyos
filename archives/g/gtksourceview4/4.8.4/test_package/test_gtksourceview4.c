/* gtksourceview4 4.8.4 — HarmonyOS PC consumer test (headless).
 *
 * Real GtkSourceView 4 API usage from a downstream consumer's point of view:
 *   - version macros of the *installed* library
 *   - GtkSourceLanguageManager: explicit search path (OHOS has no
 *     /usr/share/gtksourceview-4), language-spec XML parsed through libxml2,
 *     language metadata lookup
 *   - GtkSourceStyleSchemeManager: style XML enumeration
 *   - GtkSourceBuffer: text roundtrip
 *   - GtkSourceSearchContext: asynchronous occurrence counting + replace_all
 *   - GtkSourceBuffer undo/redo bookkeeping
 *
 * None of these APIs opens a display connection: GtkSourceView 4 is GTK3
 * based, but everything below is pure object/logic work, so the test is
 * meaningful on a platform without a window system. Output is TAP-like
 * ("ok N -" / "not ok N -") and the process exit code reflects the result.
 */
#include <gtksourceview/gtksource.h>
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond, ...)                                        \
    do {                                                        \
        checks++;                                               \
        printf("%s %d - ", (cond) ? "ok" : "not ok", checks);    \
        printf(__VA_ARGS__);                                    \
        printf("\n");                                           \
        if (!(cond))                                            \
            failures++;                                         \
    } while (0)

int main(int argc, char *argv[]) {
    /* OHOS has no window system: gtk_init_check() fails cleanly and the
     * non-display APIs below keep working (gtksourceview3 precedent). */
    gtk_init_check(&argc, &argv);

    /* ---- installed version macros: 4.8.4 ---- */
    CHECK(GTK_SOURCE_MAJOR_VERSION == 4 && GTK_SOURCE_MINOR_VERSION == 8
              && GTK_SOURCE_MICRO_VERSION == 4,
          "version macros = %d.%d.%d", GTK_SOURCE_MAJOR_VERSION,
          GTK_SOURCE_MINOR_VERSION, GTK_SOURCE_MICRO_VERSION);

    /* ---- language manager over the package's own language specs ---- */
    GtkSourceLanguageManager *lm = gtk_source_language_manager_get_default();
    CHECK(GTK_SOURCE_IS_LANGUAGE_MANAGER(lm), "default language manager created");

    const gchar *specs_dir = g_getenv("GSV_LANGSPECS_DIR");
    if (specs_dir != NULL && *specs_dir != '\0') {
        const gchar *paths[] = {specs_dir, NULL};
        gtk_source_language_manager_set_search_path(lm, paths);
        CHECK(TRUE, "language search path set to %s (OHOS: no /usr/share)", specs_dir);
    } else {
        CHECK(TRUE, "language search path left at default (GSV_LANGSPECS_DIR unset)");
    }

    const gchar *const *ids = gtk_source_language_manager_get_language_ids(lm);
    int n_langs = 0;
    if (ids != NULL) {
        for (const gchar *const *p = ids; *p != NULL; p++)
            n_langs++;
    }
    /* 4.8.4 ships ~180 *.lang specs; a low count means the XML/its files were
     * not found — the real consumer regression this test guards against. */
    CHECK(n_langs >= 100, "language ids enumerated: %d (>= 100)", n_langs);

    GtkSourceLanguage *c_lang = gtk_source_language_manager_get_language(lm, "c");
    CHECK(GTK_SOURCE_IS_LANGUAGE(c_lang), "language '%s' loaded from XML", "c");
    if (GTK_SOURCE_IS_LANGUAGE(c_lang)) {
        const gchar *lang_id = gtk_source_language_get_id(c_lang);
        const gchar *lang_name = gtk_source_language_get_name(c_lang);
        CHECK(g_strcmp0(lang_id, "c") == 0, "language id = '%s'",
              lang_id ? lang_id : "(null)");
        CHECK(lang_name != NULL && *lang_name != '\0', "language section name = '%s'",
              lang_name ? lang_name : "(null)");
        /* metadata is parsed from the .lang XML (libxml2 path) */
        const gchar *mime = gtk_source_language_get_metadata(c_lang, "mimetypes");
        CHECK(mime != NULL && *mime != '\0', "language metadata[mimetypes] = '%s'",
              mime ? mime : "(null)");
    } else {
        checks += 3;
        failures += 3;
    }

    /* ---- style scheme manager ---- */
    GtkSourceStyleSchemeManager *sm = gtk_source_style_scheme_manager_get_default();
    const gchar *const *schemes = gtk_source_style_scheme_manager_get_scheme_ids(sm);
    int n_schemes = 0;
    if (schemes != NULL) {
        for (const gchar *const *p = schemes; *p != NULL; p++)
            n_schemes++;
    }
    CHECK(n_schemes >= 5, "style schemes enumerated: %d (>= 5)", n_schemes);

    /* ---- buffer: create / set / read back ---- */
    GtkSourceBuffer *buffer = gtk_source_buffer_new(NULL);
    CHECK(GTK_SOURCE_IS_BUFFER(buffer), "GtkSourceBuffer created without a language");
    const gchar *text = "int main() { return 0; }\n";
    gtk_text_buffer_set_text(GTK_TEXT_BUFFER(buffer), text, -1);
    GtkTextIter start, end;
    gtk_text_buffer_get_bounds(GTK_TEXT_BUFFER(buffer), &start, &end);
    gchar *got = gtk_text_buffer_get_text(GTK_TEXT_BUFFER(buffer), &start, &end, TRUE);
    CHECK(g_strcmp0(got, text) == 0, "buffer text roundtrip (%" G_GSIZE_FORMAT " chars)",
          strlen(got ? got : ""));
    g_free(got);

    /* ---- search context: occurrence count + replace_all ---- */
    GtkSourceSearchContext *ctx = gtk_source_search_context_new(buffer, NULL);
    GtkSourceSearchSettings *settings = gtk_source_search_context_get_settings(ctx);
    gtk_source_search_settings_set_search_text(settings, "main");
    for (int spin = 0;
         gtk_source_search_context_get_occurrences_count(ctx) == -1 && spin < 1000;
         spin++) {
        g_main_context_iteration(NULL, FALSE);
    }
    guint n_occ = gtk_source_search_context_get_occurrences_count(ctx);
    CHECK(n_occ == 1, "search occurrences of 'main': %u (expected 1)", n_occ);

    GError *error = NULL;
    gboolean replaced = gtk_source_search_context_replace_all(ctx, "long", -1, &error);
    CHECK(replaced && error == NULL, "search replace_all 'main' -> 'long' %s",
          error ? error->message : "succeeded");
    if (error != NULL)
        g_error_free(error);
    gtk_text_buffer_get_bounds(GTK_TEXT_BUFFER(buffer), &start, &end);
    got = gtk_text_buffer_get_text(GTK_TEXT_BUFFER(buffer), &start, &end, TRUE);
    CHECK(g_strcmp0(got, "int long() { return 0; }\n") == 0,
          "buffer content after replace_all: \"%s\"", got ? got : "(null)");
    g_free(got);
    g_object_unref(ctx);

    /* ---- undo/redo bookkeeping (GtkSourceBuffer level, no display) ---- */
    gtk_text_buffer_get_start_iter(GTK_TEXT_BUFFER(buffer), &start);
    gtk_text_buffer_insert(GTK_TEXT_BUFFER(buffer), &start, "/* x */ ", -1);
    gboolean can_undo = gtk_source_buffer_can_undo(buffer);
    CHECK(can_undo, "gtk_source_buffer_can_undo() after an edit: %s",
          can_undo ? "TRUE" : "FALSE");
    if (can_undo) {
        gtk_source_buffer_undo(buffer);
        gtk_text_buffer_get_bounds(GTK_TEXT_BUFFER(buffer), &start, &end);
        got = gtk_text_buffer_get_text(GTK_TEXT_BUFFER(buffer), &start, &end, TRUE);
        CHECK(g_strcmp0(got, "int long() { return 0; }\n") == 0,
              "undo restored the previous content");
        g_free(got);
    } else {
        checks++;
        failures++;
    }

    g_object_unref(buffer);
    printf("# gtksourceview4 4.8.4 consumer test: %d checks, %d failures\n",
           checks, failures);
    printf("test gtksourceview4 4.8.4: %s\n", failures == 0 ? "OK" : "FAILED");
    return failures == 0 ? 0 : 1;
}
