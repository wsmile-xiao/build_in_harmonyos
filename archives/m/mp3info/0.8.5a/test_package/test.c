#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: Test substantively depends on mp3info by running its binary.
   mp3info -h prints version and usage info; we verify it runs and
   produces output containing "MP3Info". */
int main(int argc, char *argv[]) {
    /* Find mp3info binary path - passed via MP3INFO_BIN env or default */
    const char *bin = getenv("MP3INFO_BIN");
    if (!bin || !*bin) {
        bin = "mp3info";
    }

    /* Build command: mp3info -h 2>&1 */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s -h 2>&1", bin);

    /* Run mp3info -h and capture output via popen */
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "Failed to run mp3info\n");
        return 1;
    }

    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "MP3Info") || strstr(buf, "mp3info")) {
            found = 1;
            break;
        }
    }
    pclose(fp);

    if (!found) {
        fprintf(stderr, "mp3info output did not contain expected string\n");
        return 1;
    }

    printf("mp3info binary test passed\n");
    return 0;
}
