#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libics.h"

#define DIM0 8
#define DIM1 8
#define IMAGESIZE (DIM0 * DIM1)

/* Each successful step prints one CHECK-OK line; the test_package
   conanfile counts them for the HMBS_TEST_PACKAGE_RESULT marker. */

int main(void) {
    ICS *ip = NULL;
    Ics_DataType dt;
    int ndims = 0;
    size_t dims[ICS_MAXDIM];
    unsigned char image[IMAGESIZE];
    unsigned char check[IMAGESIZE];
    size_t i;
    const char *ver;
    Ics_Error rc;

    for (i = 0; i < IMAGESIZE; i++) {
        image[i] = (unsigned char)(i & 0xFF);
    }

    /* 1: library version available */
    ver = IcsGetLibVersion();
    if (ver == NULL || ver[0] == '\0') {
        fprintf(stderr, "IcsGetLibVersion failed\n");
        return 1;
    }
    printf("CHECK-OK: version %s\n", ver);

    /* 2: create a v1 file and describe its layout */
    rc = IcsOpen(&ip, "test_libics.ics", "w1");
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsOpen write failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    dims[0] = DIM0;
    dims[1] = DIM1;
    rc = IcsSetLayout(ip, Ics_uint8, 2, dims);
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsSetLayout failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    printf("CHECK-OK: create\n");

    /* 3: attach data, history and compression, then close (writes files) */
    rc = IcsSetData(ip, image, IMAGESIZE);
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsSetData failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    rc = IcsSetCompression(ip, IcsCompr_uncompressed, 0);
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsSetCompression failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    rc = IcsAddHistoryString(ip, "test", "hmbs-libics");
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsAddHistoryString failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    rc = IcsClose(ip);
    ip = NULL;
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsClose write failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    printf("CHECK-OK: layout\n");

    /* 4: reopen and verify layout + data round-trip */
    rc = IcsOpen(&ip, "test_libics.ics", "r");
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsOpen read failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    rc = IcsGetLayout(ip, &dt, &ndims, dims);
    if (rc != IcsErr_Ok || dt != Ics_uint8 || ndims != 2 ||
        dims[0] != DIM0 || dims[1] != DIM1) {
        fprintf(stderr, "IcsGetLayout mismatch\n");
        return 1;
    }
    if (IcsGetDataSize(ip) != IMAGESIZE) {
        fprintf(stderr, "IcsGetDataSize mismatch\n");
        return 1;
    }
    memset(check, 0, sizeof(check));
    rc = IcsGetData(ip, check, IMAGESIZE);
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsGetData failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    if (memcmp(image, check, IMAGESIZE) != 0) {
        fprintf(stderr, "data round-trip mismatch\n");
        return 1;
    }
    printf("CHECK-OK: roundtrip\n");

    /* 5: history survived the round-trip */
    {
        char history[ICS_LINE_LENGTH];
        rc = IcsGetHistoryString(ip, history, IcsWhich_First);
        if (rc != IcsErr_Ok) {
            fprintf(stderr, "IcsGetHistoryString failed: %s\n", IcsGetErrorText(rc));
            return 1;
        }
        if (strstr(history, "hmbs-libics") == NULL) {
            fprintf(stderr, "history content mismatch: %s\n", history);
            return 1;
        }
    }
    rc = IcsClose(ip);
    ip = NULL;
    if (rc != IcsErr_Ok) {
        fprintf(stderr, "IcsClose read failed: %s\n", IcsGetErrorText(rc));
        return 1;
    }
    printf("CHECK-OK: history\n");

    remove("test_libics.ics");
    remove("test_libics.ids");

    printf("test libics 1.7.0: OK (5 checks passed)\n");
    return 0;
}
