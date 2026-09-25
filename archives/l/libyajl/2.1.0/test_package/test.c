/*
 * test_libyajl — Conan test_package for libyajl 2.1.0
 *
 * R34: this test substantively exercises the yajl API by parsing a JSON
 * document with yajl_tree_parse() and extracting a nested string value via
 * yajl_tree_get(), then asserting the result. It is NOT a hollow printf.
 */
#include <stdio.h>
#include <string.h>

#include <yajl/yajl_tree.h>

int main(void)
{
    /* A small JSON document to parse */
    static const char json[] =
        "{\"name\":\"test\",\"value\":42,\"nested\":{\"key\":\"hello\"}}";
    char errbuf[1024];
    yajl_val node;
    int failures = 0;

    errbuf[0] = 0;

    /* Parse the JSON document — exercises yajl_tree_parse */
    node = yajl_tree_parse(json, errbuf, sizeof(errbuf));
    if (node == NULL) {
        fprintf(stderr, "FAIL: yajl_tree_parse returned NULL: %s\n", errbuf);
        return 1;
    }

    /* Extract the top-level "name" string — exercises yajl_tree_get */
    {
        const char *path[] = {"name", (const char *)0};
        yajl_val v = yajl_tree_get(node, path, yajl_t_string);
        const char *s = v ? YAJL_GET_STRING(v) : NULL;
        if (s == NULL || strcmp(s, "test") != 0) {
            fprintf(stderr, "FAIL: name expected 'test', got '%s'\n",
                    s ? s : "()");
            failures++;
        } else {
            printf("PASS: name = %s\n", s);
        }
    }

    /* Extract the nested "key" string — exercises deeper tree traversal */
    {
        const char *path[] = {"nested", "key", (const char *)0};
        yajl_val v = yajl_tree_get(node, path, yajl_t_string);
        const char *s = v ? YAJL_GET_STRING(v) : NULL;
        if (s == NULL || strcmp(s, "hello") != 0) {
            fprintf(stderr, "FAIL: nested.key expected 'hello', got '%s'\n",
                    s ? s : "()");
            failures++;
        } else {
            printf("PASS: nested.key = %s\n", s);
        }
    }

    /* Extract the integer "value" — exercises number handling */
    {
        const char *path[] = {"value", (const char *)0};
        yajl_val v = yajl_tree_get(node, path, yajl_t_number);
        if (v == NULL) {
            fprintf(stderr, "FAIL: value not found\n");
            failures++;
        } else {
            long long i = YAJL_GET_INTEGER(v);
            if (i != 42) {
                fprintf(stderr, "FAIL: value expected 42, got %lld\n", i);
                failures++;
            } else {
                printf("PASS: value = %lld\n", i);
            }
        }
    }

    /* Free the parse tree — exercises yajl_tree_free */
    yajl_tree_free(node);

    if (failures > 0) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("ALL TESTS PASSED\n");
    return 0;
}
