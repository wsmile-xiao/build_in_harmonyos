#include <glib.h>
#include <glib-object.h>
#include <stdio.h>

/* Real GLib smoke test: exercises string utils + hash table (glib core),
 * GVariant (glib), and the GObject type system (gobject). Returns non-zero
 * on any failure so the harness can detect regressions. */
int main(void) {
    int status = 1;
    GHashTable *ht = NULL;
    GVariant *v = NULL;
    GObject *o = NULL;

    /* glib core: string + hash table */
    gchar *s = g_strdup("hello glib");
    if (!g_str_has_prefix(s, "hello")) {
        fprintf(stderr, "FAIL: g_str_has_prefix\n");
        goto cleanup;
    }

    ht = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);
    g_hash_table_insert(ht, g_strdup("key"), g_strdup("val"));
    if (g_hash_table_size(ht) != 1) {
        fprintf(stderr, "FAIL: g_hash_table_size\n");
        status = 2;
        goto cleanup;
    }

    /* glib: GVariant */
    v = g_variant_new_int32(42);
    if (g_variant_get_int32(v) != 42) {
        fprintf(stderr, "FAIL: g_variant_get_int32\n");
        status = 3;
        goto cleanup;
    }

    /* gobject: type system — instantiate GInitiallyUnowned (GObject) */
    o = g_object_new(G_TYPE_OBJECT, NULL);
    if (!G_IS_OBJECT(o)) {
        fprintf(stderr, "FAIL: g_object_new / G_IS_OBJECT\n");
        status = 4;
        goto cleanup;
    }

    printf("test glib2 2.88.0: OK (string/hashtable/variant/gobject)\n");
    status = 0;

cleanup:
    if (o) g_object_unref(o);
    if (v) g_variant_unref(v);
    if (ht) g_hash_table_destroy(ht);
    g_free(s);
    return status;
}
