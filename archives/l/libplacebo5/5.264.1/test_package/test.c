/*
 * libplacebo5 consumer test — calls the packaged library API.
 *
 * pl_version() is a pure-CPU function (returns the library version
 * string), so it can be executed on OHOS without a GPU — unlike the
 * renderer APIs (pl_renderer_*) which need GPU/display (absent on
 * OHOS; honest environment limitation).
 */
#include <stdio.h>
#include <string.h>

#include <libplacebo/config.h>

int main(void) {
    const char *ver = pl_version();
    if (!ver || !*ver) {
        fprintf(stderr, "pl_version() returned an empty string\n");
        return 1;
    }
    printf("pl_version() = %s\n", ver);
    if (strstr(ver, "5.264.1") == NULL) {
        fprintf(stderr, "unexpected version string: %s\n", ver);
        return 1;
    }
    printf("libplacebo5 5.264.1 test: OK\n");
    return 0;
}