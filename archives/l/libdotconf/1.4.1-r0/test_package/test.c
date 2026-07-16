#include <dotconf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char parsed_value[32];

static DOTCONF_CB(read_value)
{
    snprintf(parsed_value, sizeof(parsed_value), "%s", cmd->data.str);
    return NULL;
}

static const configoption_t options[] = {
    {"Greeting", ARG_STR, read_value, NULL, CTX_ALL},
    LAST_OPTION
};

int main(void)
{
    char config_path[] = "libdotconf-test.conf";
    configfile_t *config;
    FILE *file = fopen(config_path, "w");

    if (file == NULL) {
        return 1;
    }
    fputs("Greeting hello\n", file);
    fclose(file);

    config = dotconf_create(config_path, options, NULL, NONE);
    if (config == NULL) {
        remove(config_path);
        return 2;
    }
    if (dotconf_command_loop(config) == 0) {
        dotconf_cleanup(config);
        remove(config_path);
        return 3;
    }

    dotconf_cleanup(config);
    remove(config_path);
    if (strcmp(parsed_value, "hello") != 0) {
        return 4;
    }

    puts("libdotconf parse test: OK");
    return 0;
}
