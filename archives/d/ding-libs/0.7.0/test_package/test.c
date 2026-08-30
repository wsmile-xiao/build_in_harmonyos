#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dhash.h>
#include <ini_configobj.h>

static int test_dhash(void)
{
    hash_table_t *table = NULL;
    hash_key_t key;
    hash_value_t value;
    hash_value_t found;
    char key_text[] = "answer";

    if (hash_create(0, &table, NULL, NULL) != HASH_SUCCESS || table == NULL) {
        fprintf(stderr, "hash_create failed\n");
        return 1;
    }

    key.type = HASH_KEY_STRING;
    key.str = key_text;
    value.type = HASH_VALUE_INT;
    value.i = 42;
    if (hash_enter(table, &key, &value) != HASH_SUCCESS) {
        fprintf(stderr, "hash_enter failed\n");
        hash_destroy(table);
        return 1;
    }
    if (hash_lookup(table, &key, &found) != HASH_SUCCESS ||
        found.type != HASH_VALUE_INT || found.i != 42 || hash_count(table) != 1) {
        fprintf(stderr, "hash_lookup returned the wrong value\n");
        hash_destroy(table);
        return 1;
    }
    if (hash_delete(table, &key) != HASH_SUCCESS || hash_count(table) != 0) {
        fprintf(stderr, "hash_delete failed\n");
        hash_destroy(table);
        return 1;
    }
    hash_destroy(table);
    return 0;
}

static int test_ini_config(void)
{
    static const char input[] =
        "[main]\n"
        "answer = 42\n"
        "name = ding-libs\n";
    struct ini_cfgfile *file_ctx = NULL;
    struct ini_cfgobj *config = NULL;
    struct value_obj *value = NULL;
    char *name = NULL;
    int error = 0;
    int answer;

    error = ini_config_file_from_mem((void *)input, (uint32_t)strlen(input),
                                     &file_ctx);
    if (error != 0) {
        fprintf(stderr, "ini_config_file_from_mem failed: %d\n", error);
        return 1;
    }
    error = ini_config_create(&config);
    if (error != 0) {
        fprintf(stderr, "ini_config_create failed: %d\n", error);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    error = ini_config_parse(file_ctx, INI_STOP_ON_ANY, INI_MV1S_ALLOW, 0,
                             config);
    if (error != 0) {
        fprintf(stderr, "ini_config_parse failed: %d\n", error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }

    error = ini_get_config_valueobj("main", "answer", config,
                                   INI_GET_FIRST_VALUE, &value);
    if (error != 0 || value == NULL) {
        fprintf(stderr, "ini_get_config_valueobj(answer) failed: %d\n", error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    answer = ini_get_int_config_value(value, 1, 0, &error);
    if (error != 0 || answer != 42) {
        fprintf(stderr, "INI integer value was %d (error %d)\n", answer, error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }

    value = NULL;
    error = ini_get_config_valueobj("main", "name", config,
                                   INI_GET_FIRST_VALUE, &value);
    if (error != 0 || value == NULL) {
        fprintf(stderr, "ini_get_config_valueobj(name) failed: %d\n", error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    name = ini_get_string_config_value(value, &error);
    if (error != 0 || name == NULL || strcmp(name, "ding-libs") != 0) {
        fprintf(stderr, "INI string value was unexpected (error %d)\n", error);
        free(name);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }

    free(name);
    ini_config_destroy(config);
    ini_config_file_destroy(file_ctx);
    return 0;
}

int main(void)
{
    if (test_dhash() != 0 || test_ini_config() != 0) {
        return EXIT_FAILURE;
    }
    puts("ding-libs public API test passed");
    return EXIT_SUCCESS;
}
