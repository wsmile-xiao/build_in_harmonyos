#include <stdio.h>
#include <stdlib.h>

#include "libmpeg3.h"

int main(void) {
    const char *probe_path = "libmpeg3-invalid-probe.mpg";
    FILE *probe;
    int error = 0;
    mpeg3_t *stream;

    if (mpeg3_major() != 1 || mpeg3_minor() != 8 || mpeg3_release() != 0) {
        fprintf(stderr, "unexpected libmpeg3 version\n");
        return 1;
    }

    probe = fopen(probe_path, "wb");
    if (!probe) {
        fprintf(stderr, "unable to create MPEG probe input\n");
        return 1;
    }
    fputs("not an MPEG stream\n", probe);
    fclose(probe);

    if (mpeg3_check_sig((char *)probe_path) != 0) {
        fprintf(stderr, "invalid input was accepted as MPEG\n");
        remove(probe_path);
        return 1;
    }

    stream = mpeg3_open((char *)probe_path, &error);
    remove(probe_path);
    if (stream != NULL || error == 0) {
        fprintf(stderr, "invalid MPEG input was not rejected\n");
        if (stream != NULL) {
            mpeg3_close(stream);
        }
        return 1;
    }

    printf("libmpeg3 OHOS/aarch64 consumer decode probe passed\n");
    return 0;
}
