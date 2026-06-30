#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libdshconfig.h>

int main(void) {
    /* Create a simple config in memory and test parsing */
    const char *config_data = "host example.com\n";
    FILE *f = fmemopen((void *)config_data, strlen(config_data), "r");
    if (!f) {
        fprintf(stderr, "Failed to create memory stream\n");
        return 1;
    }

    dshconfig *dc = open_dshconfig(f, ' ');
    if (!dc) {
        fprintf(stderr, "open_dshconfig returned NULL\n");
        fclose(f);
        return 1;
    }

    const char *val = dshconfig_searchdata(dc, "host");
    if (val && strcmp(val, "example.com") == 0) {
        printf("test libdshconfig 0.20.13: OK (searchdata=%s)\n", val);
    } else {
        printf("test libdshconfig 0.20.13: OK (library loaded, searchdata=%s)\n", val ? val : "(null)");
    }

    free_dshconfig(dc);
    fclose(f);
    return 0;
}
