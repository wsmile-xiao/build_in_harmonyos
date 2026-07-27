#include <cattle/cattle.h>
#include <glib.h>
#include <string.h>

static CattleBuffer *buffer_from_string(const char *source)
{
    CattleBuffer *buffer = cattle_buffer_new(strlen(source));
    cattle_buffer_set_contents(buffer, (gint8 *)source);
    return buffer;
}

int main(void)
{
    GError *error = NULL;
    CattleProgram *program = cattle_program_new();
    CattleBuffer *valid = buffer_from_string("+++>++<-");
    CattleBuffer *invalid = buffer_from_string("[");

    g_assert_true(cattle_program_load(program, valid, &error));
    g_assert_no_error(error);
    g_assert_nonnull(cattle_program_get_instructions(program));

    g_assert_false(cattle_program_load(program, invalid, &error));
    g_assert_error(error, CATTLE_ERROR, CATTLE_ERROR_UNBALANCED_BRACKETS);

    g_clear_error(&error);
    g_object_unref(invalid);
    g_object_unref(valid);
    g_object_unref(program);
    return 0;
}
