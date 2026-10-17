#include <stdio.h>
#include <string.h>
#include <trio.h>

int main(void) {
    char buf[64];
    int n = trio_snprintf(buf, sizeof(buf), "%s %d.%d", "trio", 1, 16);
    if (n < 0 || (size_t)n >= sizeof(buf)) {
        printf("trio_snprintf failed: n=%d\n", n);
        return 1;
    }
    if (strncmp(buf, "trio 1.16", 9) != 0) {
        printf("unexpected output: %s\n", buf);
        return 1;
    }
    printf("trio_snprintf OK: %s\n", buf);
    return 0;
}