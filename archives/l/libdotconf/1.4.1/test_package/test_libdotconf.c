#include <dotconf.h>

#include <stdio.h>
#include <string.h>

static char parsed_name[64];
static long parsed_count;
static long parsed_enabled;
static double parsed_ratio;
static int parsed_item_count;
static char parsed_items[3][32];
static int no_args_count;
static int callback_count;

static DOTCONF_CB(read_name)
{
    const char *name = cmd->data.str != NULL ? cmd->data.str : "";

    snprintf(parsed_name, sizeof(parsed_name), "%s", name);
    callback_count++;
    return NULL;
}

static DOTCONF_CB(read_count)
{
    parsed_count = cmd->data.value;
    callback_count++;
    return NULL;
}

static DOTCONF_CB(read_enabled)
{
    parsed_enabled = cmd->data.value;
    callback_count++;
    return NULL;
}

static DOTCONF_CB(read_ratio)
{
    parsed_ratio = cmd->data.dvalue;
    callback_count++;
    return NULL;
}

static DOTCONF_CB(read_items)
{
    int index;

    parsed_item_count = cmd->arg_count;
    for (index = 0; index < cmd->arg_count && index < 3; index++) {
        const char *item =
            cmd->data.list[index] != NULL ? cmd->data.list[index] : "";

        snprintf(
            parsed_items[index],
            sizeof(parsed_items[index]),
            "%s",
            item
        );
    }
    callback_count++;
    return NULL;
}

static DOTCONF_CB(read_no_args)
{
    (void)cmd;
    (void)ctx;
    no_args_count++;
    callback_count++;
    return NULL;
}

static const configoption_t options[] = {
    {"Name", ARG_STR, read_name, NULL, CTX_ALL},
    {"Count", ARG_INT, read_count, NULL, CTX_ALL},
    {"Enabled", ARG_TOGGLE, read_enabled, NULL, CTX_ALL},
    {"Ratio", ARG_DOUBLE, read_ratio, NULL, CTX_ALL},
    {"Items", ARG_LIST, read_items, NULL, CTX_ALL},
    {"NoArgs", ARG_NONE, read_no_args, NULL, CTX_ALL},
    LAST_OPTION
};

int main(void)
{
    char config_path[] = "libdotconf-consumer.conf";
    configfile_t *config = NULL;
    FILE *file;
    int checks = 0;
    int failed = 0;
    int parse_result;

#define CHECK(condition, message)                                             \
    do {                                                                      \
        checks++;                                                             \
        if (!(condition)) {                                                   \
            fprintf(stderr, "check %d failed: %s\n", checks, message);       \
            failed = 1;                                                       \
            goto cleanup;                                                     \
        }                                                                     \
    } while (0)

    file = fopen(config_path, "w");
    if (file == NULL) {
        fputs("unable to create test configuration\n", stderr);
        return 1;
    }

    fputs(
        "name \"HarmonyOS PC\"\n"
        "COUNT 42\n"
        "enabled yes\n"
        "Ratio 3.5\n"
        "Items alpha \"beta gamma\" delta\n"
        "NoArgs\n",
        file
    );
    fclose(file);

    config = dotconf_create(config_path, options, NULL, CASE_INSENSITIVE);
    CHECK(config != NULL, "configuration object is created");
    /* libdotconf 1.4.1 documents zero as failure and one as success. */
    parse_result = dotconf_command_loop(config);
    CHECK(parse_result == 1, "configuration parser returns its success value");
    CHECK(callback_count == 6, "all six callbacks run exactly once");
    CHECK(strcmp(parsed_name, "HarmonyOS PC") == 0, "string value matches");
    CHECK(parsed_count == 42, "integer value matches");
    CHECK(parsed_enabled == 1, "toggle value matches");
    CHECK(parsed_ratio > 3.499 && parsed_ratio < 3.501, "double value matches");
    CHECK(parsed_item_count == 3, "list contains three values");
    CHECK(strcmp(parsed_items[0], "alpha") == 0, "first list value matches");
    CHECK(strcmp(parsed_items[1], "beta gamma") == 0, "quoted list value matches");
    CHECK(strcmp(parsed_items[2], "delta") == 0, "third list value matches");
    CHECK(no_args_count == 1, "no-argument callback runs");

cleanup:
    if (config != NULL) {
        dotconf_cleanup(config);
    }
    remove(config_path);

    if (failed) {
        return 2;
    }

    printf("libdotconf consumer tests: %d/12 passed\n", checks);
    return 0;
}
