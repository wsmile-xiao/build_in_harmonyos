#include <cdio/iso9660.h>
#include <cdio/udf.h>
#include <cdio/version.h>
#include <stdio.h>

int main(void) {
    if (libcdio_version_num == 0 || cdio_version_string == NULL) {
        return 1;
    }

    /* Exercise the ISO-9660 and UDF entry points without requiring a drive. */
    if (iso9660_open("/this/file/does/not/exist") != NULL) {
        return 2;
    }
    if (udf_open("/this/file/does/not/exist") != NULL) {
        return 3;
    }

    printf("libcdio %s: API test passed\n", cdio_version_string);
    return 0;
}
