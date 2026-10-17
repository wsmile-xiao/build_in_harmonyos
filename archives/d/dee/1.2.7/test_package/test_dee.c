#include <stdio.h>

#include <glib-object.h>
#include <glib.h>

#include <dee.h>

/* R34: substantively exercise the libdee public API — create a DeeModel, set
 * a one-column schema (NULL-terminated varargs), append a row (NULL-terminated
 * GVariant array) and verify the row count. A standalone model needs no live
 * dbus session. (dee headers install flat under include/dee-1.0/, so the
 * include is <dee.h>.) */
int main(void)
{
    /* DeeModel is an interface; use the concrete sequence model. */
    DeeModel *model = dee_sequence_model_new();
    if (model == NULL) {
        fprintf(stderr, "FAIL: dee_sequence_model_new() returned NULL\n");
        return 1;
    }

    /* dee schemas use GVariant type strings ("s" = string). */
    dee_model_set_schema(model, "s", NULL);

    GVariant *row_members[2] = { g_variant_new_string("row0"), NULL };
    dee_model_append_row(model, row_members);
    g_variant_unref(row_members[0]);

    guint n = dee_model_get_n_rows(model);
    if (n != 1) {
        fprintf(stderr, "FAIL: expected 1 row, got %u\n", n);
        g_object_unref(model);
        return 1;
    }

    printf("PASS: dee model created, schema set, 1 row appended (n_rows=%u)\n", n);
    g_object_unref(model);
    return 0;
}
