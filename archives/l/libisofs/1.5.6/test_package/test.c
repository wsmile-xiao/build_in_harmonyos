#include <stdio.h>
#include <stdlib.h>
#include <libisofs/libisofs.h>

int main(void) {
    int major = 0, minor = 0, micro = 0;
    int ret;

    /* Must be callable before iso_init(): runtime ABI version check */
    iso_lib_version(&major, &minor, &micro);
    if (major != iso_lib_header_version_major || minor != iso_lib_header_version_minor) {
        fprintf(stderr, "version mismatch: header %d.%d vs runtime %d.%d\n",
                iso_lib_header_version_major, iso_lib_header_version_minor, major, minor);
        return 1;
    }

    ret = iso_init();
    if (ret < 0) {
        fprintf(stderr, "iso_init() failed: %d\n", ret);
        return 1;
    }
    iso_finish();

    printf("libisofs %d.%d.%d: OK (iso_init/iso_finish/iso_lib_version)\n",
           major, minor, micro);
    return 0;
}
