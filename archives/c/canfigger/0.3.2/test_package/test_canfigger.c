#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <canfigger.h>

/* Self-contained check macro: the condition must always be evaluated, even
 * in Release builds where CMake adds -DNDEBUG and assert() compiles to
 * nothing (upstream guards its tests with "#undef NDEBUG" for the same
 * reason).  Callers keep side effects out of CHECK conditions. */
static int g_assertions = 0;

#define CHECK(cond)                                                   \
    do {                                                              \
        if (!(cond)) {                                                \
            fprintf(stderr, "CHECK failed at %s:%d: %s\n",            \
                    __FILE__, __LINE__, #cond);                       \
            abort();                                                  \
        }                                                             \
        g_assertions++;                                               \
    } while (0)

static void
write_sample_conf (const char *path)
{
    FILE *file = fopen(path, "w");
    CHECK(file != NULL);
    CHECK(fputs("# comment line\n", file) >= 0);
    CHECK(fputs("[section header]\n", file) >= 0);
    CHECK(fputs("key1 = value1\n", file) >= 0);
    CHECK(fputs("key2 = value2, attr1, attr2\n", file) >= 0);
    CHECK(fputs("list = a, b, c\n", file) >= 0);
    CHECK(fclose(file) == 0);
}

int
main (void)
{
    const char *conf_path = "canfigger_consumer_test.conf";
    struct Canfigger *list = NULL;
    struct Canfigger *node = NULL;
    char *attr = NULL;
    char *joined = NULL;
    char *config_dir = NULL;

    /* Version macros come from the generated canfigger_version.h that is
     * installed together with canfigger.h. */
    CHECK(CANFIGGER_VERSION_MAJOR == 0);
    CHECK(CANFIGGER_VERSION_MINOR == 3);
    CHECK(CANFIGGER_VERSION_PATCH == 2);
    CHECK(CANFIGGER_CHECK_VERSION(0, 3));
    CHECK(!CANFIGGER_CHECK_VERSION(1, 0));

    write_sample_conf(conf_path);

    /* Comments and section headers must be skipped: exactly 3 nodes. */
    list = canfigger_parse_file(conf_path, ',');
    CHECK(list != NULL);

    /* Node 1: key1 = value1 (no attributes). */
    node = list;
    CHECK(strcmp(node->key, "key1") == 0);
    CHECK(node->value != NULL && strcmp(node->value, "value1") == 0);
    CHECK(node->attributes == NULL);
    canfigger_free_current_key_node_advance(&list);
    CHECK(list != NULL);

    /* Node 2: key2 = value2, attr1, attr2. */
    node = list;
    CHECK(strcmp(node->key, "key2") == 0);
    CHECK(node->value != NULL && strcmp(node->value, "value2") == 0);
    attr = NULL;
    canfigger_free_current_attr_str_advance(node->attributes, &attr);
    CHECK(attr != NULL && strcmp(attr, "attr1") == 0);
    canfigger_free_current_attr_str_advance(node->attributes, &attr);
    CHECK(attr != NULL && strcmp(attr, "attr2") == 0);
    canfigger_free_current_attr_str_advance(node->attributes, &attr);
    CHECK(attr == NULL);
    canfigger_free_current_key_node_advance(&list);
    CHECK(list != NULL);

    /* Node 3: list = a, b, c (value plus two attributes). */
    node = list;
    CHECK(strcmp(node->key, "list") == 0);
    CHECK(node->value != NULL && strcmp(node->value, "a") == 0);
    attr = NULL;
    canfigger_free_current_attr_str_advance(node->attributes, &attr);
    CHECK(attr != NULL && strcmp(attr, "b") == 0);
    canfigger_free_current_attr_str_advance(node->attributes, &attr);
    CHECK(attr != NULL && strcmp(attr, "c") == 0);
    canfigger_free_current_attr_str_advance(node->attributes, &attr);
    CHECK(attr == NULL);
    canfigger_free_current_key_node_advance(&list);
    CHECK(list == NULL);

    /* Missing file returns NULL (upstream file_open_err behavior). */
    CHECK(canfigger_parse_file("does-not-exist-404.conf", ',') == NULL);

    /* XDG config dir honours XDG_CONFIG_HOME. */
    CHECK(setenv("XDG_CONFIG_HOME", "/tmp/canfigger-consumer-cfg", 1) == 0);
    config_dir = canfigger_config_dir("consumer-app");
    CHECK(config_dir != NULL);
    CHECK(strcmp(config_dir, "/tmp/canfigger-consumer-cfg/consumer-app") == 0);
    free(config_dir);
    CHECK(unsetenv("XDG_CONFIG_HOME") == 0);

    /* path_join: separator inserted once, trailing separator tolerated. */
    joined = canfigger_path_join("/base/dir", "settings.conf");
    CHECK(joined != NULL);
    CHECK(strcmp(joined, "/base/dir/settings.conf") == 0);
    free(joined);
    joined = canfigger_path_join("/base/dir/", "settings.conf");
    CHECK(joined != NULL);
    CHECK(strcmp(joined, "/base/dir/settings.conf") == 0);
    free(joined);
    CHECK(canfigger_path_join(NULL, "x") == NULL);
    CHECK(canfigger_path_join("/base/dir", NULL) == NULL);

    remove(conf_path);

    printf("CANFIGGER_CONSUMER_TEST PASS assertions=%d\n", g_assertions);
    return 0;
}
