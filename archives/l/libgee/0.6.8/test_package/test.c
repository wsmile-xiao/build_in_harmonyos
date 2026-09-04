#include <gee.h>
#include <glib.h>
#include <stdio.h>

int main(void) {
    GeeArrayList *list = gee_array_list_new(
        G_TYPE_STRING,
        (GBoxedCopyFunc)g_strdup,
        (GDestroyNotify)g_free,
        NULL);
    GeeCollection *collection;
    gboolean ok;
    gint size;

    if (list == NULL) {
        fprintf(stderr, "gee_array_list_new returned NULL\n");
        return 1;
    }
    collection = GEE_COLLECTION(list);
    ok = gee_collection_add(collection, "libgee");
    ok = gee_collection_add(collection, "harmonyos") && ok;
    size = gee_collection_get_size(collection);
    g_object_unref(list);
    return (ok && size == 2) ? 0 : 1;
}
