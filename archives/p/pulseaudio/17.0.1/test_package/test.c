#include <stdio.h>
#include <pulse/pulseaudio.h>
#include <pulse/simple.h>

int main(void) {
    const char *ver = pa_get_library_version();
    if (ver == NULL) {
        fprintf(stderr, "FAIL: pa_get_library_version returned NULL\n");
        return 1;
    }
    printf("pulseaudio library version: %s\n", ver);

    /* Verify the version starts with 17 */
    if (ver[0] != '1' || ver[1] != '7') {
        fprintf(stderr, "FAIL: unexpected version %s\n", ver);
        return 1;
    }

    printf("test pulseaudio 17.0: OK\n");
    return 0;
}
