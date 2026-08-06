/* test_package/test_dmg2img.c — verify dmg2img binary functionality
 *
 * R34: test must actually use the tested package's binary.
 * This test compiles and runs dmg2img (no args → prints version+usage),
 * then checks the output for the expected version string.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    FILE *fp;
    char buf[256];
    int found = 0;

    /* Run dmg2img with no arguments — it prints version and usage */
    fp = popen("dmg2img 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: Cannot execute dmg2img\n");
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "dmg2img v1.6.7") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(fp);

    if (!found) {
        fprintf(stderr, "FAIL: dmg2img version string not found in output\n");
        return 1;
    }

    printf("PASS: dmg2img v1.6.7 binary verified\n");
    return 0;
}
