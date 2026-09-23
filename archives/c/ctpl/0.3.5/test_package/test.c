#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <glib.h>
#include <gio/gio.h>
#include <ctpl/ctpl.h>

/* Parse @tmpl with @env_str via the public lexer/parser API.
 * Returns a newly allocated output string, or NULL on failure
 * (with @error set when error != NULL). Mirrors the approach of
 * upstream testsuite/ctpl-test-lib.c ctpltest_parse_string(). */
static char *
parse_string(const char *tmpl, const char *env_str, GError **error)
{
    CtplEnviron *env = NULL;
    CtplToken *tree = NULL;
    GOutputStream *ostream = NULL;
    CtplOutputStream *stream = NULL;
    char *output = NULL;

    env = ctpl_environ_new();
    if (!ctpl_environ_add_from_string(env, env_str, error)) {
        ctpl_environ_unref(env);
        return NULL;
    }
    tree = ctpl_lexer_lex_string(tmpl, error);
    if (!tree) {
        ctpl_environ_unref(env);
        return NULL;
    }
    ostream = g_memory_output_stream_new(NULL, 0, realloc, free);
    stream = ctpl_output_stream_new(ostream);
    if (ctpl_parser_parse(tree, env, stream, error)) {
        gpointer data = g_memory_output_stream_get_data(G_MEMORY_OUTPUT_STREAM(ostream));
        gsize size = g_memory_output_stream_get_data_size(G_MEMORY_OUTPUT_STREAM(ostream));
        output = (char *)g_malloc(size + 1);
        memcpy(output, data, size);
        output[size] = '\0';
    }
    g_object_unref(stream);
    g_object_unref(ostream);
    ctpl_token_free(tree);
    ctpl_environ_unref(env);
    return output;
}

int main(void)
{
    int passed = 0;
    GError *error = NULL;
    char *out = NULL;

    /* Case 1: basic substitution through environ string + lexer + parser. */
    out = parse_string("Hello, {name}!", "name = \"World\";", &error);
    if (!out) {
        fprintf(stderr, "case1 parse failed: %s\n",
                error ? error->message : "unknown error");
        if (error)
            g_error_free(error);
        return 1;
    }
    if (strcmp(out, "Hello, World!") != 0) {
        fprintf(stderr, "case1 mismatch: got '%s', want 'Hello, World!'\n", out);
        g_free(out);
        return 1;
    }
    printf("PASS case1 basic substitution: '%s'\n", out);
    g_free(out);
    out = NULL;
    passed++;

    /* Case 2: environ push/lookup API (CtplEnviron + CtplValue). */
    {
        CtplEnviron *env = ctpl_environ_new();
        const CtplValue *v = NULL;

        ctpl_environ_push_string(env, "greeting", "Hi");
        ctpl_environ_push_int(env, "answer", 42);
        v = ctpl_environ_lookup(env, "greeting");
        if (!v || ctpl_value_get_held_type(v) != CTPL_VTYPE_STRING ||
            strcmp(ctpl_value_get_string(v), "Hi") != 0) {
            fprintf(stderr, "case2 string lookup failed\n");
            ctpl_environ_unref(env);
            return 1;
        }
        v = ctpl_environ_lookup(env, "answer");
        if (!v || ctpl_value_get_held_type(v) != CTPL_VTYPE_INT ||
            ctpl_value_get_int(v) != 42) {
            fprintf(stderr, "case2 int lookup failed\n");
            ctpl_environ_unref(env);
            return 1;
        }
        /* Missing symbol must return NULL (error path, not a crash). */
        if (ctpl_environ_lookup(env, "does-not-exist") != NULL) {
            fprintf(stderr, "case2 missing-symbol lookup should be NULL\n");
            ctpl_environ_unref(env);
            return 1;
        }
        ctpl_environ_unref(env);
        printf("PASS case2 environ push/lookup (string+int+missing)\n");
        passed++;
    }

    /* Case 3: failure path — unknown symbol must produce an error,
     * proving the harness is not comparing empty files to empty files. */
    out = parse_string("{missing_symbol_xyz}", "", &error);
    if (out != NULL) {
        fprintf(stderr, "case3 should have failed but got '%s'\n", out);
        g_free(out);
        return 1;
    }
    if (error)
        g_error_free(error);
    error = NULL;
    printf("PASS case3 unknown symbol correctly fails\n");
    passed++;

    printf("test ctpl 0.3.5: OK (%d/3 cases passed)\n", passed);
    return (passed == 3) ? 0 : 1;
}
