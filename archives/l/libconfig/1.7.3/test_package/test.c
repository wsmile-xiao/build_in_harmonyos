#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libconfig.h>

int main(void) {
    config_t cfg;
    config_init(&cfg);

    const char *test_config =
        "version = \"1.0\";\n"
        "count = 5;\n"
        "name = \"test\";\n";

    if (!config_read_string(&cfg, test_config)) {
        fprintf(stderr, "config_read_string error: %s (line %d)\n",
                config_error_text(&cfg), config_error_line(&cfg));
        config_destroy(&cfg);
        return 1;
    }

    const char *name = NULL;
    int count = 0;

    if (!config_lookup_string(&cfg, "name", &name)) {
        fprintf(stderr, "No 'name' setting\n");
        config_destroy(&cfg);
        return 1;
    }

    if (!config_lookup_int(&cfg, "count", &count)) {
        fprintf(stderr, "No 'count' setting\n");
        config_destroy(&cfg);
        return 1;
    }

    printf("name=%s, count=%d\n", name, count);

    int ok = (count == 5 && strcmp(name, "test") == 0);

    config_destroy(&cfg);

    if (ok) {
        printf("test libconfig 1.7.3: OK\n");
        return 0;
    }

    printf("test libconfig 1.7.3: FAIL\n");
    return 1;
}
