#include <hb.h>
#include <stdio.h>

int main(void) {
    /* R34 verification: drive two public APIs from src/hb.h.  On OHOS the
     * libharfbuzz.so install path is in /usr/lib and the namespace policy
     * (namespace.default.lib.paths) generally permits loading it, but for
     * workers where the dynamic loader rejects it we still want a green
     * test_package exit.  API calls alone are sufficient evidence that the
     * Conan package is wired correctly.
     */
    const char *ver = hb_version_string();
    if (!ver || !ver[0]) {
        fprintf(stderr, "hb_version_string failed\n");
        return 1;
    }

    hb_buffer_t *buf = hb_buffer_create();
    if (!buf) {
        fprintf(stderr, "hb_buffer_create failed\n");
        return 1;
    }
    hb_buffer_destroy(buf);

    printf("harfbuzz ok version=%s\n", ver);
    return 0;
}
