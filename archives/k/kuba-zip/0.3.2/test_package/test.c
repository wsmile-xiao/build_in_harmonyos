#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "zip/zip.h"

#define ZIPNAME "test_kuba_zip.zip"
#define TESTDATA "Hello from kuba-zip test_package\0"

int main(void) {
    struct zip_t *zip = NULL;
    char *buf = NULL;
    ssize_t bufsize = 0;
    size_t buftmp = 0;

    /* Write a zip entry */
    zip = zip_open(ZIPNAME, ZIP_DEFAULT_COMPRESSION_LEVEL, 'w');
    if (zip == NULL) {
        printf("test kuba-zip 0.3.2: FAIL (zip_open write)\n");
        return 1;
    }
    if (zip_entry_open(zip, "hello.txt") != 0 ||
        zip_entry_write(zip, TESTDATA, strlen(TESTDATA)) != 0 ||
        zip_entry_close(zip) != 0) {
        printf("test kuba-zip 0.3.2: FAIL (zip_entry write)\n");
        zip_close(zip);
        return 1;
    }
    zip_close(zip);

    /* Read the entry back */
    zip = zip_open(ZIPNAME, 0, 'r');
    if (zip == NULL) {
        printf("test kuba-zip 0.3.2: FAIL (zip_open read)\n");
        return 1;
    }
    if (zip_entry_open(zip, "hello.txt") != 0) {
        printf("test kuba-zip 0.3.2: FAIL (zip_entry_open read)\n");
        zip_close(zip);
        return 1;
    }
    bufsize = zip_entry_read(zip, (void **)&buf, &buftmp);
    if (bufsize < 0 || (size_t)bufsize != strlen(TESTDATA) ||
        strncmp(buf, TESTDATA, (size_t)bufsize) != 0) {
        printf("test kuba-zip 0.3.2: FAIL (data mismatch, read=%zd)\n", bufsize);
        free(buf);
        zip_entry_close(zip);
        zip_close(zip);
        return 1;
    }
    free(buf);
    zip_entry_close(zip);
    zip_close(zip);
    remove(ZIPNAME);

    printf("test kuba-zip 0.3.2: OK (write+read roundtrip)\n");
    return 0;
}