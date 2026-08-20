#include <stdio.h>
#include <stdlib.h>

/*
 * Consumer test for gnustep-make 2.9.2.
 *
 * Executes the installed gnustep-config command (found via PATH injected by
 * the Conan run environment) and requires a zero exit status with non-empty
 * output for the three core interfaces. Any failure makes the test return
 * non-zero so CI's destructive L1e check can verify the test genuinely
 * depends on the packaged binary.
 */
static int check_config(const char *args, const char *outfile)
{
    char cmd[1024];
    int rc;

    snprintf(cmd, sizeof(cmd), "gnustep-config %s > %s 2>&1", args, outfile);
    rc = system(cmd);
    if (rc != 0) {
        return 0;
    }
    {
        FILE *f = fopen(outfile, "rb");
        int nonempty = 0;
        if (f) {
            nonempty = (fgetc(f) != EOF);
            fclose(f);
        }
        remove(outfile);
        return nonempty;
    }
}

int main(void)
{
    int failures = 0;

    if (!check_config("--variable=GNUSTEP_MAKEFILES", "out_makefiles.txt")) {
        fprintf(stderr, "FAIL: gnustep-config --variable=GNUSTEP_MAKEFILES\n");
        failures++;
    }
    if (!check_config("--variable=GNUSTEP_CONFIG_FILE", "out_config.txt")) {
        fprintf(stderr, "FAIL: gnustep-config --variable=GNUSTEP_CONFIG_FILE\n");
        failures++;
    }
    if (!check_config("--objc-flags", "out_objcflags.txt")) {
        fprintf(stderr, "FAIL: gnustep-config --objc-flags\n");
        failures++;
    }

    if (failures > 0) {
        fprintf(stderr, "gnustep-config consumer test: %d failure(s)\n", failures);
        return 1;
    }
    printf("gnustep-config consumer test: OK\n");
    return 0;
}
