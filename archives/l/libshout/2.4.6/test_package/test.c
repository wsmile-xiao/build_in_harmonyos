/* test_libshout.c — L1 smoke test for libshout API.
 * Substantively exercises: shout_init(), shout_new(), shout_set_*(),
 * shout_get_*, shout_version(), shout_get_error(), shout_free().
 * No network connection is made (shout_connect is not called). */
#include <shout/shout.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    int major = 0, minor = 0, patch = 0;
    const char *ver = shout_version(&major, &minor, &patch);
    printf("libshout version: %s (%d.%d.%d)\n", ver, major, minor, patch);

    shout_init();

    shout_t *sh = shout_new();
    if (!sh) {
        fprintf(stderr, "FAIL: shout_new() returned NULL\n");
        return 1;
    }

    /* Configure host/port/protocol/format without connecting. */
    if (shout_set_host(sh, "localhost") != SHOUTERR_SUCCESS) {
        fprintf(stderr, "FAIL: shout_set_host: %s\n", shout_get_error(sh));
        shout_free(sh);
        shout_shutdown();
        return 1;
    }
    if (shout_set_port(sh, 8000) != SHOUTERR_SUCCESS) {
        fprintf(stderr, "FAIL: shout_set_port: %s\n", shout_get_error(sh));
        shout_free(sh);
        shout_shutdown();
        return 1;
    }
    if (shout_set_protocol(sh, SHOUT_PROTOCOL_HTTP) != SHOUTERR_SUCCESS) {
        fprintf(stderr, "FAIL: shout_set_protocol: %s\n", shout_get_error(sh));
        shout_free(sh);
        shout_shutdown();
        return 1;
    }
    if (shout_set_format(sh, SHOUT_FORMAT_OGG) != SHOUTERR_SUCCESS) {
        fprintf(stderr, "FAIL: shout_set_format: %s\n", shout_get_error(sh));
        shout_free(sh);
        shout_shutdown();
        return 1;
    }
    if (shout_set_agent(sh, "libshout-conan-test/2.4.6") != SHOUTERR_SUCCESS) {
        fprintf(stderr, "FAIL: shout_set_agent: %s\n", shout_get_error(sh));
        shout_free(sh);
        shout_shutdown();
        return 1;
    }

    /* Verify the configured values round-trip correctly. */
    const char *host = shout_get_host(sh);
    unsigned short port = shout_get_port(sh);
    const char *agent = shout_get_agent(sh);
    if (strcmp(host, "localhost") != 0) {
        fprintf(stderr, "FAIL: get_host mismatch: %s\n", host);
        shout_free(sh);
        shout_shutdown();
        return 1;
    }
    if (port != 8000) {
        fprintf(stderr, "FAIL: get_port mismatch: %u\n", port);
        shout_free(sh);
        shout_shutdown();
        return 1;
    }
    if (strcmp(agent, "libshout-conan-test/2.4.6") != 0) {
        fprintf(stderr, "FAIL: get_agent mismatch: %s\n", agent);
        shout_free(sh);
        shout_shutdown();
        return 1;
    }

    /* Should report unconnected. */
    if (shout_get_connected(sh) != SHOUTERR_UNCONNECTED) {
        fprintf(stderr, "FAIL: expected SHOUTERR_UNCONNECTED\n");
        shout_free(sh);
        shout_shutdown();
        return 1;
    }

    shout_free(sh);
    shout_shutdown();

    printf("test libshout 2.4.6: OK\n");
    return 0;
}
